# Rayo Finanças — Registro de decisões

> ADRs simplificados. “Aceita” orienta a implementação; “Proposta” ainda exige validação antes do módulo correspondente.

## ADR-001 — PostgreSQL como fonte de verdade

- **Status:** Aceita
- **Decisão:** PostgreSQL armazena estado transacional; Redis nunca é fonte única financeira.
- **Por quê:** consistência, constraints, índices e operação madura.

## ADR-002 — Monólito modular

- **Status:** Aceita
- **Decisão:** um deploy de API/worker com módulos de domínio explícitos.
- **Alternativa:** microserviços.
- **Por quê:** menor custo operacional; extração somente por evidência de escala, equipe ou isolamento.

## ADR-003 — REST + OpenAPI

- **Status:** Aceita
- **Decisão:** contratos `/api/v1` e cliente TypeScript gerado futuramente.
- **Alternativa:** GraphQL.
- **Por quê:** tipos e evolução suficientes com menor superfície.

## ADR-004 — Dinheiro e tempo explícitos

- **Status:** Aceita
- **Decisão:** `NUMERIC(19,2)`/`Decimal`, moeda ISO, instante UTC e competência/fuso explícitos.
- **Por quê:** evitar erro de ponto flutuante e fechamento mensal ambíguo.

## ADR-005 — Sessão própria após Google OAuth

- **Status:** Aceita e implementada
- **Decisão:** Authorization Code + PKCE, `state` e `nonce`; cookie de sessão opaco, seguro e revogável, CSRF por double-submit e nenhum token em `localStorage`.
- **Por quê:** reduzir exposição de tokens e permitir revogação central.

## ADR-006 — FinancialProfile como boundary

- **Status:** Aceita
- **Decisão:** todo dado financeiro pertence a `PERSONAL` ou `BUSINESS`; “Tudo” é leitura consolidada.
- **Alternativa:** inferir perfil pela conta.
- **Por quê:** metas, bills, cenários e pagamentos também precisam de contexto, mesmo sem conta.

## ADR-007 — BankProvider desacoplado

- **Status:** Aceita
- **Decisão:** Pluggy/equivalente implementa um port canônico.
- **Por quê:** domínio não conhece códigos, tokens ou payloads do fornecedor.

## ADR-008 — Dramatiq + Redis sob demanda

- **Status:** Proposta
- **Decisão:** adicionar quando existir o primeiro job confiável de sincronização.
- **Alternativa:** Celery.
- **Por quê:** API menor e suficiente para o início; não criar fila sem consumidor real.

## ADR-009 — Python calcula, IA interpreta

- **Status:** Aceita
- **Decisão:** LLM usa tools tipadas; sem SQL, ORM ou cálculos financeiros críticos livres.
- **Por quê:** auditabilidade, precisão e impossibilidade de inventar valores.

## ADR-010 — Simulações são imutáveis e temporárias

- **Status:** Aceita
- **Decisão:** cenário referencia versão-base, expira e não altera estado real.
- **Por quê:** comparar alternativas sem efeitos colaterais.

## ADR-011 — Confirmação estruturada

- **Status:** Aceita
- **Decisão:** mudanças exibem antes/depois e exigem ação pendente válida, idempotente e expiráveis.
- **Por quê:** texto do chat não é autorização inequívoca.

## ADR-012 — Health Score explicável e versionado

- **Status:** Proposta
- **Decisão:** total, subescores, confiança e versão persistidos.
- **Por quê:** uma nota sem origem reduz confiança e impede comparação histórica correta.

## ADR-013 — Saldo Livre como métrica versionada

- **Status:** Aceita
- **Decisão:** API retorna total, horizonte e componentes; crédito disponível não conta como saldo.
- **Por quê:** saldo bancário isolado não representa capacidade de gasto.

## ADR-014 — BankProvider e PaymentProvider separados

- **Status:** Aceita
- **Decisão:** ports, credenciais e consentimentos independentes, mesmo com um fornecedor comum.
- **Por quê:** agregação e iniciação têm riscos e ciclos regulatórios diferentes.

## ADR-015 — Simulação antes de qualquer pagamento

- **Status:** Aceita
- **Decisão:** todo pagamento nasce de uma simulação imutável com impacto e risco calculados em Python.
- **Por quê:** diferencial do produto e barreira contra movimentação impulsiva/acidental.

## ADR-016 — IA nunca executa pagamentos

- **Status:** Aceita
- **Decisão:** não existe tool LLM `execute_payment`; o chat pode somente localizar e propor.
- **Por quê:** autoridade financeira permanece no usuário e no fluxo bancário autenticado.

## ADR-017 — Pagamentos múltiplos são orquestrados por item

- **Status:** Aceita
- **Decisão:** `Payment` agrega; cada `PaymentItem` pode gerar operação externa independente.
- **Por quê:** providers podem não suportar lote atômico e podem retornar sucesso parcial.

## ADR-018 — Idempotência e reconciliação de pagamento

- **Status:** Aceita
- **Decisão:** chave por operação/item; estado desconhecido exige consulta, nunca retry cego.
- **Por quê:** evitar débito duplicado.

## ADR-019 — Financial Inbox canônica

- **Status:** Proposta
- **Decisão:** várias fontes vinculam-se a um `Bill`; deduplicação mantém evidências e revisão.
- **Por quê:** não ocultar nem pagar cobranças duplicadas.

## ADR-020 — Integrações de alto risco sob feature flag

- **Status:** Aceita
- **Decisão:** pagamentos, Gmail, Open Finance e IA ficam desligáveis por ambiente/perfil.
- **Por quê:** rollout controlado, kill switch e separação entre implementado, sandbox e produção.

## Como alterar uma decisão

Uma mudança relevante cria novo ADR que substitui o anterior, explica evidências, migração e impacto. Não editar silenciosamente o histórico.
