import base64
import hashlib
import hmac

from cryptography.fernet import Fernet
from fastapi import HTTPException, Request

from app.core.config import settings


def _derive_fernet_key(secret: str) -> bytes:
    """
    Deriva uma chave Fernet de 32 bytes (base64url) a partir do SECRET_KEY.

    Fernet exige exatamente 32 bytes codificados em base64url.
    Usamos SHA-256 do SECRET_KEY para obter 32 bytes determinísticos,
    independente do tamanho ou formato da chave configurada.
    """
    key_bytes = hashlib.sha256(secret.encode("utf-8")).digest()  # 32 bytes
    return base64.urlsafe_b64encode(key_bytes)                   # 44 chars base64url


fernet = Fernet(_derive_fernet_key(settings.SECRET_KEY))


async def verify_github_signature(request: Request) -> bytes:
    """
    Valida a assinatura HMAC-SHA256 do webhook do GitHub.

    O GitHub envia o header X-Hub-Signature-256 com o valor
    'sha256=<hex_digest>' calculado sobre o payload usando o
    GITHUB_WEBHOOK_SECRET como chave.
    """
    signature_header = request.headers.get("X-Hub-Signature-256")
    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing signature")

    payload_body = await request.body()
    secret = settings.GITHUB_WEBHOOK_SECRET.encode("utf-8")

    # Bug fix: Python 3 usa hmac.new(key, msg, digestmod=) — não hmac.new()
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
