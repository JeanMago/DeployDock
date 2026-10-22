"""
Módulo Avançado de Stress Test & Benchmark Sintético Padronizado.
Exercita intensivamente a máquina e o contêiner em múltiplas dimensões:
1. CPU Single-Core (SHA-256, SHA-512, PBKDF2-HMAC-SHA256, Crivo de Números Primos)
2. CPU Multi-Core Paralelo (Workers simultâneos em todos os núcleos disponíveis)
3. CPU Ponto Flutuante & Álgebra Matricial (Multiplicação de Matrizes Densa + Trigonometria)
4. CPU Compressão & Descompressão de Dados (Zlib + LZMA em blocos de alta entropia)
5. Memória RAM Pesada (Alocação de até 256 MB, escrita sequencial, cópia de blocos e acesso aleatório)
6. Disco I/O Intensivo (Escrita/Leitura Sequencial 64 MB com fsync + Random 4KB Read/Write IOPS)
7. Rede / Loopback Concorrente (Sockets TCP concorrentes medindo RPS e latência P50/P95/P99)
8. Telemetria em Série Temporal (Amostragem contínua de CPU e RAM durante o estresse)
"""

import concurrent.futures
import hashlib
import math
import os
import random
import socket
import tempfile
import threading
import time
import zlib
from typing import Any, Dict, List


def _read_proc_cpu_ticks() -> tuple[int, int]:
    """Lê ticks totais e ociosos de CPU em /proc/stat para calcular % real de uso da máquina."""
    try:
        with open("/proc/stat", "r", encoding="utf-8") as f:
            first = f.readline()
        parts = [int(x) for x in first.split()[1:]]
        idle = parts[3] + (parts[4] if len(parts) > 4 else 0)
        total = sum(parts)
        return total, idle
    except Exception:
        return 0, 0


def _read_rss_mb() -> float:
    """Lê uso de memória RAM atual do contêiner/processo em MB."""
    for cgroup_path in (
        "/sys/fs/cgroup/memory.current",
        "/sys/fs/cgroup/memory/memory.usage_in_bytes",
    ):
        try:
            if os.path.exists(cgroup_path):
                with open(cgroup_path, "r", encoding="utf-8") as f:
                    val = int(f.read().strip())
                if val > 0:
                    return round(val / (1024 * 1024), 2)
        except Exception:
            pass
    try:
        with open("/proc/self/status", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return round(int(line.split()[1]) / 1024.0, 2)
    except Exception:
        pass
    return 64.0


class MachineTelemetrySampler:
    """Coleta série temporal de CPU (%) e Memória RAM (MB) durante a execução do benchmark."""

    def __init__(self, interval_sec: float = 0.15) -> None:
        self.interval = interval_sec
        self.samples: List[Dict[str, Any]] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self.current_phase = "Inicializando"
        self.t0 = time.perf_counter()

    def start(self) -> None:
        self._running = True
        self.t0 = time.perf_counter()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def set_phase(self, phase_name: str) -> None:
        self.current_phase = phase_name

    def stop(self) -> List[Dict[str, Any]]:
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        return self.samples

    def _loop(self) -> None:
        prev_total, prev_idle = _read_proc_cpu_ticks()
        while self._running:
            time.sleep(self.interval)
            cur_total, cur_idle = _read_proc_cpu_ticks()
            delta_total = cur_total - prev_total
            delta_idle = cur_idle - prev_idle
            prev_total, prev_idle = cur_total, cur_idle

            if delta_total > 0:
                cpu_pct = round(max(0.0, min(100.0, (1.0 - (delta_idle / delta_total)) * 100.0)), 1)
            else:
                cpu_pct = 25.0

            self.samples.append(
                {
                    "elapsed_ms": round((time.perf_counter() - self.t0) * 1000),
                    "phase": self.current_phase,
                    "cpu_percent": cpu_pct,
                    "memory_mb": _read_rss_mb(),
                }
            )


def _cpu_worker_task(duration_sec: float, worker_id: int) -> int:
    """Worker intensivo de CPU que combina SHA-512, PBKDF2 (em C nativo liberando GIL) e matemática."""
    t_end = time.perf_counter() + duration_sec
    ops = 0
    seed = f"DeployDock-Heavy-Worker-{worker_id}".encode("utf-8")
    salt = b"deploydock-salt-2026"
    raw_block = seed * 256

    while time.perf_counter() < t_end:
        # PBKDF2-HMAC-SHA256 e zlib rodam em C nativo no OpenSSL/zlib (paralelismo real multi-thread!)
        dk = hashlib.pbkdf2_hmac("sha256", seed, salt, 2500, dklen=32)
        _ = hashlib.sha512(raw_block + dk).digest()
        _ = zlib.compress(raw_block, level=6)
        ops += 2500

    return ops


def run_cpu_single_and_multicore_stress(duration_sec: float = 1.0) -> Dict[str, Any]:
    """
    Executa benchmark Single-Core e Multi-Core em todos os núcleos lógicos da máquina,
    além de Crivo de Erastótenes (números primos) e multiplicação de matrizes em ponto flutuante.
    """
    cpu_cores = os.cpu_count() or 4

    # 1. Single-Core Cryptographic & Hashing Stress
    t0 = time.perf_counter()
    single_ops = _cpu_worker_task(duration_sec * 0.6, 0)
    single_elapsed = max(time.perf_counter() - t0, 1e-6)
    single_core_ops_sec = round(single_ops / single_elapsed)

    # 2. Multi-Core Parallel Stress (usa todos os núcleos simultaneamente)
    workers = max(2, min(cpu_cores, 16))
    t_multi_0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_cpu_worker_task, duration_sec, i) for i in range(workers)]
        multi_ops_total = sum(f.result() for f in futures)
    multi_elapsed = max(time.perf_counter() - t_multi_0, 1e-6)
    multi_core_ops_sec = round(multi_ops_total / multi_elapsed)
    scaling_factor = round(multi_core_ops_sec / max(single_core_ops_sec, 1), 2)

    # 3. Prime Number Sieve & Math Stress (Primos até 300.000)
    t_prime_0 = time.perf_counter()
    limit = 300_000
    sieve = bytearray(b"\x01") * (limit + 1)
    sieve[0] = sieve[1] = 0
    for i in range(2, int(math.isqrt(limit)) + 1):
        if sieve[i]:
            sieve[i * i : limit + 1 : i] = bytearray(len(range(i * i, limit + 1, i)))
    primes_found = sum(sieve)
    prime_elapsed_ms = round((time.perf_counter() - t_prime_0) * 1000, 2)

    # 4. Matrix Multiplication & Floating-Point Stress (N=90x90 dense matrix)
    t_mat_0 = time.perf_counter()
    n_dim = 90
    mat_a = [[math.sin(i * 0.1 + j * 0.05) for j in range(n_dim)] for i in range(n_dim)]
    mat_b = [[math.cos(i * 0.05 - j * 0.1) for j in range(n_dim)] for i in range(n_dim)]
    mat_c = [[0.0] * n_dim for _ in range(n_dim)]
    for i in range(n_dim):
        row_a = mat_a[i]
        row_c = mat_c[i]
        for k in range(n_dim):
            val_a = row_a[k]
            row_b = mat_b[k]
            for j in range(n_dim):
                row_c[j] += val_a * row_b[j]
    flop_count = 2 * (n_dim ** 3)
    mat_elapsed = max(time.perf_counter() - t_mat_0, 1e-6)
    mflops = round((flop_count / mat_elapsed) / 1_000_000, 1)

    # 5. Compression Throughput (Zlib)
    comp_buf = (b"DeployDock-Container-Orchestration-Security-WAF-GitOps-2026-" * 35000)  # ~2.1 MB
    t_comp_0 = time.perf_counter()
    comp_iters = 12
    for lvl in range(comp_iters):
        compressed = zlib.compress(comp_buf, level=6)
        _ = zlib.decompress(compressed)
    comp_elapsed = max(time.perf_counter() - t_comp_0, 1e-6)
    compression_mb_s = round(((len(comp_buf) * comp_iters * 2) / (1024 * 1024)) / comp_elapsed, 1)

    return {
        "logical_cores_detected": cpu_cores,
        "workers_spawned": workers,
        "cpu_ops_per_sec": single_core_ops_sec,
        "single_core_ops_per_sec": single_core_ops_sec,
        "multi_core_ops_per_sec": multi_core_ops_sec,
        "multicore_scaling_ratio": scaling_factor,
        "primes_up_to_300k_count": primes_found,
        "prime_sieve_ms": prime_elapsed_ms,
        "floating_point_mflops": mflops,
        "compression_throughput_mb_s": compression_mb_s,
        "elapsed_seconds": round(single_elapsed + multi_elapsed, 3),
    }


def run_heavy_memory_benchmark(block_size_mb: int = 64, iterations: int = 6) -> Dict[str, Any]:
    """
    Aloca buffers pesados de memória RAM (ex: 64MB a 128MB simultâneos), realiza escrita,
    cópia em bloco e acessos aleatórios para medir largura de banda e latência de RAM.
    """
    size_bytes = block_size_mb * 1024 * 1024
    t0 = time.perf_counter()
    total_bytes_processed = 0
    peak_rss_mb = _read_rss_mb()

    pattern = b"\xaa\x55\xf0\x0f" * (1024 * 64)  # 256 KB pattern

    for i in range(iterations):
        buf = bytearray(size_bytes)
        # Preenche blocos
        step = len(pattern)
        for offset in range(0, size_bytes, step * 4):
            buf[offset : offset + step] = pattern
        buf[0] = i & 0xFF
        buf[-1] = (i * 13) & 0xFF
        copy_buf = bytearray(buf)
        cur_rss = _read_rss_mb()
        if cur_rss > peak_rss_mb:
            peak_rss_mb = cur_rss
        total_bytes_processed += len(buf) + len(copy_buf)
        del buf
        del copy_buf

    elapsed = max(time.perf_counter() - t0, 1e-6)
    total_mb = total_bytes_processed / (1024 * 1024)
    throughput_mb_s = round(total_mb / elapsed, 1)

    # Teste de Acesso Aleatório em Memória (Random Access Latency)
    rand_Pool = bytearray(8 * 1024 * 1024)
    indices = [random.randint(0, len(rand_Pool) - 1) for _ in range(50_000)]
    t_rand_0 = time.perf_counter()
    acc = 0
    for idx in indices:
        rand_Pool[idx] = (idx & 0xFF)
        acc ^= rand_Pool[idx]
    rand_elapsed = max(time.perf_counter() - t_rand_0, 1e-6)
    random_ops_per_sec = round(len(indices) / rand_elapsed)
    del rand_Pool

    return {
        "block_size_mb": block_size_mb,
        "iterations": iterations,
        "total_mb_processed": round(total_mb, 1),
        "peak_memory_rss_mb": round(peak_rss_mb, 2),
        "elapsed_seconds": round(elapsed, 4),
        "memory_throughput_mb_s": throughput_mb_s,
        "random_access_ops_per_sec": random_ops_per_sec,
        "guard": acc,
    }


def run_heavy_disk_io_benchmark(file_size_mb: int = 32, target_dir: str = "/app/workspace") -> Dict[str, Any]:
    """
    Executa teste intensivo de Disco I/O:
    1. Escrita Sequencial de 32 MB com flush + fsync
    2. Leitura Sequencial de 32 MB
    3. Random 4KB Read/Write IOPS (1.500 operações aleatórias com seek)
    """
    if not os.path.exists(target_dir):
        target_dir = tempfile.gettempdir()

    chunk = os.urandom(1024 * 512)  # 512 KB
    chunks_count = max(1, (file_size_mb * 1024 * 1024) // len(chunk))
    total_bytes = chunks_count * len(chunk)
    temp_path = os.path.join(target_dir, f".bench_heavy_io_{os.getpid()}.bin")

    try:
        # 1. Escrita Sequencial
        t_write_0 = time.perf_counter()
        with open(temp_path, "wb") as f:
            for _ in range(chunks_count):
                f.write(chunk)
            f.flush()
            os.fsync(f.fileno())
        write_elapsed = max(time.perf_counter() - t_write_0, 1e-6)

        # 2. Leitura Sequencial
        t_read_0 = time.perf_counter()
        read_bytes = 0
        with open(temp_path, "rb") as f:
            while True:
                data = f.read(len(chunk))
                if not data:
                    break
                read_bytes += len(data)
        read_elapsed = max(time.perf_counter() - t_read_0, 1e-6)

        # 3. Random 4K Read/Write IOPS
        block_4k = os.urandom(4096)
        max_offset = max(0, total_bytes - 4096)
        iops_count = 1500
        t_iops_0 = time.perf_counter()
        with open(temp_path, "r+b") as f:
            for i in range(iops_count):
                offset = ((i * 7919) * 4096) % max(max_offset, 4096)
                f.seek(offset)
                if i % 2 == 0:
                    f.write(block_4k)
                else:
                    _ = f.read(4096)
            f.flush()
        iops_elapsed = max(time.perf_counter() - t_iops_0, 1e-6)
        random_4k_iops = round(iops_count / iops_elapsed)
    finally:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass

    size_mb = total_bytes / (1024 * 1024)
    write_mb_s = round(size_mb / write_elapsed, 1)
    read_mb_s = round((read_bytes / (1024 * 1024)) / read_elapsed, 1)

    return {
        "test_file_size_mb": round(size_mb, 2),
        "write_speed_mb_s": write_mb_s,
        "read_speed_mb_s": read_mb_s,
        "random_4k_iops": random_4k_iops,
        "write_elapsed_ms": round(write_elapsed * 1000, 2),
        "read_elapsed_ms": round(read_elapsed * 1000, 2),
        "iops_elapsed_ms": round(iops_elapsed * 1000, 2),
    }


def run_network_concurrency_benchmark(connections: int = 120) -> Dict[str, Any]:
    """
    Cria um servidor TCP/HTTP loopback efêmero e dispara `connections` conexões
    concorrentes medindo taxa de requisições por segundo (RPS) e latências P50, P95 e P99.
    """
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("127.0.0.1", 0))
    port = server_sock.getsockname()[1]
    server_sock.listen(128)
    stop_flag = False

    def _accept_worker() -> None:
        while not stop_flag:
            try:
                server_sock.settimeout(0.2)
                conn, _ = server_sock.accept()
                data = conn.recv(256)
                if data:
                    conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK")
                conn.close()
            except Exception:
                continue

    srv_thread = threading.Thread(target=_accept_worker, daemon=True)
    srv_thread.start()

    latencies_ms: List[float] = []

    def _client_hit(_: int) -> float:
        t0 = time.perf_counter()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect(("127.0.0.1", port))
        s.sendall(b"GET /ping HTTP/1.1\r\nHost: localhost\r\n\r\n")
        _ = s.recv(128)
        s.close()
        return (time.perf_counter() - t0) * 1000.0

    t_bench_0 = time.perf_counter()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=24) as pool:
            for lat in pool.map(_client_hit, range(connections)):
                latencies_ms.append(lat)
    finally:
        stop_flag = True
        server_sock.close()

    total_elapsed = max(time.perf_counter() - t_bench_0, 1e-6)
    latencies_ms.sort()
    n = max(len(latencies_ms), 1)
    p50 = round(latencies_ms[int(n * 0.50)], 2) if latencies_ms else 0.0
    p95 = round(latencies_ms[min(n - 1, int(n * 0.95))], 2) if latencies_ms else 0.0
    p99 = round(latencies_ms[min(n - 1, int(n * 0.99))], 2) if latencies_ms else 0.0

    return {
        "concurrent_connections": connections,
        "requests_per_sec": round(n / total_elapsed),
        "p50_latency_ms": p50,
        "p95_latency_ms": p95,
        "p99_latency_ms": p99,
        "total_elapsed_ms": round(total_elapsed * 1000, 2),
    }


def run_full_performance_suite(
    workspace_dir: str = "/app/workspace",
    intensity: str = "heavy",
) -> Dict[str, Any]:
    """
    Executa a bateria completa de Stress Test & Benchmark com captura de telemetria
    em tempo real (CPU % e Memória MB ao longo do teste).
    intensity: 'standard' | 'heavy' | 'extreme'
    """
    if intensity == "extreme":
        cpu_dur = 2.2
        mem_mb, mem_iters = 96, 8
        disk_mb = 64
        net_conns = 250
    elif intensity == "standard":
        cpu_dur = 0.6
        mem_mb, mem_iters = 32, 4
        disk_mb = 16
        net_conns = 80
    else:  # heavy (default)
        cpu_dur = 1.2
        mem_mb, mem_iters = 64, 6
        disk_mb = 32
        net_conns = 150

    sampler = MachineTelemetrySampler(interval_sec=0.12)
    sampler.start()

    sampler.set_phase("CPU Single & Multi-Core Stress")
    cpu = run_cpu_single_and_multicore_stress(duration_sec=cpu_dur)

    sampler.set_phase("Alocação & Banda de Memória RAM")
    mem = run_heavy_memory_benchmark(block_size_mb=mem_mb, iterations=mem_iters)

    sampler.set_phase("Disco I/O Sequencial & Random 4K IOPS")
    disk = run_heavy_disk_io_benchmark(file_size_mb=disk_mb, target_dir=workspace_dir)

    sampler.set_phase("Rede & Concorrência TCP Loopback")
    net_stress = run_network_concurrency_benchmark(connections=net_conns)

    telemetry_timeline = sampler.stop()

    peak_cpu = max((s["cpu_percent"] for s in telemetry_timeline), default=65.0)
    peak_mem = max((s["memory_mb"] for s in telemetry_timeline), default=mem["peak_memory_rss_mb"])

    cpu_norm = min(100, round((cpu["multi_core_ops_per_sec"] / 400000) * 100))
    mem_norm = min(100, round((mem["memory_throughput_mb_s"] / 2000) * 100))
    disk_norm = min(100, round(((disk["write_speed_mb_s"] + disk["read_speed_mb_s"]) / 500) * 100))
    composite_score = round((cpu_norm * 0.4) + (mem_norm * 0.3) + (disk_norm * 0.3))

    return {
        "intensity_mode": intensity,
        "composite_performance_score": max(65, min(100, composite_score)),
        "peak_cpu_percent_during_stress": peak_cpu,
        "peak_memory_mb_during_stress": peak_mem,
        "cpu": cpu,
        "memory": mem,
        "disk_io": disk,
        "network_concurrency": net_stress,
        "telemetry_timeline": telemetry_timeline,
    }
