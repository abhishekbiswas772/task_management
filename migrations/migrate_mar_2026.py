"""
Seed script — Internal Fuso Projects MAR 2026
Migrates all tasks from the March 2026 board into the local SQLite database
(month=3, year=2026).

Run:  python3 migrate_mar_2026.py
"""

import os
import sqlite3
import uuid
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "tasks.db")

# ── Task data extracted from screenshot ───────────────────────────────
# (title, column_name, priority)

TASKS = [
    # ── TODO (8 tasks) ────────────────────────────────────────────────
    ("Fix the DTC UAT Application",                          "TODO", "High"),
    ("Fix the DTC Dev application",                          "TODO", "High"),
    ("Development wrap up for QMPQR Chatbot",                "TODO", "High"),
    ("Data Ingestions for QMPQR Chatbot",                    "TODO", "High"),
    ("Public Dataset explorations for Cubeapps and discussions", "TODO", "Medium"),
    ("Email to DTC Client for UAT rollout",                  "TODO", "High"),
    ("Domain binding for Cubeapps",                          "TODO", "Medium"),
    ("reports db dump files for report generations",         "TODO", "Medium"),
]


# ── Helpers ───────────────────────────────────────────────────────────

def init_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            description TEXT DEFAULT '',
            column_name TEXT DEFAULT 'TODO',
            month       INTEGER NOT NULL,
            year        INTEGER NOT NULL,
            priority    TEXT DEFAULT 'Medium',
            due_date    TEXT,
            created_at  TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id         TEXT PRIMARY KEY,
            task_id    TEXT NOT NULL,
            text       TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
        )
    """)
    conn.commit()


def already_seeded(conn: sqlite3.Connection) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE month=3 AND year=2026"
    ).fetchone()[0]


def seed(conn: sqlite3.Connection):
    base = datetime(2026, 3, 23, 9, 0, 0)
    step = timedelta(minutes=30)
    rows = []

    for i, (title, column, priority) in enumerate(TASKS):
        rows.append((
            str(uuid.uuid4()),
            title, "",
            column, 3, 2026,
            priority, None,
            (base + step * i).isoformat(),
        ))

    conn.executemany(
        """INSERT INTO tasks
           (id, title, description, column_name, month, year, priority, due_date, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()
    return len(rows)


# ── Main ──────────────────────────────────────────────────────────────

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    init_db(conn)

    existing = already_seeded(conn)
    if existing:
        print(f"⚠  March 2026 already has {existing} task(s) in the DB.")
        ans = input("   Re-seed anyway? This will ADD on top (y/N): ").strip().lower()
        if ans != "y":
            print("Aborted.")
            conn.close()
            return

    count = seed(conn)
    conn.close()
    print(f"✅  Inserted {count} tasks for March 2026.")
    print("   Open http://localhost:5000 — March 2026 is the default month.")


if __name__ == "__main__":
    main()
