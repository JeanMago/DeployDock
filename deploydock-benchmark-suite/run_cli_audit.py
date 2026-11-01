"""
Executor CLI de Auditoria E2E (45 Testes), Stress Test de Máquina & Gerador de Relatório Interativo + Documento Técnico.
Executa toda a bateria de testes contra o DeployDock (ou qualquer outro software de controle Docker),
salva o snapshot JSON, o Relatório HTML Interativo, o Documento Técnico Markdown (.md)
e o Laudo Técnico HTML formatado para impressão/PDF.
"""

import argparse
import asyncio
import json
import os
import sys

from app.main import REPORTS_DIR, STATIC_INDEX, execute_complete_audit


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Executa a auditoria completa v2.0 do DeployDock Benchmark Suite e gera relatórios e documentos."
    )
    parser.add_argument(
        "--platform",
        default=None,
        help="Nome manual da plataforma sendo avaliada (ex: 'DeployDock PaaS', 'Portainer CE', 'Coolify v4')",
    )
    parser.add_argument(
        "--api-url",
        default=None,
        help="URL da API do DeployDock (ex: http://localhost:8000)",
    )
    parser.add_argument(
        "--target-url",
        default=None,
        help="URL universal do serviço/plataforma alvo para testar WAF, headers e latência (Portainer, Coolify, CapRover, DeployDock, etc.)",
    )
    parser.add_argument(
        "--export-snapshot",
        default=None,
        help="Caminho opcional para salvar o snapshot JSON desta plataforma para comparação cruzada",
    )
    parser.add_argument("--user", default="admin", help="Usuário da API DeployDock")
    parser.add_argument("--password", default="admin123", help="Senha da API DeployDock")
    parser.add_argument(
        "--intensity",
        default="heavy",
        choices=["standard", "heavy", "extreme"],
        help="Intensidade do Stress Test de Máquina (standard | heavy | extreme)",
    )
    args = parser.parse_args()

    print("=" * 88)
    print(" 🐳 DEPLOYDOCK BENCHMARK & MULTI-PLATFORM DOCKER AUDIT SUITE v2.0 (STRESS + E2E)")
    print("=" * 88)

    report = await execute_complete_audit(
        platform_label=args.platform,
        deploydock_api_url=args.api_url,
        target_url=args.target_url,
        username=args.user,
        password=args.password,
        intensity=args.intensity,
    )

    if args.export_snapshot:
        os.makedirs(os.path.dirname(os.path.abspath(args.export_snapshot)), exist_ok=True)
        with open(args.export_snapshot, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Snapshot exportado para comparação: {args.export_snapshot}")

    snap = report["current_platform_snapshot"]
    e2e = report["deploydock_e2e"]
    sec = report["security"]
    perf = report["performance"]
    cpu = perf["cpu"]
    mem = perf["memory"]
    disk = perf["disk_io"]
    net_c = perf.get("network_concurrency", {})

    print(f"\n📌 Plataforma Avaliada    : {snap['platform_name']}")
    print(f"🏆 Score Global           : {snap['overall_score']}/100 (Funcionalidades: {snap['feature_score']}%)")
    print(f"🛡️  Score Hardening        : {sec['hardening_score']}/100")
    print(f"🔥 Modo de Stress Test    : {perf.get('intensity_mode', 'heavy').upper()}")
    print(f"⚡ CPU Single-Core        : {cpu['single_core_ops_per_sec']:,} ops/s")
    print(f"🚀 CPU Multi-Core ({cpu['workers_spawned']} thr) : {cpu['multi_core_ops_per_sec']:,} ops/s ({cpu['multicore_scaling_ratio']}x scaling)")
    print(f"🧮 Ponto Flutuante & Math : {cpu['floating_point_mflops']} MFLOPS | Crivo 300k primos em {cpu['prime_sieve_ms']} ms")
    print(f"📦 Compressão Zlib        : {cpu['compression_throughput_mb_s']} MB/s")
    print(f"🧠 Memória RAM Stress     : {mem['memory_throughput_mb_s']} MB/s ({mem['total_mb_processed']} MB processados | Pico RSS: {perf['peak_memory_mb_during_stress']} MB)")
    print(
        f"💾 Disco I/O & 4K IOPS    : {disk['write_speed_mb_s']} MB/s W | "
        f"{disk['read_speed_mb_s']} MB/s R | {disk['random_4k_iops']:,} IOPS (4KB random)"
    )
    print(
        f"🌐 Concorrência de Rede   : {net_c.get('requests_per_sec', 0):,} req/s "
        f"(P50={net_c.get('p50_latency_ms')}ms | P95={net_c.get('p95_latency_ms')}ms | P99={net_c.get('p99_latency_ms')}ms)"
    )

    if e2e.get("api_reachable"):
        print(
            f"\n🧪 TESTES E2E DEPLOYDOCK ({e2e['passed_tests']}/{e2e['total_tests']} aprovados — {e2e['pass_rate_percent']}%):"
        )
        print("-" * 88)
        for idx, t in enumerate(e2e.get("tests", []), start=1):
            icon = "✅" if t["passed"] else "❌"
            print(f" {icon} #{idx:02d} [{t['category']}] {t['feature']} ({t['latency_ms']} ms)")
            print(f"       ↳ {t['evidence']}")
    else:
        print(f"\nℹ️  Modo Sonda Portável: {e2e.get('message')}")

    # Gerar Relatório HTML Interativo Standalone (com dados embutidos)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    json_out = os.path.join(REPORTS_DIR, "latest_report.json")
    html_out = os.path.join(REPORTS_DIR, "relatorio_interativo_deploydock.html")
    md_out = os.path.join(REPORTS_DIR, "RELATORIO_TECNICO_AUDITORIA_DEPLOYDOCK.md")
    print_html_out = os.path.join(REPORTS_DIR, "DOCUMENTO_LAUDO_TECNICO_IMPRESSAO.html")

    if os.path.exists(STATIC_INDEX):
        with open(STATIC_INDEX, "r", encoding="utf-8") as f:
            html_template = f.read()

        embedded_js = f"window.__EMBEDDED_REPORT__ = {json.dumps(report, ensure_ascii=False)};"
        html_standalone = html_template.replace(
            "window.__EMBEDDED_REPORT__ = null;",
            embedded_js,
        )
        with open(html_out, "w", encoding="utf-8") as f:
            f.write(html_standalone)

    print("\n" + "=" * 88)
    print(f"📄 1. Snapshot JSON Comparativo        : {json_out}")
    print(f"📊 2. Relatório HTML Interativo        : {html_out}")
    print(f"📝 3. Documento Técnico Markdown (.md) : {md_out}")
    print(f"🖨️  4. Laudo Técnico Impressão / PDF    : {print_html_out}")
    print("=" * 88)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
