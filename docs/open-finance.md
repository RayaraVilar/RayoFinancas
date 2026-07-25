# Open Finance

## Ports separados

`BankProvider` agrega dados. `PaymentProvider` inicia pagamentos. Um fornecedor pode implementar ambos, mas contratos, credenciais, consentimentos e métricas permanecem separados.

## BankProvider

- criar/revogar consentimento;
- listar instituições;
- sincronizar contas, saldos, cartões e transações;
- cursor/paginação;
- validar webhooks;
- health/status.

O adaptador converte payloads para DTOs canônicos. Pluggy/equivalente é a primeira implementação candidata, não uma dependência do domínio.

## Sincronização

```text
Consentimento → callback validado → job idempotente
→ contas → saldos → cartões/transações
→ normalização → dedupe → analytics
```

Webhooks são verificados, persistidos por chave idempotente e processados em worker. Reconciliação periódica cobre eventos perdidos.

## Consentimento

- finalidade, escopo, instituição, perfil e expiração visíveis;
- token efêmero no frontend;
- revogação local e no provider;
- estado/última atualização na UI;
- token persistido criptografado ou por referência de vault.

## Falhas

- backoff com jitter;
- erro de autenticação pede reconexão;
- rate limits respeitados;
- provider indisponível não apaga dados existentes;
- sandbox e fixtures sanitizadas;
- implementação identificada como `MOCK`, `SANDBOX`, `PENDENTE DE CREDENCIAL` ou `PRODUÇÃO`.
