from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator, Final

import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: Final[str | None] = os.getenv("DATABASE_URL")
NEON_SCHEMA: Final[str] = os.getenv("NEON_SCHEMA", "kitt_todo")

pool: asyncpg.Pool | None = None
_log = logging.getLogger("kitt-todo")


async def create_pool() -> asyncpg.Pool:
    global pool
    if pool is not None:
        return pool
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required")
    _log.warning("create_pool: connecting to Neon...")
    pool = await asyncpg.create_pool(
        dsn=DATABASE_URL,
        min_size=1,
        max_size=10,
        command_timeout=60,
    )
    _log.warning("create_pool: pool created, min=1 max=10")
    return pool


async def get_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        await create_pool()
    return pool


async def close_pool() -> None:
    global pool
    if pool is not None:
        await pool.close()
        pool = None


@asynccontextmanager
async def acquire_conn() -> AsyncIterator[asyncpg.Connection]:
    """Acquire a connection and set search_path to NEON_SCHEMA, always."""
    p = await get_pool()
    conn = await p.acquire()
    try:
        await conn.execute(f'SET search_path TO "{NEON_SCHEMA}"')
        yield conn
    finally:
        await p.release(conn)


async def init_schema() -> None:
    _log.warning("INIT_SCHEMA starting...")
    async with acquire_conn() as conn:
        _log.warning("init_schema: acquired connection with correct search_path")
        await conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{NEON_SCHEMA}"')
        _log.warning("init_schema: schema created")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
        await conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS "{NEON_SCHEMA}".tasks (
                id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
                title TEXT NOT NULL,
                priority TEXT DEFAULT 'medium' CHECK (priority IN ('high', 'medium', 'low')),
                category TEXT,
                due_date DATE,
                due_time TIME,
                repeat_type TEXT CHECK (repeat_type IS NULL OR repeat_type IN ('daily', 'weekly')),
                is_done BOOLEAN DEFAULT FALSE,
                done_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                next_due DATE,
                notes TEXT
            )
            """
        )
        await conn.execute(f'ALTER TABLE "{NEON_SCHEMA}".tasks ADD COLUMN IF NOT EXISTS notes TEXT')
        await conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS "{NEON_SCHEMA}".categories (
                id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
                name TEXT UNIQUE NOT NULL,
                icon TEXT DEFAULT '📂'
            )
            """
        )
        await conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS "{NEON_SCHEMA}".reminders (
                id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
                task_id TEXT NOT NULL,
                remind_at TIMESTAMPTZ NOT NULL,
                chat_id TEXT,
                sent BOOLEAN DEFAULT FALSE
            )
            """
        )
        await conn.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_reminders_due
            ON "{NEON_SCHEMA}".reminders (remind_at)
            """
        )
        _log.warning("init_schema: all tables verified")