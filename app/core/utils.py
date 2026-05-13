import tiktoken
from datetime import datetime, timezone
from typing import List

def utcnow() -> datetime:
    """Return a naive UTC datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

def split_document(
    content: str, 
    chunk_size: int = 500, 
    chunk_overlap: int = 100,
    model_name: str = "gpt-4o"
) -> List[dict]:
    """
    Split a document into chunks of text using token-based splitting.
    Returns a list of dictionaries with 'content' and 'token_count' keys.
    """
    if not content:
        return []

    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        # Fallback to cl100k_base (used by gpt-3.5-turbo and gpt-4)
        encoding = tiktoken.get_encoding("cl100k_base")
    
    tokens = encoding.encode(content)
    chunks = []
    
    # Step through the tokens with the specified overlap
    # i is the starting token index
    for i in range(0, len(tokens), chunk_size - chunk_overlap):
        # Slice the tokens for this chunk
        chunk_tokens = tokens[i : i + chunk_size]
        chunk_text = encoding.decode(chunk_tokens)
        
        chunks.append({
            "content": chunk_text,
            "token_count": len(chunk_tokens)
        })
        
        # Stop if we've reached the end of the tokens
        if i + chunk_size >= len(tokens):
            break
            
    return chunks