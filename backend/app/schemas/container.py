from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class ContainerSummary(BaseModel):
    id: str
    name: str
    status: str
    image: str
    ports: Dict[str, Any]
    created: str
    state: str

class ContainerDetail(ContainerSummary):
    mounts: List[Dict[str, Any]]
    networks: Dict[str, Any]
    env: List[str]
    config: Dict[str, Any]

class ContainerStats(BaseModel):
    cpu_percent: float
    memory_usage_mb: float
    memory_limit_mb: float
    memory_percent: float
    network_rx: float
    network_tx: float

class ContainerAction(BaseModel):
    action: str
