import hmac
import hashlib
from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader
from cryptography.fernet import Fernet
from app.core.config import settings

fernet = Fernet(settings.SECRET_KEY.encode() if len(settings.SECRET_KEY) == 44 else Fernet.generate_key())

async def verify_github_signature(request: Request) -> bytes:
    signature_header = request.headers.get("X-Hub-Signature-256")
    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing signature")

    payload_body = await request.body()
    secret = settings.GITHUB_WEBHOOK_SECRET.encode("utf-8")
    expected_signature = "sha256=" + hmac.new(secret, payload_body, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(signature_header, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    return payload_body

def encrypt_value(value: str) -> str:
    return fernet.encrypt(value.encode()).decode()

def decrypt_value(encrypted: str) -> str:
    return fernet.decrypt(encrypted.encode()).decode()
