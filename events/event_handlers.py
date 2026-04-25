import logging
import json
from datetime import datetime, timezone

from fastapi_events.handlers.local import local_handler
from fastapi_events.typing import Event

from models import UsageLog, Conversation
from config import AUTH_EVENTS, ADMIN_EVENTS
from dbmanager import async_session

logger = logging.getLogger(__name__)


@local_handler.register(event_name=AUTH_EVENTS.USER_REGISTERED)
async def handle_user_registered(event: Event):
    try:
        _, user = event
        async with async_session() as session:
            async with session.begin():
                # Log the registration usage
                await UsageLog.objects.create(
                    session=session,
                    user_id=user.id,
                    action="signUp",
                    tokens=0,
                    cost_usd=0.0,
                    log_metadata=json.dumps(
                        {
                            "email": user.email,
                            "tier": user.tier,
                            "signUpAt": datetime.now(timezone.utc).isoformat(),
                        }
                    ),
                )

                # Create a welcome conversation
                await Conversation.objects.create(
                    session=session,
                    user_id=user.id,
                    title="Welcome to DocuChat",
                )
    except Exception as e:
        logger.error(f"Failed to handle user registered event: {e}")


@local_handler.register(event_name=ADMIN_EVENTS.ROLE_ASSIGNED)
async def handle_role_assigned(event: Event):
    try:
        _, payload = event
        admin_id = payload.pop("admin_id")
        async with async_session() as session:
            async with session.begin():
                await UsageLog.objects.create(
                    session=session,
                    user_id=admin_id,
                    action="assign_role",
                    tokens=0,
                    cost_usd=0.0,
                    log_metadata=json.dumps(payload),
                )
    except Exception as e:
        logger.error(f"Failed to handle role assigned event: {e}")


@local_handler.register(event_name=ADMIN_EVENTS.ROLE_REVOKED)
async def handle_role_revoked(event: Event):
    try:
        _, payload = event
        admin_id = payload.pop("admin_id")
        async with async_session() as session:
            async with session.begin():
                await UsageLog.objects.create(
                    session=session,
                    user_id=admin_id,
                    action="revoke_role",
                    tokens=0,
                    cost_usd=0.0,
                    log_metadata=json.dumps(payload),
                )
    except Exception as e:
        logger.error(f"Failed to handle role revoked event: {e}")


@local_handler.register(event_name="doc:*")
async def handle_doc_events(event: Event):
    try:
        event_name, payload = event
        user_id = payload.pop("user_id")
        # Extract action from doc:action
        action = event_name.split(":")[-1]

        async with async_session() as session:
            async with session.begin():
                await UsageLog.objects.create(
                    session=session,
                    user_id=user_id,
                    action=f"doc_{action}",
                    tokens=payload.get("tokens", 0),
                    cost_usd=payload.get("cost", 0.0),
                    log_metadata=json.dumps(payload),
                )
    except Exception as e:
        logger.error(f"Failed to handle doc event: {e}")
