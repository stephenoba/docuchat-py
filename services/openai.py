import httpx
from config import get_settings
from logger import client_logger as logger

settings = get_settings()

def check_rate_limit_remaining_requests(response):
    # Ollama doesn't send standard OpenAI rate limit headers
    remaining_str = response.headers.get("x-ratelimit-remaining-requests", "999")
    try:
        remaining = int(remaining_str)
    except ValueError:
        remaining = 999
    
    if remaining < 50:
        logger.warning(f"Rate limit getting low: {remaining} remaining")

async def check_rate_limit_remaining_requests_async(response):
    check_rate_limit_remaining_requests(response)

def log_request(request):
    logger.info(f"Request: {request.method} {request.url}")

async def log_request_async(request):
    log_request(request)

def handle_response(response):
    if not response.is_success:
        logger.error(f"Error: {response.status_code}")
        response.raise_for_status()
    else:
        logger.info(f"Response: {response.status_code}")

async def handle_response_async(response):
    handle_response(response)

class OpenAIService:
    def __init__(self):
        self.base_url = settings.OPENAI_BASE_URL
        self.model = settings.OPENAI_MODEL
        self.embedding_model = settings.OPENAI_EMBEDDING_MODEL
        self.headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "DocuChat/1.0",
        }
        self.sync_hooks = {
            "request": [log_request],
            "response": [handle_response, check_rate_limit_remaining_requests]
        }
        self.async_hooks = {
            "request": [log_request_async],
            "response": [handle_response_async, check_rate_limit_remaining_requests_async]
        }

    def get_client(self):
        """Returns a synchronous client for Celery tasks."""
        return httpx.Client(
            base_url=self.base_url,
            headers=self.headers,
            event_hooks=self.sync_hooks,
            timeout=30.0,
        )

    def get_async_client(self):
        """Returns an asynchronous client for FastAPI routes."""
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            event_hooks=self.async_hooks,
            timeout=30.0,
        )
