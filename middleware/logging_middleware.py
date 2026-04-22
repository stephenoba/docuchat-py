import time
import logging
from pathlib import Path
from fastapi import Request

# Configure logs directory
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "api.log"

# Configure logger for this module
logger = logging.getLogger("api_logger")
logger.setLevel(logging.INFO)

# Formatter for file (includes timestamp)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Formatter for console (cleaner)
console_formatter = logging.Formatter('%(message)s')

# Clear existing handlers to prevent duplicates during reload
if logger.handlers:
    logger.handlers.clear()

# Add File Handler
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Add Stream Handler (Console)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(console_formatter)
logger.addHandler(stream_handler)

async def logging_middleware(request: Request, call_next):
    """
    Middleware to log every API request with timing and client metadata.
    """
    start_time = time.time()
    
    # Process the request
    try:
        response = await call_next(request)
    except Exception as e:
        # In case of an unhandled exception before the response is formed
        duration = (time.time() - start_time) * 1000
        client_ip = request.client.host if request.client else "Unknown"
        user_agent = request.headers.get("user-agent", "Unknown")
        
        logger.error(
            f"[HTTP] {request.method} {request.url.path} | "
            f"FAILURE (Exception) | "
            f"Time: {duration:.2f}ms | "
            f"IP: {client_ip} | "
            f"UA: {user_agent} | Error: {str(e)}"
        )
        raise e
        
    duration = (time.time() - start_time) * 1000
    
    # Extract metadata
    status_code = response.status_code
    method = request.method
    path = request.url.path
    client_ip = request.client.host if request.client else "Unknown"
    user_agent = request.headers.get("user-agent", "Unknown")
    
    # Success/Failure determined by status code
    result = "SUCCESS" if 200 <= status_code < 400 else "FAILURE"
    
    log_message = (
        f"[HTTP] {method} {path} | "
        f"{result} ({status_code}) | "
        f"Time: {duration:.2f}ms | "
        f"IP: {client_ip} | "
        f"UA: {user_agent}"
    )
    
    if result == "SUCCESS":
        logger.info(log_message)
    else:
        logger.error(log_message)
        
    return response
