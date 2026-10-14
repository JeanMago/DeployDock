from fastapi import APIRouter, Depends
from app.services.docker_service import DockerService
from app.api.deps import get_docker_service, require_role
from app.schemas.webhook import SystemInfo

router = APIRouter(dependencies=[Depends(require_role("admin", "developer"))])

@router.get("/info", response_model=SystemInfo)
async def system_info(docker: DockerService = Depends(get_docker_service)):
    return await docker.get_system_info()

@router.get("/images")
async def list_images(docker: DockerService = Depends(get_docker_service)):
    return await docker.list_images()

@router.delete("/images/{image_id}")
async def remove_image(image_id: str, docker: DockerService = Depends(get_docker_service)):
    await docker.remove_image(image_id)
    return {"message": "Removed"}

@router.get("/volumes")
async def list_volumes(docker: DockerService = Depends(get_docker_service)):
    return await docker.list_volumes()

@router.get("/networks")
async def list_networks(docker: DockerService = Depends(get_docker_service)):
    return await docker.list_networks()

@router.post("/prune")
async def prune_system(docker: DockerService = Depends(get_docker_service)):
    return await docker.prune_system()
