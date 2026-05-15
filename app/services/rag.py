from typing import List
from app.schemas.document import SearchResult, Citation, AssembledContext

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
