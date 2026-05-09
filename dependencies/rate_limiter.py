import time
from fastapi import Request, Response, HTTPException
from extensions.redis import redis_client, hash_key


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
    def __init__(self, requests: int, window_seconds: int):
        self.requests = requests
        self.window_ms = window_seconds * 1000

    async def __call__(self, request: Request, response: Response):
        user_id = request.client.host
        key = hash_key(f"rate_limit:{request.url.path}:{user_id}")
        now_ms = int(time.time() * 1000)

        # It uses EVALSHA if the script is already loaded
        allowed, remaining, reset_sec = await rate_limit_script(
            keys=[key], 
            args=[now_ms, self.window_ms, self.requests]
        )

        response.headers["RateLimit-Limit"] = str(self.requests)
        response.headers["RateLimit-Remaining"] = str(remaining)
        response.headers["RateLimit-Reset"] = str(reset_sec)

        if not allowed:
            raise HTTPException(
                status_code=429, 
                detail="Too Many Requests",
                headers={"Retry-After": str(reset_sec)}
            )