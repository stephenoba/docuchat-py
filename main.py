from fastapi import FastAPI
from config import get_settings
from pwdlib import PasswordHash


settings = get_settings()

password_hash = PasswordHash.recommended()

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}