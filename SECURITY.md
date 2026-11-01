# Política de Segurança

## Versões suportadas
Apenas a branch principal recebe correções de segurança.

## Como reportar uma vulnerabilidade
Não abra uma *issue* pública. Use a aba **Security → Report a vulnerability** do repositório no GitHub (ou contate o
mantenedor diretamente). Inclua passos de reprodução, versão/commit e impacto estimado. A resposta inicial é feita em
até 7 dias.

## Boas práticas para quem hospeda o DeployDock
- Use `ENVIRONMENT=production` com `SECRET_KEY` (≥ 32 caracteres), `GITHUB_WEBHOOK_SECRET` e senha de administrador
  fortes — a aplicação se recusa a iniciar com valores padrão. O script `deploy-prod.sh` já os gera.
- Mantenha o backend ligado apenas em `127.0.0.1` e exponha somente o Traefik (80/443).
- Considere um *socket proxy* para o Docker e leia [`docs/AMEACAS_E_LIMITACOES.md`](docs/AMEACAS_E_LIMITACOES.md).
- Troque a senha do administrador inicial no primeiro acesso.
