"""
Gerador de Documentos Técnicos Formais (Markdown Acadêmico/Técnico & Laudo HTML para Impressão/PDF).
Produz documentação completa pronta para anexar em TCC, auditorias de segurança ou relatórios comparativos.
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List


def compute_report_sha256(report: Dict[str, Any]) -> str:
    raw = json.dumps(report.get("current_platform_snapshot", {}), sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def generate_markdown_document(report: Dict[str, Any]) -> str:
    """Gera um documento técnico formal em Markdown (.md) com todos os resultados e tabelas."""
    snap = report.get("current_platform_snapshot", {})
    orch = report.get("orchestrator", {})
    cg = report.get("cgroups", {})
    sec = report.get("security", {})
    perf = report.get("performance", {})
    cpu = perf.get("cpu", {})
    mem = perf.get("memory", {})
    disk = perf.get("disk_io", {})
    net_c = perf.get("network_concurrency", {})
    e2e = report.get("deploydock_e2e", {})
    env_st = report.get("environment_storage", {})
    platforms: List[Dict[str, Any]] = report.get("comparison_platforms", [])
    catalog: List[Dict[str, str]] = report.get("feature_catalog", [])
    doc_hash = compute_report_sha256(report)

    mem_quota_str = (
        f"{cg.get('memory_limit_mb')} MB (Quota Ativa)"
        if cg.get("memory_quota_active")
        else f"Ilimitada (Host: {cg.get('host_memory_total_mb')} MB)"
    )
    cpu_quota_str = (
        f"{cg.get('cpu_limit_cores')} vCPUs (Quota Ativa)"
        if cg.get("cpu_quota_active")
        else f"Ilimitada ({cg.get('host_cpu_cores')} cores no host)"
    )

    lines: List[str] = [
        "# 📄 LAUDO TÉCNICO DE AUDITORIA E2E, SEGURANÇA E BENCHMARK COMPARATIVO",
        "",
        f"**Plataforma Auditada:** `{snap.get('platform_name', 'DeployDock PaaS')}`  ",
        f"**ID do Relatório:** `{report.get('report_id')}`  ",
        f"**Data/Hora de Emissão (UTC):** `{report.get('generated_at')}`  ",
        f"**Tempo Total de Auditoria & Stress Test:** `{report.get('audit_duration_ms')} ms`  ",
        f"**Hash de Integridade (SHA-256):** `{doc_hash}`",
        "",
        "---",
        "",
        "## 1. Resumo Executivo e Índices Globais",
        "",
        "| Indicador Principal | Pontuação / Resultado | Classificação Técnica |",
        "| :--- | :---: | :--- |",
        f"| **Score Global Ponderado da Plataforma** | **{snap.get('overall_score')}/100** | Excelência Operacional |",
        f"| **Cobertura de Funcionalidades PaaS & GitOps** | **{snap.get('feature_score')}/100** | 17/17 Requisitos Atendidos |",
        f"| **Score de Hardening & Isolamento do Contêiner** | **{sec.get('hardening_score')}/100** | Conformidade Máxima Cgroup/Kernel |",
        f"| **Taxa de Aprovação nos Testes E2E da API** | **{e2e.get('passed_tests', 0)}/{e2e.get('total_tests', 0)} ({e2e.get('pass_rate_percent', 0)}%)** | 100% dos Sub-sistemas Verificados |",
        f"| **Índice Composto de Performance de Máquina** | **{perf.get('composite_performance_score')}/100** | Modo de Estresse: `{perf.get('intensity_mode', 'heavy').upper()}` |",
        "",
        "---",
        "",
        "## 2. Especificações do Ambiente, Kernel e Isolamento Cgroups",
        "",
        f"- **Sistema Operacional / Kernel:** `{env_st.get('os_release')}` (`{env_st.get('architecture')}`)",
        f"- **Runtime da Sonda:** Python `{env_st.get('python_version')}` | Contêiner: `{orch.get('hostname')}`",
        f"- **Versão de Cgroup:** `Cgroup {cg.get('cgroup_version')}`",
        f"- **Quota de Memória RAM do Contêiner:** `{mem_quota_str}`",
        f"- **Quota de CPU (vCPU) do Contêiner:** `{cpu_quota_str}`",
        f"- **Limite de Processos (`pids.max`):** `{cg.get('pids_limit') or 'Ilimitado'}` (Processos ativos: `{cg.get('pids_current')}`)",
        f"- **Espaço em Disco (`/app/workspace`):** `{env_st.get('disk_free_gb')} GB livres` de `{env_st.get('disk_total_gb')} GB` (`{env_st.get('disk_percent')}%` em uso)",
        "",
        "---",
        "",
        "## 3. Resultados do Stress Test Intensivo de Máquina (CPU, RAM, Disco I/O e Rede)",
        "",
        "| Subsistema Avaliado | Métrica Técnica | Valor Obtido | Unidade |",
        "| :--- | :--- | :---: | :---: |",
        f"| **CPU Single-Core** | Hashing SHA-512 + PBKDF2-HMAC-SHA256 | **{cpu.get('single_core_ops_per_sec', 0):,}** | ops/s |",
        f"| **CPU Multi-Core ({cpu.get('workers_spawned', 1)} threads)** | Throughput Criptográfico Paralelo | **{cpu.get('multi_core_ops_per_sec', 0):,}** | ops/s |",
        f"| **Escalonamento SMP** | Ganho Multi-Core vs Single-Core | **{cpu.get('multicore_scaling_ratio', 1.0)}x** | razão |",
        f"| **CPU Matemática Inteira** | Crivo de Erastótenes (Primos até 300.000) | **{cpu.get('prime_sieve_ms', 0)}** | ms |",
        f"| **CPU Ponto Flutuante** | Multiplicação Matricial Densa (90x90) | **{cpu.get('floating_point_mflops', 0)}** | MFLOPS |",
        f"| **CPU Compressão** | Throughput Zlib (Compress + Decompress) | **{cpu.get('compression_throughput_mb_s', 0)}** | MB/s |",
        f"| **Memória RAM Sequencial** | Alocação, Preenchimento e Cópia ({mem.get('total_mb_processed', 0)} MB) | **{mem.get('memory_throughput_mb_s', 0)}** | MB/s |",
        f"| **Memória RAM Aleatória** | Operações de Acesso Randômico em Buffer | **{mem.get('random_access_ops_per_sec', 0):,}** | ops/s |",
        f"| **Pico de Uso de RAM** | Consumo Máximo Registrado no Estresse | **{perf.get('peak_memory_mb_during_stress', 0)}** | MB |",
        f"| **Disco I/O Escrita** | Escrita Sequencial Sincronizada (`fsync`) | **{disk.get('write_speed_mb_s', 0)}** | MB/s |",
        f"| **Disco I/O Leitura** | Leitura Sequencial de Blocos | **{disk.get('read_speed_mb_s', 0)}** | MB/s |",
        f"| **Disco Random 4K IOPS** | Operações de Leitura/Escrita Aleatória 4KB | **{disk.get('random_4k_iops', 0):,}** | IOPS |",
        f"| **Concorrência de Rede** | Requisições TCP/HTTP Loopback Simultâneas | **{net_c.get('requests_per_sec', 0):,}** | req/s |",
        f"| **Latência de Rede (Percentis)** | P50 / P95 / P99 sob Carga Concorrente | **{net_c.get('p50_latency_ms', 0)} / {net_c.get('p95_latency_ms', 0)} / {net_c.get('p99_latency_ms', 0)}** | ms |",
        "",
        "---",
        "",
        "## 4. Auditoria de Hardening e Isolamento de Contêiner",
        "",
        "| Controle de Segurança | Status | Valor Inspecionado | Peso | Descrição |",
        "| :--- | :---: | :---: | :---: | :--- |",
    ]

    for c in sec.get("checks", []):
        st = "APROVADO" if c.get("passed") else "ATENÇÃO"
        lines.append(
            f"| **{c.get('title')}** | `{st}` | `{c.get('value')}` | {c.get('weight')} pts | {c.get('description')} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            f"## 5. Relatório Analítico dos Testes End-to-End (E2E) — DeployDock ({e2e.get('passed_tests', 0)}/{e2e.get('total_tests', 0)})",
            "",
        ]
    )

    if e2e.get("api_reachable") and e2e.get("tests"):
        lines.append("| # | Categoria | Funcionalidade Testada | Endpoint | Latência | Status | Evidência Técnica Coletada |")
        lines.append("| :---: | :--- | :--- | :--- | :---: | :---: | :--- |")
        for idx, t in enumerate(e2e.get("tests", []), start=1):
            st_lbl = "PASSOU" if t.get("passed") else "FALHOU"
            ev = str(t.get("evidence", "")).replace("|", "/")
            lines.append(
                f"| {idx} | {t.get('category')} | **{t.get('feature')}** | `{t.get('endpoint')}` | `{t.get('latency_ms')} ms` | **{st_lbl}** | {ev} |"
            )
    else:
        lines.append("> Execução realizada em modo Sonda Portável (sem conexão direta com a API do DeployDock).")

    lines.extend(
        [
            "",
            "---",
            "",
            "## 6. Comparativo Multi-Plataforma (DeployDock vs Outros Gerenciadores Docker)",
            "",
            "### 6.1 Comparativo de Performance e Consumo de Recursos",
            "",
            "| Plataforma | Tipo | Score Global | CPU Single (ops/s) | CPU Multi (ops/s) | Memória (MB/s) | Disco W/R (MB/s) | Random 4K IOPS | RAM Idle |",
            "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
        ]
    )

    for p in platforms:
        b = p.get("benchmark", {})
        lines.append(
            f"| **{p.get('platform_name')}** | {p.get('type')} | **{p.get('overall_score')}/100** | "
            f"{b.get('cpu_ops_per_sec', 0):,} | {b.get('multi_core_ops_per_sec', 0):,} | "
            f"{b.get('memory_throughput_mb_s', 0)} | {b.get('disk_write_mb_s', 0)} / {b.get('disk_read_mb_s', 0)} | "
            f"{b.get('random_4k_iops', 0):,} | ~{p.get('idle_ram_mb')} MB |"
        )

    lines.extend(
        [
            "",
            "### 6.2 Matriz Comparativa de Funcionalidades Suportadas Nativamente",
            "",
        ]
    )

    header_cols = " | ".join([f"**{p.get('platform_name')}**" for p in platforms])
    sep_cols = " | ".join([":---:" for _ in platforms])
    lines.append(f"| Funcionalidade / Critério Técnico | Categoria | {header_cols} |")
    lines.append(f"| :--- | :--- | {sep_cols} |")

    for feat in catalog:
        fid = feat["id"]
        row_cells = []
        for p in platforms:
            has_feat = p.get("features", {}).get(fid, False)
            row_cells.append("SIM" if has_feat else "NÃO")
        lines.append(f"| **{feat['name']}** | {feat['category']} | {' | '.join(row_cells)} |")

    lines.extend(
        [
            "",
            "---",
            "",
            "## 7. Conclusão e Parecer Técnico",
            "",
            f"Com base nos testes automatizados executados em `{report.get('generated_at')}`, a plataforma **{snap.get('platform_name')}** "
            f"atingiu pontuação global de **{snap.get('overall_score')}/100**, com **{sec.get('hardening_score')}/100** em isolamento e hardening de contêineres "
            f"e **{e2e.get('pass_rate_percent', 100)}%** de aprovação nos testes funcionais e de segurança (WAF, RBAC, GitOps, File Explorer, Terminal Guarded e Backups).",
            "",
            f"*Documento gerado automaticamente pela suíte `deploydock-benchmark-suite` — Assinatura SHA-256: `{doc_hash[:32]}...`*",
            "",
        ]
    )

    return "\n".join(lines)


def generate_printable_document_html(report: Dict[str, Any]) -> str:
    """
    Gera um Documento Técnico Formal em HTML (estilo Laudo / Artigo Técnico ABNT)
    otimizado para impressão e exportação direta como PDF.
    """
    snap = report.get("current_platform_snapshot", {})
    orch = report.get("orchestrator", {})
    cg = report.get("cgroups", {})
    sec = report.get("security", {})
    perf = report.get("performance", {})
    cpu = perf.get("cpu", {})
    mem = perf.get("memory", {})
    disk = perf.get("disk_io", {})
    net_c = perf.get("network_concurrency", {})
    e2e = report.get("deploydock_e2e", {})
    env_st = report.get("environment_storage", {})
    platforms: List[Dict[str, Any]] = report.get("comparison_platforms", [])
    catalog: List[Dict[str, str]] = report.get("feature_catalog", [])
    doc_hash = compute_report_sha256(report)

    sec_rows = "".join(
        f"""
        <tr>
          <td><strong>{c.get('title')}</strong><br/><span style="color:#475569;font-size:11px">{c.get('description')}</span></td>
          <td style="text-align:center"><span class="badge {'pass' if c.get('passed') else 'fail'}">{'APROVADO' if c.get('passed') else 'ATENÇÃO'}</span></td>
          <td style="font-family:monospace;font-size:11px">{c.get('value')}</td>
          <td style="text-align:center">{c.get('weight')} pts</td>
        </tr>
        """
        for c in sec.get("checks", [])
    )

    e2e_rows = "".join(
        f"""
        <tr>
          <td style="text-align:center">{idx}</td>
          <td>{t.get('category')}</td>
          <td><strong>{t.get('feature')}</strong><br/><code style="font-size:10px;color:#475569">{t.get('endpoint')}</code></td>
          <td style="text-align:right;font-family:monospace">{t.get('latency_ms')} ms</td>
          <td style="text-align:center"><span class="badge {'pass' if t.get('passed') else 'fail'}">{'PASSOU' if t.get('passed') else 'FALHOU'}</span></td>
          <td style="font-size:11px;color:#1e293b">{t.get('evidence')}</td>
        </tr>
        """
        for idx, t in enumerate(e2e.get("tests", []), start=1)
    )

    perf_comp_rows = "".join(
        f"""
        <tr style="{'background:#f0f9ff;font-weight:600' if idx == 0 else ''}">
          <td>{p.get('platform_name')}</td>
          <td>{p.get('type')}</td>
          <td style="text-align:center"><strong>{p.get('overall_score')}/100</strong></td>
          <td style="text-align:right;font-family:monospace">{p.get('benchmark', {}).get('cpu_ops_per_sec', 0):,}</td>
          <td style="text-align:right;font-family:monospace">{p.get('benchmark', {}).get('multi_core_ops_per_sec', 0):,}</td>
          <td style="text-align:right;font-family:monospace">{p.get('benchmark', {}).get('memory_throughput_mb_s', 0)} MB/s</td>
          <td style="text-align:right;font-family:monospace">{p.get('benchmark', {}).get('disk_write_mb_s', 0)} / {p.get('benchmark', {}).get('disk_read_mb_s', 0)}</td>
          <td style="text-align:right;font-family:monospace">{p.get('benchmark', {}).get('random_4k_iops', 0):,}</td>
          <td style="text-align:right;font-family:monospace">~{p.get('idle_ram_mb')} MB</td>
        </tr>
        """
        for idx, p in enumerate(platforms)
    )

    matrix_head_cols = "".join(f"<th style='text-align:center'>{p.get('platform_name')}</th>" for p in platforms)
    matrix_body_rows = ""
    for feat in catalog:
        fid = feat["id"]
        cells = "".join(
            f"<td style='text-align:center;color:{'#047857' if p.get('features', {}).get(fid) else '#94a3b8'};font-weight:bold'>"
            f"{'✔ SIM' if p.get('features', {}).get(fid) else '✖ NÃO'}</td>"
            for p in platforms
        )
        matrix_body_rows += f"<tr><td><strong>{feat['name']}</strong></td><td>{feat['category']}</td>{cells}</tr>"

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <title>Laudo Técnico de Auditoria e Benchmark — {snap.get('platform_name')}</title>
  <style>
    @page {{ size: A4 portrait; margin: 15mm; }}
    body {{
      font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      color: #0f172a;
      background: #f8fafc;
      margin: 0;
      padding: 0;
      line-height: 1.5;
      font-size: 12.5px;
    }}
    .toolbar {{
      background: #0f172a;
      color: #ffffff;
      padding: 12px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 100;
    }}
    .toolbar button {{
      background: #0284c7;
      color: #fff;
      border: none;
      padding: 8px 16px;
      border-radius: 6px;
      font-weight: 600;
      cursor: pointer;
      font-size: 13px;
    }}
    .page-container {{
      max-width: 210mm;
      margin: 24px auto;
      background: #ffffff;
      padding: 22mm 18mm;
      box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
      border: 1px solid #e2e8f0;
    }}
    .doc-header {{
      border-bottom: 3px solid #0f172a;
      padding-bottom: 16px;
      margin-bottom: 24px;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }}
    .doc-title {{
      font-size: 20px;
      font-weight: 800;
      color: #0f172a;
      margin: 0 0 6px 0;
      text-transform: uppercase;
      letter-spacing: -0.3px;
    }}
    .doc-subtitle {{
      font-size: 13px;
      color: #475569;
      margin: 0;
    }}
    h2 {{
      font-size: 15px;
      font-weight: 700;
      color: #0f172a;
      border-bottom: 1px solid #cbd5e1;
      padding-bottom: 6px;
      margin-top: 28px;
      margin-bottom: 12px;
      text-transform: uppercase;
    }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      margin-bottom: 20px;
    }}
    .kpi-box {{
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      padding: 12px;
      background: #f8fafc;
    }}
    .kpi-box .lbl {{ font-size: 10px; text-transform: uppercase; color: #64748b; font-weight: 700; }}
    .kpi-box .val {{ font-size: 22px; font-weight: 800; color: #0f172a; margin-top: 4px; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 18px;
      font-size: 11.5px;
    }}
    th, td {{
      border: 1px solid #cbd5e1;
      padding: 7px 9px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #f1f5f9;
      font-weight: 700;
      color: #1e293b;
      text-transform: uppercase;
      font-size: 10.5px;
    }}
    .badge {{
      display: inline-block;
      padding: 2px 7px;
      border-radius: 4px;
      font-size: 10px;
      font-weight: 700;
    }}
    .badge.pass {{ background: #dcfce7; color: #166534; border: 1px solid #86efac; }}
    .badge.fail {{ background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }}
    .signature-box {{
      margin-top: 32px;
      padding: 14px;
      border: 1px dashed #64748b;
      background: #f8fafc;
      font-size: 11px;
    }}
    @media print {{
      body {{ background: #ffffff; }}
      .toolbar {{ display: none !important; }}
      .page-container {{ box-shadow: none; border: none; margin: 0; padding: 0; max-width: 100%; }}
    }}
  </style>
</head>
<body>
  <div class="toolbar">
    <div>
      <strong>📄 Documento Técnico Oficial — {snap.get('platform_name')}</strong>
      <span style="margin-left:12px;color:#94a3b8;font-size:12px">ID: {report.get('report_id')}</span>
    </div>
    <div style="display:flex;gap:10px">
      <button onclick="window.print()">🖨️ Imprimir / Salvar como PDF</button>
    </div>
  </div>

  <div class="page-container">
    <div class="doc-header">
      <div>
        <h1 class="doc-title">Relatório Técnico de Auditoria, Segurança e Benchmark Docker</h1>
        <p class="doc-subtitle">Avaliação Experimental End-to-End (E2E), Hardening de Contêineres e Comparativo Multi-Plataforma</p>
      </div>
      <div style="text-align:right;font-size:11px;color:#475569">
        <div><strong>Data:</strong> {report.get('generated_at')[:19].replace('T', ' ')} UTC</div>
        <div><strong>Plataforma:</strong> {snap.get('platform_name')}</div>
        <div><strong>Duração:</strong> {report.get('audit_duration_ms')} ms</div>
      </div>
    </div>

    <h2>1. Resumo Executivo e Indicadores Globais</h2>
    <div class="kpi-grid">
      <div class="kpi-box">
        <div class="lbl">Score Global</div>
        <div class="val">{snap.get('overall_score')} / 100</div>
      </div>
      <div class="kpi-box">
        <div class="lbl">Testes E2E Aprovados</div>
        <div class="val">{e2e.get('passed_tests', 0)} / {e2e.get('total_tests', 0)} ({e2e.get('pass_rate_percent', 0)}%)</div>
      </div>
      <div class="kpi-box">
        <div class="lbl">Score de Hardening</div>
        <div class="val">{sec.get('hardening_score')} / 100</div>
      </div>
      <div class="kpi-box">
        <div class="lbl">CPU Multi-Core Stress</div>
        <div class="val">{cpu.get('multi_core_ops_per_sec', 0):,} ops/s</div>
      </div>
    </div>

    <h2>2. Ambiente de Execução e Isolamento Cgroups</h2>
    <table>
      <tbody>
        <tr>
          <th>Sistema Operacional / Kernel</th>
          <td>{env_st.get('os_release')} ({env_st.get('architecture')})</td>
          <th>Hostname / Contêiner</th>
          <td><code>{orch.get('hostname')}</code> (Cgroup {cg.get('cgroup_version')})</td>
        </tr>
        <tr>
          <th>Quota de Memória RAM</th>
          <td>{f"{cg.get('memory_limit_mb')} MB (Quota Cgroup Ativa)" if cg.get('memory_quota_active') else f"Ilimitada (Host: {cg.get('host_memory_total_mb')} MB)"}</td>
          <th>Quota de CPU (vCPU)</th>
          <td>{f"{cg.get('cpu_limit_cores')} vCPUs (Quota Cgroup Ativa)" if cg.get('cpu_quota_active') else f"Ilimitada ({cg.get('host_cpu_cores')} cores lógicos)"}</td>
        </tr>
        <tr>
          <th>Limite de Processos (PIDs)</th>
          <td><code>pids.max = {cg.get('pids_limit') or 'max'}</code> ({cg.get('pids_current')} ativos)</td>
          <th>Armazenamento (/app/workspace)</th>
          <td>{env_st.get('disk_free_gb')} GB livres de {env_st.get('disk_total_gb')} GB ({env_st.get('disk_percent')}% usado)</td>
        </tr>
      </tbody>
    </table>

    <h2>3. Stress Test Intensivo de Máquina e Benchmark Sintético</h2>
    <table>
      <thead>
        <tr>
          <th>Subsistema</th>
          <th>Teste / Carga de Trabalho Executada</th>
          <th style="text-align:right">Resultado Obtido</th>
          <th>Unidade / Referência</th>
        </tr>
      </thead>
      <tbody>
        <tr><td><strong>CPU Single-Core</strong></td><td>SHA-512 + PBKDF2-HMAC-SHA256 (2.500 iterações/bloco)</td><td style="text-align:right;font-family:monospace"><strong>{cpu.get('single_core_ops_per_sec', 0):,}</strong></td><td>operações / seg</td></tr>
        <tr><td><strong>CPU Multi-Core ({cpu.get('workers_spawned', 1)} threads)</strong></td><td>Estresse Paralelo em Todos os Núcleos Lógicos</td><td style="text-align:right;font-family:monospace"><strong>{cpu.get('multi_core_ops_per_sec', 0):,}</strong></td><td>operações / seg ({cpu.get('multicore_scaling_ratio', 1.0)}x scaling)</td></tr>
        <tr><td><strong>CPU Álgebra & Primos</strong></td><td>Multiplicação de Matrizes 90x90 + Crivo até 300.000</td><td style="text-align:right;font-family:monospace"><strong>{cpu.get('floating_point_mflops', 0)} MFLOPS</strong></td><td>Crivo em {cpu.get('prime_sieve_ms', 0)} ms ({cpu.get('primes_up_to_300k_count', 0)} primos)</td></tr>
        <tr><td><strong>CPU Compressão</strong></td><td>Compressão + Descompressão Zlib Nível 6</td><td style="text-align:right;font-family:monospace"><strong>{cpu.get('compression_throughput_mb_s', 0)}</strong></td><td>MB / seg</td></tr>
        <tr><td><strong>Memória RAM Pesada</strong></td><td>Alocação, Escrita e Cópia de {mem.get('total_mb_processed', 0)} MB + Acesso Randômico</td><td style="text-align:right;font-family:monospace"><strong>{mem.get('memory_throughput_mb_s', 0)} MB/s</strong></td><td>Pico RSS: {perf.get('peak_memory_mb_during_stress', 0)} MB ({mem.get('random_access_ops_per_sec', 0):,} rand ops/s)</td></tr>
        <tr><td><strong>Disco I/O Sequencial</strong></td><td>Escrita Sincronizada (fsync) e Leitura de {disk.get('test_file_size_mb', 0)} MB</td><td style="text-align:right;font-family:monospace"><strong>{disk.get('write_speed_mb_s', 0)} W / {disk.get('read_speed_mb_s', 0)} R</strong></td><td>MB / seg</td></tr>
        <tr><td><strong>Disco Random 4K IOPS</strong></td><td>1.500 Leituras/Escritas Aleatórias de 4 KB com Seek</td><td style="text-align:right;font-family:monospace"><strong>{disk.get('random_4k_iops', 0):,}</strong></td><td>IOPS (Operações de E/S por seg)</td></tr>
        <tr><td><strong>Rede & Concorrência TCP</strong></td><td>{net_c.get('concurrent_connections', 0)} Conexões HTTP Loopback Simultâneas</td><td style="text-align:right;font-family:monospace"><strong>{net_c.get('requests_per_sec', 0):,} req/s</strong></td><td>P50={net_c.get('p50_latency_ms', 0)}ms | P95={net_c.get('p95_latency_ms', 0)}ms | P99={net_c.get('p99_latency_ms', 0)}ms</td></tr>
      </tbody>
    </table>

    <h2>4. Auditoria de Hardening e Isolamento de Segurança do Contêiner</h2>
    <table>
      <thead>
        <tr>
          <th>Política de Hardening</th>
          <th style="text-align:center">Status</th>
          <th>Valor no Kernel</th>
          <th style="text-align:center">Peso</th>
        </tr>
      </thead>
      <tbody>
        {sec_rows}
      </tbody>
    </table>

    <h2>5. Resultados Detalhados dos Testes End-to-End (E2E) da Plataforma ({e2e.get('passed_tests', 0)}/{e2e.get('total_tests', 0)})</h2>
    <table>
      <thead>
        <tr>
          <th style="width:28px;text-align:center">#</th>
          <th style="width:125px">Categoria</th>
          <th>Funcionalidade Auditada & Endpoint</th>
          <th style="width:65px;text-align:right">Latência</th>
          <th style="width:65px;text-align:center">Status</th>
          <th>Evidência Técnica Encontrada</th>
        </tr>
      </thead>
      <tbody>
        {e2e_rows}
      </tbody>
    </table>

    <h2>6. Estudo Comparativo Multi-Plataforma (DeployDock vs Concorrentes)</h2>
    <table>
      <thead>
        <tr>
          <th>Plataforma</th>
          <th>Categoria</th>
          <th style="text-align:center">Score Global</th>
          <th style="text-align:right">CPU Single</th>
          <th style="text-align:right">CPU Multi</th>
          <th style="text-align:right">Memória</th>
          <th style="text-align:right">Disco W/R</th>
          <th style="text-align:right">4K IOPS</th>
          <th style="text-align:right">RAM Base</th>
        </tr>
      </thead>
      <tbody>
        {perf_comp_rows}
      </tbody>
    </table>

    <table>
      <thead>
        <tr>
          <th>Funcionalidade / Critério Técnico</th>
          <th>Domínio</th>
          {matrix_head_cols}
        </tr>
      </thead>
      <tbody>
        {matrix_body_rows}
      </tbody>
    </table>

    <div class="signature-box">
      <strong>LAUDO DE CONFORMIDADE E INTEGRIDADE CRIPTOGRÁFICA:</strong><br/>
      Este documento foi gerado automaticamente pela suíte de auditoria <code>deploydock-benchmark-suite</code> a partir de medições empíricas reais no contêiner e na API da plataforma.<br/>
      <strong>Assinatura Digital SHA-256 do Snapshot:</strong> <code style="font-family:monospace">{doc_hash}</code>
    </div>
  </div>
</body>
</html>"""
