# Rayo Finanças — Backlog incremental

> Atualizado em: 24/07/2026  
> Regra: marcar como concluído somente após implementação, testes e documentação correspondentes.  
> Estado atual: etapas 1–10, simulação de pagamentos e núcleo PJ implementados e
> validados localmente. Itens que dependem de provider, revisão regulatória,
> pentest, staging ou usuários reais permanecem abertos. A matriz verificável está
> em `docs/implementation-status.md`; os checkboxes abaixo preservam a decomposição
> original e devem ser lidos junto dos bloqueios externos.

## Legenda

- `[x]` concluído e verificado
- `[ ]` pendente
- `[~]` em andamento — usar apenas durante execução ativa
- `[!]` bloqueado — registrar motivo e decisão necessária

## Agora — Etapa 0: produto e arquitetura

- [x] Consolidar visão do produto e proposta de valor.
- [x] Definir personas e problemas prioritários.
- [x] Propor arquitetura de monólito modular.
- [x] Propor estrutura de diretórios.
- [x] Propor modelo de dados e relacionamentos.
- [x] Definir páginas e estrutura do dashboard.
- [x] Definir métricas, gráficos e regras de comparação.
- [x] Definir Financial Health Score inicial.
- [x] Definir Financial Insights Engine inicial.
- [x] Incorporar dívidas, metas, cenários e planejamento mensal.
- [x] Incorporar assistente financeiro e princípio “Python calcula → IA interpreta”.
- [x] Definir estratégia BankProvider/Open Finance.
- [x] Definir autenticação, segurança, LGPD e deploy.
- [x] Definir MVP, pós-MVP, roadmap e riscos.
- [x] Criar `plan.md`.
- [x] Criar `todo.md`.
- [x] Incorporar `FinancialProfile` e contexto PF/PJ.
- [x] Definir Saldo Livre e Central de Contas.
- [x] Definir simulação, autorização e orquestração de pagamentos.
- [x] Fixar regra de que a IA nunca executa pagamentos.
- [x] Criar documentação de arquitetura, banco, segurança, IA, Open Finance e pagamentos.
- [x] Criar `decisions.md` com ADRs 001–020.
- [ ] Validar com stakeholders a persona prioritária da beta.
- [ ] Validar limites do MVP e critérios de corte.
- [ ] Validar terminologia e arquitetura de informação com usuários.
- [ ] Definir política de retenção de chat e payloads externos.
- [ ] Definir fornecedor de hospedagem, secrets e observabilidade.
- [ ] Definir provedor de LLM e requisitos contratuais de privacidade.
- [ ] Revisar score e comunicação de dívidas com especialista financeiro/jurídico.
- [x] Criar ADRs iniciais listados em `plan.md`.
- [ ] Criar mapa de dados/LGPD e threat model.
- [ ] Criar fluxos e wireframes do MVP.
- [ ] Testar protótipo com 5–8 pessoas das personas A–C.

## Etapa 1 — Skeleton executável

- [x] Inicializar monorepo.
- [x] Criar app Next.js + TypeScript + Tailwind.
- [ ] Adicionar shadcn/ui junto do primeiro componente reutilizável; não instalar pacote órfão.
- [x] Criar API FastAPI + Pydantic + SQLAlchemy + Alembic.
- [x] Configurar PostgreSQL e Docker Compose.
- [x] Adicionar configuração tipada e secrets por ambiente.
- [x] Adicionar health/readiness checks.
- [x] Configurar lint, format e typecheck.
- [x] Configurar testes unitários mínimos.
- [x] Configurar GitHub Actions sem deploy.
- [x] Implementar landing mínima integrada ao health check.
- [x] Documentar execução local.
- [x] Verificar build limpo das imagens Docker.
- [x] Executar teste de integração com PostgreSQL real.
- [x] Auditar dependências npm sem vulnerabilidades conhecidas.
- [x] Revisar landing visualmente em desktop e breakpoint mobile.

**Aceite:** atendido localmente — landing/API/PostgreSQL saudáveis via Compose, checks verdes e nenhum segredo versionado. A execução remota do workflow ocorrerá no primeiro push.

## Etapa 2 — Identidade e onboarding manual

- [x] Modelar `users`, `financial_profiles`, `oauth_identities`, sessões e consentimentos.
- [x] Implementar Google Authorization Code + PKCE.
- [x] Implementar cookie seguro, rotação, logout e revogação.
- [x] Criar middleware/contexto `UserScope`.
- [x] Criar `FinancialContext` obrigatório e seletor Tudo/Pessoal/Empresa.
- [x] Testar isolamento entre usuários e IDOR.
- [x] Criar onboarding acessível e responsivo.
- [x] Permitir primeira conta manual.
- [x] Exibir consentimentos e privacidade em linguagem simples.
- [x] Auditar login, revogação e mudanças sensíveis sem PII em logs.

**Aceite:** usuário autentica, consente, cria perfil/conta manual e jamais lê dados de outro usuário ou perfil não autorizado.

## Etapa 3 — Transações e categorias

- [x] Modelar contas, cartões, faturas, transações e categorias.
- [x] Implementar valores com Decimal/NUMERIC e datas por competência.
- [x] Implementar CRUD manual de transação.
- [x] Implementar lista com paginação cursor, busca e filtros.
- [x] Implementar categorias padrão e personalizadas.
- [x] Implementar edição e split.
- [x] Implementar regra de categorização criada pelo usuário.
- [x] Tratar transferências próprias.
- [ ] Tratar compras, faturas, pagamentos e estornos sem dupla contagem.
- [ ] Tratar pendente → confirmada com idempotência.
- [x] Criar testes unitários e de integração do fluxo manual.
- [ ] Criar E2E de navegador após estabilizar o login Google.

**Aceite:** totais mensais reconciliam com transações e regras contábeis documentadas.

## Etapa 4 — Integração bancária

- [ ] Criar port e DTOs canônicos `BankProvider`.
- [ ] Implementar adaptador Pluggy em sandbox.
- [ ] Implementar consentimento, callback e revogação.
- [ ] Criptografar/referenciar tokens do provider.
- [ ] Configurar Redis e Dramatiq.
- [ ] Implementar webhooks autenticados e idempotentes.
- [ ] Implementar sync paginado de contas, saldos, cartões e transações.
- [ ] Implementar normalização, deduplicação e reconciliação.
- [ ] Implementar retries, dead-letter e métricas.
- [ ] Exibir último sync, progresso, falha e reconexão.
- [ ] Criar contract tests com fixtures sanitizadas.

**Aceite:** conexão sandbox popula dados canônicos sem duplicidade e pode ser revogada.

## Etapa 5 — Analytics e dashboard

- [ ] Definir contratos de métricas com período, cobertura e confiança.
- [ ] Implementar receita, despesa, saldo, economia e patrimônio.
- [ ] Implementar comparação por período equivalente.
- [ ] Implementar despesas por categoria.
- [ ] Implementar detecção inicial de recorrência.
- [ ] Implementar projeção de fechamento do mês.
- [ ] Criar snapshots/agregados apenas onde profiling justificar.
- [ ] Criar dashboard responsivo conforme hierarquia do `plan.md`.
- [ ] Implementar estados vazio, carregando, parcial, atrasado e erro.
- [ ] Adicionar “Como calculamos”.
- [ ] Testar acessibilidade e formatação pt-BR.
- [ ] Criar golden/property tests dos cálculos.

**Aceite:** dashboard responde às perguntas centrais e distingue realizado de projetado.

## Etapa 5B — Contas a pagar e Saldo Livre

- [ ] Modelar `Bill`, `BillSource` e máquina de estados.
- [ ] Implementar cadastro manual e primeira fonte bancária/fatura.
- [ ] Implementar dedupe exato e candidatos ambíguos para revisão.
- [ ] Criar Central de Contas/Financial Inbox.
- [ ] Definir contrato versionado de Saldo Livre com componentes e horizonte.
- [ ] Excluir limite de crédito e recebível incerto do saldo.
- [ ] Integrar compromissos confirmados à projeção.
- [ ] Respeitar `FinancialContext` e alertar possível mistura PF/PJ.
- [ ] Testar transições, dedupe, competência, isolamento e arredondamento.

**Aceite:** usuário confirma uma cobrança e entende o Saldo Livre sem iniciar pagamento.

## Etapa 6 — Orçamentos e planejamento mensal

- [ ] Modelar orçamentos, planos e itens.
- [ ] Implementar limites mensais por categoria.
- [ ] Calcular consumido, ritmo e projeção.
- [ ] Implementar renda prevista, essenciais, dívidas e metas.
- [ ] Calcular margem disponível sem dupla contagem.
- [ ] Alertar déficit projetado.
- [ ] Criar tela de orçamento e visão mensal.
- [ ] Testar fechamento, virada de competência e fuso horário.

**Aceite:** usuário entende quanto ainda pode gastar e quais premissas formam esse valor.

## Etapa 7 — Metas e cenários

- [ ] Modelar metas, contribuições e versões de plano.
- [ ] Implementar progresso, restante, meses e aporte necessário.
- [ ] Implementar simulador sem mutação real.
- [ ] Modelar cenários, deltas e resultados.
- [ ] Comparar atual/conservador/equilibrado/agressivo.
- [ ] Implementar ação pendente com antes/depois e expiração.
- [ ] Implementar confirmação idempotente e optimistic lock.
- [ ] Propagar mudança confirmada para plano, dashboard e projeção.
- [ ] Testar casos-limite de datas, zero, arredondamento e conflito.

**Aceite:** simulação nunca altera a meta antes de confirmação e histórico permanece rastreável.

## Etapa 8 — Dívidas

- [ ] Modelar dívidas, taxas e pagamentos.
- [ ] Implementar cadastro manual e qualidade dos dados.
- [ ] Criar painel de saldo, parcelas, juros e prazo.
- [ ] Implementar amortização Price e SAC.
- [ ] Implementar snowball e avalanche.
- [ ] Implementar adicional único/recorrente e valores predefinidos.
- [ ] Comparar prazo, meses, juros e margem.
- [ ] Mostrar limitações quando taxa/CET/sistema forem desconhecidos.
- [ ] Integrar parcelas ao planejamento.
- [ ] Criar golden/property tests de amortização.

**Aceite:** cenários são reprodutíveis, explicáveis e nunca prometem exatidão sem dados.

## Etapa 9 — Patrimônio, futuro e Health Score

- [ ] Criar snapshots de patrimônio.
- [ ] Implementar projeções de 3, 6, 12, 24 meses e personalizadas.
- [ ] Exibir premissas editáveis em cenário temporário.
- [ ] Especificar curvas exatas do Health Score com exemplos.
- [ ] Implementar subescores, confiança e dados insuficientes.
- [ ] Versionar algoritmo e snapshots.
- [ ] Criar página “Meu Futuro Financeiro”.
- [ ] Validar compreensão e efeito emocional do score com usuários.

**Aceite:** projeção e score são explicáveis, versionados e tolerantes a dados ausentes.

## Etapa 10 — Financial Insights Engine

- [ ] Criar contrato de regra e mensagem estruturada.
- [ ] Implementar pipeline, prioridade, dedupe e cooldown.
- [ ] Implementar regras iniciais do `plan.md`.
- [ ] Limitar dashboard a 1–3 insights prioritários.
- [ ] Implementar feed, estados, feedback e CTA.
- [ ] Adicionar evidências e “Como calculamos”.
- [ ] Criar fixtures de casos positivos, negativos e limítrofes.
- [ ] Medir utilidade sem usar dados sensíveis em analytics.

**Aceite:** cada insight é reproduzível por regra/versão e leva a uma ação relevante.

## Etapa 11 — Assistente financeiro

- [ ] Selecionar LLM provider conforme privacidade, custo e confiabilidade.
- [ ] Criar port de LLM e orquestrador.
- [ ] Criar registry com allowlist e schemas Pydantic.
- [ ] Implementar tools de leitura.
- [ ] Implementar tools de simulação.
- [ ] Implementar `FinancialContext` em todas as tools e testes PF/PJ.
- [ ] Implementar `get_free_balance`, bills, recebíveis e compromissos de cartão.
- [ ] Garantir por contrato que não existe tool `execute_payment`.
- [ ] Implementar propostas sem mutação.
- [ ] Integrar ações pendentes e confirmação estruturada.
- [ ] Impedir SQL/ORM/provider token no contexto do LLM.
- [ ] Implementar redaction, limites, timeouts e auditoria.
- [ ] Distinguir fato, estimativa e simulação na resposta.
- [ ] Responder “dados insuficientes” sem inventar.
- [ ] Criar evals de precisão, tool selection, prompt injection e confirmação.
- [ ] Implementar retenção/exclusão de conversas.
- [ ] Criar interface de chat acessível e responsiva.

**Aceite:** toda resposta numérica crítica deriva de tool; nenhuma mutação ocorre sem confirmação.

## Etapa 12 — Hardening e beta privada

- [ ] Concluir mapa de dados, DPIA/avaliação equivalente e revisão LGPD.
- [ ] Implementar exportação e exclusão.
- [ ] Ativar/testar RLS ou documentar controle equivalente aprovado.
- [ ] Executar threat modeling e pentest.
- [ ] Configurar CSP, CSRF, CORS e rate limiting.
- [ ] Configurar secret manager e rotação.
- [ ] Configurar backup e testar restauração.
- [ ] Configurar logs, métricas, traces, alertas e runbooks.
- [ ] Definir SLOs a partir de baseline.
- [ ] Executar testes de carga dos fluxos críticos.
- [ ] Auditar WCAG 2.2 AA e mobile.
- [ ] Criar staging e pipeline de deploy.
- [ ] Preparar suporte e resposta a incidentes.
- [ ] Conduzir beta privada e revisar métricas.

**Aceite:** controles de segurança/privacidade são verificáveis e operação possui runbooks.

## Etapa 13 — Simulação de pagamentos

- [ ] Modelar `PaymentSimulation` imutável e expiráveis.
- [ ] Selecionar uma, várias ou todas as bills elegíveis.
- [ ] Comparar contas pagadoras do mesmo perfil.
- [ ] Calcular saldo pós-pagamento, compromissos e Saldo Livre.
- [ ] Implementar risco determinístico versionado.
- [ ] Exibir operações externas potencialmente múltiplas.
- [ ] Criar proposta estruturada pelo chat sem mutação.
- [ ] Vincular resumo a hash; qualquer alteração invalida a proposta.
- [ ] Alertar e pedir confirmação específica para PF/PJ cruzado.
- [ ] Testar que “pague X” nunca inicia movimentação.

**Aceite:** toda intenção de pagamento termina em simulação revisável e nenhuma chamada externa de pagamento existe.

## Etapa 14 — Iniciação de pagamentos

- [ ] Selecionar provider/ITP e validar requisitos regulatórios/contratuais.
- [ ] Criar port `PaymentProvider` separado de `BankProvider`.
- [ ] Modelar `Payment`, `PaymentItem`, autorização e comprovante.
- [ ] Implementar feature flag e kill switch.
- [ ] Implementar autorização explícita e autenticação bancária.
- [ ] Implementar idempotência por item e proteção contra replay.
- [ ] Implementar estados parcial/desconhecido e reconciliação.
- [ ] Implementar webhook/polling verificados.
- [ ] Atualizar Bill/transação/analytics somente após confirmação.
- [ ] Auditar sem registrar barcode, Pix, token ou PII desnecessária.
- [ ] Executar threat model, pentest e testes adversariais.
- [ ] Preparar limites, alertas, suporte e runbook.

**Aceite:** pagamento sandbox autorizado é reconciliado exatamente uma vez; produção continua desativada até aprovação formal.

## Etapa 15 — PJ e Financial Inbox avançada

- [ ] Modelar contas a receber.
- [ ] Implementar fluxo a pagar × receber e capital de giro.
- [ ] Implementar fornecedores/impostos/pró-labore sem escopo de ERP.
- [ ] Implementar calendário financeiro e saldo por data.
- [ ] Implementar assinaturas e confirmação de recorrência.
- [ ] Projetar Gmail OAuth com consentimento separado.
- [ ] Implementar ingestão mínima, phishing controls e conteúdo não confiável.
- [ ] Implementar dedupe multi-fonte e revisão humana.
- [ ] Adicionar notificações configuráveis.

**Aceite:** perfil Empresa enxerga compromissos e recebimentos futuros sem contabilidade/ERP e sem confiar automaticamente em email.

## Pós-MVP — não iniciar sem evidência

- [ ] Notificações configuráveis.
- [ ] Importação OFX/CSV avançada.
- [ ] Contas compartilhadas e permissões.
- [ ] Investimentos e ativos.
- [ ] Multi-moeda.
- [ ] Novos BankProviders.
- [ ] Novos PaymentProviders.
- [ ] App nativo.
- [ ] Categorização assistida por modelo.
- [ ] Billing e planos.

## Registro de andamento

| Data | Mudança | Evidência |
|---|---|---|
| 24/07/2026 | Planejamento inicial criado; nenhum código implementado | `plan.md` e `todo.md` |
| 24/07/2026 | Fundação Next.js/FastAPI/PostgreSQL implementada e validada | build, lint, types, testes, Docker e health/readiness |
| 24/07/2026 | Arquitetura ampliada para PF/PJ, Bills, Saldo Livre e pagamentos autorizados | `plan.md`, `decisions.md` e `docs/` |
| 24/07/2026 | Identidade, sessão, perfis, consentimento e onboarding manual implementados | migração Alembic, 13 testes, build Next.js e testes de isolamento |
| 24/07/2026 | Ledger manual implementado com categorias, transações, filtros, totais e dashboard | migração `0002`, 15 testes e build Next.js |
| 24/07/2026 | Diagnóstico OAuth seguro e access log de callback removido | falhas categorizadas sem registrar códigos ou tokens |
| 24/07/2026 | Cartões e faturas manuais implementados; pagamento tratado como transferência idempotente | migração `0003`, 21 testes e build Next.js |
| 24/07/2026 | Transferências pareadas e estornos idempotentes implementados sem distorcer totais | migração `0004`, 23 testes e build Next.js |
| 24/07/2026 | Splits reconciliados e regras determinísticas de categorização implementados | migração `0005`, 24 testes e build Next.js |

## Bloqueios

A Etapa 2 está implementada. O teste ponta a ponta com uma conta Google real depende das credenciais `RAYO_GOOGLE_CLIENT_ID` e `RAYO_GOOGLE_CLIENT_SECRET`; enquanto ausentes, o produto informa esse estado sem simular login. Pagamentos de produção permanecem bloqueados até provider/ITP, revisão regulatória, threat model, pentest e aprovação formal.
