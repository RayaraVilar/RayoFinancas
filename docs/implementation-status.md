# Estado de implementação

Atualizado em 24/07/2026. Este documento separa código verificável de dependências
externas e de validações operacionais que não podem ser simuladas.

## Entregue e validado localmente

- identidade, onboarding, perfis Pessoal/Empresa, sessões, CSRF e isolamento;
- ledger, cartões, faturas, transferências, estornos, splits e regras;
- port Pluggy, consentimento, webhooks, sync assíncrono, dedupe e reconciliação;
- analytics, projeção, cobertura, confiança e explicações;
- contas a pagar, Saldo Livre, orçamento e planejamento mensal;
- metas, cenários, ações pendentes e confirmação idempotente;
- dívidas Price/SAC, snowball e avalanche;
- patrimônio, projeções, Health Score e insights versionados;
- registry do assistente limitado a leitura/simulação, sem ferramenta de pagamento;
- simulações imutáveis de pagamento e port de iniciação separado;
- recebíveis, assinaturas, calendário de caixa, Inbox com revisão humana e
  preferências de notificação para Empresa;
- exportação LGPD e exclusão com revogação de sessões/consentimentos;
- rate limiting, CSP, headers de segurança, request IDs e logs seguros.

As migrações `0001`–`0015`, lint, tipagem e a suíte PostgreSQL foram executados
localmente. O dashboard integra planejamento, futuro, metas, dívidas, insights,
simulações revisáveis e formulários PJ.

## Deliberadamente desativado

- iniciação real de pagamento: feature flag falsa, kill switch ativo e sem ITP;
- ingestão Gmail: `DESIGN_ONLY`, consentimento separado e revisão humana;
- chat LLM: allowlist pronta, mas chamadas bloqueadas sem `RAYO_OPENAI_API_KEY`.

## Dependências externas para aceite integral

1. Credenciais Pluggy sandbox para teste real do provider.
2. Chave OpenAI e aprovação de privacidade/retenção para o adapter.
3. Provider/ITP, análise regulatória, threat model e pentest para pagamentos.
4. Secret manager, staging, observabilidade e pipeline do ambiente escolhido.
5. DPIA/LGPD, pentest independente, restauração, carga, WCAG e beta com usuários.

Nenhum desses itens é declarado concluído por configuração local ou mock.
