from fastapi import APIRouter, Depends, HTTPException
from typing import List, Any
from app.services.docker_service import DockerService
from app.api.deps import get_docker_service
from app.schemas.container import ContainerSummary, ContainerDetail

router = APIRouter()

@router.get("", response_model=List[ContainerSummary])
async def list_containers(all: bool = True, docker: DockerService = Depends(get_docker_service)):
    return await docker.list_containers(all=all)

@router.get("/{container_id}", response_model=ContainerDetail)
async def get_container(container_id: str, docker: DockerService = Depends(get_docker_service)):
    try:
        return await docker.get_container(container_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{container_id}/start")
async def start_container(container_id: str, docker: DockerService = Depends(get_docker_service)):
    await docker.start_container(container_id)
    return {"message": "Started"}

@router.post("/{container_id}/stop")
async def stop_container(container_id: str, docker: DockerService = Depends(get_docker_service)):
    await docker.stop_container(container_id)
    return {"message": "Stopped"}

@router.post("/{container_id}/restart")
async def restart_container(container_id: str, docker: DockerService = Depends(get_docker_service)):
    await docker.restart_container(container_id)
    return {"message": "Restarted"}

@router.delete("/{container_id}")
async def remove_container(container_id: str, docker: DockerService = Depends(get_docker_service)):
    await docker.remove_container(container_id)
    return {"message": "Removed"}

@router.get("/{container_id}/logs")
async def get_container_logs(container_id: str, tail: int = 100, docker: DockerService = Depends(get_docker_service)):
    return await docker.get_container_logs(container_id, tail)
