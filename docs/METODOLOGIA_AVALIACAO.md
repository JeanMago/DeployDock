# Metodologia de Avaliação

Este documento define **como** o DeployDock é avaliado para responder à questão de pesquisa da proposta:

> *Como conceber e implementar uma ferramenta de baixo consumo de recursos que integre a gestão da Docker Engine à
> automação de implantação via webhooks do GitHub, garantindo consistência de ambiente, segurança nas requisições e
> minimização do tempo de inatividade?*

> [!IMPORTANT]
> O laudo atual em `deploydock-benchmark-suite/reports/` é uma **única execução** com pontuações compostas definidas
> pelo próprio autor. Serve como verificação funcional (smoke/E2E), mas **não** como evidência estatística. Para o TCC,
> reporte os experimentos abaixo, com repetições, média, desvio-padrão e intervalo de confiança.

## 1. Hipóteses

| ID | Hipótese | Experimento |
|---|---|---|
| H1 | O deploy por webhook inicia em menos de 5 s após o `push` (latência de reação) e conclui o pipeline em tempo comparável ao *build* manual | EXP-01 |
| H2 | A janela de indisponibilidade durante o deploy é limitada e com rollback automático evita falha prolongada | EXP-01, EXP-03 |
| H3 | O consumo ocioso (RAM/CPU) da pilha DeployDock é menor que o de alternativas completas (Coolify, CapRover, Portainer + CI) | EXP-02 |
| H4 | O WAF bloqueia as classes de ataque testadas com baixa taxa de falsos positivos e sobrecarga de latência desprezível | EXP-05 |
| H5 | Usuários sem experiência em DevOps conseguem publicar uma aplicação com usabilidade ≥ 68 (média SUS) | EXP-04 |

## 2. Ambiente de teste (registrar no texto do TCC)

Registrar para **toda** medição: CPU/RAM/disco do host, SO e kernel, versões (`docker version`, Python, Traefik,
PostgreSQL), *commit* do DeployDock (`git rev-parse HEAD`), latência de rede e se o host estava dedicado.
Use a mesma máquina e as mesmas aplicações de teste para todas as ferramentas comparadas.

Aplicações de teste sugeridas: (a) site estático Nginx; (b) API Node.js; (c) API Python com banco.

## 3. Experimentos

### EXP-01 — Duração do deploy e indisponibilidade
- **Ferramenta:** `scripts/bench_deploy_downtime.py` (sonda a URL a cada 100 ms durante o deploy).
- **Procedimento:** ≥ 10 repetições por aplicação, após 1 deploy de aquecimento (cache de camadas). Executar também com
  cache frio (`docker builder prune`) para separar o custo de *build*.
- **Métricas:** `deploy_s`, `downtime_s` (maior intervalo contínuo de falhas) e disponibilidade (%).
- **Saída:** CSV bruto + média, desvio-padrão, mediana, mín/máx e IC 95 %.

### EXP-02 — Consumo de recursos em repouso
- **Procedimento:** após 5 min ocioso, coletar 30 amostras de `docker stats --no-stream` (intervalo 10 s) de toda a pilha
  de cada ferramenta, sem aplicações implantadas e depois com 3 aplicações.
- **Métricas:** RAM (MiB) e CPU (%) agregados, imagem (MB) e tempo de *cold start* até a API responder.

### EXP-03 — Rollback automático
- **Procedimento:** implantar versão saudável; depois implantar versão defeituosa (health check falha) 10 vezes.
- **Métricas:** taxa de rollback bem-sucedido, tempo até restaurar o serviço, indisponibilidade acumulada.

### EXP-04 — Usabilidade (SUS)
- **Amostra:** 5–10 participantes (idealmente 2 perfis: estudantes de TI e pessoas sem experiência com Docker).
- **Tarefas cronometradas:** (T1) entrar e criar um projeto a partir de um repositório; (T2) configurar o webhook e
  disparar um deploy; (T3) localizar os logs de um contêiner com erro; (T4) fazer rollback.
- **Instrumentos:** tempo por tarefa, taxa de conclusão, questionário SUS (Anexo A) e comentários livres.
- **Cuidados éticos:** termo de consentimento, dados anônimos, participação voluntária (verificar exigência de comitê
  de ética da instituição).
- **Análise:** pontuação SUS (0–100), média e IC 95 %.

### EXP-05 — Eficácia e custo do WAF
- **Eficácia:** enviar payloads de SQLi, XSS, *path traversal* e RCE (ex.: listas do projeto SecLists / OWASP) e medir
  taxa de detecção.
- **Falsos positivos:** replicar tráfego legítimo da aplicação (≥ 1.000 requisições) e contar bloqueios indevidos.
- **Sobrecarga:** comparar latência p50/p95/p99 com `waf_enabled` ligado e desligado (ex.: `hey`, `wrk` ou `k6`),
  ≥ 5 repetições de 60 s.
- **Limites a declarar:** o WAF baseia-se em assinaturas sobre URL/query; não inspeciona corpo nem substitui ModSecurity.

### EXP-06 — Qualidade do software
- Cobertura de testes (`pytest --cov`), resultado do CI, análise estática (`ruff`) e número de requisitos com teste
  automatizado (ver [`REQUISITOS.md`](REQUISITOS.md)).

## 4. Comparação com ferramentas relacionadas

Critérios qualitativos (tabela de funcionalidades) e quantitativos (EXP-01 e EXP-02) para: **Portainer CE**,
**Coolify**, **CapRover**, **Watchtower** (+ Docker CLI). Instalar todas na mesma máquina, nas versões atuais, e
registrar as versões. Evitar atribuir pontuações subjetivas: use presença/ausência de recursos verificada na
documentação oficial, com data de consulta.

## 5. Tratamento estatístico

- Reportar **n**, média, desvio-padrão amostral, mediana e IC 95 % (t de Student para n < 30).
- Para comparar ferramentas: teste de Mann–Whitney U (amostras pequenas, sem pressupor normalidade) e tamanho de
  efeito; indicar *p*-valor e limitações.
- Descartar *outliers* somente com critério declarado a priori; manter dados brutos no repositório (`resultados/`).
- Registrar ameaças à validade: ambiente único, aplicações sintéticas, cache de rede/camadas, amostra de usuários pequena.

## 6. Reprodutibilidade

```bash
# 1) subir o DeployDock
cp .env.example .env && docker compose up -d
# 2) cadastrar o projeto de teste e anotar o ID (UI ou POST /api/v1/projects)
# 3) executar o benchmark
python scripts/bench_deploy_downtime.py --api http://localhost:8000 --user admin --password '***' \
    --project-id <UUID> --url http://meusite.localhost --runs 10 --out resultados/exp01_nginx.csv
# 4) testes automatizados e cobertura
cd backend && pip install -r requirements-dev.txt && pytest --cov=app
```

---

## Anexo A — Questionário SUS (System Usability Scale)

Escala de 1 (discordo totalmente) a 5 (concordo totalmente). Versão traduzida e adaptada ao português; citar Brooke (1996).

1. Acho que gostaria de usar este sistema com frequência.
2. Achei o sistema desnecessariamente complexo.
3. Achei o sistema fácil de usar.
4. Acho que precisaria de ajuda de uma pessoa técnica para conseguir usar este sistema.
5. Achei que as várias funções do sistema estavam bem integradas.
6. Achei que havia muita inconsistência neste sistema.
7. Imagino que a maioria das pessoas aprenderia a usar este sistema rapidamente.
8. Achei o sistema muito complicado de usar.
9. Senti-me muito confiante ao usar o sistema.
10. Precisei aprender várias coisas antes de conseguir usar o sistema.

**Cálculo:** itens ímpares → (resposta − 1); itens pares → (5 − resposta); somar os dez valores e multiplicar por 2,5
(resultado 0–100). Média de referência na literatura: ≈ 68.

## Anexo B — Roteiro de tarefas para o teste de usabilidade

| Tarefa | Descrição | Critério de sucesso | Tempo máx. |
|---|---|---|---|
| T1 | Fazer login e cadastrar o projeto "meu-site" a partir de um repositório fornecido | Projeto aparece na lista | 5 min |
| T2 | Configurar o webhook no GitHub e realizar um `push` | Deploy `healthy` visível | 10 min |
| T3 | Encontrar a mensagem de erro nos logs do contêiner "app-quebrado" | Erro lido em voz alta | 3 min |
| T4 | Reverter para o deploy anterior | Status volta à versão anterior | 3 min |
