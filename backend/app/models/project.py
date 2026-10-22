from sqlalchemy import Column, String, Boolean, Integer, Float, DateTime
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy.sql import func
from app.db.base import Base
from app.core.routing import project_host, public_url as build_public_url
import uuid


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    repo_url: Mapped[str] = mapped_column(String, nullable=False)
    branch: Mapped[str] = mapped_column(String, default="main")
    webhook_secret: Mapped[str] = mapped_column(String, nullable=False)
    docker_compose_path: Mapped[str] = mapped_column(String, default="docker-compose.yml")
    dockerfile_path: Mapped[str] = mapped_column(String, default="Dockerfile")
    auto_deploy: Mapped[bool] = mapped_column(Boolean, default=True)
    health_check_url: Mapped[str | None] = mapped_column(String, nullable=True)
    health_check_interval: Mapped[int] = mapped_column(Integer, default=30)
    # --- URL pública (proxy reverso) ---
    subdomain: Mapped[str | None] = mapped_column(String(63), unique=True, nullable=True)
    custom_domain: Mapped[str | None] = mapped_column(String(253), unique=True, nullable=True)
    container_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # --- Recursos, Repositório Privado, Preview Deploys e Auto-Healing ---
    git_token: Mapped[str | None] = mapped_column(String, nullable=True)
    preview_deployments_enabled: Mapped[bool | None] = mapped_column(Boolean, default=True, nullable=True)
    memory_limit_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cpu_limit_cores: Mapped[float | None] = mapped_column(Float, nullable=True)
    auto_heal: Mapped[bool | None] = mapped_column(Boolean, default=True, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    deployments = relationship("Deployment", back_populates="project", cascade="all, delete-orphan")
    environment_variables = relationship("EnvironmentVariable", back_populates="project", cascade="all, delete-orphan")

    @property
    def public_host(self) -> str:
        return project_host(self.subdomain, self.custom_domain, self.name)

    @property
    def public_url(self) -> str:
        return build_public_url(self.public_host)

    @property
    def has_git_token(self) -> bool:
        return bool(self.git_token and self.git_token.strip())
