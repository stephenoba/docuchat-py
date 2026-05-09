from typing import Generic, Optional, TypeVar, List
from pydantic import BaseModel

DataT = TypeVar("DataT")


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Optional[List[ErrorDetail]] = None


class SuccessResponse(BaseModel, Generic[DataT]):
    success: bool = True
    data: Optional[DataT] = None
    message: Optional[str] = None
    meta: Optional[PaginationMeta] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorBody
