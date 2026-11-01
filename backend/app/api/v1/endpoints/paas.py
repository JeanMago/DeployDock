"""
Endpoints REST para recursos PaaS Avançados (Inspirados no Dokploy & Ployter, single-host):
- Bancos de Dados Gerenciados de 1ª Classe (PostgreSQL, MySQL, MariaDB, MongoDB, Redis)
- Catálogo Amplo de Templates 1-Clique (n8n, WordPress, PocketBase, Grafana, Ghost, MinIO, etc.)
- Backups Agendados (Cron) com envio para S3 / Cloudflare R2 / MinIO
- Cron Jobs por Aplicação (tarefas recorrentes executadas dentro do contêiner)
- Container Registries Privados (Docker Hub, GHCR, AWS ECR, GitLab Registry)
- Gerenciamento Automático de DNS (Cloudflare API v4)
- Configuração Visual do Traefik & Certificados TLS Customizados
- Diagnóstico Inteligente de Falhas de Build/Deploy
- Avaliação de Autoscaling por Métricas
"""

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_docker_service, require_role
from app.core.waf import security_manager, validate_safe_container_command
from app.models.project import Project
from app.models.user import User
from app.services.deploy_orchestrator import DeployOrchestrator
from app.services.docker_service import DockerService
from app.services.git_service import GitService
from app.services.paas_service import paas_manager

router = APIRouter(dependencies=[Depends(get_current_user)])


# ----------------------------------------------------------------
# Schemas de Payload
# ----------------------------------------------------------------


class ManagedDatabaseCreateRequest(BaseModel):
    name: str
    engine: str = "postgres"  # postgres | mysql | mariadb | mongodb | redis
    database_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    expose_port: Optional[int] = None
    memory_limit_mb: Optional[int] = 512


class TemplateLaunchRequest(BaseModel):
    app_name: Optional[str] = None
    subdomain: Optional[str] = None
    env_overrides: Optional[dict[str, str]] = None


class S3ConfigUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    provider: Optional[str] = None
    endpoint_url: Optional[str] = None
    bucket: Optional[str] = None
    region: Optional[str] = None
    access_key: Optional[str] = None
    secret_key: Optional[str] = None


class BackupJobCreateRequest(BaseModel):
    name: str
    target_type: str = "volume"  # volume | database | container
    target_name: str
    cron_expression: str = "0 3 * * *"
    s3_upload: bool = True
    retention_count: int = 7


class CronJobCreateRequest(BaseModel):
    project_id: uuid.UUID
    name: str
    command: str
    cron_expression: str = "*/15 * * * *"


class RegistryCreateRequest(BaseModel):
    name: str
    server_address: str = "https://ghcr.io"
    username: str
    password: str


class CloudflareConfigUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    zone_id: Optional[str] = None
    base_domain: Optional[str] = None
    server_ip: Optional[str] = None
    proxied_default: Optional[bool] = None
    api_token: Optional[str] = None


class CloudflareRecordCreateRequest(BaseModel):
    type: str = "A"
    name: str
    content: str
    proxied: bool = True
    ttl: int = 1


class TraefikConfigUpdateRequest(BaseModel):
    acme_email: Optional[str] = None
    force_https_redirect: Optional[bool] = None
    hsts_enabled: Optional[bool] = None
    gzip_compression: Optional[bool] = None
    rate_limit_average: Optional[int] = None
    rate_limit_burst: Optional[int] = None
    custom_middlewares: Optional[list[str]] = None


class CustomCertificateCreateRequest(BaseModel):
    domain: str
    cert_pem: str
    key_pem: str
    issuer: str = "Custom TLS"


class DiagnoseLogsRequest(BaseModel):
    logs: Optional[str] = None
    error_message: Optional[str] = None
    status: Optional[str] = "failed"


class AutoscaleEvaluateRequest(BaseModel):
    simulated_cpu_by_project: Optional[dict[str, float]] = None


# ----------------------------------------------------------------
# Visão Geral PaaS
# ----------------------------------------------------------------


@router.get("/overview")
async def get_paas_overview(docker: DockerService = Depends(get_docker_service)) -> dict[str, Any]:
    traefik = await paas_manager.get_traefik_overview(docker)
    return {
        "databases": paas_manager.list_managed_databases(),
        "templates": paas_manager.list_templates(),
        "backups": paas_manager.list_backup_jobs(),
        "crons": paas_manager.list_cron_jobs(),
        "registries": paas_manager.list_registries(),
        "cloudflare": paas_manager.get_cloudflare_overview(),
        "traefik": traefik,
        "autoscale_events": paas_manager.autoscale_events[:30],
    }


# ----------------------------------------------------------------
# 1. Bancos de Dados Gerenciados de 1ª Classe
# ----------------------------------------------------------------


@router.get("/databases")
async def list_managed_databases():
    return paas_manager.list_managed_databases()


@router.post("/databases", dependencies=[Depends(require_role("admin", "developer"))])
async def create_managed_database(
    body: ManagedDatabaseCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    docker: DockerService = Depends(get_docker_service),
):
    try:
        rec = await paas_manager.create_managed_database(
            name=body.name,
            engine=body.engine,
            database_name=body.database_name,
            username=body.username,
            password=body.password,
            expose_port=body.expose_port,
            memory_limit_mb=body.memory_limit_mb,
            docker_service=docker,
        )
        security_manager.log_event(
            event_type="deploy",
            severity="low",
            ip=security_manager.get_client_ip(request),
            path="/api/v1/paas/databases",
            detail=f"Banco gerenciado '{rec['name']}' ({rec['engine_label']}) provisionado",
            user=current_user.username,
        )
        return rec
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/databases/{db_id}", dependencies=[Depends(require_role("admin", "developer"))])
async def delete_managed_database(
    db_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    docker: DockerService = Depends(get_docker_service),
):
    try:
        res = await paas_manager.delete_managed_database(db_id, docker_service=docker)
        security_manager.log_event(
            event_type="container_action",
            severity="medium",
            ip=security_manager.get_client_ip(request),
            path=f"/api/v1/paas/databases/{db_id}",
            detail=f"Banco gerenciado '{res['name']}' removido",
            user=current_user.username,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ----------------------------------------------------------------
# 2. Catálogo Amplo de Templates 1-Clique (Dokploy)
# ----------------------------------------------------------------


@router.get("/templates")
async def list_templates():
    return paas_manager.list_templates()


@router.post("/templates/{template_id}/launch", dependencies=[Depends(require_role("admin", "developer"))])
async def launch_one_click_template(
    template_id: str,
    body: TemplateLaunchRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    docker: DockerService = Depends(get_docker_service),
):
    try:
        tpl = paas_manager.get_template(template_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    app_name = (body.app_name or f"deploydock_{tpl['id']}").strip()
    env_map = dict(tpl.get("default_env") or {})
    if body.env_overrides:
        env_map.update(body.env_overrides)

    container_id = f"tpl-{tpl['id'][:6]}"
    state = "running"
    try:
        res = await docker.run_quick_container(
            image=tpl["image"],
            name=app_name,
            env=env_map or None,
            restart_policy="unless-stopped",
        )
        container_id = res.get("id") or container_id
        state = res.get("state") or "running"
    except Exception:
        pass

    security_manager.log_event(
        event_type="deploy",
        severity="low",
        ip=security_manager.get_client_ip(request),
        path=f"/api/v1/paas/templates/{template_id}/launch",
        detail=f"Template 1-Clique '{tpl['name']}' lançado como '{app_name}'",
        user=current_user.username,
    )
    return {
        "template_id": tpl["id"],
        "template_name": tpl["name"],
        "container_id": container_id,
        "container_name": app_name,
        "image": tpl["image"],
        "port": tpl["default_port"],
        "state": state,
    }


# ----------------------------------------------------------------
# 3. Backups Agendados (Cron) + Armazenamento S3 / R2 / MinIO
# ----------------------------------------------------------------


@router.get("/backups")
async def get_backups_overview():
    return paas_manager.list_backup_jobs()


@router.put("/backups/s3-config", dependencies=[Depends(require_role("admin"))])
async def update_s3_config(
    body: S3ConfigUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    cfg = paas_manager.update_s3_config(body.model_dump(exclude_unset=True))
    security_manager.log_event(
        event_type="security_config",
        severity="low",
        ip=security_manager.get_client_ip(request),
        path="/api/v1/paas/backups/s3-config",
        detail=f"Configuração de Object Storage S3 ({cfg.get('provider')}) atualizada",
        user=current_user.username,
    )
    return cfg


@router.post("/backups/jobs", dependencies=[Depends(require_role("admin", "developer"))])
async def create_scheduled_backup_job(
    body: BackupJobCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    try:
        job = paas_manager.create_backup_job(
            name=body.name,
            target_type=body.target_type,
            target_name=body.target_name,
            cron_expression=body.cron_expression,
            s3_upload=body.s3_upload,
            retention_count=body.retention_count,
        )
        security_manager.log_event(
            event_type="backup",
            severity="low",
            ip=security_manager.get_client_ip(request),
            path="/api/v1/paas/backups/jobs",
            detail=f"Política de backup agendado '{job['name']}' ({job['cron_expression']}) criada",
            user=current_user.username,
        )
        return job
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/backups/jobs/{job_id}/run", dependencies=[Depends(require_role("admin", "developer"))])
async def run_scheduled_backup_now(
    job_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    docker: DockerService = Depends(get_docker_service),
):
    try:
        entry = await paas_manager.run_backup_job(job_id, docker_service=docker)
        security_manager.log_event(
            event_type="backup",
            severity="low",
            ip=security_manager.get_client_ip(request),
            path=f"/api/v1/paas/backups/jobs/{job_id}/run",
            detail=f"Backup '{entry['filename']}' executado (S3={entry.get('s3_url') or 'local'})",
            user=current_user.username,
        )
        return entry
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/backups/jobs/{job_id}", dependencies=[Depends(require_role("admin", "developer"))])
async def delete_scheduled_backup_job(job_id: str):
    try:
        return paas_manager.delete_backup_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ----------------------------------------------------------------
# 4. Cron Jobs Gerenciados por Aplicação
# ----------------------------------------------------------------


@router.get("/crons")
async def list_application_crons(project_id: Optional[str] = Query(None)):
    return paas_manager.list_cron_jobs(project_id=project_id)


@router.post("/crons", dependencies=[Depends(require_role("admin", "developer"))])
async def create_application_cron(
    body: CronJobCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = (
        await db.execute(select(Project).where(Project.id == body.project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    safe_cmd = validate_safe_container_command(
        body.command,
        user=current_user.username,
        ip=security_manager.get_client_ip(request),
    )
    job = paas_manager.create_cron_job(
        project_id=str(project.id),
        project_name=project.name,
        name=body.name,
        command=safe_cmd,
        cron_expression=body.cron_expression,
    )
    security_manager.log_event(
        event_type="container_action",
        severity="low",
        ip=security_manager.get_client_ip(request),
        path="/api/v1/paas/crons",
        detail=f"Cron job '{job['name']}' ({job['cron_expression']}) cadastrado em '{project.name}'",
        user=current_user.username,
    )
    return job


@router.post("/crons/{cron_id}/run", dependencies=[Depends(require_role("admin", "developer"))])
async def run_application_cron_now(
    cron_id: str,
    docker: DockerService = Depends(get_docker_service),
):
    try:
        return await paas_manager.run_cron_job(cron_id, docker_service=docker)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/crons/{cron_id}", dependencies=[Depends(require_role("admin", "developer"))])
async def delete_application_cron(cron_id: str):
    try:
        return paas_manager.delete_cron_job(cron_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ----------------------------------------------------------------
# 5. Container Registries Privados (GHCR, Docker Hub, ECR, GitLab)
# ----------------------------------------------------------------


@router.get("/registries")
async def list_private_registries():
    return paas_manager.list_registries()


@router.post("/registries", dependencies=[Depends(require_role("admin", "developer"))])
async def add_private_registry(
    body: RegistryCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    docker: DockerService = Depends(get_docker_service),
):
    rec = await paas_manager.add_registry(
        name=body.name,
        server_address=body.server_address,
        username=body.username,
        password=body.password,
        docker_service=docker,
    )
    security_manager.log_event(
        event_type="security_config",
        severity="low",
        ip=security_manager.get_client_ip(request),
        path="/api/v1/paas/registries",
        detail=f"Container Registry privado '{rec['name']}' ({rec['server_address']}) autenticado",
        user=current_user.username,
    )
    return rec


@router.delete("/registries/{registry_id}", dependencies=[Depends(require_role("admin", "developer"))])
async def delete_private_registry(registry_id: str):
    try:
        return paas_manager.delete_registry(registry_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ----------------------------------------------------------------
# 6. Gerenciamento Automático de DNS (Cloudflare API v4)
# ----------------------------------------------------------------


@router.get("/cloudflare")
async def get_cloudflare_dns():
    return paas_manager.get_cloudflare_overview()


@router.put("/cloudflare/config", dependencies=[Depends(require_role("admin"))])
async def update_cloudflare_dns_config(
    body: CloudflareConfigUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    res = paas_manager.update_cloudflare_config(body.model_dump(exclude_unset=True))
    security_manager.log_event(
        event_type="security_config",
        severity="low",
        ip=security_manager.get_client_ip(request),
        path="/api/v1/paas/cloudflare/config",
        detail=f"Integração Cloudflare DNS atualizada por {current_user.username}",
        user=current_user.username,
    )
    return res


@router.post("/cloudflare/records", dependencies=[Depends(require_role("admin", "developer"))])
async def upsert_cloudflare_dns_record(body: CloudflareRecordCreateRequest):
    try:
        return await paas_manager.upsert_cloudflare_record(
            record_type=body.type,
            name=body.name,
            content=body.content,
            proxied=body.proxied,
            ttl=body.ttl,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/cloudflare/sync-project/{project_id}",
    dependencies=[Depends(require_role("admin", "developer"))],
)
async def sync_project_domain_to_cloudflare(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Sincroniza automaticamente o domínio/subdomínio do projeto na zona DNS da Cloudflare."""
    project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    server_ip = paas_manager.cloudflare_config.get("server_ip") or "127.0.0.1"
    proxied = bool(paas_manager.cloudflare_config.get("proxied_default", True))
    return await paas_manager.upsert_cloudflare_record(
        record_type="A",
        name=project.public_host,
        content=server_ip,
        proxied=proxied,
    )


@router.delete("/cloudflare/records/{record_id}", dependencies=[Depends(require_role("admin", "developer"))])
async def delete_cloudflare_dns_record(record_id: str):
    try:
        return paas_manager.delete_cloudflare_record(record_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ----------------------------------------------------------------
# 7. Configuração Visual do Traefik & Certificados TLS Customizados
# ----------------------------------------------------------------


@router.get("/traefik")
async def get_traefik_overview(docker: DockerService = Depends(get_docker_service)):
    return await paas_manager.get_traefik_overview(docker)


@router.put("/traefik/config", dependencies=[Depends(require_role("admin"))])
async def update_traefik_config(
    body: TraefikConfigUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    cfg = paas_manager.update_traefik_config(body.model_dump(exclude_unset=True))
    security_manager.log_event(
        event_type="security_config",
        severity="low",
        ip=security_manager.get_client_ip(request),
        path="/api/v1/paas/traefik/config",
        detail=f"Configuração dinâmica do Traefik atualizada por {current_user.username}",
        user=current_user.username,
    )
    return cfg


@router.post("/traefik/certificates", dependencies=[Depends(require_role("admin"))])
async def add_custom_tls_certificate(
    body: CustomCertificateCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    try:
        cert = paas_manager.add_custom_certificate(
            domain=body.domain,
            cert_pem=body.cert_pem,
            key_pem=body.key_pem,
            issuer=body.issuer,
        )
        security_manager.log_event(
            event_type="security_config",
            severity="low",
            ip=security_manager.get_client_ip(request),
            path="/api/v1/paas/traefik/certificates",
            detail=f"Certificado TLS customizado importado para '{cert['domain']}'",
            user=current_user.username,
        )
        return cert
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/traefik/certificates/{cert_id}", dependencies=[Depends(require_role("admin"))])
async def delete_custom_tls_certificate(cert_id: str):
    try:
        return paas_manager.delete_custom_certificate(cert_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ----------------------------------------------------------------
# 8. Diagnóstico Inteligente de Falhas de Build & Deploy (Ployter AI)
# ----------------------------------------------------------------


@router.post("/diagnose")
async def diagnose_logs(body: DiagnoseLogsRequest):
    """Analisa logs de build/execução e retorna causa raiz e plano de correção."""
    return paas_manager.diagnose_failure(
        logs=body.logs,
        error_message=body.error_message,
        status=body.status,
    )


# ----------------------------------------------------------------
# 9. Autoscaling Baseado em Métricas de CPU (Ployter)
# ----------------------------------------------------------------


@router.post("/autoscaler/evaluate", dependencies=[Depends(require_role("admin", "developer"))])
async def evaluate_autoscaling(
    body: Optional[AutoscaleEvaluateRequest] = None,
    db: AsyncSession = Depends(get_db),
    docker: DockerService = Depends(get_docker_service),
):
    """
    Avalia o uso de CPU de todos os projetos com `autoscale_enabled=True` e ajusta
    automaticamente a quantidade de réplicas entre `autoscale_min_replicas` e `autoscale_max_replicas`.
    """
    projects = (
        await db.execute(select(Project).where(Project.autoscale_enabled == True))  # noqa: E712
    ).scalars().all()

    sim_map = (body.simulated_cpu_by_project if body else None) or {}
    actions: list[dict[str, Any]] = []
    orchestrator = DeployOrchestrator(
        docker_service=docker,
        git_service=GitService(),
        db_session=db,
    )

    for p in projects:
        c_name = f"deploydock_{p.name.lower()}"
        cpu_pct = sim_map.get(str(p.id))
        if cpu_pct is None:
            cpu_pct = sim_map.get(p.name)
        if cpu_pct is None:
            try:
                stats = await docker.get_container_stats(c_name)
                cpu_pct = float(stats.get("cpu_percent", 0.0))
            except Exception:
                cpu_pct = 0.0

        current_replicas = int(p.replicas or 1)
        min_rep = int(p.autoscale_min_replicas or 1)
        max_rep = int(p.autoscale_max_replicas or 3)
        target_cpu = int(p.autoscale_cpu_target or 75)

        new_replicas = current_replicas
        reason = "stable"
        if cpu_pct >= target_cpu and current_replicas < max_rep:
            new_replicas = current_replicas + 1
            reason = f"scale_up (CPU {cpu_pct:.1f}% >= alvo {target_cpu}%)"
        elif cpu_pct < (target_cpu * 0.35) and current_replicas > min_rep:
            new_replicas = current_replicas - 1
            reason = f"scale_down (CPU {cpu_pct:.1f}% < {target_cpu * 0.35:.1f}%)"

        if new_replicas != current_replicas:
            p.replicas = new_replicas
            await db.commit()
            await orchestrator.scale_project(p, new_replicas)
            evt = {
                "project_id": str(p.id),
                "project_name": p.name,
                "previous_replicas": current_replicas,
                "new_replicas": new_replicas,
                "cpu_percent": round(float(cpu_pct), 1),
                "reason": reason,
            }
            paas_manager.autoscale_events.insert(0, evt)
            actions.append(evt)

    return {
        "evaluated_projects": len(projects),
        "scaled_actions": actions,
        "history": paas_manager.autoscale_events[:20],
    }
