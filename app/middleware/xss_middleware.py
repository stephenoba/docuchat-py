import json
import bleach
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class XSSMiddleware(BaseHTTPMiddleware):
    """
    Middleware that sanitizes all incoming JSON request bodies and query parameters
    to prevent XSS attacks using the 'bleach' library.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                body = await request.body()
                if body:
                    try:
                        data = json.loads(body)
                        sanitized_data = self._sanitize_data(data)
                        sanitized_body = json.dumps(sanitized_data).encode("utf-8")

                        async def receive():
                            return {
                                "type": "http.request",
                                "body": sanitized_body,
                                "more_body": False
                            }
                        
                        request._receive = receive
                        request._body = sanitized_body

                    except json.JSONDecodeError:
                        # If JSON is malformed, let the standard FastAPI handlers catch it
                        pass

        return await call_next(request)

    def _sanitize_data(self, data):
        """Recursively sanitize strings in nested dictionaries and lists."""
        if isinstance(data, str):
            # bleach.clean removes tags and escapes characters by default
            return bleach.clean(data)
        elif isinstance(data, dict):
            return {k: self._sanitize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_data(i) for i in data]
        return data
