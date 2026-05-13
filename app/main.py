from datetime import datetime
import time
import httpx

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi_events.middleware import EventHandlerASGIMiddleware
from fastapi_events.handlers.local import local_handler

from app.core.config import get_settings
from app.routers.v1 import api_v1_router
from app.schemas import SuccessResponse
from app.middleware.logging_middleware import api_logging_middleware
from app.middleware.exception_handlers import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from app.middleware.xss_middleware import XSSMiddleware
from app.middleware.security_headers_middleware import SecurityHeadersMiddleware
from app.models.dbmanager import async_engine
from app.extensions.redis import redis_client

import app.events  # noqa: F401
from app.core.utils import utcnow

settings = get_settings()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(EventHandlerASGIMiddleware, handlers=[local_handler])

app.add_middleware(XSSMiddleware)
app.middleware("http")(api_logging_middleware)


# Exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Routes
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health/live")
async def live_check():

    return SuccessResponse(
        data={
            "status": "ok",
            "timestamp": utcnow().isoformat(),
            "uptime": time.time(),
            "service": "docuchat"
        },
        message="Service is healthy",
    )


@app.get("/health/ready")
async def ready_check():

    checks = {}
    try:
        from sqlalchemy import text
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as e:
        checks["database"] = {"status": "error", "message": str(e)}

    try:
        await redis_client.ping()
        checks["redis"] = {"status": "ok"}
    except Exception as e:
        checks["redis"] = {"status": "error", "message": str(e)}
    try:
        if settings.USE_OLLAMA:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{settings.OPENAI_BASE_URL}/models")
                if resp.status_code == 200:
                    checks["ollama"] = {"status": "ok"}
                else:
                    checks["ollama"] = {"status": "error", "message": f"Ollama returned {resp.status_code}"}
    except Exception as e:
        checks["ollama"] = {"status": "error", "message": str(e)}

    
    all_healthy = all(c["status"] == "ok" for c in checks.values())
    
    return SuccessResponse(
        data={
            "status": "ok" if all_healthy else "partial_failure",
            "timestamp": utcnow().isoformat(),
            "checks": checks,
        },
        message="Service is ready" if all_healthy else "Service is degraded",
    )

