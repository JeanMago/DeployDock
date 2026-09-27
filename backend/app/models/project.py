from sqlalchemy import Column, String, Boolean, Integer, DateTime
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy.sql import func
from app.db.base import Base
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
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    deployments = relationship("Deployment", back_populates="project", cascade="all, delete-orphan")
    environment_variables = relationship("EnvironmentVariable", back_populates="project", cascade="all, delete-orphan")
