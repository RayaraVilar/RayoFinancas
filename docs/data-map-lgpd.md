# Mapa de dados e ciclo LGPD

| Domínio | Dados | Finalidade |
|---|---|---|
| Identidade | nome, email, avatar, identificador Google | acesso |
| Financeiro | contas, transações, faturas, metas e dívidas | gestão financeira |
| Open Finance | identificadores externos e estado de sync | sincronização consentida |
| Empresa | recebíveis, assinaturas e caixa | planejamento PJ |
| Auditoria | ação, alvo, resultado e request ID | segurança |

Tokens, códigos OAuth, barcodes, chaves Pix e conteúdo bruto de email não devem
aparecer em logs.

## Direitos implementados

- `GET /api/v1/privacy/export`: JSON versionado e sem cache;
- `POST /api/v1/privacy/delete-account`: bloqueia a conta e revoga sessões,
  consentimentos bancários e de email;
- exclusão física deve seguir job e prazo de retenção aprovados.

A organização ainda deve aprovar controlador/operadores, prazos, canal do titular,
transferência internacional, RIPD/DPIA e contratos. Isto não substitui revisão jurídica.
