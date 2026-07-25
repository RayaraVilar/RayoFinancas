# Pagamentos

## Não negociáveis

1. Simulação antes da movimentação.
2. Autorização explícita.
3. Backend calcula; IA explica.
4. IA nunca movimenta dinheiro autonomamente.
5. Aplicação não custodia recursos.

## Jornada

```text
Selecionar bills
→ Simular
→ Escolher/comparar conta pagadora
→ Ver saldo, compromissos, Saldo Livre e risco
→ Revisar resumo exato
→ Autorizar
→ Autenticar no banco/ITP
→ Processar/reconciliar
→ Exibir comprovante e atualizar projeções
```

“Simular” e “Continuar para pagamento” são ações distintas. Pedido pelo chat termina em proposta revisável.

## Estados

`DRAFT`, `SIMULATED`, `AWAITING_AUTHORIZATION`, `AUTHORIZED`, `PROCESSING`, `SUCCEEDED`, `PARTIALLY_SUCCEEDED`, `FAILED`, `UNKNOWN`, `EXPIRED`, `CANCELLED`.

Cada item mantém seu próprio estado. `Bill` só vira `PAID` após confirmação/reconciliação do provider.

## Autorização

- usuário, itens, valores, conta pagadora, perfil e premissas;
- hash do resumo;
- expiração;
- autenticação step-up quando necessário;
- qualquer alteração invalida a autorização;
- mistura PF/PJ exige alerta e confirmação adicional.

## Idempotência

- chave por comando e `PaymentItem`;
- webhook com dedupe/replay protection;
- timeout não significa falha;
- estado `UNKNOWN` chama status/reconciliação;
- nunca repetir uma operação externa sem evidência segura.

## Pagamento múltiplo

Um lote Rayo pode virar várias operações externas. O orquestrador:

- consulta capacidades do provider;
- cria itens;
- acompanha sucesso parcial;
- preserva comprovante por item;
- apresenta total efetivamente pago e itens pendentes/falhos.

## Gate de produção

- provider/ITP e termos regulatórios aprovados;
- threat model e pentest;
- testes de autorização, idempotência, replay, falha parcial e reconciliação;
- limites, alertas, suporte e runbook;
- feature flag e kill switch;
- auditoria e observabilidade sem dados sensíveis.
