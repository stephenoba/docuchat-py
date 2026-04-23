from fastapi import APIRouter

from api.v1.auth import auth_router
from api.v1.user import user_router


api_v1_router = APIRouter()

api_v1_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(user_router, prefix="/user", tags=["user"])