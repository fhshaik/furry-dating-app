import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.rate_limit import RateLimiter
from app.core.sentry import init_sentry
from app.database import get_db
from app.routers import (
    auth,
    conversations,
    discover,
    fursonas,
    items,
    matches,
    notifications,
    packs,
    reports,
    species,
    swipes,
    users,
    ws,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    sentry_enabled = init_sentry()
    logger.info(
        "Starting FurConnect API",
        extra={
            "environment": settings.environment,
            "sentry_enabled": sentry_enabled,
        },
    )
    yield
    logger.info("Shutting down FurConnect API")


app = FastAPI(
    title="FurConnect API",
    version="0.1.0",
    lifespan=lifespan,
)
app.state.rate_limiter = RateLimiter(settings.api_rate_limit)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=settings.jwt_secret)


@app.middleware("http")
async def log_http_requests(request: Request, call_next):
    started_at = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log_request(request, 500, started_at, failed=True)
        raise

    log_request(request, response.status_code, started_at)
    return response


@app.middleware("http")
async def rate_limit_requests(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)

    result = await request.app.state.rate_limiter.check(request)
    if not result.allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers=result.headers,
        )

    response = await call_next(request)
    for header, value in result.headers.items():
        response.headers[header] = value
    return response


def log_request(
    request: Request, status_code: int, started_at: float, failed: bool = False
) -> None:
    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    forwarded_for = request.headers.get("x-forwarded-for")
    client_ip = (
        forwarded_for.split(",")[0].strip()
        if forwarded_for
        else request.client.host if request.client else None
    )

    extra = {
        "method": request.method,
        "path": request.url.path,
        "status_code": status_code,
        "duration_ms": duration_ms,
    }
    if client_ip:
        extra["client_ip"] = client_ip

    request_id = request.headers.get("x-request-id")
    if request_id:
        extra["request_id"] = request_id

    if failed:
        logger.exception("Request failed", extra=extra)
        return

    logger.info("Request completed", extra=extra)

app.include_router(items.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(packs.router)
app.include_router(discover.router)
app.include_router(matches.router)
app.include_router(notifications.router)
app.include_router(reports.router)
app.include_router(conversations.router)
app.include_router(swipes.router)
app.include_router(fursonas.router)
app.include_router(species.router)
app.include_router(ws.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/health")
async def api_health() -> dict[str, str]:
    return {"status": "ok", "version": app.version}


@app.get("/api/health/db")
async def api_health_db(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
