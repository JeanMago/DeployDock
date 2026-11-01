# Fundamentação Teórica e Trabalhos Relacionados

> Material de apoio para o capítulo de revisão da literatura. **Verifique cada referência** (edição, páginas, DOI/URL e
> data de acesso) antes de incluí-la no texto final e formate conforme a ABNT adotada pela instituição.

## 1. Conceitos

| Tema | Ideia central para o TCC | Referência de partida |
|---|---|---|
| Contêineres | Isolamento leve (namespaces/cgroups) e reprodutibilidade de ambiente | MERKEL, D. *Docker: lightweight Linux containers for consistent development and deployment.* Linux Journal, n. 239, 2014. |
| Orquestração | Complexidade e custo operacional de plataformas de grande porte | BURNS, B. et al. *Borg, Omega, and Kubernetes.* ACM Queue, v. 14, n. 1, 2016. |
| Entrega contínua | Automação do caminho commit → produção | HUMBLE, J.; FARLEY, D. *Continuous Delivery.* Addison-Wesley, 2010. |
| DevOps / confiabilidade | Operação como disciplina de engenharia; disponibilidade e rollback | BEYER, B. et al. *Site Reliability Engineering.* O'Reilly, 2016. |
| GitOps | Repositório como fonte de verdade do estado desejado | Documentação do Argo CD / Flux (OpenGitOps Principles, CNCF) |
| Autenticação de webhooks | HMAC para integridade e autenticidade da mensagem | KRAWCZYK, H. et al. *HMAC: Keyed-Hashing for Message Authentication.* RFC 2104, 1997; documentação "Validating webhook deliveries" do GitHub |
| Tokens | Estrutura e riscos do JWT | JONES, M. et al. *JSON Web Token (JWT).* RFC 7519, 2015 |
| Segurança web | Classes de ataque cobertas pelo WAF (injeção, XSS, SSRF) | OWASP Top 10 (2021); OWASP Cheat Sheet Series |
| Armazenamento de senhas | KDFs com salt e custo ajustável | NIST SP 800-132 (PBKDF2); OWASP Password Storage Cheat Sheet |
| Usabilidade | Escala SUS | BROOKE, J. *SUS: a "quick and dirty" usability scale.* In: Usability Evaluation in Industry. Taylor & Francis, 1996. |
| Estatística experimental | Projeto de experimentos e análise em engenharia de software | WOHLIN, C. et al. *Experimentation in Software Engineering.* Springer, 2012. |
| Segurança de contêineres | Riscos do `docker.sock`, privilégio e isolamento | NIST SP 800-190, *Application Container Security Guide*, 2017 |

## 2. Comparação com as duas plataformas de referência do TCC

Para manter o foco experimental e estatístico, a comparação direta do TCC concentra-se no **DeployDock** e em **duas plataformas de referência** com arquiteturas distintas: **Portainer CE** (gerenciador leve de contêineres) e **Coolify v4** (PaaS auto-hospedável completo). O passo a passo de medição encontra-se em [`ROTEIRO_BENCHMARK_COMPARATIVO.md`](ROTEIRO_BENCHMARK_COMPARATIVO.md).

| Recurso | DeployDock | Portainer CE 2.21 | Coolify v4 |
|---|---|---|---|
| Gestão visual de contêineres | ✅ | ✅ | ✅ |
| Deploy por webhook (push HMAC-SHA256) | ✅ | verificar (varia por edição) | ✅ |
| Build a partir do Git (Zero-Config / Dockerfile) | ✅ | verificar | ✅ |
| Rollback automático + Deploy Blue/Green | ✅ | ❌ | ✅ |
| HTTPS automático (Traefik + Let's Encrypt) | ✅ | ❌ nativo | ✅ |
| WAF / rate limit / anti-brute-force integrados | ✅ | ❌ | ❌ |
| Explorador de arquivos interno + Backup `.tar.gz` | ✅ | ❌ | parcial |
| Consumo ocioso (RAM / CPU) | medir ([roteiro](ROTEIRO_BENCHMARK_COMPARATIVO.md)) | medir ([roteiro](ROTEIRO_BENCHMARK_COMPARATIVO.md)) | medir ([roteiro](ROTEIRO_BENCHMARK_COMPARATIVO.md)) |

> Células "verificar" devem ser resolvidas por consulta à documentação e/ou teste prático. Não afirme diferenciais
> que não tenham sido confirmados — a banca costuma checar.

## 3. Posicionamento (lacuna)

O DeployDock **não** pretende substituir Kubernetes nem plataformas multi-nó. A contribuição está na combinação, em uma
única aplicação leve e auto-hospedável, de: (i) gestão visual da Docker Engine, (ii) CD orientado a eventos com HMAC e
rollback, e (iii) camada de segurança ativa integrada — para infraestruturas de pequeno e médio porte. A avaliação
(ver [`METODOLOGIA_AVALIACAO.md`](METODOLOGIA_AVALIACAO.md)) deve confirmar ou refutar essa proposição com dados.

## 4. Sugestão de estrutura do texto do TCC

1. Introdução (contexto, problema, objetivos — já na `proposta_tcc.txt`)
2. Fundamentação teórica (seção 1 acima)
3. Trabalhos relacionados (seção 2)
4. Especificação (`REQUISITOS.md`) e arquitetura (`ARQUITETURA.md`)
5. Implementação (decisões, segurança, testes)
6. Avaliação (EXP-01 a EXP-06, resultados e ameaças à validade)
7. Limitações e trabalhos futuros (`AMEACAS_E_LIMITACOES.md`)
8. Conclusão (resposta explícita à questão de pesquisa)
