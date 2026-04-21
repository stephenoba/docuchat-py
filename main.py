from fastapi import FastAPI
from decouple import config
from pwdlib import PasswordHash


SECRET_KEY = config("SECRET_KEY")

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}