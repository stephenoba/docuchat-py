from typing import Annotated, List
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select, func

from auth import PermissionChecker
from models import User, Conversation, Message, Document
from schemas import SuccessResponse
from schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)
from dbmanager import async_session

conversation_router = APIRouter()


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

    from schemas import PaginationMeta

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
        conversation.updated_at = datetime.now()
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
    response_model=SuccessResponse[MessageResponse],
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    user: Annotated[User, Depends(PermissionChecker("conversations:create"))],
    conversation_id: UUID,
    data: MessageCreate,
):
    conversation = await Conversation.objects.get(id=conversation_id, user_id=user.id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    if data.document_id:
        document = await Document.objects.get(
            id=data.document_id, user_id=user.id, deleted_at=None
        )
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            )

    message = await Message.objects.create(
        conversation_id=conversation_id,
        role="user",
        content=data.content,
        document_id=data.document_id,
    )
    return SuccessResponse[MessageResponse](
        data=MessageResponse.model_validate(message),
        message="Message sent successfully",
    )
