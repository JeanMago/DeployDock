from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid
from app.api.deps import get_db
from app.models.deployment import Deployment
from app.schemas.deployment import DeploymentRead, DeploymentList

router = APIRouter()

@router.get("", response_model=List[DeploymentList])
async def list_deployments(project_id: uuid.UUID = None, db: AsyncSession = Depends(get_db)):
    q = select(Deployment)
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

@router.post("/{deployment_id}/rollback")
async def rollback_deployment(deployment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return {"message": "Rollback triggered"}
