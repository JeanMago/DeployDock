#!/usr/bin/env python3
"""
Benchmark de deploy: duração do pipeline e janela de indisponibilidade (downtime).

Para cada repetição o script:
  1. dispara um deploy de um projeto via API (POST /api/v1/projects/{id}/deploy);
  2. em paralelo, sonda a URL pública da aplicação a cada `--interval` ms;
  3. mede (a) o tempo até o deployment atingir um estado final e
     (b) o maior intervalo contínuo de sondas falhas (downtime observado).

Ao final reporta média, desvio-padrão amostral, mediana, mínimo, máximo e IC 95 %
(t de Student) e grava um CSV com os dados brutos para análise no TCC.

Uso:
  python scripts/bench_deploy_downtime.py \
      --api http://localhost:8000 --user admin --password '***' \
      --project-id <UUID> --url http://meusite.localhost --runs 10 --out resultados.csv

Somente biblioteca padrão (reprodutível em qualquer máquina com Python 3.9+).
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import threading
import time
import urllib.error
import urllib.request

FINAL_STATES = {"healthy", "failed", "rolled_back"}

# t crítico bilateral 95 % (graus de liberdade 1..30); acima disso usa-se 1.96
T_95 = [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228, 2.201, 2.179, 2.160,
        2.145, 2.131, 2.120, 2.110, 2.101, 2.093, 2.086, 2.080, 2.074, 2.069, 2.064, 2.060, 2.056,
        2.052, 2.048, 2.045, 2.042]


def http_json(method: str, url: str, token: str | None = None, body: dict | None = None, timeout: float = 15.0):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


def probe_ok(url: str, timeout: float) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except urllib.error.HTTPError as exc:
        return exc.code < 500
    except Exception:
        return False


class Prober(threading.Thread):
    """Sonda a URL continuamente e acumula o maior intervalo seguido de falhas."""

    def __init__(self, url: str, interval_s: float, timeout_s: float):
        super().__init__(daemon=True)
        self.url, self.interval_s, self.timeout_s = url, interval_s, timeout_s
        self.stop_event = threading.Event()
        self.samples: list[tuple[float, bool]] = []

    def run(self) -> None:
        while not self.stop_event.is_set():
            t0 = time.monotonic()
            self.samples.append((t0, probe_ok(self.url, self.timeout_s)))
            self.stop_event.wait(max(0.0, self.interval_s - (time.monotonic() - t0)))

    def downtime_seconds(self) -> float:
        longest, start = 0.0, None
        for ts, ok in self.samples:
            if not ok and start is None:
                start = ts
            elif ok and start is not None:
                longest = max(longest, ts - start)
                start = None
        if start is not None and self.samples:
            longest = max(longest, self.samples[-1][0] - start)
        return round(longest, 3)

    def availability(self) -> float:
        return 100.0 * sum(ok for _, ok in self.samples) / len(self.samples) if self.samples else 0.0


def summarize(values: list[float]) -> dict:
    n = len(values)
    mean = statistics.fmean(values)
    sd = statistics.stdev(values) if n > 1 else 0.0
    t = T_95[n - 2] if 1 < n <= 31 else 1.96
    half = t * sd / (n ** 0.5) if n > 1 else 0.0
    return {"n": n, "media": mean, "desvio_padrao": sd, "mediana": statistics.median(values),
            "min": min(values), "max": max(values), "ic95_inf": mean - half, "ic95_sup": mean + half}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", required=True, help="URL base do backend, ex.: http://localhost:8000")
    ap.add_argument("--user", required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument("--project-id", required=True)
    ap.add_argument("--url", required=True, help="URL pública da aplicação sondada durante o deploy")
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--interval", type=int, default=100, help="intervalo entre sondas (ms)")
    ap.add_argument("--probe-timeout", type=float, default=1.0)
    ap.add_argument("--deploy-timeout", type=int, default=600)
    ap.add_argument("--settle", type=int, default=5, help="segundos de espera entre repetições")
    ap.add_argument("--out", default="bench_deploy_resultados.csv")
    args = ap.parse_args()

    api = args.api.rstrip("/")
    token = http_json("POST", f"{api}/api/v1/auth/login", body={"username": args.user, "password": args.password})["access_token"]

    rows = []
    for i in range(1, args.runs + 1):
        prober = Prober(args.url, args.interval / 1000, args.probe_timeout)
        prober.start()
        time.sleep(1.0)  # linha de base antes do deploy
        t0 = time.monotonic()
        http_json("POST", f"{api}/api/v1/projects/{args.project_id}/deploy", token=token)
        final = "timeout"
        while time.monotonic() - t0 < args.deploy_timeout:
            time.sleep(1.0)
            deployments = http_json("GET", f"{api}/api/v1/deployments?project_id={args.project_id}", token=token) or []
            latest = deployments[0] if isinstance(deployments, list) and deployments else None
            if latest and latest.get("status") in FINAL_STATES:
                final = latest["status"]
                break
        duration = time.monotonic() - t0
        time.sleep(1.0)
        prober.stop_event.set()
        prober.join()
        row = {"run": i, "status": final, "deploy_s": round(duration, 2),
               "downtime_s": prober.downtime_seconds(), "disponibilidade_pct": round(prober.availability(), 3)}
        rows.append(row)
        print(row, flush=True)
        time.sleep(args.settle)

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    ok_rows = [r for r in rows if r["status"] == "healthy"]
    print(f"\nExecuções bem-sucedidas: {len(ok_rows)}/{len(rows)}  (dados brutos em {args.out})")
    if ok_rows:
        for key in ("deploy_s", "downtime_s"):
            print(key, {k: round(v, 3) for k, v in summarize([r[key] for r in ok_rows]).items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
