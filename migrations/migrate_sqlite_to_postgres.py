#!/usr/bin/env python3
"""One-time migration from local SQLite to the Docker Compose Postgres DB."""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from psycopg import sql


TABLES_IN_ORDER = ("users", "board_columns", "tasks", "comments")
SEQUENCE_TABLES = ("users", "board_columns")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy data from tasks.db into the configured PostgreSQL database."
    )
    parser.add_argument(
        "--sqlite-path",
        default="tasks.db",
        help="Path to the SQLite database file. Default: %(default)s",
    )
    parser.add_argument(
        "--postgres-url",
        default=None,
        help="Optional PostgreSQL connection string. Falls back to env vars if omitted.",
    )
    parser.add_argument(
        "--wait-seconds",
        type=int,
        default=30,
        help="How long to wait for PostgreSQL to accept connections. Default: %(default)s",
    )
    return parser.parse_args()


def build_postgres_url(explicit_url: str | None) -> str:
    database_url = explicit_url or os.environ.get("DATABASE_URL")
    if database_url:
        return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    user = os.environ.get("POSTGRES_USER", "taskboard")
    password = os.environ.get("POSTGRES_PASSWORD", "taskboard")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "taskboard")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def require_sqlite_file(sqlite_path: Path) -> None:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")
    if not sqlite_path.is_file():
        raise FileNotFoundError(f"SQLite path is not a file: {sqlite_path}")


def get_sqlite_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    if not rows:
        raise RuntimeError(f"SQLite table '{table}' was not found.")
    return [row["name"] for row in rows]


def get_postgres_columns(conn: psycopg.Connection, table: str) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table,),
        )
        rows = cur.fetchall()

    if not rows:
        raise RuntimeError(
            f"Postgres table '{table}' was not found. Start the app once so it creates tables first."
        )
    return [row[0] for row in rows]


def get_postgres_boolean_columns(conn: psycopg.Connection, table: str) -> set[str]:
    """Return the set of column names that are boolean-typed in PostgreSQL."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
              AND data_type = 'boolean'
            """,
            (table,),
        )
        return {row[0] for row in cur.fetchall()}


def fetch_sqlite_rows(
    conn: sqlite3.Connection, table: str, columns: list[str]
) -> list[tuple]:
    column_list = ", ".join(columns)
    return [
        tuple(row[column] for column in columns)
        for row in conn.execute(f"SELECT {column_list} FROM {table} ORDER BY rowid")
    ]


def build_upsert_sql(table: str, columns: list[str], bool_cols: set[str] | None = None) -> str:
    column_list = ", ".join(columns)
    bool_cols = bool_cols or set()
    placeholders = ", ".join(
        "%s::boolean" if col in bool_cols else "%s"
        for col in columns
    )
    update_columns = [column for column in columns if column != "id"]

    if update_columns:
        update_set = ", ".join(f"{column} = EXCLUDED.{column}" for column in update_columns)
        conflict_clause = f"DO UPDATE SET {update_set}"
    else:
        conflict_clause = "DO NOTHING"

    return (
        f"INSERT INTO {table} ({column_list}) VALUES ({placeholders}) "
        f"ON CONFLICT (id) {conflict_clause}"
    )


def _cast_row(row: tuple, columns: list[str], bool_cols: set[str]) -> tuple:
    """Convert SQLite 0/1 integers to Python bools for PostgreSQL boolean columns."""
    if not bool_cols:
        return row
    return tuple(
        bool(val) if col in bool_cols and val is not None else val
        for val, col in zip(row, columns)
    )


def _parse_legacy_timestamp(value: object) -> str | None:
    """Normalize legacy SQLite timestamps to stable UTC ISO-8601 strings."""
    if value in (None, ""):
        return None

    if isinstance(value, datetime):
        dt = value
    else:
        raw = str(value).strip()
        if raw.endswith("Z"):
            raw = f"{raw[:-1]}+00:00"
        dt = datetime.fromisoformat(raw)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)
    return dt.isoformat()


def _normalize_row(table: str, row: tuple, columns: list[str]) -> tuple:
    """Repair legacy values while copying from SQLite to PostgreSQL."""
    values = dict(zip(columns, row))

    if table in {"tasks", "comments"} and "created_at" in values:
        normalized_created_at = _parse_legacy_timestamp(values["created_at"])
        if normalized_created_at is not None:
            values["created_at"] = normalized_created_at

            if table == "tasks":
                created_dt = datetime.fromisoformat(normalized_created_at)
                if "month" in values:
                    values["month"] = created_dt.month
                if "year" in values:
                    values["year"] = created_dt.year

    return tuple(values[column] for column in columns)


def migrate_table(
    sqlite_conn: sqlite3.Connection,
    pg_conn: psycopg.Connection,
    table: str,
) -> int:
    sqlite_columns = get_sqlite_columns(sqlite_conn, table)
    postgres_columns = get_postgres_columns(pg_conn, table)
    shared_columns = [column for column in sqlite_columns if column in postgres_columns]

    if not shared_columns:
        raise RuntimeError(f"No shared columns found for table '{table}'.")

    rows = fetch_sqlite_rows(sqlite_conn, table, shared_columns)
    if not rows:
        return 0

    rows = [_normalize_row(table, row, shared_columns) for row in rows]

    bool_cols = get_postgres_boolean_columns(pg_conn, table)
    if bool_cols:
        rows = [_cast_row(r, shared_columns, bool_cols) for r in rows]

    sql = build_upsert_sql(table, shared_columns, bool_cols)
    with pg_conn.cursor() as cur:
        cur.executemany(sql, rows)
    return len(rows)


def reset_sequence(pg_conn: psycopg.Connection, table: str) -> None:
    with pg_conn.cursor() as cur:
        cur.execute(
            sql.SQL(
                """
            SELECT setval(
                pg_get_serial_sequence(%s, 'id'),
                COALESCE((SELECT MAX(id) FROM public.{table}), 1),
                (SELECT COUNT(*) > 0 FROM public.{table})
            )
            """
            ).format(table=sql.Identifier(table)),
            (f"public.{table}",),
        )


def print_summary(inserted_counts: dict[str, int]) -> None:
    print("Migration complete.")
    for table in TABLES_IN_ORDER:
        print(f"  {table}: {inserted_counts.get(table, 0)} rows processed")


def connect_with_retry(postgres_url: str, wait_seconds: int) -> psycopg.Connection:
    deadline = time.monotonic() + max(wait_seconds, 0)
    last_error: Exception | None = None

    while True:
        try:
            return psycopg.connect(postgres_url)
        except psycopg.OperationalError as exc:
            last_error = exc
            if time.monotonic() >= deadline:
                break
            time.sleep(1)

    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "taskboard")
    raise RuntimeError(
        "Could not connect to PostgreSQL. "
        f"Checked host={host} port={port} db={db}. "
        "Make sure the `postgres` service is running with `docker compose up -d postgres`, "
        "and if you changed the published port in Compose, export `POSTGRES_PORT` before running this script."
    ) from last_error


def main() -> int:
    args = parse_args()
    sqlite_path = Path(args.sqlite_path).resolve()
    postgres_url = build_postgres_url(args.postgres_url)

    try:
        require_sqlite_file(sqlite_path)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    inserted_counts: dict[str, int] = {}

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row

    try:
        with connect_with_retry(postgres_url, args.wait_seconds) as pg_conn:
            for table in TABLES_IN_ORDER:
                inserted_counts[table] = migrate_table(sqlite_conn, pg_conn, table)

            for table in SEQUENCE_TABLES:
                reset_sequence(pg_conn, table)

            pg_conn.commit()
    except Exception as exc:
        print(f"Migration failed: {exc}", file=sys.stderr)
        return 1
    finally:
        sqlite_conn.close()

    print_summary(inserted_counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
