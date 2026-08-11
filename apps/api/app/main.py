import json
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import models  # noqa: F401
from app.api import (
    admin,
    analytics,
    athlete,
    auth,
    cv,
    habits,
    nutrition,
    privacy,
    recommendations,
    training,
)
from app.config import settings
from app.db import Base, SessionLocal, engine
from app.domains.catalog import seed_catalogues
from app.errors import DomainError

logger = logging.getLogger("athleteos")
logging.basicConfig(level=logging.INFO, format="%(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_db and settings.app_env in {"development", "test"}:
        Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_catalogues(db)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Idempotency-Key", "X-Request-ID"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(json.dumps({"severity": "error", "request_id": request_id, "route": request.url.path}))
        raise
    response.headers["X-Request-ID"] = request_id
    logger.info(
        json.dumps(
            {
                "severity": "info",
                "request_id": request_id,
                "method": request.method,
                "route": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            }
        )
    )
    return response


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
            "request_id": getattr(request.state, "request_id", None),
            "retryable": exc.retryable,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Please correct the highlighted fields.",
            "details": exc.errors(),
            "request_id": getattr(request.state, "request_id", None),
            "retryable": False,
        },
    )


@app.get("/health", tags=["operations"])
def health():
    return {"status": "ok"}


@app.get("/ready", tags=["operations"])
def ready():
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
        return {"status": "ready"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready"})


for router in (
    auth.router,
    athlete.router,
    training.router,
    nutrition.router,
    habits.router,
    analytics.router,
    cv.router,
    recommendations.router,
    privacy.router,
    admin.router,
):
    app.include_router(router, prefix=settings.api_prefix)

