from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

try:
    from ..db import NEON_SCHEMA, get_pool
except ImportError:  # pragma: no cover
    from db import NEON_SCHEMA, get_pool


router = APIRouter(prefix="/tasks", tags=["tasks"])

Priority = Literal["high", "medium", "low"]
RepeatType = Literal["daily", "weekly"]
Status = Literal["pending", "done"]


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    priority: Priority = "medium"
    due_date: date | None = None
    due_time: time | None = None
    category: str | None = None
    repeat_type: RepeatType | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    priority: Priority | None = None
    due_date: date | None = None
    due_time: time | None = None
    category: str | None = None
    repeat_type: RepeatType | None = None
    is_done: bool | None = None


def _task_dict(record) -> dict:
    task = dict(record)
    if isinstance(task.get("due_time"), time):
        task["due_time"] = task["due_time"].strftime("%H:%M")
    return task


@router.get("")
async def list_tasks(
    status: Status | None = Query(default=None),
    category: str | None = Query(default=None),
    priority: Priority | None = Query(default=None),
) -> list[dict]:
    where = ["1=1"]
    values: list[object] = []
    if status == "pending":
        where.append("is_done = FALSE")
    elif status == "done":
        where.append("is_done = TRUE")
    if category:
        values.append(category)
        where.append(f"category = ${len(values)}")
    if priority:
        values.append(priority)
        where.append(f"priority = ${len(values)}")

    query = f"""
        SELECT *
        FROM "{NEON_SCHEMA}".tasks
        WHERE {" AND ".join(where)}
        ORDER BY
            CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
            COALESCE(due_date, DATE '9999-12-31'),
            COALESCE(due_time, TIME '23:59:59'),
            created_at
    """
    db_pool = await get_pool()
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(query, *values)
    return [_task_dict(row) for row in rows]


@router.post("", status_code=201)
async def create_task(payload: TaskCreate) -> dict:
    db_pool = await get_pool()
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""
            INSERT INTO "{NEON_SCHEMA}".tasks (
                title, priority, due_date, due_time, category, repeat_type, next_due
            )
            VALUES ($1, $2, $3, $4, $5, $6, $3)
            RETURNING *
            """,
            payload.title.strip(),
            payload.priority,
            payload.due_date,
            payload.due_time,
            payload.category,
            payload.repeat_type,
        )
    return _task_dict(row)


@router.get("/{task_id}")
async def get_task(task_id: str) -> dict:
    db_pool = await get_pool()
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(f'SELECT * FROM "{NEON_SCHEMA}".tasks WHERE id = $1', task_id)
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_dict(row)


@router.put("/{task_id}")
async def update_task(task_id: str, payload: TaskUpdate) -> dict:
    updates = payload.model_dump(exclude_unset=True)
    if "title" in updates and updates["title"] is not None:
        updates["title"] = updates["title"].strip()
    if not updates:
        return await get_task(task_id)

    assignments: list[str] = []
    values: list[object] = []
    for column, value in updates.items():
        values.append(value)
        assignments.append(f"{column} = ${len(values)}")
    if "due_date" in updates:
        assignments.append("next_due = due_date")
    values.append(task_id)

    db_pool = await get_pool()
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""
            UPDATE "{NEON_SCHEMA}".tasks
            SET {", ".join(assignments)}
            WHERE id = ${len(values)}
            RETURNING *
            """,
            *values,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_dict(row)


@router.delete("/{task_id}")
async def delete_task(task_id: str) -> dict[str, bool]:
    db_pool = await get_pool()
    async with db_pool.acquire() as conn:
        result = await conn.execute(f'DELETE FROM "{NEON_SCHEMA}".tasks WHERE id = $1', task_id)
    deleted = result.endswith("1")
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"deleted": True}


@router.post("/{task_id}/done")
async def mark_task_done(task_id: str) -> dict:
    db_pool = await get_pool()
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            task = await conn.fetchrow(f'SELECT * FROM "{NEON_SCHEMA}".tasks WHERE id = $1 FOR UPDATE', task_id)
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            done_at = datetime.now(timezone.utc)
            done_task = await conn.fetchrow(
                f"""
                UPDATE "{NEON_SCHEMA}".tasks
                SET is_done = TRUE, done_at = $1
                WHERE id = $2
                RETURNING *
                """,
                done_at,
                task_id,
            )

            if task["repeat_type"]:
                due_date = task["due_date"]
                next_due = None
                if due_date is not None:
                    delta = timedelta(days=1 if task["repeat_type"] == "daily" else 7)
                    due_date = due_date + delta
                    next_due = due_date
                await conn.execute(
                    f"""
                    INSERT INTO "{NEON_SCHEMA}".tasks (
                        title, priority, category, due_date, due_time, repeat_type, created_at, next_due
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    task["title"],
                    task["priority"],
                    task["category"],
                    due_date,
                    task["due_time"],
                    task["repeat_type"],
                    task["created_at"],
                    next_due,
                )

    return _task_dict(done_task)
