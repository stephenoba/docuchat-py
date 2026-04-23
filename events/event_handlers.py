import logging
import json
from datetime import datetime, timezone

from fastapi_events.handlers.local import local_handler
from fastapi_events.typing import Event

from models import UsageLog, Conversation
from config import AUTH_EVENTS
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
        print(e)
