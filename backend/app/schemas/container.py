from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class ContainerSummary(BaseModel):
    id: str
    name: str
    status: str
    image: str
    # O Docker retorna ports como Dict[str, Optional[List[Dict]]] — pode ser vazio ou None
    ports: Optional[Dict[str, Any]] = None
    # created pode ser None em containers muito recentes ou em estado transiente
    created: Optional[str] = None
    # state pode ser None para containers em estados intermediários
    state: Optional[str] = None
    labels: Optional[Dict[str, str]] = None
    public_url: Optional[str] = None


class ContainerDetail(ContainerSummary):
    mounts: Optional[List[Dict[str, Any]]] = None
    networks: Optional[Dict[str, Any]] = None
    env: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None
    restart_policy: Optional[Dict[str, Any]] = None


class ContainerStats(BaseModel):
    cpu_percent: float
    memory_usage_mb: float
    memory_limit_mb: float
    memory_percent: float
    # Bug fix: nomes alinhados com o retorno de DockerService.get_container_stats()
    network_rx_mb: float
    network_tx_mb: float


class ContainerAction(BaseModel):
    action: str
