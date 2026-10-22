from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import uuid

from app.api.deps import get_db, get_current_user, require_role
from app.core.waf import security_manager
from app.models.deployment import Deployment
from app.models.user import User
from app.schemas.deployment import DeploymentRead, DeploymentList
from app.services.deploy_orchestrator import DeployOrchestrator
from app.services.docker_service import DockerService
from app.services.git_service import GitService

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=List[DeploymentList])
async def list_deployments(
    project_id: Optional[uuid.UUID] = None, db: AsyncSession = Depends(get_db)
):
    q = select(Deployment).order_by(Deployment.started_at.desc())
    if project_id:
        q = q.where(Deployment.project_id == project_id)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{deployment_id}", response_model=DeploymentRead)
async def get_deployment(deployment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    dep = result.scalar_one_or_none()
    if not dep:
        raise HTTPException(status_code=404, detail="Not found")
    return dep


@router.post(
    "/{deployment_id}/rollback",
    response_model=DeploymentRead,
    dependencies=[Depends(require_role("admin", "developer"))],
)
async def rollback_deployment(
    deployment_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    orchestrator = DeployOrchestrator(
        docker_service=DockerService(),
        git_service=GitService(),
        db_session=db,
    )
    try:
        dep = await orchestrator.rollback(str(deployment_id), db)
        security_manager.log_event(
            event_type="deploy",
            severity="medium",
            ip=security_manager.get_client_ip(request),
            path=f"/api/v1/deployments/{deployment_id}/rollback",
            detail=f"Rollback manual executado para o deployment {str(deployment_id)[:8]}",
            user=current_user.username,
        )
        return dep
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao executar rollback: {e}")
