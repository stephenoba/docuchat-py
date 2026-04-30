from fastapi import APIRouter, Request, Depends
from middleware.webhook import verify_webhook_signature
from config import get_settings

settings = get_settings()
webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@webhook_router.post(
    "/openai",
    dependencies=[Depends(verify_webhook_signature(settings.OPENAI_WEBHOOK_SECRET))],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def handle_openai_webhook(request: Request):
    """Handle OpenAI webhook events"""
    data = await request.json()
    return {"message": "Webhook received successfully"}

