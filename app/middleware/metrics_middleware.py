import re
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.metrics import HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Normalize path
        path = self._normalize_path(request.url.path)
        method = request.method

        # Start timer
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            
            # Stop timer and record duration
            duration = time.perf_counter() - start_time
            HTTP_REQUEST_DURATION.labels(method=method, path=path).observe(duration)
            
            # Record request total
            HTTP_REQUESTS_TOTAL.labels(
                method=method, 
                path=path, 
                status_code=str(response.status_code)
            ).inc()
            
            return response
        except Exception as e:
            # Record failed request
            HTTP_REQUESTS_TOTAL.labels(
                method=method, 
                path=path, 
                status_code="500"
            ).inc()
            raise e

    def _normalize_path(self, path: str) -> str:
        """
        Normalize paths so /documents/abc-123 becomes /documents/:id
        and /documents/123 becomes /documents/:num
        """
        # Replace UUIDs
        path = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            ':id',
            path
        )
        # Replace numbers
        path = re.sub(r'/\d+', '/:num', path)
        return path
