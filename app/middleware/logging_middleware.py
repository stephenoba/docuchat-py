import uuid
import time
from fastapi import Request

from app.core.logger import api_logger as logger


async def api_logging_middleware(request: Request, call_next):

    """
    Middleware to log every API request with timing and client metadata.
    """
    start_time = time.time()
    correlation_id = request.headers.get("X-Correlation-Id", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id


    # Process the request
    try:
        response = await call_next(request)
        response.headers["X-Correlation-Id"] = correlation_id
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
            f"UA: {user_agent} | Error: {str(e)} | "
            f"Correlation ID: {correlation_id}"
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
    if status_code > 500:
        result = "SERVER_ERROR"
    elif status_code >= 400:
        result = "CLIENT_ERROR"
    else:
        result = "SUCCESS"

    log_message = (
        f"[HTTP] {method} {path} | "
        f"{result} ({status_code}) | "
        f"Time: {duration:.2f}ms | "
        f"IP: {client_ip} | "
        f"UA: {user_agent} | "
        f"Correlation ID: {correlation_id}"
    )

    if result == "SUCCESS":
        logger.info(log_message)
    elif result == "CLIENT_ERROR":
        logger.warning(log_message)
    elif result == "SERVER_ERROR":
        logger.error(log_message)

    return response
