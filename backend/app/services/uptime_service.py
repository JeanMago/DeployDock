"""
Monitor de Uptime HTTP, Histórico de Latência e Auto-Healing de Contêineres.

Executa verificações periódicas em background nos projetos ativos:
- Mede latência HTTP (ms) e código de status via Proxy Reverso Traefik (ou porta direta)
- Calcula porcentagem de Uptime (99.9%) e armazena série temporal de latência
- Executa Auto-Healing (reinício automático do contêiner) em caso de falhas consecutivas
- Monitora uso de CPU/RAM do host para disparar alertas preventivos
"""

import asyncio
import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, Optional

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.core.waf import security_manager
from app.db.session import async_session_factory
from app.models.project import Project
from app.services.docker_service import DockerService, _collect_host_metrics_sync
from app.services.notification_service import notification_manager

logger = logging.getLogger(__name__)


class UptimeMonitorService:
    """Serviço singleton de monitoramento contínuo de Uptime, Latência e Auto-Healing."""

    def __init__(self) -> None:
        self._records: Dict[str, Dict[str, Any]] = {}
        self._histories: Dict[str, Deque[Dict[str, Any]]] = {}
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self.total_auto_heals = 0

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._running = True
            self._task = asyncio.create_task(self._monitor_loop())

    def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()

    async def _monitor_loop(self) -> None:
        # Pequeno atraso inicial após boot
        await asyncio.sleep(3)
        while self._running:
            try:
                await self.check_all_projects()
                await self._check_host_resources()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Ciclo UptimeMonitor ignorou erro transitório: {e}")
            await asyncio.sleep(30)

    async def _check_host_resources(self) -> None:
        try:
            metrics = await asyncio.to_thread(_collect_host_metrics_sync)
            cpu_pct = metrics.get("cpu_percent", 0.0)
            mem_pct = metrics.get("memory_percent", 0.0)
            cpu_limit = float(notification_manager.config.get("cpu_threshold_percent", 85))
            ram_limit = float(notification_manager.config.get("ram_threshold_percent", 85))

            if cpu_pct >= cpu_limit or mem_pct >= ram_limit:
                await notification_manager.notify(
                    event_type="high_resource",
                    title="Alerta de Sobrecarga de Recursos no Servidor",
                    message=(
                        f"O host **{metrics.get('hostname')}** atingiu uso elevado:\n"
                        f"• CPU: **{cpu_pct}%** (limite: {cpu_limit}%)\n"
                        f"• RAM: **{mem_pct}%** (limite: {ram_limit}%)"
                    ),
                    severity="warning",
                    metadata={"cpu_percent": cpu_pct, "memory_percent": mem_pct},
                )
        except Exception:
            pass

    async def check_single_project(
        self, project: Project, docker_svc: Optional[DockerService] = None
    ) -> Dict[str, Any]:
        pid = str(project.id)
        docker = docker_svc or DockerService()
        host_header = project.public_host
        proxy_port = settings.PROXY_HTTP_PORT or 80
        target_url = f"http://127.0.0.1:{proxy_port}/"

        reachable = False
        status_code = 0
        error_str: Optional[str] = None
        t0 = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=4.0, follow_redirects=True) as client:
                resp = await client.get(target_url, headers={"Host": host_header})
                latency_ms = round((time.perf_counter() - t0) * 1000, 1)
                status_code = resp.status_code
                reachable = 200 <= resp.status_code < 400
        except Exception as exc:
            latency_ms = round((time.perf_counter() - t0) * 1000, 1)
            error_str = str(exc)

        # Fallback: se Traefik não respondeu 2xx/3xx, verifica porta direta do contêiner no Docker
        container_name = f"deploydock_{project.name.lower()}"
        container_state = "missing"
        try:
            c_detail = await docker.get_container(container_name)
            container_state = c_detail.get("state") or c_detail.get("status") or "unknown"
            if not reachable and container_state == "running":
                ports = c_detail.get("ports") or {}
                host_port = None
                for bindings in ports.values():
                    if isinstance(bindings, list) and bindings:
                        hp = bindings[0].get("HostPort")
                        if hp:
                            host_port = hp
                            break
                if host_port:
                    t1 = time.perf_counter()
                    async with httpx.AsyncClient(timeout=3.5, follow_redirects=True) as client:
                        resp2 = await client.get(f"http://127.0.0.1:{host_port}/")
                        latency_ms = round((time.perf_counter() - t1) * 1000, 1)
                        status_code = resp2.status_code
                        reachable = 200 <= resp2.status_code < 400
                        error_str = None
        except Exception:
            pass

        now_iso = datetime.now(timezone.utc).isoformat()
        hist = self._histories.setdefault(pid, deque(maxlen=24))
        hist.append(
            {
                "timestamp": now_iso,
                "latency_ms": latency_ms,
                "status_code": status_code,
                "ok": reachable,
            }
        )

        prev = self._records.get(pid, {})
        consecutive_failures = 0 if reachable else (prev.get("consecutive_failures", 0) + 1)
        auto_heals = prev.get("auto_heals_count", 0)

        # Auto-Healing se o contêiner caiu ou falhou 3 vezes seguidas e auto_heal está ativo
        auto_heal_enabled = getattr(project, "auto_heal", True)
        if auto_heal_enabled is None:
            auto_heal_enabled = True

        if (
            auto_heal_enabled
            and not reachable
            and consecutive_failures >= 3
            and container_state in ("running", "exited", "dead")
        ):
            try:
                await docker.restart_container(container_name, timeout=10)
                auto_heals += 1
                self.total_auto_heals += 1
                consecutive_failures = 0
                security_manager.log_event(
                    event_type="auto_heal",
                    severity="medium",
                    ip="127.0.0.1",
                    path=f"/projects/{project.name}",
                    detail=f"Auto-Healing reiniciou automaticamente o contêiner '{container_name}' após 3 falhas de health check.",
                    user="uptime-monitor",
                    blocked=False,
                )
                await notification_manager.notify(
                    event_type="container_down",
                    title=f"Auto-Healing Executado: {project.name}",
                    message=(
                        f"O projeto **{project.name}** apresentou indisponibilidade HTTP "
                        f"e seu contêiner `{container_name}` foi reiniciado automaticamente."
                    ),
                    severity="warning",
                    metadata={"project": project.name, "container": container_name},
                )
            except Exception as heal_err:
                logger.warning(f"[Auto-Heal] Falha ao reiniciar {container_name}: {heal_err}")

        ok_count = sum(1 for item in hist if item["ok"])
        uptime_percent = round((ok_count / len(hist)) * 100.0, 1) if hist else 0.0
        ok_latencies = [item["latency_ms"] for item in hist if item["ok"]]
        avg_latency_ms = (
            round(sum(ok_latencies) / len(ok_latencies), 1)
            if ok_latencies
            else latency_ms
        )

        record = {
            "project_id": pid,
            "name": project.name,
            "public_url": project.public_url,
            "reachable": reachable,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "avg_latency_ms": avg_latency_ms,
            "uptime_percent": uptime_percent,
            "consecutive_failures": consecutive_failures,
            "auto_heal_enabled": bool(auto_heal_enabled),
            "auto_heals_count": auto_heals,
            "container_state": container_state,
            "last_checked_at": now_iso,
            "error": error_str,
            "history": list(hist),
        }
        self._records[pid] = record
        return record

    async def check_all_projects(self) -> Dict[str, Dict[str, Any]]:
        async with async_session_factory() as session:
            projects = (await session.execute(select(Project))).scalars().all()
            if not projects:
                return {}
            docker = DockerService()
            results = await asyncio.gather(
                *(self.check_single_project(p, docker) for p in projects),
                return_exceptions=True,
            )
            out: Dict[str, Dict[str, Any]] = {}
            for r in results:
                if isinstance(r, dict) and "project_id" in r:
                    out[r["project_id"]] = r
            return out

    def get_all_records(self) -> Dict[str, Dict[str, Any]]:
        return self._records

    def get_project_record(self, project_id: str) -> Optional[Dict[str, Any]]:
        return self._records.get(str(project_id))


uptime_monitor = UptimeMonitorService()
