# Deploy com HTTPS, Google OAuth e Pluggy

Este blueprint é neutro para qualquer VPS Linux com Docker Compose. Ele não substitui
secret manager, backup gerenciado, observabilidade ou revisão de segurança.

## Deploy no Render

O arquivo `render.yaml` cria PostgreSQL, Key Value, API, worker e frontend. No
Render, escolha **New → Blueprint** e conecte este repositório. Preencha:

```text
RAYO_FRONTEND_URL=https://rayo-web.onrender.com
RAYO_PUBLIC_API_URL=https://rayo-api.onrender.com
RAYO_GOOGLE_REDIRECT_URI=https://rayo-api.onrender.com/api/v1/auth/google/callback
INTERNAL_API_URL=https://rayo-api.onrender.com
PUBLIC_API_URL=https://rayo-api.onrender.com
```

Além das credenciais Google e Pluggy solicitadas. Se o Render acrescentar um sufixo
ao hostname, use exatamente a URL exibida no painel.

O worker usa plano `starter`, porque background workers não aceitam plano gratuito.
Revise custos antes de aplicar o Blueprint. API e worker ficam na mesma região do
banco/Key Value. O Render fornece PostgreSQL como `postgresql://`; a configuração
da API normaliza esse esquema para `postgresql+asyncpg://`.

Se preferir criar serviços manualmente:

```text
Backend Root Directory: apps/api
Frontend Root Directory: apps/web
Worker Root Directory: apps/api
```

### Testar sem gastar builds a cada commit

Os serviços Git do Blueprint usam `autoDeployTrigger: off`. Assim, commits e
pushes não iniciam builds automaticamente no Render.

Fluxo recomendado:

1. Desenvolva e valide localmente com Docker Compose.
2. Faça commits e pushes normalmente.
3. Quando uma versão estiver estável, abra o serviço no Render e use
   **Manual Deploy > Deploy latest commit**.

Se os serviços já existiam antes dessa configuração, confirme em cada um:
**Settings > Build & Deploy > Auto-Deploy > Off**.

Isso evita builds automáticos, mas não interrompe a cobrança de instâncias pagas
que estejam em execução. Neste Blueprint, `rayo-api` e `rayo-bank-worker` usam o
plano `starter`; frontend, PostgreSQL e Key Value usam planos gratuitos.

## 1. Domínios e servidor

Crie registros DNS públicos apontando para o servidor:

```text
app.seudominio.com  -> frontend
api.seudominio.com  -> API, Google callback e webhook Pluggy
```

Libere as portas 80 e 443. O Caddy obtém e renova TLS automaticamente.

## 2. Segredos

No servidor:

```bash
cp .env.production.example .env.production
chmod 600 .env.production
```

Troque todos os valores de exemplo. `RAYO_DATABASE_URL` deve usar a mesma senha de
`POSTGRES_PASSWORD`. Mantenha iniciação de pagamentos falsa e o kill switch verdadeiro.

## 3. Subida

```bash
docker compose \
  --env-file .env.production \
  -f compose.production.yaml \
  up -d --build
```

Verifique:

```bash
docker compose --env-file .env.production -f compose.production.yaml ps
curl -fsS https://api.seudominio.com/api/v1/ready
curl -fsS https://app.seudominio.com/
```

## 4. Google Cloud

No cliente OAuth Web, adicione exatamente:

```text
https://api.seudominio.com/api/v1/auth/google/callback
```

Mantenha o callback localhost se ainda usar desenvolvimento local. Configure a
homepage, os Termos e a Política de Privacidade no domínio verificado.

## 5. Webhook Pluggy

Depois que a API pública responder com HTTPS, registre ou atualize o webhook:

```bash
docker compose \
  --env-file .env.production \
  -f compose.production.yaml \
  exec -T api python -m app.cli.register_pluggy_webhook
```

O comando cria um webhook `all` em:

```text
https://api.seudominio.com/api/v1/webhooks/pluggy
```

Ele configura `X-Rayo-Webhook-Secret` sem imprimir o segredo. O endpoint persiste o
evento idempotente, responde `202` imediatamente e delega sincronização ao worker.

## 6. Smoke test e rollback

Antes de liberar usuários, confirme login, conexão sandbox, webhook, sync, revogação
e isolamento PF/PJ. Para rollback, volte ao commit/imagem anterior; não reverta
migrations destrutivamente. Restaure banco apenas em ambiente isolado e conforme o
runbook em `docs/operations.md`.

## Pendências externas

- host, domínio e DNS;
- secret manager e backup gerenciado;
- staging separado;
- logs/métricas/alertas gerenciados;
- pentest, DPIA/LGPD, carga e WCAG;
- provider/ITP e aprovação formal antes de pagamentos.
