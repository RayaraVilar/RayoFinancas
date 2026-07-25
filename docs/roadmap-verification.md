# Verificação do roadmap — etapas 4 a 15

Atualizada em 25/07/2026. A tabela relaciona cada etapa a evidência presente no
repositório. “Gate externo” não é tratado como concluído por mock ou configuração
local.

| Etapa | Estado local | Evidência principal | Gate externo |
|---|---|---|---|
| 4 — Integração bancária | Implementada | migrações `0006`–`0008`, `banking/`, worker Dramatiq, Redis, contract tests e integração PostgreSQL | validar Pluggy sandbox/produção com credenciais rotacionadas |
| 5 — Analytics/dashboard | Implementada | `analytics/`, dashboard responsivo, cobertura/confiança, projeção e testes de cálculo | validação de compreensão com usuários |
| 5B — Contas/Saldo Livre | Implementada | migração `0009`, `planning/`, dedupe, estados, orçamento e testes PostgreSQL | conciliação com dados reais |
| 6 — Planejamento | Implementada | plano mensal, budgets, ritmo, déficit e virada de competência | pesquisa com usuários |
| 7 — Metas/cenários | Implementada | migração `0010`, cenários, before/after, expiração, lock e idempotência | validação de conteúdo |
| 8 — Dívidas | Implementada | migração `0011`, Price/SAC, snowball/avalanche e golden tests | revisão financeira/jurídica |
| 9 — Futuro/score | Implementada | migração `0012`, snapshots, projeções, score versionado e testes | validar efeito emocional do score |
| 10 — Insights | Implementada | migração `0013`, regras versionadas, prioridade, dedupe, cooldown e feedback | medir utilidade na beta |
| 11 — Assistente | Implementada | provider Gemini, orquestrador, contexto minimizado, chave por usuário, registry sem execução e testes contra exfiltração básica | cada usuário fornece a própria chave; concluir DPIA do operador |
| 12 — Hardening/beta | Parcial verificável | CSRF, CSP, HSTS, rate limit, exportação/exclusão, threat model, auditoria de secrets | pentest, restore, carga, WCAG, observabilidade e beta |
| 13 — Simulação de pagamentos | Implementada | migração `0014`, hash imutável, expiração, risco e testes determinísticos | validação com provider |
| 14 — Iniciação de pagamentos | Protegida e desativada | port separado, modelos, feature flag falsa, kill switch verdadeiro e endpoint bloqueado | ITP/provider, contrato, regulação, SCA, pentest e aprovação formal |
| 15 — PJ/inbox | Núcleo implementado | migração `0015`, recebíveis, assinaturas, calendário, revisão humana e preferências | Gmail permanece `DESIGN_ONLY` até consentimento e controles aprovados |

## Evidência de validação

- migrações Alembic `0001`–`0016`;
- suíte unitária e integração com PostgreSQL real;
- Ruff, mypy estrito, ESLint e TypeScript;
- builds Docker multi-stage da API e do frontend;
- health/readiness e smoke test local;
- varredura de padrões de segredos no estado atual e em todo o histórico Git.
