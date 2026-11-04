import asyncio
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.core.security import get_password_hash, verify_password
from app.db.session import async_session_factory
from app.models.user import User
from sqlalchemy import select

async def main():
    new_password = sys.argv[1] if len(sys.argv) > 1 else "Tecnica2026@"
    username = sys.argv[2] if len(sys.argv) > 2 else "admin"

    print(f"Atualizando senha do usuário '{username}'...")
    hashed = get_password_hash(new_password)
    print(f"Hash gerado: {hashed}")
    assert verify_password(new_password, hashed), "Erro de validação do hash"

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if not user:
            print(f"Usuário '{username}' não encontrado! Criando...")
            user = User(
                username=username,
                email="admin@deploydock.local",
                hashed_password=hashed,
                role="admin",
                is_active=True
            )
            session.add(user)
        else:
            print(f"Usuário '{username}' encontrado (ID: {user.id}, email: {user.email}). Atualizando senha...")
            user.hashed_password = hashed
        await session.commit()
        print("Senha atualizada com sucesso no banco de dados!")

if __name__ == "__main__":
    asyncio.run(main())
