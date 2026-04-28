
def split_document(content: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
    """Split a document into chunks of text."""
    chunks = []
    for i in range(0, len(content), chunk_size - chunk_overlap):
        chunks.append(content[i:i + chunk_size])
    return chunks