from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:  # Supports both `uvicorn api.main:app` and `cd api && uvicorn main:app`.
    from .db import acquire_conn, close_pool, create_pool, init_schema
    from .routers import categories, tasks, reminders
except ImportError:  # pragma: no cover
    from db import acquire_conn, close_pool, create_pool, init_schema
    from routers import categories, tasks, reminders


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_pool()
    await init_schema()
    yield
    await close_pool()


app = FastAPI(title="KITT-TODO API", version="2.0.0", lifespan=lifespan)

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


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/debug/pool")
async def debug_pool() -> dict:
    async with acquire_conn() as conn:
        row = await conn.fetchrow("SELECT now() as ts")
    from .db import get_pool
    p = await get_pool()
    return {"pool_size": p.get_size(), "time": str(row["ts"])}