FROM python:3.11-slim

LABEL maintainer="DeployDock Benchmark Suite"
LABEL description="Sonda de diagnóstico, testes E2E e benchmark comparativo para plataformas de gerenciamento Docker (DeployDock, Portainer, Coolify, CapRover, Dokploy)"

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    BENCHMARK_ENV_INJECTED="dockerfile-default"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/workspace /app/reports

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
