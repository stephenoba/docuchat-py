from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from schemas import ErrorResponse, ErrorBody, ErrorDetail
from logger import error_logger


async def http_exception_handler(request: Request, exc: HTTPException):
    detail = str(exc.detail)
    error_code = detail.upper().replace(" ", "_")
    
    error_logger.warning(f"[HTTP {exc.status_code}] {request.method} {request.url.path} - {detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=ErrorBody(
                code=error_code,
                message=detail,
            )
        ).model_dump(),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        details.append(
            ErrorDetail(
                field=field or "unknown",
                message=error["msg"],
            )
        )

    error_logger.warning(f"[Validation Error] {request.method} {request.url.path} - {len(details)} fields failed")
    
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
    error_logger.exception(f"[Unhandled Error] {request.method} {request.url.path} - {str(exc)}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=ErrorBody(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred",
            )
        ).model_dump(),
    )
