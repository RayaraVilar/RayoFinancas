# Segurança e privacidade

## Princípios

- menor privilégio e minimização;
- isolamento por usuário e perfil financeiro;
- nenhum segredo em código/log;
- nenhum armazenamento de senha bancária;
- simulação separada de execução;
- autorização explícita e autenticada;
- conteúdo externo é não confiável.

## Controles

- TLS e cookies `HttpOnly/Secure` em ambientes não locais;
- Authorization Code + PKCE, `state`, `nonce` e validação do ID token Google;
- sessão opaca com apenas hash no banco, expiração, rotação e revogação;
- CSRF por cookie + header vinculados à sessão;
- CSP, CORS restrito e rate limiting antes da exposição pública;
- validação contra SQL injection, XSS, SSRF e webhook replay;
- tokens de providers com envelope encryption/KMS;
- logs por allowlist e redaction;
- auditoria de login, conexão, mudança, simulação, autorização, pagamento e falha;
- backups criptografados e restore testado;
- scans de dependência, segredo e imagem.

## Identidade e isolamento

- o escopo autenticado nasce da sessão e do usuário ativo no banco;
- toda consulta financeira filtra `user_id` e valida a propriedade do `FinancialProfile`;
- “Tudo” é apenas contexto de leitura; não remove o vínculo de origem;
- a API responde `404` ao tentar selecionar perfil de outro usuário;
- testes de integração cobrem CSRF, onboarding e acesso cruzado/IDOR;
- consentimento de privacidade é versionado e auditado;
- credenciais e tokens Google nunca entram em logs ou tabelas de domínio.
- access logs HTTP ficam desativados no container para não registrar códigos OAuth presentes no callback;
- falhas OAuth são registradas somente por categoria segura, sem código, token ou payload do Google.
- chaves Gemini pertencem ao usuário, ficam criptografadas e nunca são devolvidas;
- a demonstração usa identidade isolada, dados fictícios e bloqueia integrações externas.

## Pagamentos

- feature flag desligada por padrão;
- hash imutável do resumo autorizado;
- expiração e idempotency key;
- autenticação bancária/SCA no provider;
- nenhuma tool de execução para o LLM;
- falha/timeout vira reconciliação;
- confirmação específica para mistura PF/PJ;
- limites transacionais e step-up auth definidos antes de produção.

## Gmail/Financial Inbox

- consentimento separado e escopo mínimo;
- links/anexos/texto tratados como dados hostis;
- nenhuma instrução contida em email alcança tools;
- cobrança é candidata até validação;
- phishing controls e confirmação humana.

## LGPD

Manter inventário de dados/finalidade, base legal, retenção, operadores, exportação, revogação e exclusão. Open Finance, Gmail, IA e pagamentos têm consentimentos distintos. Revisão jurídica, threat model e pentest são gate de beta pública/pagamentos.
