"""
Sonda de Segurança & Hardening de Contêiner Docker.
Avalia as políticas de isolamento aplicadas pela plataforma de controle Docker ao criar o contêiner:
- no-new-privileges (NoNewPrivs)
- Seccomp syscall filtering
- Capabilities Linux (verificando se CAP_SYS_ADMIN / Privileged Mode estão bloqueados)
- Proteção contra Fork Bomb (pids.max)
- Isolamento do Docker Socket (/var/run/docker.sock)
- Execução de usuário e permissões
"""

import os
from typing import Any, Dict, List

from app.probes.container_probe import _read_file_safe, inspect_cgroups


def inspect_container_security() -> Dict[str, Any]:
    """Audita o nível de hardening do contêiner em execução e calcula pontuação de segurança."""
    status_content = _read_file_safe("/proc/self/status") or ""
    status_map: Dict[str, str] = {}
    for line in status_content.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            status_map[k.strip()] = v.strip()

    # 1. NoNewPrivileges (impede escalação de privilégio via binários setuid)
    no_new_privs_raw = status_map.get("NoNewPrivs", "0")
    no_new_privs = no_new_privs_raw == "1"

    # 2. Seccomp (0=disabled, 1=strict, 2=filter)
    seccomp_raw = status_map.get("Seccomp", "0")
    seccomp_active = seccomp_raw in ("1", "2")
    seccomp_mode = (
        "filter (bpf)" if seccomp_raw == "2" else ("strict" if seccomp_raw == "1" else "disabled")
    )

    # 3. Capabilities Efetivas (CapEff) — verifica se CAP_SYS_ADMIN (bit 21) está ativo (modo privilegiado)
    cap_eff_hex = status_map.get("CapEff", "0000000000000000")
    try:
        cap_eff_int = int(cap_eff_hex, 16)
    except ValueError:
        cap_eff_int = 0

    cap_sys_admin = bool(cap_eff_int & (1 << 21))
    is_privileged = cap_sys_admin and cap_eff_hex.lower().startswith("000001ffffffffff")

    # 4. Docker Socket exposto dentro do contêiner de aplicação (risco crítico de escape)
    docker_sock_mounted = os.path.exists("/var/run/docker.sock")

    # 5. Limite de Processos (PIDs Limit contra Fork Bomb)
    cgroups = inspect_cgroups()
    pids_limit_active = bool(cgroups.get("pids_quota_active"))
    pids_limit_val = cgroups.get("pids_limit")

    # 6. Limite de Memória/CPU configurado
    resource_limits_active = bool(cgroups.get("memory_quota_active") or cgroups.get("cpu_quota_active"))

    checks: List[Dict[str, Any]] = [
        {
            "id": "no_new_privileges",
            "title": "Bloqueio de Escalação de Privilégio (no-new-privileges)",
            "passed": no_new_privs,
            "value": f"NoNewPrivs={no_new_privs_raw}",
            "weight": 25,
            "description": "Impede que processos ganhem novos privilégios via binários SUID/SGID (ativado nativamente pelo DeployDock).",
        },
        {
            "id": "pids_limit",
            "title": "Proteção Anti-Fork-Bomb (Limite de PIDs no Cgroup)",
            "passed": pids_limit_active,
            "value": f"pids.max={pids_limit_val}" if pids_limit_active else "Ilimitado (max)",
            "weight": 20,
            "description": "Limita o número máximo de processos simultâneos no contêiner (DeployDock define pids_limit=256).",
        },
        {
            "id": "docker_socket_isolation",
            "title": "Isolamento do Docker Socket (/var/run/docker.sock)",
            "passed": not docker_sock_mounted,
            "value": "Isolado (Seguro)" if not docker_sock_mounted else "EXPOSTO (Crítico)",
            "weight": 20,
            "description": "Garante que o contêiner da aplicação não tenha acesso ao daemon Docker do host.",
        },
        {
            "id": "non_privileged_mode",
            "title": "Restrição de Modo Privilegiado (CAP_SYS_ADMIN bloqueado)",
            "passed": not cap_sys_admin,
            "value": f"CapEff=0x{cap_eff_hex}",
            "weight": 15,
            "description": "Verifica se capabilities administrativas críticas do Kernel Linux estão desativadas.",
        },
        {
            "id": "seccomp_profile",
            "title": "Filtro de Syscalls do Kernel (Seccomp BPF)",
            "passed": seccomp_active,
            "value": seccomp_mode,
            "weight": 10,
            "description": "Restringe chamadas de sistema perigosas no nível do Kernel.",
        },
        {
            "id": "resource_quotas",
            "title": "Quotas de Recursos Cgroup (RAM / CPU)",
            "passed": resource_limits_active,
            "value": (
                f"RAM={cgroups.get('memory_limit_mb') or 'Max'}MB, CPU={cgroups.get('cpu_limit_cores') or 'Max'} cores"
            ),
            "weight": 10,
            "description": "Protege o servidor contra exaustão de memória (OOM) ou monopólio de CPU por um único contêiner.",
        },
    ]

    score = sum(c["weight"] for c in checks if c["passed"])

    return {
        "hardening_score": score,
        "no_new_privileges": no_new_privs,
        "seccomp_mode": seccomp_mode,
        "cap_eff_hex": cap_eff_hex,
        "cap_sys_admin_enabled": cap_sys_admin,
        "is_privileged_container": is_privileged,
        "docker_socket_exposed": docker_sock_mounted,
        "pids_limit_active": pids_limit_active,
        "pids_limit": pids_limit_val,
        "checks": checks,
    }
