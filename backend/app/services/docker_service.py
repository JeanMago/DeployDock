"""
Camada de abstração sobre o Docker SDK (docker-py).

Todas as operações síncronas do docker-py são executadas via asyncio.to_thread()
para não bloquear o event loop do FastAPI. Métodos geradores (streaming) são
executados em threads separadas e alimentam filas assíncronas.
"""

import asyncio
import time
from typing import Any, Generator

import docker
from docker.errors import APIError, NotFound, ImageNotFound

from app.core.config import settings


class DockerService:
    """Wrapper assíncrono para o Docker SDK."""

    def __init__(self) -> None:
        if settings.DOCKER_HOST:
            self.client = docker.DockerClient(base_url=settings.DOCKER_HOST)
        else:
            self.client = docker.from_env()

    # ----------------------------------------------------------------
    # Contêineres — Listagem e Detalhes
    # ----------------------------------------------------------------

    async def list_containers(self, all: bool = True) -> list[dict[str, Any]]:
        """Lista todos os contêineres com informações resumidas."""
        containers = await asyncio.to_thread(self.client.containers.list, all=all)
        return [
            {
                "id": c.short_id,
                "full_id": c.id,
                "name": c.name,
                "status": c.status,
                "image": c.image.tags[0] if c.image.tags else c.image.short_id,
                "ports": c.ports,
                "created": c.attrs.get("Created"),
                "state": c.attrs.get("State", {}).get("Status"),
            }
            for c in containers
        ]

    async def get_container(self, container_id: str) -> dict[str, Any]:
        """Retorna detalhes completos de um contêiner."""
        try:
            c = await asyncio.to_thread(self.client.containers.get, container_id)
        except NotFound:
            raise ValueError(f"Contêiner '{container_id}' não encontrado.")
        return {
            "id": c.short_id,
            "full_id": c.id,
            "name": c.name,
            "status": c.status,
            "image": c.image.tags[0] if c.image.tags else c.image.short_id,
            "ports": c.ports,
            "created": c.attrs.get("Created"),
            "state": c.attrs.get("State", {}).get("Status"),
            "mounts": c.attrs.get("Mounts", []),
            "networks": c.attrs.get("NetworkSettings", {}).get("Networks", {}),
            "env": c.attrs.get("Config", {}).get("Env", []),
            "config": c.attrs.get("Config", {}),
            "restart_policy": c.attrs.get("HostConfig", {}).get("RestartPolicy", {}),
        }

    # ----------------------------------------------------------------
    # Contêineres — Ciclo de Vida
    # ----------------------------------------------------------------

    async def start_container(self, container_id: str) -> dict[str, str]:
        """Inicia um contêiner."""
        try:
            c = await asyncio.to_thread(self.client.containers.get, container_id)
            await asyncio.to_thread(c.start)
            await asyncio.to_thread(c.reload)
            return {"id": c.short_id, "name": c.name, "status": c.status}
        except NotFound:
            raise ValueError(f"Contêiner '{container_id}' não encontrado.")
        except APIError as e:
            raise RuntimeError(f"Erro Docker Engine: {e.explanation}")

    async def stop_container(self, container_id: str, timeout: int = 10) -> dict[str, str]:
        """Para um contêiner com timeout."""
        try:
            c = await asyncio.to_thread(self.client.containers.get, container_id)
            await asyncio.to_thread(c.stop, timeout=timeout)
            await asyncio.to_thread(c.reload)
            return {"id": c.short_id, "name": c.name, "status": c.status}
        except NotFound:
            raise ValueError(f"Contêiner '{container_id}' não encontrado.")
        except APIError as e:
            raise RuntimeError(f"Erro Docker Engine: {e.explanation}")

    async def restart_container(self, container_id: str, timeout: int = 10) -> dict[str, str]:
        """Reinicia um contêiner."""
        try:
            c = await asyncio.to_thread(self.client.containers.get, container_id)
            await asyncio.to_thread(c.restart, timeout=timeout)
            await asyncio.to_thread(c.reload)
            return {"id": c.short_id, "name": c.name, "status": c.status}
        except NotFound:
            raise ValueError(f"Contêiner '{container_id}' não encontrado.")
        except APIError as e:
            raise RuntimeError(f"Erro Docker Engine: {e.explanation}")

    async def remove_container(self, container_id: str, force: bool = False) -> None:
        """Remove um contêiner."""
        try:
            c = await asyncio.to_thread(self.client.containers.get, container_id)
            await asyncio.to_thread(c.remove, force=force)
        except NotFound:
            raise ValueError(f"Contêiner '{container_id}' não encontrado.")
        except APIError as e:
            raise RuntimeError(f"Erro Docker Engine: {e.explanation}")

    # ----------------------------------------------------------------
    # Contêineres — Logs
    # ----------------------------------------------------------------

    async def get_container_logs(
        self, container_id: str, tail: int = 100, timestamps: bool = True
    ) -> list[str]:
        """Retorna as últimas N linhas de log de um contêiner."""
        try:
            c = await asyncio.to_thread(self.client.containers.get, container_id)
            logs = await asyncio.to_thread(
                c.logs, tail=tail, timestamps=timestamps, stdout=True, stderr=True
            )
            return logs.decode("utf-8", errors="replace").splitlines()
        except NotFound:
            raise ValueError(f"Contêiner '{container_id}' não encontrado.")

    def stream_container_logs(
        self, container_id: str, tail: int = 100
    ) -> Generator[str, None, None]:
        """
        Generator síncrono que produz linhas de log em tempo real.
        Deve ser executado em uma thread separada (não no event loop).
        """
        c = self.client.containers.get(container_id)
        for chunk in c.logs(
            stream=True, follow=True, tail=tail, stdout=True, stderr=True, timestamps=True
        ):
            yield chunk.decode("utf-8", errors="replace")

    # ----------------------------------------------------------------
    # Contêineres — Métricas (CPU / Memória / Rede)
    # ----------------------------------------------------------------

    async def get_container_stats(self, container_id: str) -> dict[str, Any]:
        """
        Snapshot pontual de métricas de CPU, memória e rede.

        Cálculo de CPU%:
          cpu_delta = current.total_usage - previous.total_usage
          system_delta = current.system_cpu_usage - previous.system_cpu_usage
          cpu_percent = (cpu_delta / system_delta) * online_cpus * 100
        """
        try:
            c = await asyncio.to_thread(self.client.containers.get, container_id)
            stats = await asyncio.to_thread(c.stats, stream=False)
        except NotFound:
            raise ValueError(f"Contêiner '{container_id}' não encontrado.")

        # CPU
        cpu_stats = stats.get("cpu_stats", {})
        precpu_stats = stats.get("precpu_stats", {})
        cpu_delta = (
            cpu_stats.get("cpu_usage", {}).get("total_usage", 0)
            - precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
        )
        system_delta = cpu_stats.get("system_cpu_usage", 0) - precpu_stats.get(
            "system_cpu_usage", 0
        )
        online_cpus = cpu_stats.get("online_cpus") or len(
            cpu_stats.get("cpu_usage", {}).get("percpu_usage", [1])
        )
        cpu_percent = 0.0
        if system_delta > 0.0 and cpu_delta > 0.0:
            cpu_percent = (cpu_delta / system_delta) * online_cpus * 100.0

        # Memória (desconta cache para memória real)
        memory_stats = stats.get("memory_stats", {})
        raw_usage = memory_stats.get("usage", 0)
        memory_limit = memory_stats.get("limit", 1)
        stats_detail = memory_stats.get("stats", {})
        cache = stats_detail.get(
            "total_inactive_file",
            stats_detail.get("inactive_file", stats_detail.get("cache", 0)),
        )
        real_usage = max(0, raw_usage - cache)
        memory_percent = (real_usage / memory_limit) * 100.0 if memory_limit > 0 else 0.0

        # Rede
        networks = stats.get("networks", {})
        network_rx = sum(net.get("rx_bytes", 0) for net in networks.values())
        network_tx = sum(net.get("tx_bytes", 0) for net in networks.values())

        return {
            "cpu_percent": round(cpu_percent, 2),
            "memory_usage_mb": round(real_usage / (1024 * 1024), 2),
            "memory_limit_mb": round(memory_limit / (1024 * 1024), 2),
            "memory_percent": round(memory_percent, 2),
            "network_rx_mb": round(network_rx / (1024 * 1024), 2),
            "network_tx_mb": round(network_tx / (1024 * 1024), 2),
        }

    def _stream_container_stats_sync(
        self, container_id: str, interval: float = 2.0
    ) -> Generator[dict[str, Any], None, None]:
        """
        Generator síncrono que produz métricas continuamente.
        Deve ser executado em uma thread separada (via asyncio.to_thread ou threading.Thread).
        """
        while True:
            try:
                c = self.client.containers.get(container_id)
                stats = c.stats(stream=False)

                cpu_stats = stats.get("cpu_stats", {})
                precpu_stats = stats.get("precpu_stats", {})
                cpu_delta = (
                    cpu_stats.get("cpu_usage", {}).get("total_usage", 0)
                    - precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
                )
                system_delta = cpu_stats.get("system_cpu_usage", 0) - precpu_stats.get(
                    "system_cpu_usage", 0
                )
                online_cpus = cpu_stats.get("online_cpus") or len(
                    cpu_stats.get("cpu_usage", {}).get("percpu_usage", [1])
                )
                cpu_percent = 0.0
                if system_delta > 0 and cpu_delta > 0:
                    cpu_percent = (cpu_delta / system_delta) * online_cpus * 100.0

                memory_stats = stats.get("memory_stats", {})
                raw_usage = memory_stats.get("usage", 0)
                memory_limit = memory_stats.get("limit", 1)
                stats_detail = memory_stats.get("stats", {})
                cache = stats_detail.get(
                    "total_inactive_file",
                    stats_detail.get("inactive_file", stats_detail.get("cache", 0)),
                )
                real_usage = max(0, raw_usage - cache)
                memory_percent = (real_usage / memory_limit * 100.0) if memory_limit > 0 else 0.0

                networks = stats.get("networks", {})
                network_rx = sum(net.get("rx_bytes", 0) for net in networks.values())
                network_tx = sum(net.get("tx_bytes", 0) for net in networks.values())

                yield {
                    "cpu_percent": round(cpu_percent, 2),
                    "memory_usage_mb": round(real_usage / (1024 * 1024), 2),
                    "memory_limit_mb": round(memory_limit / (1024 * 1024), 2),
                    "memory_percent": round(memory_percent, 2),
                    "network_rx_mb": round(network_rx / (1024 * 1024), 2),
                    "network_tx_mb": round(network_tx / (1024 * 1024), 2),
                }
                time.sleep(interval)
            except Exception:
                break

    # ----------------------------------------------------------------
    # Imagens
    # ----------------------------------------------------------------

    def build_image(
        self, path: str, tag: str, dockerfile: str = "Dockerfile"
    ) -> Generator[str, None, None]:
        """
        Build de imagem Docker com streaming de logs.
        Generator síncrono — deve ser executado em thread separada.
        """
        for chunk in self.client.api.build(
            path=path, tag=tag, dockerfile=dockerfile, rm=True, decode=True
        ):
            if "stream" in chunk:
                yield chunk["stream"]
            elif "error" in chunk:
                error_msg = chunk.get("errorDetail", {}).get("message", chunk["error"])
                raise RuntimeError(f"Erro no Docker Build: {error_msg}")

    async def list_images(self) -> list[dict[str, Any]]:
        """Lista todas as imagens Docker."""
        images = await asyncio.to_thread(self.client.images.list)
        return [
            {
                "id": i.short_id,
                "tags": i.tags,
                "size_mb": round(i.attrs.get("Size", 0) / (1024 * 1024), 2),
                "created": i.attrs.get("Created"),
            }
            for i in images
        ]

    async def remove_image(self, image_id: str, force: bool = False) -> None:
        """Remove uma imagem Docker."""
        try:
            await asyncio.to_thread(self.client.images.remove, image_id, force=force)
        except ImageNotFound:
            raise ValueError(f"Imagem '{image_id}' não encontrada.")

    # ----------------------------------------------------------------
    # Volumes e Redes
    # ----------------------------------------------------------------

    async def list_volumes(self) -> list[dict[str, Any]]:
        """Lista todos os volumes Docker."""
        vols = await asyncio.to_thread(self.client.volumes.list)
        return [
            {
                "name": v.name,
                "driver": v.attrs.get("Driver"),
                "mountpoint": v.attrs.get("Mountpoint"),
                "created": v.attrs.get("CreatedAt"),
            }
            for v in vols
        ]

    async def list_networks(self) -> list[dict[str, Any]]:
        """Lista todas as redes Docker."""
        nets = await asyncio.to_thread(self.client.networks.list)
        return [
            {
                "id": n.short_id,
                "name": n.name,
                "driver": n.attrs.get("Driver"),
                "scope": n.attrs.get("Scope"),
            }
            for n in nets
        ]

    # ----------------------------------------------------------------
    # Sistema
    # ----------------------------------------------------------------

    async def get_system_info(self) -> dict[str, Any]:
        """Informações gerais do Docker Engine."""
        info = await asyncio.to_thread(self.client.info)
        version = await asyncio.to_thread(self.client.version)
        return {
            "docker_version": version.get("Version"),
            "api_version": version.get("ApiVersion"),
            "os": info.get("OperatingSystem"),
            "architecture": info.get("Architecture"),
            "cpus": info.get("NCPU"),
            "memory_total_mb": round(info.get("MemTotal", 0) / (1024 * 1024), 2),
            "containers_count": info.get("Containers"),
            "containers_running": info.get("ContainersRunning"),
            "containers_stopped": info.get("ContainersStopped"),
            "containers_paused": info.get("ContainersPaused"),
            "images_count": info.get("Images"),
            "volumes_count": len(await self.list_volumes()),
            "networks_count": len(await self.list_networks()),
        }

    async def prune_system(self) -> dict[str, Any]:
        """Remove contêineres, imagens, volumes e redes não utilizados."""
        containers = await asyncio.to_thread(self.client.containers.prune)
        images = await asyncio.to_thread(self.client.images.prune)
        volumes = await asyncio.to_thread(self.client.volumes.prune)
        networks = await asyncio.to_thread(self.client.networks.prune)
        return {
            "containers_deleted": len(containers.get("ContainersDeleted") or []),
            "images_deleted": len(images.get("ImagesDeleted") or []),
            "volumes_deleted": len(volumes.get("VolumesDeleted") or []),
            "networks_deleted": len(networks.get("NetworksDeleted") or []),
            "space_reclaimed_mb": round(
                (
                    containers.get("SpaceReclaimed", 0)
                    + images.get("SpaceReclaimed", 0)
                    + volumes.get("SpaceReclaimed", 0)
                )
                / (1024 * 1024),
                2,
            ),
        }
