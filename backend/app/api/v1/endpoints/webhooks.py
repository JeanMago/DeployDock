"""
Receptor de Webhooks do GitHub.

Valida a assinatura HMAC-SHA256 e dispara o pipeline de deploy
em background para eventos de push na branch monitorada ou
cria Preview Deployments automáticos para outras branches / Pull Requests.
"""

import hashlib
import hmac
import json
import logging
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.core.waf import security_manager
from app.models.project import Project
from app.services.deploy_orchestrator import DeployOrchestrator
from app.services.docker_service import DockerService
from app.services.git_service import GitService
from app.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = APIRouter()


def _verify_hmac(payload_bytes: bytes, signature_header: str | None, secret_str: str | None) -> bool:
    if not signature_header or not secret_str:
        return False
    expected = "sha256=" + hmac.new(
        secret_str.encode("utf-8"), payload_bytes, digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature_header, expected)


def _normalize_repo_url(url: str) -> str:
    u = (url or "").strip().lower().rstrip("/")
    if u.endswith(".git"):
        u = u[:-4]
    return u


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


async def _trigger_preview_deploy(project_id: str, branch: str) -> None:
    """Dispara Preview Deployment automático para branch/PR em background."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return
        orchestrator = DeployOrchestrator(
            docker_service=DockerService(),
            git_service=GitService(),
            db_session=session,
        )
        try:
            await orchestrator.deploy_preview(project, branch)
        except Exception as e:
            logger.error(f"Falha no preview deploy automático ({project.name}@{branch}): {e}")


@router.post("/github", status_code=status.HTTP_202_ACCEPTED)
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(None, alias="X-GitHub-Event"),
    x_github_delivery: str = Header(None, alias="X-GitHub-Delivery"),
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
    db: AsyncSession = Depends(get_db),
):
    payload_bytes = await request.body()
    if not x_hub_signature_256:
        raise HTTPException(status_code=401, detail="Cabeçalho X-Hub-Signature-256 ausente.")

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Payload JSON inválido.")

    repo_info = payload.get("repository", {}) or {}
    clone_url = repo_info.get("clone_url", "")
    html_url = repo_info.get("html_url", "")
    target_norm = _normalize_repo_url(clone_url or html_url)

    all_projects = (await db.execute(select(Project))).scalars().all()
    matching_projects = [
        p for p in all_projects if _normalize_repo_url(p.repo_url) == target_norm
    ]

    signature_valid = _verify_hmac(payload_bytes, x_hub_signature_256, settings.GITHUB_WEBHOOK_SECRET)
    if not signature_valid:
        for p in matching_projects:
            if _verify_hmac(payload_bytes, x_hub_signature_256, p.webhook_secret):
                signature_valid = True
                break

    if not signature_valid:
        security_manager.log_event(
            event_type="waf_block",
            severity="high",
            ip=security_manager.get_client_ip(request),
            path="/api/v1/webhooks/github",
            detail=f"Assinatura HMAC inválida no Webhook GitHub para '{clone_url or html_url}'",
            blocked=True,
        )
        raise HTTPException(status_code=401, detail="Assinatura do Webhook inválida (Secret incorreto).")

    if x_github_event == "ping":
        return {
            "status": "pong",
            "delivery": x_github_delivery,
            "matched_projects": [p.name for p in matching_projects],
        }

    # Suporte a Pull Requests para Preview Environments
    if x_github_event == "pull_request":
        pr_action = payload.get("action", "")
        pr_num = payload.get("number")
        pr_head_ref = (payload.get("pull_request") or {}).get("head", {}).get("ref", "")
        preview_project = next(
            (p for p in matching_projects if p.preview_deployments_enabled is not False),
            None,
        )
        if preview_project and pr_action in ("opened", "synchronize", "reopened") and pr_head_ref:
            branch_label = f"pr-{pr_num}" if pr_num else pr_head_ref
            background_tasks.add_task(_trigger_preview_deploy, str(preview_project.id), branch_label)
            return {
                "status": "preview_queued",
                "project": preview_project.name,
                "preview_branch": branch_label,
                "delivery": x_github_delivery,
            }
        return {"status": "ignored_pr_action", "action": pr_action}

    if x_github_event != "push":
        return {
            "status": "ignored",
            "event": x_github_event,
            "delivery": x_github_delivery,
        }

    ref = payload.get("ref", "")
    branch = ref.split("/")[-1] if ref.startswith("refs/heads/") else ""
    commit_sha = payload.get("after", "")

    if not branch or not target_norm:
        return {"status": "invalid_payload", "delivery": x_github_delivery}

    project = next(
        (p for p in matching_projects if p.branch == branch and p.auto_deploy),
        None,
    )

    if not project:
        # Verificar se algum projeto do repositório tem Preview Deployments ativo para branches secundárias
        preview_proj = next(
            (
                p
                for p in matching_projects
                if p.auto_deploy and (p.preview_deployments_enabled is not False)
            ),
            None,
        )
        if preview_proj:
            security_manager.log_event(
                event_type="deploy",
                severity="low",
                ip=security_manager.get_client_ip(request),
                path="/api/v1/webhooks/github",
                detail=f"Preview Deploy via GitHub Webhook para '{preview_proj.name}' ({branch})",
                user="github-webhook",
            )
            background_tasks.add_task(_trigger_preview_deploy, str(preview_proj.id), branch)
            return {
                "status": "preview_queued",
                "project": preview_proj.name,
                "branch": branch,
                "delivery": x_github_delivery,
            }

        return {
            "status": "no_matching_project",
            "repo": clone_url or html_url,
            "branch": branch,
            "delivery": x_github_delivery,
        }

    security_manager.log_event(
        event_type="deploy",
        severity="low",
        ip=security_manager.get_client_ip(request),
        path="/api/v1/webhooks/github",
        detail=f"Auto-deploy via GitHub Webhook para '{project.name}' ({branch}@{commit_sha[:8]})",
        user="github-webhook",
        blocked=False,
    )

    background_tasks.add_task(_trigger_deploy, str(project.id), commit_sha, branch)

    return {
        "status": "queued",
        "project": project.name,
        "branch": branch,
        "commit": commit_sha[:8],
        "delivery": x_github_delivery,
    }
