"""
Aplicação Principal — DeployDock Benchmark & Multi-Platform PaaS Probe.
Pode ser executada dentro do DeployDock, Portainer, Coolify, CapRover, Dokploy ou via Docker/Python local.
Inclui Stress Test de Máquina, 45 Testes E2E, Painel Interativo e Gerador de Documentos Técnicos Formais (.md e PDF/Print HTML).
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel

from app.probes.comparison_matrix import (
    FEATURE_CATALOG,
    REFERENCE_PLATFORMS,
    build_current_platform_snapshot,
)
from app.probes.container_probe import (
    detect_orchestrator_platform,
    inspect_cgroups,
    inspect_environment_and_storage,
    inspect_network_and_dns,
)
from app.probes.deploydock_api_tester import run_deploydock_e2e_suite
from app.probes.document_generator import (
    compute_report_sha256,
    generate_markdown_document,
    generate_printable_document_html,
)
from app.probes.performance_bench import run_full_performance_suite
from app.probes.security_probe import inspect_container_security

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("deploydock-benchmark")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.getenv("BENCHMARK_WORKSPACE_DIR", os.path.join(os.path.dirname(BASE_DIR), "workspace"))
REPORTS_DIR = os.getenv("BENCHMARK_REPORTS_DIR", os.path.join(os.path.dirname(BASE_DIR), "reports"))
STATIC_INDEX = os.path.join(BASE_DIR, "static", "index.html")

os.makedirs(WORKSPACE_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

START_TIME = time.time()

CHAOS_STATE: Dict[str, Any] = {
    "healthy": True,
    "simulated_status_code": 200,
    "artificial_delay_ms": 0,
    "logs_emitted_count": 0,
}

LATEST_REPORT: Optional[Dict[str, Any]] = None
IMPORTED_SNAPSHOTS: List[Dict[str, Any]] = []


class AuditRunRequest(BaseModel):
    platform_label: Optional[str] = None
    deploydock_api_url: Optional[str] = None
    username: str = "admin"
    password: str = "admin123"
    intensity: str = "heavy"  # standard | heavy | extreme


class ChaosHealthRequest(BaseModel):
    healthy: bool = True
    status_code: int = 200
    delay_ms: int = 0


class LogBurstRequest(BaseModel):
    level: str = "ALL"
    count: int = 10
    custom_message: Optional[str] = None


class WorkspaceFilePayload(BaseModel):
    filename: str
    content: str


app = FastAPI(
    title="DeployDock Benchmark & PaaS Comparison Suite",
    description=(
        "Suite interativa de testes E2E (45 testes), stress test de máquina, sondagem de contêineres, "
        "auditoria de segurança, gerador de laudo técnico e benchmark comparativo entre gerenciadores Docker."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def serve_interactive_dashboard():
    if os.path.exists(STATIC_INDEX):
        return FileResponse(STATIC_INDEX, media_type="text/html")
    return HTMLResponse("<h1>Interface estática não encontrada.</h1>", status_code=404)


@app.get("/health")
async def health_check_endpoint():
    if CHAOS_STATE["artificial_delay_ms"] > 0:
        await asyncio.sleep(CHAOS_STATE["artificial_delay_ms"] / 1000.0)

    if not CHAOS_STATE["healthy"]:
        logger.error("[ERROR] Healthcheck falhou propositalmente (Simulação de Falha / Auto-Heal Test)")
        return JSONResponse(
            status_code=CHAOS_STATE["simulated_status_code"] or 500,
            content={
                "status": "unhealthy",
                "simulation": True,
                "message": "Falha simulada ativa para teste de Health Check / Rollback / Auto-Healing",
                "uptime_seconds": round(time.time() - START_TIME, 1),
            },
        )

    return {
        "status": "healthy",
        "service": "deploydock-benchmark-suite",
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _persist_all_report_artifacts(report: Dict[str, Any]) -> None:
    """Salva o JSON, o Documento Técnico em Markdown (.md) e o Laudo HTML para Impressão/PDF."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    md_text = generate_markdown_document(report)
    print_html = generate_printable_document_html(report)
    report["markdown_document"] = md_text
    report["integrity_sha256"] = compute_report_sha256(report)

    try:
        with open(os.path.join(REPORTS_DIR, "latest_report.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        with open(os.path.join(REPORTS_DIR, "RELATORIO_TECNICO_AUDITORIA_DEPLOYDOCK.md"), "w", encoding="utf-8") as f:
            f.write(md_text)
        with open(os.path.join(REPORTS_DIR, "DOCUMENTO_LAUDO_TECNICO_IMPRESSAO.html"), "w", encoding="utf-8") as f:
            f.write(print_html)
    except Exception as exc:
        logger.warning(f"Falha ao persistir artefatos de relatório em {REPORTS_DIR}: {exc}")


async def execute_complete_audit(
    request_headers: Optional[Dict[str, str]] = None,
    platform_label: Optional[str] = None,
    deploydock_api_url: Optional[str] = None,
    username: str = "admin",
    password: str = "admin123",
    intensity: str = "heavy",
) -> Dict[str, Any]:
    """Executa todas as sondas internas, stress test de máquina, testes E2E e gera os documentos formais."""
    global LATEST_REPORT
    t0 = time.perf_counter()

    cgroups = inspect_cgroups()
    orchestrator = detect_orchestrator_platform(request_headers)
    if platform_label and platform_label.strip():
        orchestrator["platform_name"] = platform_label.strip()
        orchestrator["confidence"] = "manual"

    net_dns = inspect_network_and_dns()
    env_storage = inspect_environment_and_storage(WORKSPACE_DIR)
    security = inspect_container_security()
    performance = await asyncio.to_thread(run_full_performance_suite, WORKSPACE_DIR, intensity)

    e2e_results = await run_deploydock_e2e_suite(
        api_url=deploydock_api_url,
        username=username,
        password=password,
    )

    current_snapshot = build_current_platform_snapshot(
        orchestrator_info=orchestrator,
        cgroups_info=cgroups,
        security_info=security,
        perf_info=performance,
        e2e_info=e2e_results,
    )
    if platform_label and platform_label.strip():
        current_snapshot["platform_name"] = platform_label.strip()

    report: Dict[str, Any] = {
        "report_id": f"bench-{int(time.time())}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "audit_duration_ms": round((time.perf_counter() - t0) * 1000, 1),
        "orchestrator": orchestrator,
        "cgroups": cgroups,
        "network": net_dns,
        "environment_storage": env_storage,
        "security": security,
        "performance": performance,
        "deploydock_e2e": e2e_results,
        "current_platform_snapshot": current_snapshot,
        "feature_catalog": FEATURE_CATALOG,
        "comparison_platforms": [current_snapshot] + IMPORTED_SNAPSHOTS + REFERENCE_PLATFORMS,
        "chaos_state": CHAOS_STATE,
    }

    _persist_all_report_artifacts(report)
    LATEST_REPORT = report

    logger.info(
        f"[INFO] Auditoria completa ({intensity}) executada em {report['audit_duration_ms']}ms — "
        f"Score Global: {current_snapshot['overall_score']}/100 | "
        f"Testes E2E: {e2e_results['passed_tests']}/{e2e_results['total_tests']}"
    )
    return report


@app.get("/api/audit/latest")
async def get_latest_audit(request: Request):
    if LATEST_REPORT is not None:
        LATEST_REPORT["chaos_state"] = CHAOS_STATE
        LATEST_REPORT["environment_storage"] = inspect_environment_and_storage(WORKSPACE_DIR)
        return LATEST_REPORT
    return await execute_complete_audit(dict(request.headers))


@app.post("/api/audit/run")
async def trigger_audit_run(body: AuditRunRequest, request: Request):
    return await execute_complete_audit(
        request_headers=dict(request.headers),
        platform_label=body.platform_label,
        deploydock_api_url=body.deploydock_api_url,
        username=body.username,
        password=body.password,
        intensity=body.intensity,
    )


@app.post("/api/chaos/health")
async def configure_chaos_health(body: ChaosHealthRequest):
    CHAOS_STATE["healthy"] = body.healthy
    CHAOS_STATE["simulated_status_code"] = body.status_code if not body.healthy else 200
    CHAOS_STATE["artificial_delay_ms"] = max(0, min(body.delay_ms, 15000))
    state_str = "SAUDÁVEL (200 OK)" if body.healthy else f"FALHA SIMULADA (HTTP {CHAOS_STATE['simulated_status_code']})"
    logger.warning(f"[WARN] Estado do Healthcheck alterado para: {state_str} (Delay={CHAOS_STATE['artificial_delay_ms']}ms)")
    return {"chaos_state": CHAOS_STATE, "message": f"Healthcheck configurado para {state_str}"}


@app.post("/api/chaos/logs")
async def emit_test_logs(body: LogBurstRequest):
    count = max(1, min(body.count, 100))
    lvl = body.level.upper()
    emitted = []
    for i in range(1, count + 1):
        ts = datetime.now(timezone.utc).isoformat()
        custom = f" - {body.custom_message}" if body.custom_message else ""
        if lvl == "ERROR" or (lvl == "ALL" and i % 3 == 0):
            line = f"{ts} [ERROR] [BenchmarkProbe #{i}] Falha simulada de conexão com banco/cache para teste de filtro ERR{custom}"
            print(line, file=sys.stderr, flush=True)
        elif lvl == "WARN" or (lvl == "ALL" and i % 2 == 0):
            line = f"{ts} [WARN] [BenchmarkProbe #{i}] Latência elevada detectada no worker (420ms > threshold){custom}"
            print(line, file=sys.stdout, flush=True)
        else:
            line = f"{ts} [INFO] [BenchmarkProbe #{i}] Requisição de telemetria processada com sucesso (status=200){custom}"
            print(line, file=sys.stdout, flush=True)
        emitted.append(line)
        CHAOS_STATE["logs_emitted_count"] += 1

    return {
        "emitted_count": len(emitted),
        "total_emitted_session": CHAOS_STATE["logs_emitted_count"],
        "sample_lines": emitted[:5],
    }


@app.get("/api/workspace/files")
async def list_workspace_files():
    return inspect_environment_and_storage(WORKSPACE_DIR)


@app.post("/api/workspace/files")
async def create_workspace_file(body: WorkspaceFilePayload):
    safe_name = os.path.basename(body.filename.strip())
    if not safe_name:
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido.")
    target = os.path.join(WORKSPACE_DIR, safe_name)
    with open(target, "w", encoding="utf-8") as f:
        f.write(body.content)
    logger.info(f"[INFO] Arquivo de teste '{safe_name}' gravado em {WORKSPACE_DIR} ({len(body.content)} bytes)")
    return inspect_environment_and_storage(WORKSPACE_DIR)


@app.post("/api/comparison/import")
async def import_external_snapshot(snapshot: Dict[str, Any]):
    snap = snapshot.get("current_platform_snapshot", snapshot)
    if "platform_name" not in snap or "benchmark" not in snap:
        raise HTTPException(
            status_code=400,
            detail="Formato de snapshot inválido. Exporte o JSON pelo botão 'Exportar Snapshot JSON' desta aplicação.",
        )

    snap["is_imported"] = True
    snap["platform_id"] = f"imported_{int(time.time())}"
    IMPORTED_SNAPSHOTS.insert(0, snap)

    if LATEST_REPORT is not None:
        LATEST_REPORT["comparison_platforms"] = (
            [LATEST_REPORT["current_platform_snapshot"]] + IMPORTED_SNAPSHOTS + REFERENCE_PLATFORMS
        )
        _persist_all_report_artifacts(LATEST_REPORT)

    return {
        "message": f"Snapshot da plataforma '{snap['platform_name']}' importado com sucesso!",
        "imported_snapshot": snap,
        "comparison_platforms": (
            LATEST_REPORT["comparison_platforms"]
            if LATEST_REPORT
            else [snap] + REFERENCE_PLATFORMS
        ),
    }


@app.get("/api/report/export-json")
async def export_snapshot_json(request: Request):
    report = LATEST_REPORT or await execute_complete_audit(dict(request.headers))
    slug = report["current_platform_snapshot"]["platform_name"].lower().replace(" ", "_")
    content = json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="benchmark_snapshot_{slug}.json"'
        },
    )


@app.get("/api/report/document-md")
async def export_markdown_document(request: Request):
    """Faz download do Documento Técnico formal em formato Markdown (.md)."""
    report = LATEST_REPORT or await execute_complete_audit(dict(request.headers))
    md_text = generate_markdown_document(report)
    return Response(
        content=md_text.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="RELATORIO_TECNICO_AUDITORIA_DEPLOYDOCK.md"'
        },
    )


@app.get("/api/report/document-html", response_class=HTMLResponse)
async def view_or_print_formal_document(request: Request):
    """Abre o Laudo Técnico Formal formatado para Impressão / Exportação PDF."""
    report = LATEST_REPORT or await execute_complete_audit(dict(request.headers))
    html_doc = generate_printable_document_html(report)
    return HTMLResponse(content=html_doc)
