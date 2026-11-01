import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel as _BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_role
from app.core.security import (
    build_totp_uri,
    create_access_token,
    decrypt_value,
    encrypt_value,
    generate_totp_secret,
    get_password_hash,
    verify_password,
    verify_totp,
)
from app.core.waf import security_manager
from app.models.user import User
from app.schemas.user import LoginRequest, TokenResponse, UserCreate, UserRead

router = APIRouter()


class PasswordChangeRequest(_BaseModel):
    current_password: str
    new_password: str


class RoleUpdateRequest(_BaseModel):
    role: str  # 'admin' | 'developer' | 'viewer'


class TotpVerifyRequest(_BaseModel):
    code: str


def _resolve_totp_secret(user: User) -> str | None:
    raw = getattr(user, "totp_secret", None)
    if not raw:
        return None
    if raw.startswith("enc:"):
        try:
            return decrypt_value(raw[4:])
        except Exception:
            return None
    return raw


@router.post("/login", response_model=TokenResponse)
async def login(request: Request, login_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Autentica o usuário por username ou email e retorna o token JWT, com proteção Anti-Brute-Force e 2FA/TOTP."""
    client_ip = security_manager.get_client_ip(request)
    username_or_email = login_data.username.strip().lower()
    result = await db.execute(
        select(User).where(
            (User.username.ilike(username_or_email)) | (User.email.ilike(username_or_email))
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(login_data.password, user.hashed_password):
        blocked = security_manager.record_login_failure(client_ip, username_or_email)
        if blocked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Muitas tentativas falhas de login. Seu IP foi bloqueado temporariamente por segurança.",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nome de usuário ou senha incorretos.",
        )

    if not user.is_active:
        security_manager.record_login_failure(client_ip, username_or_email)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta conta de usuário está desativada.",
        )

    if bool(user.totp_enabled):
        secret = _resolve_totp_secret(user)
        if secret:
            if not login_data.otp_code or not login_data.otp_code.strip():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="2FA_REQUIRED: Informe o código de 6 dígitos do autenticador (TOTP).",
                )
            if not verify_totp(secret, login_data.otp_code):
                security_manager.record_login_failure(client_ip, username_or_email)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Código 2FA (TOTP) inválido ou expirado.",
                )

    security_manager.record_login_success(client_ip, user.username)

    token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role}
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserRead.model_validate(user),
    )


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    """Retorna os dados do usuário atualmente logado e seu nível de permissão."""
    return current_user


@router.post("/2fa/setup")
async def setup_2fa(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Gera um novo segredo TOTP (Base32) e URI otpauth:// para configurar Google Authenticator / Authy."""
    secret = generate_totp_secret()
    current_user.totp_secret = f"enc:{encrypt_value(secret)}"
    current_user.totp_enabled = False
    await db.commit()

    uri = build_totp_uri(secret, current_user.username)
    security_manager.log_event(
        event_type="rbac",
        severity="low",
        ip=security_manager.get_client_ip(request),
        path="/api/v1/auth/2fa/setup",
        detail=f"Setup de 2FA (TOTP) iniciado para '{current_user.username}'",
        user=current_user.username,
    )
    return {
        "secret": secret,
        "otpauth_uri": uri,
        "totp_enabled": False,
    }


@router.post("/2fa/enable")
async def enable_2fa(
    body: TotpVerifyRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Valida o código de 6 dígitos e ativa a autenticação em duas etapas (2FA) na conta."""
    secret = _resolve_totp_secret(current_user)
    if not secret:
        raise HTTPException(
            status_code=400,
            detail="Execute primeiro /api/v1/auth/2fa/setup para gerar o segredo TOTP.",
        )
    if not verify_totp(secret, body.code):
        raise HTTPException(
            status_code=400,
            detail="Código TOTP inválido. Verifique o horário do dispositivo e tente novamente.",
        )
    current_user.totp_enabled = True
    await db.commit()

    security_manager.log_event(
        event_type="rbac",
        severity="low",
        ip=security_manager.get_client_ip(request),
        path="/api/v1/auth/2fa/enable",
        detail=f"Autenticação 2FA (TOTP) ativada para '{current_user.username}'",
        user=current_user.username,
    )
    return {
        "totp_enabled": True,
        "message": "Autenticação em duas etapas (2FA/TOTP) ativada com sucesso.",
    }


@router.post("/2fa/disable")
async def disable_2fa(
    body: TotpVerifyRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Desativa o 2FA da conta mediante confirmação do código TOTP atual."""
    secret = _resolve_totp_secret(current_user)
    if secret and bool(current_user.totp_enabled):
        if not verify_totp(secret, body.code):
            raise HTTPException(status_code=400, detail="Código TOTP inválido para desativar 2FA.")
    current_user.totp_enabled = False
    current_user.totp_secret = None
    await db.commit()

    security_manager.log_event(
        event_type="rbac",
        severity="medium",
        ip=security_manager.get_client_ip(request),
        path="/api/v1/auth/2fa/disable",
        detail=f"Autenticação 2FA (TOTP) desativada para '{current_user.username}'",
        user=current_user.username,
    )
    return {
        "totp_enabled": False,
        "message": "Autenticação 2FA desativada.",
    }


@router.get("/users", response_model=list[UserRead], dependencies=[Depends(get_current_user)])
async def list_users(db: AsyncSession = Depends(get_db)):
    """Lista os usuários cadastrados (gerenciamento restrito a administradores)."""
    result = await db.execute(select(User))
    return result.scalars().all()


@router.post("/users", response_model=UserRead, dependencies=[Depends(require_role("admin"))])
async def create_user(
    user_in: UserCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cria novo usuário com role específica (acesso restrito a administradores)."""
    existing = await db.execute(
        select(User).where(
            (User.username == user_in.username) | (User.email == user_in.email)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username ou e-mail já cadastrados.",
        )

    new_user = User(
        username=user_in.username.strip(),
        email=user_in.email.strip().lower(),
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role if user_in.role in ("admin", "developer", "viewer") else "developer",
        is_active=user_in.is_active,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    security_manager.log_event(
        event_type="rbac",
        severity="low",
        ip=security_manager.get_client_ip(request),
        path="/api/v1/auth/users",
        detail=f"Usuário '{new_user.username}' criado com perfil '{new_user.role}'",
        user=current_user.username,
    )
    return new_user


@router.put("/password")
async def change_password(
    body: PasswordChangeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Permite ao usuário logado alterar sua própria senha (essencial para produção)."""
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="A senha atual informada está incorreta.")
    if len(body.new_password.strip()) < 6:
        raise HTTPException(status_code=400, detail="A nova senha deve ter pelo menos 6 caracteres.")
    current_user.hashed_password = get_password_hash(body.new_password.strip())
    await db.commit()

    security_manager.log_event(
        event_type="rbac",
        severity="low",
        ip=security_manager.get_client_ip(request),
        path="/api/v1/auth/password",
        detail=f"Senha da conta '{current_user.username}' atualizada",
        user=current_user.username,
    )
    return {"message": "Senha atualizada com sucesso."}


@router.patch("/users/{user_id}/role", response_model=UserRead, dependencies=[Depends(require_role("admin"))])
async def update_user_role(
    user_id: _uuid.UUID,
    body: RoleUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Altera o papel RBAC (admin, developer, viewer) de um usuário."""
    if body.role not in ("admin", "developer", "viewer"):
        raise HTTPException(status_code=400, detail="Papel inválido. Use 'admin', 'developer' ou 'viewer'.")
    if user_id == current_user.id and body.role != "admin":
        raise HTTPException(status_code=400, detail="Você não pode remover seu próprio privilégio de admin.")
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    old_role = user.role
    user.role = body.role
    await db.commit()
    await db.refresh(user)

    security_manager.log_event(
        event_type="rbac",
        severity="medium",
        ip=security_manager.get_client_ip(request),
        path=f"/api/v1/auth/users/{user_id}/role",
        detail=f"Permissão RBAC de '{user.username}' alterada: {old_role} → {user.role}",
        user=current_user.username,
    )
    return user


@router.patch("/users/{user_id}/toggle", response_model=UserRead, dependencies=[Depends(require_role("admin"))])
async def toggle_user_active(
    user_id: _uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode desativar sua própria conta.")
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    user.is_active = not user.is_active
    await db.commit()
    await db.refresh(user)

    security_manager.log_event(
        event_type="rbac",
        severity="medium",
        ip=security_manager.get_client_ip(request),
        path=f"/api/v1/auth/users/{user_id}/toggle",
        detail=f"Conta '{user.username}' {'ativada' if user.is_active else 'desativada'}",
        user=current_user.username,
    )
    return user


@router.delete("/users/{user_id}", dependencies=[Depends(require_role("admin"))])
async def delete_user_account(
    user_id: _uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode excluir sua própria conta.")
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    uname = user.username
    await db.delete(user)
    await db.commit()

    security_manager.log_event(
        event_type="rbac",
        severity="medium",
        ip=security_manager.get_client_ip(request),
        path=f"/api/v1/auth/users/{user_id}",
        detail=f"Conta de usuário '{uname}' removida",
        user=current_user.username,
    )
    return {"message": "Usuário removido com sucesso."}
