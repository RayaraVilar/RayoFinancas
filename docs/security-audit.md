# Auditoria de segurança para publicação

Atualizada em 25/07/2026. Esta revisão cobre o repositório e os controles
implementáveis localmente; não substitui pentest independente, DPIA ou revisão
jurídica.

## Resultado da varredura de segredos

- os 7 commits existentes foram pesquisados por padrões de chaves Google/Gemini,
  OpenAI, URLs PostgreSQL com senha e secrets OAuth;
- nenhum arquivo do histórico apresentou correspondência;
- `.env` não é rastreado pelo Git;
- `.env*` é excluído dos contextos Docker da API e do frontend;
- somente `.env.example` e `.env.production.example`, sem valores reais, são
  versionados;
- a aplicação não registra corpo de requisição, códigos OAuth, chaves Gemini ou
  tokens do Pluggy nos logs HTTP.

As credenciais que apareceram em capturas de tela durante a configuração devem ser
consideradas expostas fora do Git. Antes de abrir o produto ao público, rotacione:

1. senha/URL do PostgreSQL;
2. Google OAuth Client Secret;
3. Pluggy Client Secret e webhook secret;
4. `RAYO_SECRET_KEY`;
5. a chave Gemini anteriormente usada no ambiente.

Faça a rotação de `RAYO_SECRET_KEY` antes de usuários reais cadastrarem chaves
Gemini: ela encerra sessões existentes e torna credenciais pessoais já criptografadas
indecifráveis.

## Controles verificados no código

- sessão opaca: apenas o hash do token fica no PostgreSQL;
- cookie de sessão `HttpOnly`, `Secure` fora do ambiente local e `SameSite=Lax`;
- CSRF vinculado à sessão em todas as mutações autenticadas;
- Google OAuth com PKCE, state, nonce, issuer, audience e assinatura;
- proxy OAuth same-origin para que a sessão pertença ao domínio do frontend;
- CSP, HSTS em produção, `frame-ancestors 'none'`, anti-sniff, Referrer Policy e
  Permissions Policy;
- limites separados para autenticação, criação de demonstração, assistente e API;
- webhook Pluggy autenticado, hash idempotente e resposta assíncrona;
- isolamento obrigatório por `user_id` e `financial_profile_id`;
- chave Gemini por usuário, criptografada com Fernet e chave derivada do secret da
  aplicação;
- chave Gemini nunca é devolvida; somente a dica com quatro caracteres finais;
- exclusão de conta remove imediatamente a credencial do assistente;
- exportação LGPD informa apenas provider e dica, nunca o ciphertext;
- demonstrações recebem usuário e dados próprios, todos fictícios, e não podem
  conectar banco nem cadastrar credencial;
- pagamentos externos continuam desativados por feature flag e kill switch.

## Riscos residuais antes de divulgação ampla

- executar pentest independente e teste de carga;
- configurar backup gerenciado e testar restauração;
- configurar alertas, retenção e acesso aos logs do Render;
- concluir DPIA/revisão LGPD e publicar Termos/Política de Privacidade;
- revisar WCAG 2.2 AA com tecnologia assistiva e usuários;
- confirmar contrato, ambiente e limites do Pluggy;
- manter iniciação de pagamentos e Gmail desligados até aprovação específica.
