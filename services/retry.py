import time
import asyncio
import httpx
from functools import wraps
from config import get_settings
from logger import client_logger as logger

settings = get_settings()


def is_retryable(error: Exception) -> bool:
    if isinstance(error, httpx.RequestError):
        return True
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        return status in (408, 429) or status >= 500
    return False


def retry_with_backoff(
    max_retries: int = 3, base_delay: int = settings.OPENAI_RETRY_DELAY or 1
):
    """
    Retry decorator for functions that may fail due to network issues.

    example usage:
        @retry_with_backoff(max_retries=5, base_delay=2)
        def get_embedding_sync(self, text):
            with self.get_client() as client:
                return client.post("/embeddings", ...)

        @retry_with_backoff(max_retries=3)
        async def get_embedding_async(self, text):
            async with self.get_async_client() as client:
                return await client.post("/embeddings", ...)
    """
    def decorator(func):
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                for i in range(max_retries):
                    try:
                        return await func(*args, **kwargs)
                    except (httpx.HTTPStatusError, httpx.RequestError) as e:
                        if i == max_retries - 1 or not is_retryable(e):
                            raise
                        delay = base_delay * (2**i)
                        logger.warning(
                            f"Retrying {func.__name__} in {delay}s... ({i+1}/{max_retries})"
                        )
                        await asyncio.sleep(delay)

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                for i in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except (httpx.HTTPStatusError, httpx.RequestError) as e:
                        if i == max_retries - 1 or not is_retryable(e):
                            raise
                        
                        delay = base_delay * (2**i)
                        
                        # Handle Retry-After header if present
                        if isinstance(e, httpx.HTTPStatusError):
                            retry_after = e.response.headers.get("Retry-After")
                            if retry_after and retry_after.isdigit():
                                delay = int(retry_after)

                        logger.warning(
                            f"Retrying {func.__name__} in {delay}s... ({i+1}/{max_retries})"
                        )
                        time.sleep(delay)

            return sync_wrapper

    return decorator

