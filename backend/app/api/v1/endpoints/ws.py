"""
Endpoints WebSocket para streaming em tempo real.

- /ws/containers/{container_id}/logs — Streaming de logs
- /ws/containers/{container_id}/metrics — Métricas CPU/RAM a cada 2s
- /ws/deployments/{deployment_id}/stream — Progresso do deploy
"""

import asyncio
import threading
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.docker_service import DockerService
from app.services.websocket_manager import ws_manager

router = APIRouter()


@router.websocket("/containers/{container_id}/logs")
async def container_logs_ws(websocket: WebSocket, container_id: str) -> None:
    """
    Streaming de logs de um contêiner em tempo real.

    O docker-py é síncrono e bloqueante — usamos uma thread daemon
    para alimentar uma asyncio.Queue que é consumida no event loop.
    """
    await ws_manager.connect(websocket, f"logs_{container_id}")
    loop = asyncio.get_running_loop()
    log_queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=500)
    stop_event = threading.Event()

    def _log_worker() -> None:
        """Thread daemon que lê logs do Docker e enfileira linhas."""
        try:
            docker = DockerService()
            for line in docker.stream_container_logs(container_id, tail=100):
                if stop_event.is_set():
                    break
                loop.call_soon_threadsafe(log_queue.put_nowait, line)
        except Exception:
            pass
        finally:
            loop.call_soon_threadsafe(log_queue.put_nowait, None)

    thread = threading.Thread(target=_log_worker, daemon=True)
    thread.start()

    try:
        while True:
            line = await log_queue.get()
            if line is None:
                break
            await websocket.send_json({"type": "log", "data": line})
    except WebSocketDisconnect:
        pass
    finally:
        stop_event.set()
        ws_manager.disconnect(websocket, f"logs_{container_id}")


@router.websocket("/containers/{container_id}/metrics")
async def container_metrics_ws(websocket: WebSocket, container_id: str) -> None:
    """
    Streaming de métricas (CPU, memória, rede) a cada 2 segundos.

    Usa asyncio.to_thread para cada chamada de stats, evitando bloquear o loop.
    """
    await ws_manager.connect(websocket, f"metrics_{container_id}")
    docker = DockerService()

    try:
        while True:
            try:
                stats = await docker.get_container_stats(container_id)
                await websocket.send_json({"type": "metrics", "data": stats})
            except ValueError:
                # Contêiner não encontrado — encerrar stream
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Contêiner não encontrado"},
                })
                break
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": str(e)},
                })
                break
            await asyncio.sleep(2.0)
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(websocket, f"metrics_{container_id}")


@router.websocket("/deployments/{deployment_id}/stream")
async def deployment_stream_ws(websocket: WebSocket, deployment_id: str) -> None:
    """
    Stream de progresso do deploy.

    O DeployOrchestrator envia atualizações via ws_manager.broadcast(),
    que são automaticamente entregues a todas as conexões neste tópico.
    """
    topic = f"deploy_{deployment_id}"
    await ws_manager.connect(websocket, topic)
    try:
        while True:
            # Mantém a conexão aberta aguardando mensagens do cliente (ping/pong)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(websocket, topic)
