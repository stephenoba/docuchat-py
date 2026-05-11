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


import app.events  # noqa: F401

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


@app.get("/health")
async def health_check():
    return SuccessResponse(
        data={"status": "ok"},
        message="Service is healthy",
    )
