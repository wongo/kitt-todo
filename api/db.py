from __future__ import annotations

import logging
import os
from typing import Final

import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: Final[str | None] = os.getenv("DATABASE_URL")
NEON_SCHEMA: Final[str] = os.getenv("NEON_SCHEMA", "kitt_todo")

pool: asyncpg.Pool | None = None
_log = logging.getLogger("kitt-todo")


async def _init_connection(conn: asyncpg.Connection) -> None:
    await conn.execute(f'SET search_path TO "{NEON_SCHEMA}"')


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
        init=_init_connection,
    )
    _log.warning("create_pool: pool created")
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


async def init_schema() -> None:
    _log.warning("INIT_SCHEMA starting...")
    db_pool = await get_pool()
    async with db_pool.acquire() as conn:
        _log.warning("init_schema: acquired connection")
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
        sp = await conn.fetchval("SHOW search_path")
        _log.warning("init_schema: search_path = %s", sp)