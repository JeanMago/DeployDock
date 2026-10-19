from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from typing import List, Any, Optional
from app.services.docker_service import DockerService
from app.api.deps import get_docker_service, require_role, get_current_user
from app.core.waf import security_manager, validate_safe_container_command
from app.models.user import User
from app.schemas.container import ContainerSummary, ContainerDetail

router = APIRouter(dependencies=[Depends(require_role("admin", "developer"))])


class ContainerExecRequest(BaseModel):
    command: str
    workdir: Optional[str] = None


class QuickContainerRunRequest(BaseModel):
    image: str
    name: Optional[str] = None
    host_port: Optional[int] = None
    container_port: Optional[int] = None
    env_text: Optional[str] = None
    restart_policy: str = "unless-stopped"


@router.get("", response_model=List[ContainerSummary])
async def list_containers(all: bool = True, docker: DockerService = Depends(get_docker_service)):
    return await docker.list_containers(all=all)


@router.post("/run")
async def run_quick_container(
    body: QuickContainerRunRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    docker: DockerService = Depends(get_docker_service),
):
    image = (body.image or "").strip()
    if not image:
        raise HTTPException(status_code=400, detail="Informe o nome da imagem Docker (ex: redis:alpine).")

    ports_map = None
    if body.host_port and body.container_port:
        ports_map = {f"{body.container_port}/tcp": int(body.host_port)}

    env_map: dict[str, str] = {}
    if body.env_text and body.env_text.strip():
        for line in body.env_text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip():
                env_map[k.strip()] = v.strip()

    try:
        res = await docker.run_quick_container(
            image=image,
            name=body.name.strip() if body.name and body.name.strip() else None,
            ports=ports_map,
            env=env_map or None,
            restart_policy=body.restart_policy,
        )
        security_manager.log_event(
            event_type="deploy",
            severity="low",
            ip=security_manager.get_client_ip(request),
            path="/api/v1/containers/run",
            detail=f"Contêiner rápido iniciado a partir de '{image}' ({res.get('name')})",
            user=current_user.username,
            blocked=False,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Falha ao iniciar contêiner: {e}")


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
async def get_container_logs(
    container_id: str,
    tail: int = Query(250, ge=0, le=10000),
    timestamps: bool = Query(True),
    since_seconds: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    docker: DockerService = Depends(get_docker_service),
):
    try:
        return await docker.get_container_logs(
            container_id,
            tail=tail,
            timestamps=timestamps,
            since_seconds=since_seconds,
            search=search,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{container_id}/exec")
async def exec_in_container(
    container_id: str,
    body: ContainerExecRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    docker: DockerService = Depends(get_docker_service),
):
    if not body.command or not body.command.strip():
        raise HTTPException(status_code=400, detail="Informe um comando para executar.")
    safe_cmd = validate_safe_container_command(
        body.command,
        user=current_user.username,
        ip=security_manager.get_client_ip(request),
    )
    try:
        return await docker.exec_container_command(
            container_id, safe_cmd, workdir=body.workdir
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{container_id}/files")
async def list_files_in_container(
    container_id: str,
    path: str = Query("/"),
    docker: DockerService = Depends(get_docker_service),
):
    try:
        return await docker.list_container_files(container_id, path=path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{container_id}/files/content")
async def read_file_in_container(
    container_id: str,
    path: str = Query(...),
    docker: DockerService = Depends(get_docker_service),
):
    try:
        return await docker.read_container_file(container_id, file_path=path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


