from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import select, func

from app.auth import PermissionChecker
from app.models.models import User, Conversation, Message, Document
from app.schemas import SuccessResponse
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)
from app.models.dbmanager import async_session
from app.dependencies.rate_limiter import general_limiter, chat_limiter
from app.core.utils import utcnow
from app.services.conversation import send_message as send_message_service


conversation_router = APIRouter(dependencies=[Depends(general_limiter)])



@conversation_router.post(
    "",
    response_model=SuccessResponse[ConversationResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    user: Annotated[User, Depends(PermissionChecker("conversations:create"))],
    data: ConversationCreate,
):
    conversation = await Conversation.objects.create(user_id=user.id, title=data.title)
    return SuccessResponse[ConversationResponse](
        data=ConversationResponse.model_validate(conversation),
        message="Conversation created successfully",
    )


@conversation_router.get("", response_model=SuccessResponse[List[ConversationResponse]])
async def list_conversations(
    user: Annotated[User, Depends(PermissionChecker("conversations:read"))],
    skip: int = 0,
    limit: int = 100,
):
    async with async_session() as session:
        base_query = select(Conversation).where(Conversation.user_id == user.id)

        # Count total
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_result = await session.execute(count_stmt)
        total = total_result.scalar() or 0

        statement = base_query.offset(skip).limit(limit)
        results = await session.execute(statement)
        conversations = results.scalars().all()

    from app.schemas import PaginationMeta

    return SuccessResponse[List[ConversationResponse]](
        data=[ConversationResponse.model_validate(c) for c in conversations],
        message="Conversations retrieved successfully",
        meta=PaginationMeta(
            page=(skip // limit) + 1 if limit > 0 else 1,
            limit=limit,
            total=total,
        ),
    )


@conversation_router.get(
    "/{conversation_id}", response_model=SuccessResponse[ConversationResponse]
)
async def get_conversation(
    user: Annotated[User, Depends(PermissionChecker("conversations:read"))],
    conversation_id: UUID,
):
    conversation = await Conversation.objects.get(id=conversation_id, user_id=user.id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    return SuccessResponse[ConversationResponse](
        data=ConversationResponse.model_validate(conversation),
        message="Conversation retrieved successfully",
    )


@conversation_router.patch(
    "/{conversation_id}", response_model=SuccessResponse[ConversationResponse]
)
async def update_conversation(
    user: Annotated[User, Depends(PermissionChecker("conversations:read"))],
    conversation_id: UUID,
    data: ConversationUpdate,
):
    conversation = await Conversation.objects.get(id=conversation_id, user_id=user.id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        for key, value in update_data.items():
            setattr(conversation, key, value)
        conversation.updated_at = utcnow()
        await Conversation.objects.save(conversation)

    return SuccessResponse[ConversationResponse](
        data=ConversationResponse.model_validate(conversation),
        message="Conversation updated successfully",
    )


@conversation_router.delete("/{conversation_id}", response_model=SuccessResponse)
async def delete_conversation(
    user: Annotated[User, Depends(PermissionChecker("conversations:read"))],
    conversation_id: UUID,
):
    conversation = await Conversation.objects.get(id=conversation_id, user_id=user.id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    await Conversation.objects.delete(conversation)

    return SuccessResponse(message="Conversation deleted successfully")


@conversation_router.post(
    "/{conversation_id}/messages",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(chat_limiter)],
)
async def send_message(
    user: Annotated[User, Depends(PermissionChecker("conversations:create"))],
    conversation_id: UUID,
    data: MessageCreate,
    request: Request,
):
    correlation_id = getattr(request.state, "correlation_id", "web-request")

    async with async_session() as session:
        result = await send_message_service(
            session=session,
            conversation_id=conversation_id,
            user_id=user.id,
            content=data.content,
            document_id=data.document_id,
            correlation_id=correlation_id
        )

    return SuccessResponse[dict](
        data={
            "user_message": MessageResponse.model_validate(result["user_message"]),
            "assistant_message": {
                **MessageResponse.model_validate(result["assistant_message"]).model_dump(),
                "citations": result["citations"]
            }
        },
        message="Message sent successfully",
    )
