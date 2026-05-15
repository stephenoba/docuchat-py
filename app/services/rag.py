import time
from typing import List, Optional
from app.schemas.document import SearchResult, Citation, AssembledContext
from app.schemas.conversation import RAGResponse, TokenUsage
from app.core.logger import client_logger as logger
from app.core.config import get_settings, AI_EVENTS
from app.core.prompt import RAG_SYSTEM_PROMPT
from app.services.breaker import openai_request
from app.core.utils import safe_dispatch

settings = get_settings()
CONTEXT_TOKEN_BUDGET = 3500


def is_redundant(candidate: SearchResult, selected: List[SearchResult]) -> bool:
    """
    Check if a candidate chunk is redundant (adjacent to an already selected chunk from the same document).
    """
    return any(
        s.document_id == candidate.document_id and abs(s.chunk_index - candidate.chunk_index) <= 1
        for s in selected
    )


def assemble_context(search_results: List[SearchResult]) -> AssembledContext:
    """
    Selects the best chunks that fit within the token budget and formats them for the prompt.
    Includes deduplication to avoid adjacent overlapping chunks.
    """
    selected: List[SearchResult] = []
    total_tokens = 0

    # search_results are expected to be already sorted by score descending from the search service
    for result in search_results:
        # Deduplication: Skip if redundant
        if is_redundant(result, selected):
            continue

        if total_tokens + result.token_count > CONTEXT_TOKEN_BUDGET:
            break  # Budget exhausted
        
        selected.append(result)
        total_tokens += result.token_count

    # Build citations
    citations = [
        Citation(
            index=i + 1,
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            document_title=chunk.document_title,
            chunk_index=chunk.chunk_index,
            score=chunk.score
        )
        for i, chunk in enumerate(selected)
    ]

    # Build the context text block with source labels
    context_parts = [
        f'[Source {i + 1}: "{chunk.document_title}", Section {chunk.chunk_index + 1}]\n{chunk.content}'
        for i, chunk in enumerate(selected)
    ]
    
    context_text = "\n\n---\n\n".join(context_parts)

    return AssembledContext(
        chunks=selected,
        context_text=context_text,
        total_tokens=total_tokens,
        citations=citations
    )


async def generate_rag_response(
    question: str,
    context: AssembledContext,
    user_id: str,
    conversation_id: str,
    correlation_id: str,
    conversation_history: Optional[List[dict]] = None,
) -> RAGResponse:
    """
    Generates a RAG response using the provided context and conversation history.
    """
    # Build the messages array
    messages = [
        {"role": "system", "content": RAG_SYSTEM_PROMPT},
    ]

    # Add recent conversation history (last 5 exchanges = 10 messages)
    if conversation_history:
        recent = conversation_history[-10:]
        messages.extend(recent)

    # Add the context and question
    if context.chunks:
        content = (
            "Here is the relevant context from my documents:\n\n"
            f"{context.context_text}\n\n"
            "---\n\n"
            f"My question: {question}"
        )
    else:
        # No relevant context found
        content = (
            "No relevant context was found in my documents for this question.\n\n"
            f"My question: {question}"
        )

    messages.append({"role": "user", "content": content})

    start_time = time.perf_counter()

    # Call the LLM through the circuit breaker
    # Note: openai_request returns a Response object
    resp = await openai_request(
        "POST",
        "/chat/completions",
        {
            "model": settings.OPENAI_MODEL,
            "messages": messages,
            "temperature": 0.1,  # Low temperature for factual answers
            "max_tokens": 1500,
        }
    )

    result = resp.json()
    answer = result["choices"][0]["message"]["content"]
    usage = result["usage"]
    duration_ms = int((time.perf_counter() - start_time) * 1000)

    # Calculate cost (GPT-4o pricing as default)
    # Input: $2.50 / 1M tokens, Output: $10.00 / 1M tokens
    prompt_tokens = usage["prompt_tokens"]
    completion_tokens = usage["completion_tokens"]
    
    cost_usd = (
        (prompt_tokens / 1_000_000) * 2.50 +
        (completion_tokens / 1_000_000) * 10.00
    )

    logger.info(
        "RAG response generated",
        extra={
            "correlationId": correlation_id,
            "conversationId": conversation_id,
            "model": settings.OPENAI_MODEL,
            "contextChunks": len(context.chunks),
            "promptTokens": prompt_tokens,
            "completionTokens": completion_tokens,
            "costUsd": round(cost_usd, 6),
            "durationMs": duration_ms,
        }
    )

    # Track usage
    safe_dispatch(
        AI_EVENTS.CHAT_COMPLETED.value,
        payload={
            "user_id": user_id,
            "conversation_id": conversation_id,
            "correlation_id": correlation_id,
            "model": settings.OPENAI_MODEL,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": cost_usd,
        }
    )

    return RAGResponse(
        answer=answer,
        citations=context.citations,
        tokens_used=TokenUsage(
            prompt=prompt_tokens,
            completion=completion_tokens,
            total=usage["total_tokens"]
        ),
        cost_usd=cost_usd,
        model=settings.OPENAI_MODEL
    )
