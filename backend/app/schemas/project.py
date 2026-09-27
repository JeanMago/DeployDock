from pydantic import BaseModel, ConfigDict
import uuid
from datetime import datetime
from typing import Optional

class ProjectBase(BaseModel):
    name: str
    repo_url: str
    branch: str = "main"
    webhook_secret: str
    docker_compose_path: str = "docker-compose.yml"
    dockerfile_path: str = "Dockerfile"
    auto_deploy: bool = True
    health_check_url: Optional[str] = None
    health_check_interval: int = 30

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    repo_url: Optional[str] = None
    branch: Optional[str] = None
    webhook_secret: Optional[str] = None
    docker_compose_path: Optional[str] = None
    dockerfile_path: Optional[str] = None
    auto_deploy: Optional[bool] = None
    health_check_url: Optional[str] = None
    health_check_interval: Optional[int] = None

class ProjectRead(ProjectBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ProjectList(BaseModel):
    id: uuid.UUID
    name: str
    repo_url: str
    branch: str
    auto_deploy: bool
    
    model_config = ConfigDict(from_attributes=True)
