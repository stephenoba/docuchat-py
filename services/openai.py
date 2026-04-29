import httpx
from config import get_settings
from logger import client_logger as logger

settings = get_settings()


def log_request(request):
    logger.info(f"Request: {request.method} {request.url}")


def handle_response(response):
    if not response.is_success:
        logger.error(f"Error: {response.status_code}")
        response.raise_for_status()
    else:
        logger.info(f"Response: {response.status_code}")


class OpenAIService:
    def __init__(self):
        self.base_url = settings.OPENAI_BASE_URL
        self.model = settings.OPENAI_MODEL
        self.headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "DocuChat/1.0",
        }
        self.hooks = {"request": [log_request], "response": [handle_response]}

    def get_client(self):
        """Returns a synchronous client for Celery tasks."""
        return httpx.Client(
            base_url=self.base_url,
            headers=self.headers,
            event_hooks=self.hooks,
            timeout=30.0,
        )

    def get_async_client(self):
        """Returns an asynchronous client for FastAPI routes."""
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            event_hooks=self.hooks,
            timeout=30.0,
        )
