import json
from datetime import datetime
from fastapi import APIRouter, Request, Depends, status, BackgroundTasks
from fastapi.responses import JSONResponse

from middleware.webhook import verify_webhook_signature
from config import get_settings
from models import WebhookEvent, WebhookEventStatus
from logger import api_logger as logger

settings = get_settings()
webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def process_webhook_event(event_id: str, payload: dict):
    """
    Background task to process the webhook event.
    Reflects your 'processWebhookEvent' switch logic.
    """
    try:
        event_type = payload.get("type")
        logger.info(f"Processing webhook {event_id} of type: {event_type}")

        # Update status to processing
        await WebhookEvent.objects.update_by_id(
            event_id, status=WebhookEventStatus.PROCESSING.value
        )

        # --- ROUTE TO HANDLERS ---
        if event_type == "document.imported":
            # Example: Trigger a Celery task or internal service
            # from queues.celery_task import process_document
            # process_document.delay(...)
            pass
        else:
            logger.info(f"Unhandled webhook event type: {event_type}")

        # Mark as SUCCESS
        await WebhookEvent.objects.update_by_id(
            event_id,
            status=WebhookEventStatus.SUCCESS.value,
            processed_at=datetime.now(),
        )

    except Exception as e:
        logger.error(f"Webhook {event_id} processing failed: {str(e)}")
        await WebhookEvent.objects.update_by_id(
            event_id, status=WebhookEventStatus.FAILED.value
        )


@webhook_router.post(
    "/openai",
    dependencies=[Depends(verify_webhook_signature(settings.WEBHOOK_SECRET))],
)
async def handle_openai_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Main entry point for OpenAI webhooks.
    """
    data = await request.json()
    event_id = data.get("id")
    event_type = data.get("type", "unknown")

    if not event_id:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content={"error": "Missing event id"}
        )

    existing = await WebhookEvent.objects.get_or_none(id=event_id)
    if existing and existing.processed_at:
        return {"received": True, "duplicate": True}

    if not existing:
        await WebhookEvent.objects.create(
            id=event_id,
            provider="openai",
            event_type=event_type,
            payload=json.dumps(data),
            status=WebhookEventStatus.PENDING.value,
        )

    background_tasks.add_task(process_webhook_event, event_id, data)

    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"received": True})

