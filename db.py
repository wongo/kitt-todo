from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Iterator

from config import BACKUP_JSON_PATH, DATA_DIR, DB_PATH


PRIORITIES = {"high", "medium", "low"}
REPEAT_TYPES = {"daily", "weekly"}


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()


def new_id() -> str:
    return uuid.uuid4().hex[:8]


def ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    ensure_data_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                priority TEXT DEFAULT 'medium',
                category TEXT,
                due_date TEXT,
                due_time TEXT,
                repeat_type TEXT,
                is_done INTEGER DEFAULT 0,
                done_at TEXT,
                created_at TEXT NOT NULL,
                next_due TEXT,
                notes TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                icon TEXT DEFAULT '📂'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                remind_at TEXT NOT NULL,
                chat_id TEXT,
                sent INTEGER DEFAULT 0,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
            """
        )
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(reminders)").fetchall()}
        if "chat_id" not in columns:
            conn.execute("ALTER TABLE reminders ADD COLUMN chat_id TEXT")
        # Migration: add notes column if it doesn't exist
        task_cols = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
        if "notes" not in task_cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN notes TEXT")


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def create_task(
    title: str,
    priority: str = "medium",
    category: str | None = None,
    due_date: str | None = None,
    due_time: str | None = None,
    repeat_type: str | None = None,
    notes: str | None = None,
    task_id: str | None = None,
    created_at: str | None = None,
    next_due: str | None = None,
) -> dict[str, Any]:
    init_db()
    if priority not in PRIORITIES:
        raise ValueError("priority must be high, medium, or low")
    if repeat_type is not None and repeat_type not in REPEAT_TYPES:
        raise ValueError("repeat_type must be daily or weekly")

    task = {
        "id": task_id or new_id(),
        "title": title.strip(),
        "priority": priority,
        "category": category,
        "due_date": due_date,
        "due_time": due_time,
        "repeat_type": repeat_type,
        "is_done": 0,
        "done_at": None,
        "created_at": created_at or utc_now_iso(),
        "next_due": next_due,
        "notes": notes,
    }
    if not task["title"]:
        raise ValueError("title is required")

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO tasks (
                id, title, priority, category, due_date, due_time, repeat_type,
                is_done, done_at, created_at, next_due, notes
            )
            VALUES (
                :id, :title, :priority, :category, :due_date, :due_time,
                :repeat_type, :is_done, :done_at, :created_at, :next_due, :notes
            )
            """,
            task,
        )
    return task


def get_task(task_id: str) -> dict[str, Any] | None:
    init_db()
    with connect() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return row_to_dict(row)


def list_tasks(category: str | None = None, include_done: bool = False) -> list[dict[str, Any]]:
    init_db()
    query = "SELECT * FROM tasks WHERE 1=1"
    params: list[Any] = []
    if not include_done:
        query += " AND is_done = 0"
    if category:
        query += " AND category = ?"
        params.append(category)
    query += """
        ORDER BY
            CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
            COALESCE(due_date, '9999-12-31'),
            COALESCE(due_time, '99:99'),
            created_at
    """
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def update_task_title(task_id: str, title: str) -> bool:
    init_db()
    with connect() as conn:
        cur = conn.execute("UPDATE tasks SET title = ? WHERE id = ?", (title.strip(), task_id))
        return cur.rowcount > 0


def set_task_category(task_id: str, category: str | None) -> bool:
    init_db()
    with connect() as conn:
        cur = conn.execute("UPDATE tasks SET category = ? WHERE id = ?", (category, task_id))
        return cur.rowcount > 0


def delete_task(task_id: str) -> bool:
    init_db()
    with connect() as conn:
        conn.execute("DELETE FROM reminders WHERE task_id = ?", (task_id,))
        cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return cur.rowcount > 0


def _next_repeat_due(task: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    if not task.get("repeat_type") or not task.get("due_date"):
        return None, None, None
    current = datetime.fromisoformat(task["due_date"])
    delta = timedelta(days=1 if task["repeat_type"] == "daily" else 7)
    next_dt = current + delta
    due_date = next_dt.date().isoformat()
    due_time = task.get("due_time")
    next_due = f"{due_date}T{due_time or '00:00'}"
    return due_date, due_time, next_due


def mark_task_done(task_id: str) -> dict[str, Any] | None:
    init_db()
    task = get_task(task_id)
    if not task:
        return None

    done_at = utc_now_iso()
    with connect() as conn:
        conn.execute("UPDATE tasks SET is_done = 1, done_at = ? WHERE id = ?", (done_at, task_id))

    if task.get("repeat_type"):
        due_date, due_time, next_due = _next_repeat_due(task)
        create_task(
            title=task["title"],
            priority=task["priority"],
            category=task["category"],
            due_date=due_date,
            due_time=due_time,
            repeat_type=task["repeat_type"],
            created_at=task["created_at"],
            next_due=next_due,
        )

    task["is_done"] = 1
    task["done_at"] = done_at
    return task


def add_category(name: str, icon: str = "📂") -> dict[str, Any]:
    init_db()
    category = {"id": new_id(), "name": name.strip(), "icon": icon or "📂"}
    if not category["name"]:
        raise ValueError("category name is required")
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO categories (id, name, icon)
            VALUES (:id, :name, :icon)
            ON CONFLICT(name) DO UPDATE SET icon = excluded.icon
            """,
            category,
        )
        row = conn.execute("SELECT * FROM categories WHERE name = ?", (category["name"],)).fetchone()
    return dict(row)


def get_category(name: str) -> dict[str, Any] | None:
    init_db()
    with connect() as conn:
        row = conn.execute("SELECT * FROM categories WHERE name = ?", (name,)).fetchone()
    return row_to_dict(row)


def list_categories() -> list[dict[str, Any]]:
    init_db()
    with connect() as conn:
        rows = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    return [dict(row) for row in rows]


def create_reminder(task_id: str, remind_at: str, chat_id: str | int | None = None) -> dict[str, Any]:
    init_db()
    if not get_task(task_id):
        raise ValueError("task not found")
    reminder = {"id": new_id(), "task_id": task_id, "remind_at": remind_at, "chat_id": str(chat_id) if chat_id else None, "sent": 0}
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO reminders (id, task_id, remind_at, chat_id, sent)
            VALUES (:id, :task_id, :remind_at, :chat_id, :sent)
            """,
            reminder,
        )
    return reminder


def due_reminders(now_iso: str) -> list[dict[str, Any]]:
    init_db()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT reminders.*, tasks.title
            FROM reminders
            JOIN tasks ON tasks.id = reminders.task_id
            WHERE reminders.sent = 0 AND reminders.remind_at <= ? AND tasks.is_done = 0
            ORDER BY reminders.remind_at
            """,
            (now_iso,),
        ).fetchall()
    return [dict(row) for row in rows]


def mark_reminder_sent(reminder_id: str) -> bool:
    init_db()
    with connect() as conn:
        cur = conn.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))
        return cur.rowcount > 0


def overdue_tasks(now: datetime | None = None) -> list[dict[str, Any]]:
    init_db()
    now = now or datetime.now()
    today = now.date().isoformat()
    current_time = now.strftime("%H:%M")
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM tasks
            WHERE is_done = 0
              AND due_date IS NOT NULL
              AND (
                due_date < ?
                OR (due_date = ? AND due_time IS NOT NULL AND due_time < ?)
              )
            ORDER BY due_date, COALESCE(due_time, '00:00')
            """,
            (today, today, current_time),
        ).fetchall()
    return [dict(row) for row in rows]


def export_backup(path: str | None = None) -> dict[str, Any]:
    init_db()
    path = path or BACKUP_JSON_PATH
    with connect() as conn:
        tasks = [dict(row) for row in conn.execute("SELECT * FROM tasks ORDER BY created_at").fetchall()]
        categories = [dict(row) for row in conn.execute("SELECT * FROM categories ORDER BY name").fetchall()]
    payload = {"tasks": tasks, "categories": categories, "exported_at": utc_now_iso()}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return payload
