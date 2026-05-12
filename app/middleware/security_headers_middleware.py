from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

import secure


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.secure = secure.Secure.with_default_headers()
        # Configure security headers with custom CSP to allow Swagger UI CDNs
        # csp = (
        #     secure.ContentSecurityPolicy()
        #     .default_src("'self'")
        #     .script_src("'self'", "'unsafe-inline'", "cdn.jsdelivr.net")
        #     .style_src("'self'", "'unsafe-inline'", "cdn.jsdelivr.net")
        #     .img_src("'self'", "data:", "cdn.jsdelivr.net")
        #     .connect_src("'self'", "cdn.jsdelivr.net")
        # )
        # self.secure = secure.Secure(
        #     csp=csp,
        #     hsts=secure.StrictTransportSecurity().include_subdomains().preload().max_age(31536000),
        #     xfo=secure.XFrameOptions().deny(),
        #     xcto=secure.XContentTypeOptions().nosniff(),
        #     referrer=secure.ReferrerPolicy().no_referrer(),
        #     cache=secure.CacheControl().no_cache().no_store().must_revalidate()
        # )





    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        exclude = ["/docs", "/redoc"]
        # Skip security headers for health endpoints
        if not any(request.url.path.startswith(x) for x in exclude):
            await self.secure.set_headers_async(response)
            
        return response

