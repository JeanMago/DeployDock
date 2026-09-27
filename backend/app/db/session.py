"""
Configuração do banco de dados PostgreSQL com SQLAlchemy 2.0 async.

Utiliza asyncpg como driver assíncrono para PostgreSQL.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.db.base import Base

# Engine assíncrona
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# Factory de sessões assíncronas
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Injeção de dependência para rotas FastAPI.
    Gerencia o ciclo de vida da sessão com commit/rollback automático.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Cria todas as tabelas no banco de dados se não existirem."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
