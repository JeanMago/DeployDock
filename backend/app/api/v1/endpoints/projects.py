from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import os
import secrets
import git
import logging
import uuid

from app.api.deps import get_db
from app.core.config import settings
from app.core.routing import slugify
from app.db.session import async_session_factory
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectRead, ProjectList, RoutingConfig
from app.api.v1.endpoints.webhooks import _trigger_deploy
from app.services.deploy_orchestrator import DeployOrchestrator
from app.services.docker_service import DockerService
from app.services.git_service import GitService

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/routing-config", response_model=RoutingConfig)
async def get_routing_config():
    """Retorna configurações de domínio e TLS para ajudar o frontend a exibir prévias das URLs."""
    if settings.APPS_TLS_ENABLED:
        scheme = "https"
        port_suffix = "" if settings.PROXY_HTTPS_PORT == 443 else f":{settings.PROXY_HTTPS_PORT}"
    else:
        scheme = "http"
        port_suffix = "" if settings.PROXY_HTTP_PORT == 80 else f":{settings.PROXY_HTTP_PORT}"

    return RoutingConfig(
        base_domain=settings.APPS_BASE_DOMAIN,
        tls_enabled=settings.APPS_TLS_ENABLED,
        scheme=scheme,
        port_suffix=port_suffix,
    )

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


async def _ensure_routing_available(
    db: AsyncSession,
    subdomain: str | None,
    custom_domain: str | None,
    exclude_id: uuid.UUID | None = None,
) -> None:
    """Garante que subdomínio/domínio não estejam em uso por outro projeto (HTTP 409)."""
    checks = [
        (Project.subdomain, subdomain, "subdomínio"),
        (Project.custom_domain, custom_domain, "domínio"),
    ]
    for column, value, label in checks:
        if not value:
            continue
        query = select(Project.id).where(column == value)
        if exclude_id:
            query = query.where(Project.id != exclude_id)
        if (await db.execute(query)).first():
            raise HTTPException(status_code=409, detail=f"O {label} '{value}' já está em uso por outro projeto.")


async def _unique_subdomain(db: AsyncSession, base: str) -> str:
    """Gera um subdomínio livre a partir do nome (meu-site, meu-site-2, ...)."""
    candidate, n = base, 2
    while (await db.execute(select(Project.id).where(Project.subdomain == candidate))).first():
        suffix = f"-{n}"
        candidate = f"{base[:63 - len(suffix)]}{suffix}"
        n += 1
    return candidate


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

    # URL pública: subdomínio informado pelo usuário ou gerado a partir do nome
    subdomain = project_in.subdomain or await _unique_subdomain(db, slugify(project_in.name))
    await _ensure_routing_available(db, subdomain, project_in.custom_domain)

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
        subdomain=subdomain,
        custom_domain=project_in.custom_domain,
        container_port=project_in.container_port,
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


ROUTING_FIELDS = ("subdomain", "custom_domain", "container_port")


async def _reapply_routing(project_id: str) -> None:
    """Background task: recria o contêiner com a nova URL pública (sem rebuild)."""
    async with async_session_factory() as session:
        project = (
            await session.execute(select(Project).where(Project.id == uuid.UUID(project_id)))
        ).scalar_one_or_none()
        if not project:
            return
        orchestrator = DeployOrchestrator(
            docker_service=DockerService(), git_service=GitService(), db_session=session
        )
        try:
            applied = await orchestrator.apply_routing(project)
            if not applied:
                logger.info(f"[Routing] {project.name} sem contêiner ativo; URL será usada no próximo deploy.")
        except Exception as e:
            logger.error(f"[Routing] Falha ao reaplicar URL de {project.name}: {e}")


@router.put("/{project_id}", response_model=ProjectRead)
@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: uuid.UUID,
    project_in: ProjectUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    project = await get_project(project_id, db)
    update_data = project_in.model_dump(exclude_unset=True)

    # Subdomínio vazio => volta ao padrão gerado a partir do nome
    if "subdomain" in update_data and not update_data["subdomain"]:
        base = slugify(update_data.get("name") or project.name)
        update_data["subdomain"] = (
            project.subdomain if project.subdomain == base else await _unique_subdomain(db, base)
        )

    await _ensure_routing_available(
        db, update_data.get("subdomain"), update_data.get("custom_domain"), exclude_id=project.id
    )

    routing_changed = any(
        k in update_data and update_data[k] != getattr(project, k) for k in ROUTING_FIELDS
    )
    for k, v in update_data.items():
        setattr(project, k, v)
    await db.commit()
    await db.refresh(project)

    if routing_changed:
        background_tasks.add_task(_reapply_routing, str(project.id))
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
