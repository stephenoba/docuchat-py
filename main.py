from fastapi import FastAPI
from fastapi_events.middleware import EventHandlerASGIMiddleware
from fastapi_events.handlers.local import local_handler

from config import get_settings
from api.v1 import api_v1_router
from middleware.logging_middleware import logging_middleware
import events  # noqa: F401

settings = get_settings()

app = FastAPI()

app.add_middleware(EventHandlerASGIMiddleware, handlers=[local_handler])
app.middleware("http")(logging_middleware)
app.include_router(api_v1_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "ok"}