"""
HTTP client for KITT-TODO Render API.
Writes to Neon PostgreSQL via https://kitt-todo-api.onrender.com
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("kitt-todo")

BASE_URL = "https://kitt-todo-api.onrender.com"
TIMEOUT = 15.0


def _get_client() -> httpx.Client:
    return httpx.Client(base_url=BASE_URL, timeout=TIMEOUT)


def _handle_error(resp: httpx.Response, action: str) -> Any | None:
    if resp.status_code >= 500:
        logger.error("API server error %d for %s", resp.status_code, action)
        return None
    if resp.status_code >= 400:
        logger.warning("API client error %d for %s: %s", resp.status_code, action, resp.text)
        return None
    return None


# Tasks

def create_task(
    title: str,
    priority: str = "medium",
    category: str | None = None,
    due_date: str | None = None,
    due_time: str | None = None,
    repeat_type: str | None = None,
) -> dict[str, Any] | None:
    """POST /api/tasks"""
    payload = {
        "title": title,
        "priority": priority,
        "category": category,
        "due_date": due_date,
        "due_time": due_time,
        "repeat_type": repeat_type,
    }
    try:
        resp = _get_client().post("/api/tasks", json=payload)
        if resp.status_code == 201:
            return resp.json()
        return _handle_error(resp, "create_task")
    except httpx.RequestError as exc:
        logger.error("Network error creating task: %s", exc)
        return None


def list_tasks(category: str | None = None, status: str | None = None) -> list[dict[str, Any]] | None:
    """GET /api/tasks"""
    params = {}
    if category:
        params["category"] = category
    if status:
        params["status"] = status
    try:
        resp = _get_client().get("/api/tasks", params=params)
        if resp.status_code == 200:
            return resp.json()
        return _handle_error(resp, "list_tasks")
    except httpx.RequestError as exc:
        logger.error("Network error listing tasks: %s", exc)
        return None


def get_task(task_id: str) -> dict[str, Any] | None:
    """GET /api/tasks/{task_id}"""
    try:
        resp = _get_client().get(f"/api/tasks/{task_id}")
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 404:
            return None
        return _handle_error(resp, f"get_task({task_id})")
    except httpx.RequestError as exc:
        logger.error("Network error getting task %s: %s", task_id, exc)
        return None


def update_task(
    task_id: str,
    title: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    due_date: str | None = None,
    due_time: str | None = None,
    repeat_type: str | None = None,
) -> dict[str, Any] | None:
    """PUT /api/tasks/{task_id}"""
    payload = {}
    if title is not None:
        payload["title"] = title
    if priority is not None:
        payload["priority"] = priority
    if category is not None:
        payload["category"] = category
    if due_date is not None:
        payload["due_date"] = due_date
    if due_time is not None:
        payload["due_time"] = due_time
    if repeat_type is not None:
        payload["repeat_type"] = repeat_type
    if not payload:
        return get_task(task_id)
    try:
        resp = _get_client().put(f"/api/tasks/{task_id}", json=payload)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 404:
            return None
        return _handle_error(resp, f"update_task({task_id})")
    except httpx.RequestError as exc:
        logger.error("Network error updating task %s: %s", task_id, exc)
        return None


def delete_task(task_id: str) -> bool:
    """DELETE /api/tasks/{task_id}"""
    try:
        resp = _get_client().delete(f"/api/tasks/{task_id}")
        if resp.status_code == 200:
            return True
        if resp.status_code == 404:
            return False
        _handle_error(resp, f"delete_task({task_id})")
        return False
    except httpx.RequestError as exc:
        logger.error("Network error deleting task %s: %s", task_id, exc)
        return False


def mark_task_done(task_id: str) -> dict[str, Any] | None:
    """POST /api/tasks/{task_id}/done"""
    try:
        resp = _get_client().post(f"/api/tasks/{task_id}/done")
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 404:
            return None
        return _handle_error(resp, f"mark_task_done({task_id})")
    except httpx.RequestError as exc:
        logger.error("Network error marking task done %s: %s", task_id, exc)
        return None


# Categories

def add_category(name: str, icon: str = "📂") -> dict[str, Any] | None:
    """POST /api/categories"""
    try:
        resp = _get_client().post("/api/categories", json={"name": name, "icon": icon})
        if resp.status_code in (200, 201):
            return resp.json()
        return _handle_error(resp, f"add_category({name})")
    except httpx.RequestError as exc:
        logger.error("Network error adding category: %s", exc)
        return None


def get_category(name: str) -> dict[str, Any] | None:
    """GET /api/categories - find by name (no endpoint for single category by name)"""
    try:
        resp = _get_client().get("/api/categories")
        if resp.status_code == 200:
            categories = resp.json()
            for cat in categories:
                if cat.get("name") == name:
                    return cat
            return None
        return _handle_error(resp, f"get_category({name})")
    except httpx.RequestError as exc:
        logger.error("Network error getting category: %s", exc)
        return None


def list_categories() -> list[dict[str, Any]] | None:
    """GET /api/categories"""
    try:
        resp = _get_client().get("/api/categories")
        if resp.status_code == 200:
            return resp.json()
        return _handle_error(resp, "list_categories")
    except httpx.RequestError as exc:
        logger.error("Network error listing categories: %s", exc)
        return None


def set_task_category(task_id: str, category: str | None) -> dict[str, Any] | None:
    """PUT /api/tasks/{task_id} with category field"""
    return update_task(task_id, category=category)