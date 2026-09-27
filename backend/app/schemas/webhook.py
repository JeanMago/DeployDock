from pydantic import BaseModel
from typing import Optional

class WebhookResponse(BaseModel):
    status: str
    branch: Optional[str] = None
    commit: Optional[str] = None
    delivery: Optional[str] = None

class SystemInfo(BaseModel):
    docker_version: str
    containers_count: int
    images_count: int
    volumes_count: int
    networks_count: int
