from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi_events.middleware import EventHandlerASGIMiddleware
from fastapi_events.handlers.local import local_handler

from config import get_settings
from api.v1 import api_v1_router
from schemas import SuccessResponse
from middleware.logging_middleware import logging_middleware
from middleware.exception_handlers import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
import events  # noqa: F401

settings = get_settings()

app = FastAPI()

# Middleware
app.add_middleware(EventHandlerASGIMiddleware, handlers=[local_handler])
app.middleware("http")(logging_middleware)

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