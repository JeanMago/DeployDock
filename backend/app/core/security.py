import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from cryptography.fernet import Fernet
from fastapi import HTTPException, Request

from app.core.config import settings

JWT_ALGORITHM = "HS256"


def _derive_fernet_key(secret: str) -> bytes:
    """
    Deriva uma chave Fernet de 32 bytes (base64url) a partir do SECRET_KEY.
    """
    key_bytes = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(key_bytes)


fernet = Fernet(_derive_fernet_key(settings.SECRET_KEY))


def get_password_hash(password: str) -> str:
    """Gera hash PBKDF2-HMAC-SHA256 com salt aleatório."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"pbkdf2:sha256:100000${salt.hex()}${dk.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha em texto puro confere com o hash armazenado."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 3:
            return False
        header, salt_hex, hash_hex = parts
        _, _, iterations_str = header.split(":")
        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)
        expected_dk = bytes.fromhex(hash_hex)
        dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(dk, expected_dk)
    except Exception:
        return False


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Cria um token JWT codificado com expiração."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodifica e valida o token JWT."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Token inválido ou expirado: {e}")


async def verify_github_signature(request: Request) -> bytes:
    """Valida a assinatura HMAC-SHA256 do webhook do GitHub."""
    signature_header = request.headers.get("X-Hub-Signature-256")
    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing signature")

    payload_body = await request.body()
    secret = settings.GITHUB_WEBHOOK_SECRET.encode("utf-8")
    expected_signature = (
        "sha256=" + hmac.new(secret, payload_body, digestmod=hashlib.sha256).hexdigest()
    )

    if not hmac.compare_digest(signature_header, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    return payload_body


def encrypt_value(value: str) -> str:
    """Encripta um valor usando Fernet (AES-128-CBC + HMAC-SHA256)."""
    return fernet.encrypt(value.encode()).decode()


def decrypt_value(encrypted: str) -> str:
    """Decripta um valor previamente encriptado com encrypt_value."""
    return fernet.decrypt(encrypted.encode()).decode()
