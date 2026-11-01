# Contribuindo

## Ambiente de desenvolvimento
```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload

# Frontend
cd frontend && npm ci && npm run dev
```
Ou use `start-dev.sh` / `start-dev.ps1` / `start-dev.bat`.

## Antes de abrir um Pull Request
```bash
cd backend
ruff check app tests          # lint
pytest --cov=app              # testes (não exigem Docker)
alembic check                 # modelos e migrações coerentes
cd ../frontend && npm run build
```
O CI (`.github/workflows/ci.yml`) executa as mesmas verificações.

## Convenções
- Alterou um modelo? Gere a migração: `alembic revision --autogenerate -m "descrição"`.
- Nova funcionalidade ou correção deve vir com teste em `backend/tests/` e, se aplicável, atualizar
  [`docs/REQUISITOS.md`](docs/REQUISITOS.md).
- Mensagens de commit no imperativo e objetivas (ex.: `Exige JWT nos WebSockets`).
- Nunca versionar `.env`, bancos `.db` ou segredos.
