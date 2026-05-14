from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

try:
    from ..db import NEON_SCHEMA, get_pool
except ImportError:  # pragma: no cover
    from db import NEON_SCHEMA, get_pool


router = APIRouter(prefix="/categories", tags=["categories"])


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    icon: str = Field(default="📂", max_length=8)


@router.get("")
async def list_categories() -> list[dict]:
    db_pool = await get_pool()
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(f'SELECT * FROM "{NEON_SCHEMA}".categories ORDER BY name')
    return [dict(row) for row in rows]


@router.post("", status_code=201)
async def create_category(payload: CategoryCreate) -> dict:
    db_pool = await get_pool()
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""
            INSERT INTO "{NEON_SCHEMA}".categories (name, icon)
            VALUES ($1, $2)
            ON CONFLICT (name) DO UPDATE SET icon = excluded.icon
            RETURNING *
            """,
            payload.name.strip(),
            payload.icon or "📂",
        )
    return dict(row)


@router.delete("/{category_id}")
async def delete_category(category_id: str) -> dict[str, bool]:
    db_pool = await get_pool()
    async with db_pool.acquire() as conn:
        result = await conn.execute(f'DELETE FROM "{NEON_SCHEMA}".categories WHERE id = $1', category_id)
    if not result.endswith("1"):
        raise HTTPException(status_code=404, detail="Category not found")
    return {"deleted": True}
