# Arquitetura de IA

## Regra central

**Python calcula. IA interpreta.**

```text
Usuário → Orquestrador → Tool Registry → Serviços de domínio → PostgreSQL
                      ↘ LLM para linguagem ↗
```

O modelo não recebe SQL, ORM, tokens bancários nem acesso genérico a dados.
O Gemini recebe somente resumos necessários à pergunta após ação explícita do usuário.
Conversas não são persistidas pela Rayo.

## Contexto

Toda tool recebe `UserScope` e `FinancialContext` validados pelo backend. Perguntas na visão Pessoal usam apenas PF. Comparações entre perfis exigem intenção explícita e autorização.
Cada usuário cadastra sua própria chave Gemini. Ela é criptografada no banco, nunca é
devolvida pela API e é removida junto da solicitação de exclusão da conta. Não existe
chave Gemini global no deploy público.

## Tools

Leitura: saldos, Saldo Livre, renda, despesas, categorias, bills, recebíveis, dívidas, metas, orçamento, cartão, score e projeção.

Simulação: compra, meta, dívida, perda de renda, pagamento e comparação de contas pagadoras.

Proposição: mudança de plano/orçamento/meta ou proposta de pagamento.

Não existe tool `execute_payment`.

## Ações

1. IA interpreta a intenção.
2. Backend encontra dados e calcula.
3. IA explica fatos, estimativas e premissas.
4. Mudança cria ação pendente com antes/depois.
5. Pagamento cria somente simulação/proposta.
6. UI estruturada obtém confirmação; pagamento segue autenticação bancária.

## Guardrails e evals

- allowlist e Pydantic estrito;
- insuficiência declarada;
- redaction e limite de período/linhas;
- prompt injection em transações/email tratada como conteúdo não confiável;
- auditoria de tool/versão/latência;
- evals de invenção, contexto PF/PJ, tool selection, confirmação e exfiltração;
- preferências/memória somente quando explicitamente confirmadas;
- sugestões proativas desligáveis.
