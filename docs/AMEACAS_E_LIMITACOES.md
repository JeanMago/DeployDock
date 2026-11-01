# Modelo de Ameaças, Limitações e Trabalhos Futuros

## 1. Ativos e fronteiras de confiança

| Ativo | Por que importa |
|---|---|
| `docker.sock` montado no backend | Equivale a *root* no host |
| `SECRET_KEY` | Assina JWT e deriva a chave Fernet |
| Tokens Git (PAT) e segredos de webhook | Acesso a repositórios privados / disparo de deploys |
| Contêineres das aplicações | Disponibilidade e dados dos usuários |

Fronteiras: Internet → Traefik/Frontend → Backend → Docker Engine → contêineres de terceiros (código não confiável).

## 2. Análise STRIDE

| Ameaça | Cenário | Mitigação implementada | Risco residual |
|---|---|---|---|
| **S**poofing | Webhook forjado dispara deploy | HMAC-SHA256 com comparação em tempo constante; segredo por projeto | Segredo global padrão — mitigado por RNF-07 (bloqueio em produção) |
| **S**poofing | JWT forjado / `alg=none` | Algoritmo fixo HS256; expiração; testes de adulteração | Sem revogação nem *refresh token* |
| **T**ampering | Corpo do webhook alterado em trânsito | Assinatura cobre o corpo bruto | — |
| **T**ampering | Injeção de argumentos Git (`--upload-pack`, `ext::`) | `validate_safe_git_url` (somente http/https, sem flags) | Revalidar em todo ponto que aceite URL |
| **R**epudiation | Ação administrativa sem rastro | Trilha de auditoria (últimos 300 eventos, em memória) | Auditoria não persistente — melhoria futura |
| **I**nformation disclosure | Logs/WS lidos por não autenticados | JWT obrigatório em REST e WebSocket (RNF-06) | Token na *query string* pode aparecer em logs de proxy |
| **I**nformation disclosure | Token Git em repouso | Cifrado com Fernet (chave derivada de `SECRET_KEY`) | Rotacionar `SECRET_KEY` invalida segredos cifrados |
| **D**enial of service | Inundação de requisições / força bruta | Rate limit por IP; bloqueio temporário | Limite por processo; `X-Forwarded-For` confiável apenas atrás do Traefik |
| **E**levation of privilege | SSRF via URL de repositório para metadados/rede interna | Bloqueio de loopback, link-local, redes privadas e hosts de metadados | DNS *rebinding* não tratado |
| **E**levation of privilege | Usuário `developer` executa comandos destrutivos no contêiner | Política de comandos + RBAC | Lista de bloqueio é contornável; ver 3.1 |
| **E**levation of privilege | Fuga do contêiner/uso do `docker.sock` | Execução com `no-new-privileges`; bloqueio de acesso ao socket nos comandos | Ver 3.1 |

## 3. Limitações conhecidas

### 3.1 Exposição do `docker.sock`
O backend precisa do socket para operar. Quem comprometer o backend controla o host. Para ambientes sensíveis, usar um
*socket proxy* com permissões restritas (ex.: `tecnativa/docker-socket-proxy`) ou Docker em modo *rootless*.

### 3.2 Estado em memória
WAF, *rate limit*, bloqueios, auditoria e *WebSocket manager* vivem na memória do processo. Consequências:
execução com **um único worker**, perda de estado em reinício e ausência de escala horizontal.

### 3.3 Estratégias de implantação (`recreate` vs `blue_green`)
Cada projeto pode escolher `deploy_strategy = "recreate"` (para o contêiner antigo e inicia o novo, com breve janela de
indisponibilidade) ou `deploy_strategy = "blue_green"` (sobe o contêiner candidato paralelamente na mesma rede e com as
mesmas *labels* do Traefik, valida o *health check* interno e só então drena e remove a versão anterior; se o candidato
falhar, ele é descartado sem derrubar a versão em produção). Ambas as estratégias podem ser comparadas empiricamente com
`scripts/bench_deploy_downtime.py` e `scripts/bench_multiplatform_compare.py`.

### 3.4 Escopo
- Um único host Docker (sem multi-nó, Swarm ou Kubernetes).
- Somente GitHub como origem de webhooks.
- Papéis simples (`admin`/`developer`/`viewer`), sem permissões por projeto.
- Sem 2FA nem SSO; sem revogação de JWT.
- Backup/restore de dados do próprio DeployDock não automatizado (apenas de volumes dos usuários).

## 4. Trabalhos futuros (priorizados)

1. Estratégia *blue/green* / *rolling* para deploy sem indisponibilidade.
2. Auditoria e estado do WAF persistidos (Redis/PostgreSQL) para múltiplos workers.
3. *Socket proxy* do Docker e execução do backend sem privilégios de root.
4. 2FA/OIDC, *refresh tokens* e revogação de sessões; RBAC por projeto.
5. Suporte a GitLab/Bitbucket e a registries de imagens privados.
6. Testes de ponta a ponta (Playwright) e testes de carga automatizados no CI.
7. Exportação de métricas/traces (OpenTelemetry) e painéis Grafana.
8. Rotação de chaves (`SECRET_KEY`) com re-cifragem de segredos.
