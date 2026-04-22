from typing import Annotated

from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordBearer

from config import get_settings
from api.v1 import api_v1_router
from middleware.logging_middleware import logging_middleware

settings = get_settings()

oauth2_password_bearer = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

app = FastAPI()

app.middleware("http")(logging_middleware)
app.include_router(api_v1_router, prefix="/api/v1")

async def get_current_user(token: Annotated[str, Depends(oauth2_password_bearer)]):
    return token

@app.get("/health")
async def health_check():
    return {"status": "ok"}