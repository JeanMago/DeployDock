from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.api.deps import get_db
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectRead, ProjectList
import uuid

router = APIRouter()

@router.get("", response_model=List[ProjectList])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project))
    return result.scalars().all()

@router.post("", response_model=ProjectRead)
async def create_project(project_in: ProjectCreate, db: AsyncSession = Depends(get_db)):
    db_obj = Project(**project_in.model_dump())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Not found")
    return project

@router.put("/{project_id}", response_model=ProjectRead)
@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(project_id: uuid.UUID, project_in: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    project = await get_project(project_id, db)
    update_data = project_in.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(project, k, v)
    await db.commit()
    await db.refresh(project)
    return project

@router.delete("/{project_id}")
async def delete_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    project = await get_project(project_id, db)
    await db.delete(project)
    await db.commit()
    return {"message": "Deleted"}

@router.post("/{project_id}/deploy")
async def deploy_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    # Trigger manual deploy
    return {"message": "Deploy triggered"}

@router.get("/{project_id}/env")
async def list_env(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return []

@router.post("/{project_id}/env")
async def add_env(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return {}

@router.delete("/{project_id}/env/{env_id}")
async def delete_env(project_id: uuid.UUID, env_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return {"message": "Deleted"}
