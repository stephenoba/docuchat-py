from fastapi import APIRouter

from api.v1.auth import auth_router
from api.v1.user import user_router
from api.v1.document import document_router
from api.v1.conversation import conversation_router


api_v1_router = APIRouter()

api_v1_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(user_router, prefix="/user", tags=["user"])
api_v1_router.include_router(document_router, prefix="/document", tags=["document"])
api_v1_router.include_router(
    conversation_router, prefix="/conversation", tags=["conversation"]
)
