import re
from typing import Any

# Sensitive data patterns
SENSITIVE_PATTERNS = [
    re.compile(r"Bearer [A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),  # JWT tokens
    re.compile(r"sk-[A-Za-z0-9\-]{20,}", re.IGNORECASE),           # OpenAI keys

    re.compile(r"password[\"']?\s*[:=]\s*[\"']?[^\"'\s,}]+[\"']?", re.IGNORECASE), # Passwords
]


def scrub_sensitive_data(data: Any) -> Any:
    """
    Recursively scrubs sensitive data from strings, lists, and dictionaries.
    Replaces sensitive patterns with '[REDACTED]'.
    """
    if isinstance(data, str):
        scrubbed = data
        for pattern in SENSITIVE_PATTERNS:
            scrubbed = pattern.sub("[REDACTED]", scrubbed)
        return scrubbed
    
    elif isinstance(data, dict):
        return {k: scrub_sensitive_data(v) for k, v in data.items()}
    
    elif isinstance(data, list):
        return [scrub_sensitive_data(item) for item in data]
    
    return data
