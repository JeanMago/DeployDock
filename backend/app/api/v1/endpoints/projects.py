from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import os
import secrets
import git
import uuid

from app.api.deps import get_db
from app.core.config import settings
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectRead, ProjectList
from app.api.v1.endpoints.webhooks import _trigger_deploy

router = APIRouter()

TEMPLATES = {
    "fastapi": {
        "Dockerfile": """FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn
COPY main.py .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
""",
        "main.py": """from fastapi import FastAPI

app = FastAPI(title="Minha API")

@app.get("/")
def home():
    return {"status": "online", "message": "DeployDock - API FastAPI em execução!"}

@app.get("/health")
def health():
    return {"status": "healthy"}
""",
    },
    "express": {
        "Dockerfile": """FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY index.js .
EXPOSE 3000
CMD ["node", "index.js"]
""",
        "package.json": """{
  "name": "minha-api-node",
  "version": "1.0.0",
  "main": "index.js",
  "dependencies": {
    "express": "^4.19.2"
  }
}
""",
        "index.js": """const express = require('express');
const app = express();
const port = process.env.PORT || 3000;

app.get('/', (req, res) => {
  res.json({ status: 'online', message: 'DeployDock - Aplicação Node.js em execução!' });
});

app.get('/health', (req, res) => {
  res.json({ status: 'healthy' });
});

app.listen(port, () => console.log(`Rodando na porta ${port}`));
""",
    },
    "static": {
        "Dockerfile": """FROM nginx:alpine
COPY index.html /usr/share/nginx/html/index.html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
""",
        "index.html": """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>DeployDock App</title>
  <style>
    body { font-family: sans-serif; background: #0b0f19; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
    .card { background: #131b2e; padding: 2rem; border-radius: 12px; border: 1px solid #1e2a45; text-align: center; }
    h1 { color: #0ea5e9; }
  </style>
</head>
<body>
  <div class="card">
    <h1>🚀 DeployDock</h1>
    <p>Site estático publicado com sucesso!</p>
  </div>
</body>
</html>
""",
    }
}

@router.get("", response_model=List[ProjectList])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project))
    return result.scalars().all()

@router.post("", response_model=ProjectRead)
async def create_project(
    project_in: ProjectCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    project_id = uuid.uuid4()
    webhook_secret = project_in.webhook_secret or secrets.token_hex(16)
    repo_url = (project_in.repo_url or "").strip()
    branch = project_in.branch or "main"

    # Se não forneceu URL do Git ou escolheu modelo pronto, criamos repositório local gerenciado automaticamente
    if not repo_url or repo_url.startswith("local:") or project_in.template:
        repo_dir = os.path.abspath(os.path.join(settings.REPOS_BASE_PATH, str(project_id)))
        os.makedirs(repo_dir, exist_ok=True)

        template_key = project_in.template or "static"
        template_files = TEMPLATES.get(template_key, TEMPLATES["static"]).copy()

        if project_in.dockerfile_content:
            template_files["Dockerfile"] = project_in.dockerfile_content

        for filename, content in template_files.items():
            file_path = os.path.join(repo_dir, filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        # Inicializa Git localmente
        try:
            repo = git.Repo.init(repo_dir)
            repo.git.checkout("-b", branch)
            repo.git.add(A=True)
            repo.git.commit("-m", f"Initial commit for {project_in.name}")
        except Exception:
            pass

        repo_url = repo_dir

    db_obj = Project(
        id=project_id,
        name=project_in.name,
        repo_url=repo_url,
        branch=branch,
        webhook_secret=webhook_secret,
        docker_compose_path=project_in.docker_compose_path or "docker-compose.yml",
        dockerfile_path=project_in.dockerfile_path or "Dockerfile",
        auto_deploy=project_in.auto_deploy,
        health_check_url=project_in.health_check_url,
        health_check_interval=project_in.health_check_interval or 30,
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
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
    return {"message": "Projeto excluído com sucesso"}

@router.post("/{project_id}/deploy")
async def deploy_project(
    project_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    project = await get_project(project_id, db)
    background_tasks.add_task(_trigger_deploy, str(project.id), "manual", project.branch)
    return {"message": "Deploy iniciado com sucesso"}

@router.get("/{project_id}/env")
async def list_env(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return []

@router.post("/{project_id}/env")
async def add_env(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return {}

@router.delete("/{project_id}/env/{env_id}")
async def delete_env(project_id: uuid.UUID, env_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return {"message": "Deleted"}
