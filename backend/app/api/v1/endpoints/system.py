from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.docker_service import DockerService
from app.api.deps import get_docker_service, require_role
from app.schemas.webhook import SystemInfo

router = APIRouter(dependencies=[Depends(require_role("admin", "developer"))])

@router.get("/info", response_model=SystemInfo)
async def system_info(docker: DockerService = Depends(get_docker_service)):
    return await docker.get_system_info()

@router.get("/resources")
async def system_resources(docker: DockerService = Depends(get_docker_service)):
    return await docker.get_resources_overview()

@router.get("/images")
async def list_images(docker: DockerService = Depends(get_docker_service)):
    return await docker.list_images()

@router.delete("/images/{image_id}")
async def remove_image(image_id: str, docker: DockerService = Depends(get_docker_service)):
    try:
        await docker.remove_image(image_id, force=True)
        return {"message": "Removed"}
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/volumes")
async def list_volumes(docker: DockerService = Depends(get_docker_service)):
    return await docker.list_volumes()

@router.delete("/volumes/{volume_name}")
async def remove_volume(volume_name: str, docker: DockerService = Depends(get_docker_service)):
    try:
        await docker.remove_volume(volume_name)
        return {"message": "Removed"}
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/networks")
async def list_networks(docker: DockerService = Depends(get_docker_service)):
    return await docker.list_networks()

@router.post("/prune")
async def prune_system(
    target: str = Query("all", description="all | images | containers | volumes | networks"),
    docker: DockerService = Depends(get_docker_service),
):
    return await docker.prune_system(target=target)


@router.get("/production-check")
async def production_check(docker: DockerService = Depends(get_docker_service)):
    """Verifica itens essenciais de segurança e infraestrutura para subir em Produção."""
    from app.core.config import settings

    containers = await docker.list_containers(all=True)
    traefik_running = any(
        "traefik" in c.get("name", "").lower() and c.get("state") == "running"
        for c in containers
    )
    postgres_running = any(
        ("db" in c.get("name", "").lower() or "postgres" in c.get("image", "").lower())
        and c.get("state") == "running"
        for c in containers
    )

    secret_key_ok = settings.SECRET_KEY not in (
        "changeme-secret-key",
        "change-me-in-production",
        "dev-secret-key-change-in-production",
    )
    webhook_secret_ok = settings.GITHUB_WEBHOOK_SECRET not in ("changeme", "")
    domain_ok = settings.APPS_BASE_DOMAIN not in ("localhost", "127.0.0.1")
    tls_ok = bool(settings.APPS_TLS_ENABLED)

    checks = [
        {
            "id": "traefik",
            "label": "Proxy Reverso Traefik v3.6 em execução",
            "passed": traefik_running,
            "hint": "Necessário para rotear subdomínios, domínios customizados e SSL Let's Encrypt.",
        },
        {
            "id": "database",
            "label": "Banco de Dados PostgreSQL 16 ativo",
            "passed": postgres_running,
            "hint": "Garante persistência transacional em produção.",
        },
        {
            "id": "secret_key",
            "label": "Chave Criptográfica (SECRET_KEY) personalizada",
            "passed": secret_key_ok,
            "hint": "Altere SECRET_KEY no arquivo .env para uma string aleatória de 64 caracteres.",
        },
        {
            "id": "domain",
            "label": f"Domínio Base de Produção ({settings.APPS_BASE_DOMAIN})",
            "passed": domain_ok,
            "hint": "Em produção, defina APPS_BASE_DOMAIN=seudominio.com ou SEU_IP.sslip.io.",
        },
        {
            "id": "tls",
            "label": "Certificados HTTPS Automáticos (APPS_TLS_ENABLED)",
            "passed": tls_ok,
            "hint": "Ative APPS_TLS_ENABLED=true no .env quando apontar um domínio real para a VPS.",
        },
        {
            "id": "webhook",
            "label": "Segredo Global de Webhook configurado",
            "passed": webhook_secret_ok,
            "hint": "Cada projeto também possui seu próprio webhook_secret exclusivo.",
        },
    ]

    passed_count = sum(1 for c in checks if c["passed"])
    return {
        "score": round((passed_count / len(checks)) * 100),
        "passed_count": passed_count,
        "total_count": len(checks),
        "apps_base_domain": settings.APPS_BASE_DOMAIN,
        "apps_tls_enabled": settings.APPS_TLS_ENABLED,
        "checks": checks,
    }


