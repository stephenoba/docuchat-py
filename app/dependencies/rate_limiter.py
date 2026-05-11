import time
import jwt
from fastapi import Request, Response, HTTPException, status

from app.extensions.redis import redis_client, hash_key
from app.core.config import get_settings

settings = get_settings()



LUA_SLIDING_WINDOW = """
local window_start = ARGV[1] - ARGV[2]
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', window_start)
local current_count = redis.call('ZCARD', KEYS[1])
local allowed = 0

if current_count < tonumber(ARGV[3]) then
    redis.call('ZADD', KEYS[1], ARGV[1], ARGV[1])
    redis.call('EXPIRE', KEYS[1], math.ceil(ARGV[2] / 1000))
    allowed = 1
    current_count = current_count + 1
end

return {allowed, tonumber(ARGV[3]) - current_count, math.ceil(ARGV[2] / 1000)}
"""

rate_limit_script = redis_client.register_script(LUA_SLIDING_WINDOW)


class RateLimiter:
    def __init__(self, requests: int, window_seconds: int, name: str = "default"):
        self.requests = requests
        self.window_ms = window_seconds * 1000
        self.name = name

    async def _check_rate_limit(self, key: str, requests: int, window_ms: int, response: Response):
        now_ms = int(time.time() * 1000)
        allowed, remaining, reset_sec = await rate_limit_script(
            keys=[key], 
            args=[now_ms, window_ms, requests]
        )

        response.headers["RateLimit-Limit"] = str(requests)
        response.headers["RateLimit-Remaining"] = str(remaining)
        response.headers["RateLimit-Reset"] = str(reset_sec)

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests",
                headers={
                    "Retry-After": str(reset_sec),
                    "RateLimit-Limit": str(requests),
                    "RateLimit-Remaining": str(remaining),
                    "RateLimit-Reset": str(reset_sec)
                }
            )


    async def __call__(self, request: Request, response: Response):
        user_id = request.client.host
        key = hash_key(self.name, f"rate_limit:{request.url.path}:{user_id}")
        await self._check_rate_limit(key, self.requests, self.window_ms, response)


class TieredRateLimiter(RateLimiter):
    def __init__(self, limits: dict[str, tuple[int, int]], name: str = "tiered"):
        """
        limits = {
            "free": (requests, window_seconds),
            "pro": (requests, window_seconds),
            "enterprise": (requests, window_seconds)
        }
        """
        self.tiered_limits = {
            tier: (req, win * 1000) for tier, (req, win) in limits.items()
        }
        self.name = name

    async def __call__(self, request: Request, response: Response):
        # Identify user and tier
        user_id = request.client.host
        tier = "free"

        # Try to get tier from JWT if present
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            try:
                # We decode without verification if we just want the tier for rate limiting
                # Or we can verify to be stricter. Let's do a quick decode.
                payload = jwt.decode(
                    token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
                )
                user_id = payload.get("sub", user_id)
                tier = payload.get("tier", "free")
            except Exception:
                # If token is invalid, we fall back to IP and free tier
                pass

        # Fallback to free tier if tier not in limits
        if tier not in self.tiered_limits:
            tier = "free"
            
        requests, window_ms = self.tiered_limits[tier]
        key = hash_key(self.name, f"rate_limit:{request.url.path}:{tier}:{user_id}")
        
        await self._check_rate_limit(key, requests, window_ms, response)



# --- Predefined Limiters ---

# General API: 100/500/2000 per 15 min (900s)
general_limiter = TieredRateLimiter({
    "free": (100, 900),
    "pro": (500, 900),
    "enterprise": (2000, 900)
}, name="general")

# Auth: 10/10/10 per 15 min (900s)
auth_limiter = RateLimiter(requests=10, window_seconds=900, name="auth")

# Document upload: 5/50/500 per 1 hour (3600s)
upload_limiter = TieredRateLimiter({
    "free": (5, 3600),
    "pro": (50, 3600),
    "enterprise": (500, 3600)
}, name="upload")

# Chat/AI queries: 10/30/100 per 1 minute (60s)
chat_limiter = TieredRateLimiter({
    "free": (10, 60),
    "pro": (30, 60),
    "enterprise": (100, 60)
}, name="chat")