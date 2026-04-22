from typing import Generic, Optional, TypeVar, Any
from pydantic import BaseModel

DataT = TypeVar("DataT")

class BaseResponse(BaseModel, Generic[DataT]):
    status: str
    status_code: int
    message: str
    data: Optional[DataT] = None