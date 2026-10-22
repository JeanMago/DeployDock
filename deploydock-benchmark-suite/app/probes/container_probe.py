"""
Sonda de Ambiente de Contêiner, Cgroups (v1/v2), Rede, Proxy Reverso e Persistência.
Compatível com qualquer gerenciador Docker (DeployDock, Portainer, Coolify, CapRover, Dokploy, Docker Engine).
Utiliza apenas biblioteca padrão Python + leitura direta de /proc e /sys para portabilidade máxima.
"""

import os
import platform
import shutil
import socket
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _read_file_safe(path: str) -> Optional[str]:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read().strip()
    except Exception:
        pass
    return None


def _get_host_memory_total_bytes() -> int:
    meminfo = _read_file_safe("/proc/meminfo") or ""
    for line in meminfo.splitlines():
        if line.startswith("MemTotal:"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                return int(parts[1]) * 1024
    return 8 * 1024 * 1024 * 1024  # Fallback 8GB


def _get_process_rss_bytes() -> int:
    status = _read_file_safe("/proc/self/status") or ""
    for line in status.splitlines():
        if line.startswith("VmRSS:"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                return int(parts[1]) * 1024
    return 45 * 1024 * 1024


def inspect_cgroups() -> Dict[str, Any]:
    """Lê limites reais de CPU, Memória RAM e PIDs configurados no Cgroup v2 ou v1."""
    cgroup_version = "v2" if os.path.exists("/sys/fs/cgroup/cgroup.controllers") else "v1"

    # 1. Limite de Memória (RAM Quota)
    mem_max_raw = (
        _read_file_safe("/sys/fs/cgroup/memory.max")
        or _read_file_safe("/sys/fs/cgroup/memory/memory.limit_in_bytes")
    )
    mem_current_raw = (
        _read_file_safe("/sys/fs/cgroup/memory.current")
        or _read_file_safe("/sys/fs/cgroup/memory/memory.usage_in_bytes")
    )

    host_mem_total = _get_host_memory_total_bytes()
    mem_limit_bytes: Optional[int] = None
    mem_quota_active = False

    if mem_max_raw and mem_max_raw != "max":
        try:
            val = int(mem_max_raw)
            if 0 < val < (host_mem_total * 2) and val < (1 << 50):
                mem_limit_bytes = val
                mem_quota_active = True
        except ValueError:
            pass

    mem_current_bytes = None
    if mem_current_raw:
        try:
            mem_current_bytes = int(mem_current_raw)
        except ValueError:
            pass

    # 2. Limite de CPU (vCPU Quota)
    cpu_max_raw = _read_file_safe("/sys/fs/cgroup/cpu.max")
    cpu_quota_cores: Optional[float] = None
    cpu_quota_active = False

    if cpu_max_raw:
        parts = cpu_max_raw.split()
        if len(parts) == 2 and parts[0] != "max":
            try:
                quota = int(parts[0])
                period = int(parts[1])
                if quota > 0 and period > 0:
                    cpu_quota_cores = round(quota / period, 2)
                    cpu_quota_active = True
            except ValueError:
                pass
    else:
        q_v1 = _read_file_safe("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
        p_v1 = _read_file_safe("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
        if q_v1 and p_v1:
            try:
                q_val, p_val = int(q_v1), int(p_v1)
                if q_val > 0 and p_val > 0:
                    cpu_quota_cores = round(q_val / p_val, 2)
                    cpu_quota_active = True
            except ValueError:
                pass

    # 3. Limite de Processos (PIDs Limit / Proteção Anti-Fork-Bomb)
    pids_max_raw = (
        _read_file_safe("/sys/fs/cgroup/pids.max")
        or _read_file_safe("/sys/fs/cgroup/pids/pids.max")
    )
    pids_current_raw = (
        _read_file_safe("/sys/fs/cgroup/pids.current")
        or _read_file_safe("/sys/fs/cgroup/pids/pids.current")
    )
    pids_limit: Optional[int] = None
    pids_quota_active = False

    if pids_max_raw and pids_max_raw != "max":
        try:
            val = int(pids_max_raw)
            if 0 < val < 100000:
                pids_limit = val
                pids_quota_active = True
        except ValueError:
            pass

    pids_current = int(pids_current_raw) if (pids_current_raw and pids_current_raw.isdigit()) else None

    return {
        "cgroup_version": cgroup_version,
        "memory_quota_active": mem_quota_active,
        "memory_limit_mb": round(mem_limit_bytes / (1024 * 1024), 1) if mem_limit_bytes else None,
        "memory_current_mb": (
            round(mem_current_bytes / (1024 * 1024), 2)
            if mem_current_bytes
            else round(_get_process_rss_bytes() / (1024 * 1024), 2)
        ),
        "host_memory_total_mb": round(host_mem_total / (1024 * 1024), 1),
        "cpu_quota_active": cpu_quota_active,
        "cpu_limit_cores": cpu_quota_cores,
        "host_cpu_cores": os.cpu_count() or 1,
        "pids_quota_active": pids_quota_active,
        "pids_limit": pids_limit,
        "pids_current": pids_current,
    }


def detect_orchestrator_platform(request_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Detecta automaticamente em qual plataforma de controle Docker o contêiner está rodando
    analisando hostname, variáveis de ambiente, limites de PIDs/Hardening e headers HTTP.
    """
    headers = {k.lower(): v for k, v in (request_headers or {}).items()}
    explicit_name = os.getenv("PLATFORM_NAME", "").strip()
    hostname = socket.gethostname()
    cgroups = inspect_cgroups()

    no_new_privs = False
    status_txt = _read_file_safe("/proc/self/status") or ""
    for line in status_txt.splitlines():
        if line.startswith("NoNewPrivs:"):
            no_new_privs = line.split(":", 1)[1].strip() == "1"

    indicators: List[str] = []
    detected = "Docker Engine (Standalone)"
    confidence = "medium"

    if explicit_name and explicit_name.lower() != "auto-detect":
        detected = explicit_name
        confidence = "high"
        indicators.append(f"Definido via variável PLATFORM_NAME={explicit_name}")

    # Indicadores DeployDock
    if (
        cgroups.get("pids_limit") == 256
        or no_new_privs
        or os.getenv("DEPLOYDOCK_PROJECT")
        or "x-deploydock-shield" in headers
    ):
        if detected in ("Docker Engine (Standalone)", "Auto-Detect"):
            detected = "DeployDock PaaS"
            confidence = "high"
        if cgroups.get("pids_limit") == 256:
            indicators.append("pids_limit=256 ativo (Assinatura padrão DeployDock)")
        if no_new_privs:
            indicators.append("security_opt no-new-privileges=true ativo (Hardening DeployDock)")

    if any(k.startswith("COOLIFY_") for k in os.environ):
        detected = "Coolify"
        confidence = "high"
        indicators.append("Variáveis COOLIFY_* detectadas no ambiente")

    if any(k.startswith("CAPROVER_") for k in os.environ) or os.getenv("CAPTAIN_IS_DEBUG"):
        detected = "CapRover"
        confidence = "high"
        indicators.append("Variáveis CAPROVER_* detectadas no ambiente")

    if any(k.startswith("PORTAINER_") for k in os.environ):
        detected = "Portainer"
        confidence = "high"
        indicators.append("Variáveis PORTAINER_* detectadas")

    proxy_detected = bool(
        headers.get("x-forwarded-for")
        or headers.get("x-forwarded-proto")
        or headers.get("x-forwarded-host")
        or headers.get("x-real-ip")
    )
    if proxy_detected:
        indicators.append(
            f"Proxy Reverso detectado (Proto: {headers.get('x-forwarded-proto', 'http')}, "
            f"Host: {headers.get('x-forwarded-host') or headers.get('host', 'local')})"
        )

    is_container = os.path.exists("/.dockerenv") or "docker" in (_read_file_safe("/proc/1/cgroup") or "").lower()

    return {
        "platform_name": detected,
        "confidence": confidence,
        "running_in_container": is_container,
        "hostname": hostname,
        "reverse_proxy_detected": proxy_detected,
        "forwarded_proto": headers.get("x-forwarded-proto", "http"),
        "forwarded_host": headers.get("x-forwarded-host") or headers.get("host", f"{hostname}:8080"),
        "forwarded_for": headers.get("x-forwarded-for") or headers.get("x-real-ip", "direct"),
        "indicators": indicators,
    }


def inspect_network_and_dns() -> Dict[str, Any]:
    """Inspeciona interfaces de rede do contêiner, resolução DNS interna do Docker e conectividade."""
    interfaces = []
    try:
        host_ip = socket.gethostbyname(socket.gethostname())
        interfaces.append({"interface": "eth0/primary", "ipv4": [host_ip]})
    except Exception:
        interfaces.append({"interface": "lo", "ipv4": ["127.0.0.1"]})

    resolv_conf = _read_file_safe("/etc/resolv.conf") or ""
    nameservers = [
        line.split()[1]
        for line in resolv_conf.splitlines()
        if line.strip().startswith("nameserver") and len(line.split()) >= 2
    ]

    t0 = time.perf_counter()
    dns_ok = False
    resolved_ip = None
    try:
        resolved_ip = socket.gethostbyname("localhost")
        dns_ok = True
    except Exception:
        pass
    dns_latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    return {
        "interfaces": interfaces,
        "nameservers": nameservers,
        "docker_embedded_dns": "127.0.0.11" in nameservers,
        "dns_resolution_ok": dns_ok,
        "dns_latency_ms": dns_latency_ms,
        "resolved_localhost": resolved_ip,
    }


def inspect_environment_and_storage(workspace_dir: str = "/app/workspace") -> Dict[str, Any]:
    """Verifica variáveis de ambiente injetadas e capacidade de armazenamento/volumes."""
    os.makedirs(workspace_dir, exist_ok=True)
    probe_file = os.path.join(workspace_dir, "deploydock_probe_marker.txt")
    if not os.path.exists(probe_file):
        try:
            with open(probe_file, "w", encoding="utf-8") as f:
                f.write(
                    f"Arquivo de sonda criado em {datetime.now(timezone.utc).isoformat()}\n"
                    "Este arquivo pode ser lido, editado ou baixado pelo Explorador de Arquivos da plataforma Docker.\n"
                )
        except Exception:
            pass

    files_in_workspace = []
    try:
        for entry in sorted(os.listdir(workspace_dir)):
            full = os.path.join(workspace_dir, entry)
            if os.path.isfile(full):
                stat = os.stat(full)
                files_in_workspace.append(
                    {
                        "name": entry,
                        "size_bytes": stat.st_size,
                        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                    }
                )
    except Exception:
        pass

    safe_env_keys = {}
    for k, v in sorted(os.environ.items()):
        if any(secret_word in k.upper() for secret_word in ("PASSWORD", "SECRET", "TOKEN", "KEY")):
            safe_env_keys[k] = f"***MASKED (len={len(v)})***"
        else:
            safe_env_keys[k] = v

    usage = shutil.disk_usage(workspace_dir if os.path.exists(workspace_dir) else "/")
    used_pct = round(((usage.total - usage.free) / max(usage.total, 1)) * 100, 1)

    return {
        "env_count": len(os.environ),
        "benchmark_env_injected": os.getenv("BENCHMARK_ENV_INJECTED", "not-set"),
        "custom_env_vars_detected": [
            k for k in os.environ.keys()
            if k.startswith(("DEPLOYDOCK_", "BENCHMARK_", "APP_", "COOLIFY_", "CAPROVER_"))
        ],
        "environment_snapshot": safe_env_keys,
        "workspace_dir": os.path.abspath(workspace_dir),
        "workspace_writable": os.access(workspace_dir, os.W_OK),
        "workspace_files": files_in_workspace,
        "disk_total_gb": round(usage.total / (1024 ** 3), 2),
        "disk_free_gb": round(usage.free / (1024 ** 3), 2),
        "disk_percent": used_pct,
        "os_release": platform.platform(),
        "python_version": platform.python_version(),
        "architecture": platform.machine(),
    }
