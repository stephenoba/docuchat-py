from pypdf import PdfReader
from io import BytesIO
import re

SUPPORTED_FILE_FORMATS = {"txt": "text", "pdf": "pdf", "md": "markdown"}

def detect_format(filename: str) -> str:
    """Detect file format from filename."""
    ext = filename.split(".").pop().lower()
    if ext in SUPPORTED_FILE_FORMATS:
        return SUPPORTED_FILE_FORMATS[ext]
    raise ValueError(f"Unsupported file format: .{ext}")

def extract_pdf_text(content_bytes: bytes) -> tuple[str, int]:
    """Extract text and page count from PDF bytes."""
    reader = PdfReader(BytesIO(content_bytes))
    text = ""
    page_count = len(reader.pages)
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text, page_count

def strip_markdown(content: str) -> str:
    """Strip markdown from content."""
    # Headers
    content = re.sub(r'#{1,6}\s+', '', content)
    # Bold/italic
    content = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', content)
    # Links
    content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)
    # Code blocks
    content = re.sub(r'`{1,3}[^`]*`{1,3}', '', content)
    # List markers
    content = re.sub(r'^[\-*+]\s+', '', content, flags=re.MULTILINE)
    return content.strip()

def clean_extracted_text(content: str) -> str:
    """Clean extracted text using regex to normalize spacing."""
    content = content.replace('\r\n', '\n')
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = re.sub(r'\s{3,}', ' ', content)
    return content.strip()

def extract_text(
    content: bytes,
    format: str,
) -> dict[str, str | int]:
    if format == 'text':
        return {
            'text': content.decode('utf-8'),
            'page_count': 1
        }
    elif format == 'markdown':
        return {
            'text': strip_markdown(content.decode('utf-8')),
            'page_count': 1
        }
    elif format == 'pdf':
        text, page_count = extract_pdf_text(content)
        return {
            'text': text,
            'page_count': page_count
        }
    else:
        raise ValueError(f"Unsupported format: {format}")
