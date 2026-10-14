from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, require_role
from app.core.security import verify_password, create_access_token, get_password_hash
from app.models.user import User
from app.schemas.user import LoginRequest, TokenResponse, UserRead, UserCreate

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Autentica o usuário por username ou email e retorna o token JWT."""
    username_or_email = login_data.username.strip().lower()
    result = await db.execute(
        select(User).where(
            (User.username.ilike(username_or_email)) | (User.email.ilike(username_or_email))
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nome de usuário ou senha incorretos.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta conta de usuário está desativada.",
        )

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


@router.get("/users", response_model=list[UserRead], dependencies=[Depends(require_role("admin"))])
async def list_users(db: AsyncSession = Depends(get_db)):
    """Lista todos os usuários (acesso restrito a administradores)."""
    result = await db.execute(select(User))
    return result.scalars().all()


@router.post("/users", response_model=UserRead, dependencies=[Depends(require_role("admin"))])
async def create_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
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
        role=user_in.role,
        is_active=user_in.is_active,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
