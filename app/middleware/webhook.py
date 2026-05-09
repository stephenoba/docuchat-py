import hmac
import hashlib
from fastapi import Request, HTTPException, status
from typing import Callable


def verify_webhook_signature(
    secret: str, header_name: str = "X-Webhook-Signature"
) -> Callable:
    """
    Dependency factory for verifying webhook signatures.

    Args:
        secret: The shared secret used to sign the payload.
        header_name: The name of the header containing the signature.
    """

    async def dependency(request: Request):
        signature = request.headers.get(header_name.lower())

        if not signature:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing signature header",
            )

        raw_body = await request.body()

        computed_signature = hmac.new(
            secret.encode("utf-8"), raw_body, hashlib.sha256
        ).hexdigest()

        # 3. Use compare_digest to prevent timing attacks (equivalent to timingSafeEqual)
        if not hmac.compare_digest(computed_signature, signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature",
            )

    return dependency
