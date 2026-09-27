"""
Receptor de Webhooks do GitHub.

Valida a assinatura HMAC-SHA256 e dispara o pipeline de deploy
em background para eventos de push na branch monitorada.
"""

import json
import logging
from fastapi import APIRouter, BackgroundTasks, Depends, Header, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_docker_service
from app.core.security import verify_github_signature
from app.models.project import Project
from app.services.deploy_orchestrator import DeployOrchestrator
from app.services.docker_service import DockerService
from app.services.git_service import GitService
from app.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = APIRouter()


async def _trigger_deploy(project_id: str, commit_sha: str, branch: str) -> None:
    """
    Executa o pipeline de deploy em uma sessão de banco independente.
    Chamada como background task — desacoplada do ciclo de vida do request HTTP.
    """
    async with async_session_factory() as session:
        result = await session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            logger.error(f"Projeto {project_id} não encontrado para deploy.")
            return

        orchestrator = DeployOrchestrator(
            docker_service=DockerService(),
            git_service=GitService(),
            db_session=session,
        )
        deployment = await orchestrator.deploy(project, commit_sha, branch)
        logger.info(
            f"Deploy concluído para {project.name}: "
            f"status={deployment.status}, duração={deployment.duration_seconds}s"
        )


@router.post("/github", status_code=status.HTTP_202_ACCEPTED)
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    payload_bytes: bytes = Depends(verify_github_signature),
    x_github_event: str = Header(None, alias="X-GitHub-Event"),
    x_github_delivery: str = Header(None, alias="X-GitHub-Delivery"),
    db: AsyncSession = Depends(get_db),
):
    """
    Receptor de webhooks do GitHub.

    Fluxo:
    1. Valida assinatura HMAC-SHA256 (via dependência verify_github_signature)
    2. Processa eventos 'ping' e 'push'
    3. Busca projeto associado ao repositório e branch
    4. Dispara pipeline de deploy em background
    """
    # Evento ping — resposta de confirmação
    if x_github_event == "ping":
        return {
            "status": "pong",
            "delivery": x_github_delivery,
        }

    # Ignorar eventos que não são push
    if x_github_event != "push":
        logger.info(f"Webhook ignorado: evento '{x_github_event}'")
        return {
            "status": "ignored",
            "event": x_github_event,
            "delivery": x_github_delivery,
        }

    # Processar push event
    payload = json.loads(payload_bytes.decode("utf-8"))
    ref = payload.get("ref", "")
    branch = ref.split("/")[-1] if ref.startswith("refs/heads/") else ""
    commit_sha = payload.get("after", "")
    repo_url = payload.get("repository", {}).get("clone_url", "")

    logger.info(f"Webhook push recebido: repo={repo_url}, branch={branch}, commit={commit_sha[:8]}")

    if not branch or not repo_url:
        return {"status": "invalid_payload", "delivery": x_github_delivery}

    # Buscar projeto correspondente
    result = await db.execute(
        select(Project).where(
            Project.repo_url == repo_url,
            Project.branch == branch,
            Project.auto_deploy == True,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        logger.info(f"Nenhum projeto configurado para {repo_url}@{branch}")
        return {
            "status": "no_matching_project",
            "repo": repo_url,
            "branch": branch,
            "delivery": x_github_delivery,
        }

    # Disparar deploy em background
    background_tasks.add_task(_trigger_deploy, str(project.id), commit_sha, branch)

    return {
        "status": "queued",
        "project": project.name,
        "branch": branch,
        "commit": commit_sha[:8],
        "delivery": x_github_delivery,
    }
