from __future__ import annotations

import logging
import traceback
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger("kitt-todo")


try:
    from ..db import NEON_SCHEMA, get_pool
except ImportError:  # pragma: no cover
    from db import NEON_SCHEMA, get_pool

router = APIRouter(prefix="/reminders", tags=["reminders"])


class ReminderCreate(BaseModel):
    task_id: str
    remind_at: str  # ISO8601 timestamp
    chat_id: str | None = None


class ReminderSent(BaseModel):
    sent: bool = True


@router.post("")
async def create_reminder(payload: ReminderCreate) -> dict[str, Any]:
    """POST /api/reminders - create a reminder"""
    logger.warning("CREATE_REMINDER called with task_id=%s", payload.task_id)
    try:
        pool = await get_pool()
        logger.warning("Pool acquired")
        async with pool.acquire() as conn:
            logger.warning("Connection acquired")
            task_row = await conn.fetchrow(
                f'SELECT id FROM "{NEON_SCHEMA}".tasks WHERE id = $1',
                payload.task_id,
            )
            logger.warning("Task check result: %s", task_row)
            if not task_row:
                raise HTTPException(status_code=404, detail="Task not found")

            remind_dt = datetime.fromisoformat(payload.remind_at.replace("Z", "+00:00"))
            logger.warning("Parsed datetime: %s", remind_dt)
            row = await conn.fetchrow(
                """
                INSERT INTO reminders (task_id, remind_at, chat_id)
                VALUES ($1, $2, $3)
                RETURNING id, task_id, remind_at::text, chat_id, sent
                """,
                payload.task_id,
                remind_dt,
                payload.chat_id,
            )
            logger.warning("Insert result: %s", dict(row))
            return dict(row)
    except HTTPException:
        logger.warning("HTTPException raised")
        raise
    except Exception as exc:
        logger.error("create_reminder EXCEPTION: %s\n%s", exc, traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/due")
async def get_due_reminders(now: str | None = Query(default=None)) -> list[dict[str, Any]]:
    """GET /api/reminders/due?now=... - get reminders due before now"""
    logger.warning("GET_DUE_REMINDERS called, now=%s", now)
    try:
        pool = await get_pool()
        logger.warning("Pool acquired in due")
        if now is None:
            now_val = datetime.now(timezone.utc).replace(microsecond=0)
        else:
            now_val = datetime.fromisoformat(now.replace("Z", "+00:00"))
        logger.warning("now_val=%s", now_val)
        async with pool.acquire() as conn:
            logger.warning("Connection acquired in due")
            rows = await conn.fetch(
                """
                SELECT r.id, r.task_id, r.remind_at::text, r.chat_id, r.sent, t.title
                FROM reminders r
                JOIN tasks t ON t.id = r.task_id
                WHERE r.sent = FALSE AND r.remind_at <= $1 AND t.is_done = FALSE
                ORDER BY r.remind_at
                """,
                now_val,
            )
            logger.warning("Query result: %d rows", len(rows))
            return [dict(row) for row in rows]
    except Exception as exc:
        logger.error("get_due_reminders EXCEPTION: %s\n%s", exc, traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{reminder_id}/sent")
async def mark_reminder_sent(reminder_id: str) -> dict[str, Any]:
    """POST /api/reminders/{id}/sent - mark a reminder as sent"""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE reminders SET sent = TRUE WHERE id = $1
                RETURNING id, task_id, remind_at::text, chat_id, sent
                """,
                reminder_id,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Reminder not found")
            return dict(row)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("mark_reminder_sent EXCEPTION: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error")