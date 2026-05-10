import pybreaker
from typing import Any

from app.core.logger import client_logger as logger
from app.services.retry import retry_with_backoff
from app.services.openai import OpenAIService

openai_service = OpenAIService()


@retry_with_backoff(max_retries=3)
async def _call_openai_async(method: str, path: str, body: dict = {}):
    async with openai_service.get_async_client() as client:
        response = {}
        if method.lower() == "post":
            response = await client.post(path, json=body)
        elif method.lower() == "get":
            response = await client.get(path)
        else:
            raise
        return response


@retry_with_backoff(max_retries=3)
def _call_openai_sync(method: str, path: str, body: dict = {}):
    with openai_service.get_client() as client:
        if method.lower() == "post":
            response = client.post(path, json=body)
        elif method.lower() == "get":
            response = client.get(path)
        else:
            raise
        return response


class LogListener(pybreaker.CircuitBreakerListener):
    def state_change(self, cb, old_state, new_state):
        msg = f"OpenAI circuit breaker {new_state.name.upper()}"
        if new_state.name == "open":
            logger.warning(f"⚠️  {msg} — requests will fail fast")
        elif new_state.name == "half-open":
            logger.warning(f"⚠️  {msg} — testing recovery")
        elif new_state.name == "closed":
            logger.info(f"✅ {msg} — normal operation")


openai_breaker = pybreaker.CircuitBreaker(
    fail_max=5, reset_timeout=30, listeners=[LogListener()]
)


async def openai_request(method: str, path: str, body: Any = {}):
    """Async version for FastAPI routes"""
    try:
        return await openai_breaker.call_async(_call_openai_async, method, path, body)
    except pybreaker.CircuitBreakerError:
        # FALLBACK: Instant failure if the service is down
        raise Exception("OpenAI is temporarily unavailable. Please try again shortly.")


def openai_request_sync(path: str, body: Any):
    """Sync version for Celery tasks"""
    try:
        return openai_breaker.call(_call_openai_sync, path, body)
    except pybreaker.CircuitBreakerError:
        raise Exception("OpenAI is temporarily unavailable. Please try again shortly.")
