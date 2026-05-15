import json
from uuid import UUID
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from fastapi import HTTPException, status

from app.models.models import Conversation, Message, Document
from app.services.search import semantic_search
from app.services.rag import assemble_context, generate_rag_response
from app.core.utils import utcnow


async def send_message(
    session: AsyncSession,
    conversation_id: UUID,
    user_id: UUID,
    content: str,
    document_id: Optional[UUID] = None,
    correlation_id: Optional[str] = None,
):
    """
    Handles the full RAG pipeline: retrieval, augmentation, and generation.
    """
    # 1. Verify conversation ownership
    conversation = await session.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    # 2. Verify document if provided
    if document_id:
        document = await session.get(Document, document_id)
        if not document or document.user_id != user_id or document.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            )

    # 3. Save user message
    user_message = Message(
        conversation_id=conversation_id,
        document_id=document_id,
        role="user",
        content=content,
    )
    session.add(user_message)
    await session.flush()  # To get IDs if needed

    # 4. Load recent conversation history (last 10 messages)
    stmt = (
        select(Message.role, Message.content)
        .where(Message.conversation_id == conversation_id)
        .order_by(desc(Message.created_at))
        .limit(10)
    )
    history_results = (await session.execute(stmt)).all()
    # Reverse to get chronological order
    conversation_history = [
        {"role": r.role, "content": r.content} for r in reversed(history_results)
    ]

    # 5. RAG: Retrieve (Semantic Search)
    search_results = await semantic_search(
        query=content,
        user_id=user_id,
        session=session,
        document_id=document_id,
        correlation_id=correlation_id
    )

    # 6. RAG: Augment (Assemble Context)
    context = assemble_context(search_results)

    # 7. RAG: Generate (LLM Response)
    rag_response = await generate_rag_response(
        question=content,
        context=context,
        user_id=str(user_id),
        conversation_id=str(conversation_id),
        correlation_id=correlation_id or "rag-gen",
        conversation_history=conversation_history
    )

    # 8. Save assistant message with metadata
    assistant_message = Message(
        conversation_id=conversation_id,
        document_id=document_id,
        role="assistant",
        content=rag_response.answer,
        prompt_tokens=rag_response.tokens_used.prompt,
        completion_tokens=rag_response.tokens_used.completion,
        cost_usd=rag_response.cost_usd,
        # We store citations as a JSON string in 'sources' or metadata
        sources=json.dumps([c.model_dump(mode="json") for c in rag_response.citations]),
    )
    session.add(assistant_message)

    # 9. Touch conversation updatedAt
    conversation.updated_at = utcnow()
    session.add(conversation)

    await session.commit()
    await session.refresh(user_message)
    await session.refresh(assistant_message)

    return {
        "user_message": user_message,
        "assistant_message": assistant_message,
        "citations": rag_response.citations
    }
