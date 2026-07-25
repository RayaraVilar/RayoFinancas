# Threat model resumido

Ativos críticos: sessão, dados financeiros, consentimentos, propostas e pagamentos.
Fronteiras: navegador/API, API/PostgreSQL, API/Redis-worker e providers externos.

| Ameaça | Controle | Validação pendente |
|---|---|---|
| IDOR | ownership e contexto explícito | pentest |
| sessão roubada | token opaco com hash, rotação e revogação | adversarial |
| CSRF | double-submit em mutações | DAST |
| replay/webhook | assinatura e idempotência | sandbox real |
| duplicidade | chaves canônicas, locks e versões | concorrência |
| prompt injection | conteúdo não confiável e allowlist | evals LLM |
| pagamento indevido | sem tool na IA, kill switch e sem provider | threat model ITP |
| vazamento | logs sem payload e `no-store` | revisão operacional |
| abuso | limite por IP/classe | gateway distribuído |

O rate limiter em memória serve ao desenvolvimento. Produção exige limite
distribuído no gateway/Redis e política por conta.
