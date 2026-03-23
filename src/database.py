"""
Async SQLAlchemy engine + session management.
All API routes use get_session() for async DB access.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

engine: create_async_engine | None = None
AsyncSessionLocal: async_sessionmaker | None = None


class Base(DeclarativeBase):
    pass


def init_engine(database_url: str, echo: bool = False) -> None:
    global engine, AsyncSessionLocal
    engine = create_async_engine(
        database_url,
        echo=echo,
        connect_args={"check_same_thread": False},
    )
    AsyncSessionLocal = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session; auto-commit on success, rollback on error."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_tables() -> None:
    """Create all ORM-mapped tables and run incremental column migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _migrate_columns(conn)


async def _migrate_columns(conn) -> None:
    """Add new columns to existing tables without losing data."""
    task_cols = [
        ("created_by", "INTEGER"),
        ("tags",       "TEXT DEFAULT ''"),
    ]
    comment_cols = [
        ("user_id",  "INTEGER"),
        ("username", "TEXT DEFAULT ''"),
    ]

    for col, defn in task_cols:
        try:
            await conn.execute(text(f"ALTER TABLE tasks ADD COLUMN {col} {defn}"))
        except Exception:
            pass

    for col, defn in comment_cols:
        try:
            await conn.execute(text(f"ALTER TABLE comments ADD COLUMN {col} {defn}"))
        except Exception:
            pass
