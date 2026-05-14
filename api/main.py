from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:  # Supports both `uvicorn api.main:app` and `cd api && uvicorn main:app`.
    from .db import close_pool, create_pool, get_pool, init_schema
    from .routers import categories, tasks, reminders
except ImportError:  # pragma: no cover
    from db import close_pool, create_pool, get_pool, init_schema
    from routers import categories, tasks, reminders


app = FastAPI(title="KITT-TODO API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(reminders.router, prefix="/api")


@app.on_event("startup")
async def startup() -> None:
    await create_pool()
    await init_schema()


@app.on_event("shutdown")
async def shutdown() -> None:
    await close_pool()


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/debug/pool")
async def debug_pool() -> dict[str, str]:
    """Test the database pool - this uses the same pool as reminders router"""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT 1 as test, now() as ts")
            return {"pool": "ok", "test": dict(row)}
    except Exception as exc:
        import traceback
        return {"pool": "error", "detail": str(exc), "trace": traceback.format_exc()}
