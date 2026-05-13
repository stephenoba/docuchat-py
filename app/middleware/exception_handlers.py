from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.schemas import ErrorResponse, ErrorBody, ErrorDetail
from app.core.logger import error_logger as logger
from app.core.security import scrub_sensitive_data



async def http_exception_handler(request: Request, exc: HTTPException):
    detail = str(exc.detail)
    error_code = detail.upper().replace(" ", "_")
    correlation_id = request.headers.get("X-Correlation-ID")
    
    logger.warning(f"[{correlation_id}] [HTTP {exc.status_code}] {request.method} {request.url.path} - {detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=ErrorBody(
                code=error_code,
                message=scrub_sensitive_data(detail),
            )

        ).model_dump(),
        headers=getattr(exc, "headers", None),
    )



async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = []
    correlation_id = request.headers.get("X-Correlation-ID")
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        details.append(
            ErrorDetail(
                field=field or "unknown",
                message=scrub_sensitive_data(error["msg"]),
            )

        )

    logger.warning(f"[{correlation_id}] [Validation Error] {request.method} {request.url.path} - {len(details)} fields failed")
    
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error=ErrorBody(
                code="VALIDATION_ERROR",
                message="Request validation failed",
                details=details,
            )
        ).model_dump(),
    )


async def generic_exception_handler(request: Request, exc: Exception):
    correlation_id = request.headers.get("X-Correlation-ID")
    logger.exception(f"[{correlation_id}] [Unhandled Error] {request.method} {request.url.path} - {str(exc)}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=ErrorBody(
                code="INTERNAL_ERROR",
                message=scrub_sensitive_data(str(exc)) if not isinstance(exc, HTTPException) else "An unexpected error occurred",
            )

        ).model_dump(),
    )
