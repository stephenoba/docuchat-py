from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

import secure


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.secure = secure.Secure.with_default_headers()

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        await self.secure.set_headers_async(response)
        return response
