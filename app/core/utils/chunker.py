import tiktoken
from typing import List

def count_tokens(text: str, model_name: str = "gpt-4o") -> int:
    """Count tokens in a string using tiktoken."""
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


def get_last_n_tokens(text: str, n: int, model_name: str = "gpt-4o") -> str:
    """Extract the last n tokens from a string and return as text."""
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    return encoding.decode(tokens[-n:])


def recursive_split(
    text: str, 
    separators: List[str], 
    max_tokens: int, 
    model_name: str,
    base_offset: int = 0
) -> List[dict]:
    """Recursively split text based on a hierarchy of separators with absolute offsets."""
    # Base case: If the text is already within the token limit, return it as a single chunk
    if count_tokens(text, model_name) <= max_tokens:
        return [{"text": text, "start_char": base_offset}]

    # Iterate through separators in order of priority (e.g., paragraphs, then sentences, then words)
    for sep in separators:
        # Split text by the current separator and filter out empty parts
        parts = [p for p in text.split(sep) if p.strip()]
        if len(parts) <= 1:
            # If the separator doesn't split the text further, try the next separator in the list
            continue

        chunks = []
        current = ""
        char_offset = 0 # Tracks position relative to the start of the current recursive call's text
        chunk_start = 0 # Marks where the current accumulated chunk began

        for part in parts:
            # Try to combine the next part with the current buffer
            combined = current + sep + part if current else part
            
            # If combining exceeds the limit, push the current buffer and start a new chunk
            if count_tokens(combined, model_name) > max_tokens and current:
                chunks.append({
                    "text": current.strip(), 
                    "start_char": base_offset + chunk_start # Calculate absolute document position
                })
                current = part
                chunk_start = char_offset
            else:
                # Otherwise, continue accumulating
                if not current:
                    chunk_start = char_offset
                current = combined
            
            # Update the character offset by the length of the part and the separator
            char_offset += len(part) + len(sep)

        # Append the final remaining buffer
        if current.strip():
            chunks.append({
                "text": current.strip(), 
                "start_char": base_offset + chunk_start
            })

        # Post-processing: Recursively split any chunks that are still over the token limit
        # using the remaining (finer-grained) separators.
        result = []
        for chunk in chunks:
            if count_tokens(chunk["text"], model_name) > max_tokens:
                try:
                    sep_index = separators.index(sep)
                    remaining_seps = separators[sep_index + 1:]
                    if remaining_seps:
                        # Recursive call: Pass the chunk's absolute start_char as the new base_offset
                        result.extend(recursive_split(
                            chunk["text"], 
                            remaining_seps, 
                            max_tokens, 
                            model_name,
                            base_offset=chunk["start_char"]
                        ))
                    else:
                        # No more separators left to try; return the chunk as is (hard limit reached)
                        result.append(chunk)
                except ValueError:
                    result.append(chunk)
            else:
                # Chunk is within limits
                result.append(chunk)
        return result

    # Fallback: If no separators worked, return the text as a single chunk
    return [{"text": text, "start_char": base_offset}]


def add_overlap(
    chunks: List[dict], 
    overlap_tokens: int, 
    model_name: str
) -> List[dict]:
    """Prepend a portion of the previous chunk to the current one for context continuity."""
    if overlap_tokens == 0 or len(chunks) <= 1:
        return chunks

    result = [chunks[0]]
    for i in range(1, len(chunks)):
        prev_text = chunks[i-1]["text"]
        overlap_text = get_last_n_tokens(prev_text, overlap_tokens, model_name)
        result.append({
            "text": overlap_text + "\n" + chunks[i]["text"],
            "start_char": chunks[i]["start_char"]
        })
    return result


def split_document(
    content: str, 
    chunk_size: int = 500, 
    chunk_overlap: int = 50,
    min_chunk_tokens: int = 50,
    model_name: str = "gpt-4o"
) -> List[dict]:
    """
    Split a document into chunks using a recursive separator strategy.
    Uses tiktoken for accurate token counting and context overlap.
    """
    if not content:
        return []

    separators = [
        '\n\n', 
        '\n', 
        '. ', 
        '? ', 
        '! ', 
        ' '
    ]
    raw_chunks = recursive_split(content, separators, chunk_size, model_name)
    with_overlap = add_overlap(raw_chunks, chunk_overlap, model_name)
    final_chunks = []
    for i, c in enumerate(with_overlap):
        token_count = count_tokens(c["text"], model_name)
        if token_count >= min_chunk_tokens:
            final_chunks.append({
                "content": c["text"],
                "index": i,
                "token_count": token_count,
                "metadata": {
                    "start_char": c["start_char"],
                    "end_char": c["start_char"] + len(c["text"])
                }
            })
            
    return final_chunks