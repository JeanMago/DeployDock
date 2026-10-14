"""
Orquestrador de Deploy.

Implementa o pipeline completo de deploy automático:
Webhook → Clone/Pull → Build → Deploy → Health Check → Rollback (em caso de falha).
"""

import asyncio
import logging
import os
import threading
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.deployment import Deployment
from app.models.project import Project
from app.services.docker_service import DockerService
from app.services.git_service import GitService
from app.services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)


class DeployOrchestrator:
    """Orquestra o ciclo completo de deploy de um projeto."""

    def __init__(
        self,
        docker_service: DockerService,
        git_service: GitService,
        db_session: AsyncSession,
    ) -> None:
        self.docker = docker_service
        self.git = git_service
        self.db = db_session

    async def deploy(self, project: Project, commit_sha: str, branch: str) -> Deployment:
        """
        Executa o pipeline de deploy completo:
        1. Cria registro de deployment
        2. Clone/Pull do repositório
        3. Docker build com streaming de logs
        4. Para contêiner antigo e inicia o novo
        5. Executa health check
        6. Em caso de falha, faz rollback automático
        """
        deployment = Deployment(
            project_id=project.id,
            commit_sha=commit_sha,
            branch=branch,
            status="pending",
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(deployment)
        await self.db.commit()
        await self.db.refresh(deployment)

        deploy_topic = f"deploy_{deployment.id}"
        start_time = time.monotonic()

        try:
            # ── Etapa 1: Clonar / Atualizar repositório ──
            deployment.status = "cloning"
            await self.db.commit()
            await ws_manager.broadcast(deploy_topic, {"status": "cloning", "step": 1})
            logger.info(f"[Deploy {deployment.id}] Clonando {project.repo_url}@{branch}")

            repo_path = os.path.join(settings.REPOS_BASE_PATH, str(project.id))

            if os.path.exists(repo_path):
                try:
                    actual_sha = await self.git.pull_repo(repo_path, branch)
                except Exception as e:
                    logger.warning(f"Git pull ignorado ({e}). Prosseguindo com repositório local.")
            else:
                actual_sha = await self.git.clone_repo(project.repo_url, repo_path, branch)

            try:
                commit_info = await self.git.get_current_commit(repo_path)
                deployment.commit_sha = commit_info.get("sha", commit_sha or "initial")
                deployment.commit_message = commit_info.get("message", "Deploy inicial")
                deployment.commit_author = commit_info.get("author", "DeployDock")
            except Exception:
                deployment.commit_sha = commit_sha or "initial"
                deployment.commit_message = "Deploy manual"
                deployment.commit_author = "DeployDock"
            await self.db.commit()
            await ws_manager.broadcast(deploy_topic, {
                "status": "cloning",
                "step": 1,
                "commit": commit_info,
            })

            # ── Etapa 2: Docker Build ──
            deployment.status = "building"
            await self.db.commit()
            await ws_manager.broadcast(deploy_topic, {"status": "building", "step": 2})
            logger.info(f"[Deploy {deployment.id}] Construindo imagem...")

            image_tag = f"deploydock-{project.name.lower()}:{deployment.commit_sha[:8]}"
            build_logs: list[str] = []

            # Build é síncrono — rodamos em thread daemon e alimentamos uma asyncio.Queue
            # Usamos threading.Thread diretamente (não asyncio.to_thread) para garantir
            # streaming progressivo dos logs durante o build (padrão adotado em ws.py)
            log_queue: asyncio.Queue[str | None] = asyncio.Queue()
            loop = asyncio.get_running_loop()

            def _build_worker():
                try:
                    for line in self.docker.build_image(
                        path=repo_path,
                        tag=image_tag,
                        dockerfile=project.dockerfile_path,
                    ):
                        loop.call_soon_threadsafe(log_queue.put_nowait, line)
                    loop.call_soon_threadsafe(log_queue.put_nowait, None)
                except Exception as exc:
                    loop.call_soon_threadsafe(log_queue.put_nowait, f"BUILD_ERROR: {exc}")
                    loop.call_soon_threadsafe(log_queue.put_nowait, None)

            build_thread = threading.Thread(target=_build_worker, daemon=True)
            build_thread.start()

            while True:
                line = await log_queue.get()
                if line is None:
                    break
                if line.startswith("BUILD_ERROR:"):
                    raise RuntimeError(line)
                build_logs.append(line)
                await ws_manager.broadcast(deploy_topic, {"log": line, "step": 2})

            deployment.build_logs = "".join(build_logs)
            await self.db.commit()

            # ── Etapa 3: Deploy (Container Swap) ──
            deployment.status = "deploying"
            await self.db.commit()
            await ws_manager.broadcast(deploy_topic, {"status": "deploying", "step": 3})
            logger.info(f"[Deploy {deployment.id}] Substituindo contêiner...")

            container_name = f"deploydock_{project.name.lower()}"

            # Salvar referência ao contêiner/imagem anterior para rollback
            try:
                old_container = await self.docker.get_container(container_name)
                deployment.previous_image_id = old_container.get("image")
                await self.db.commit()
                await self.docker.stop_container(container_name, timeout=15)
                await self.docker.remove_container(container_name, force=True)
                logger.info(f"[Deploy {deployment.id}] Contêiner anterior removido.")
            except (ValueError, Exception):
                logger.info(f"[Deploy {deployment.id}] Nenhum contêiner anterior encontrado.")

            # Iniciar novo contêiner
            new_container = await asyncio.to_thread(
                self.docker.client.containers.run,
                image_tag,
                name=container_name,
                detach=True,
                restart_policy={"Name": "unless-stopped"},
            )
            logger.info(f"[Deploy {deployment.id}] Novo contêiner iniciado: {new_container.short_id}")

            # ── Etapa 4: Health Check ──
            if project.health_check_url:
                await ws_manager.broadcast(deploy_topic, {"status": "health_check", "step": 4})
                logger.info(f"[Deploy {deployment.id}] Executando health check: {project.health_check_url}")

                healthy = await self._run_health_check(
                    project.health_check_url,
                    retries=settings.HEALTH_CHECK_RETRIES,
                    timeout=settings.HEALTH_CHECK_TIMEOUT,
                )
                if not healthy:
                    raise RuntimeError(
                        f"Health check falhou após {settings.HEALTH_CHECK_RETRIES} tentativas "
                        f"em {project.health_check_url}"
                    )

            # ── Sucesso ──
            deployment.status = "healthy"
            deployment.finished_at = datetime.now(timezone.utc)
            deployment.duration_seconds = round(time.monotonic() - start_time, 2)
            await self.db.commit()
            await ws_manager.broadcast(deploy_topic, {
                "status": "healthy",
                "step": 5,
                "duration": deployment.duration_seconds,
            })
            logger.info(
                f"[Deploy {deployment.id}] ✅ Deploy concluído em {deployment.duration_seconds}s"
            )

        except Exception as e:
            # ── Falha — Rollback automático ──
            logger.error(f"[Deploy {deployment.id}] ❌ Falha: {e}")

            deployment.status = "failed"
            deployment.error_message = str(e)
            deployment.finished_at = datetime.now(timezone.utc)
            deployment.duration_seconds = round(time.monotonic() - start_time, 2)
            await self.db.commit()

            # Tentar rollback se há imagem anterior
            if deployment.previous_image_id:
                try:
                    await self._perform_rollback(
                        project, deployment.previous_image_id, container_name, deploy_topic
                    )
                    deployment.status = "rolled_back"
                    await self.db.commit()
                except Exception as rollback_err:
                    logger.error(f"[Deploy {deployment.id}] Rollback também falhou: {rollback_err}")

            await ws_manager.broadcast(deploy_topic, {
                "status": deployment.status,
                "error": str(e),
                "step": -1,
            })

        return deployment

    async def rollback(self, deployment_id: str, db: AsyncSession) -> Deployment:
        """Rollback manual para a versão anterior de um deployment."""
        result = await db.execute(
            select(Deployment).where(Deployment.id == deployment_id)
        )
        deployment = result.scalar_one_or_none()
        if not deployment:
            raise ValueError(f"Deployment '{deployment_id}' não encontrado.")

        if not deployment.previous_image_id:
            raise ValueError("Sem imagem anterior disponível para rollback.")

        # Buscar projeto
        project_result = await db.execute(
            select(Project).where(Project.id == deployment.project_id)
        )
        project = project_result.scalar_one()

        container_name = f"deploydock_{project.name.lower()}"
        deploy_topic = f"deploy_{deployment.id}"

        await self._perform_rollback(
            project, deployment.previous_image_id, container_name, deploy_topic
        )

        deployment.status = "rolled_back"
        await db.commit()
        return deployment

    async def _perform_rollback(
        self, project: Project, previous_image: str, container_name: str, topic: str
    ) -> None:
        """Executa o rollback: para contêiner atual e reinicia com imagem anterior."""
        logger.info(f"[Rollback] Revertendo para imagem: {previous_image}")
        await ws_manager.broadcast(topic, {"status": "rolling_back"})

        # Parar e remover contêiner atual
        try:
            await self.docker.stop_container(container_name, timeout=10)
            await self.docker.remove_container(container_name, force=True)
        except Exception:
            pass

        # Iniciar contêiner com imagem anterior
        await asyncio.to_thread(
            self.docker.client.containers.run,
            previous_image,
            name=container_name,
            detach=True,
            restart_policy={"Name": "unless-stopped"},
        )

        await ws_manager.broadcast(topic, {"status": "rolled_back"})
        logger.info(f"[Rollback] ✅ Rollback concluído com sucesso.")

    async def _run_health_check(self, url: str, retries: int, timeout: int) -> bool:
        """
        Verifica se o serviço está respondendo com status 200.
        Tenta `retries` vezes com intervalo de 3 segundos.
        """
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(1, retries + 1):
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        logger.info(f"[Health Check] ✅ Tentativa {attempt}: OK")
                        return True
                    logger.warning(
                        f"[Health Check] Tentativa {attempt}: status {response.status_code}"
                    )
                except Exception as e:
                    logger.warning(f"[Health Check] Tentativa {attempt}: {e}")
                await asyncio.sleep(3)
        return False
