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

# Importar todos os modelos para que Base.metadata os registre antes do create_all.
# Sem esses imports, o SQLAlchemy não encontra as tabelas ao chamar metadata.create_all().
import app.models.project          # noqa: F401
import app.models.deployment        # noqa: F401
import app.models.environment       # noqa: F401

# Engine assíncrona
is_sqlite = settings.DATABASE_URL.startswith("sqlite")
engine_kwargs: dict = {"echo": False}
if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
    })

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

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
    global engine, async_session_factory
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        if "postgresql" in settings.DATABASE_URL:
            import logging
            logger = logging.getLogger("deploydock")
            logger.warning(
                f"PostgreSQL indisponível ({e}). Alternando para SQLite local (deploydock.db)..."
            )
            engine = create_async_engine(
                "sqlite+aiosqlite:///deploydock.db",
                connect_args={"check_same_thread": False},
            )
            async_session_factory = async_sessionmaker(
                bind=engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        else:
            raise
