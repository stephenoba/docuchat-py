import time
from fastapi import Request
from logger import api_logger as logger


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
