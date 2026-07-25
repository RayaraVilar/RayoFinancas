# Rayo Finanças

> Estado atual: etapas funcionais 1–10, simulação segura de pagamentos e núcleo PJ
> implementados. Integrações que exigem credenciais, aprovação regulatória ou
> validação independente permanecem explicitamente bloqueadas. Consulte
> [o estado verificável](./docs/implementation-status.md).

Aplicação de gestão financeira pessoal orientada a decisões. O repositório começa como um monólito modular com frontend Next.js e backend FastAPI.

## Estado atual

O produto cobre identidade, ledger, Open Finance/Pluggy, analytics, Saldo Livre,
planejamento, metas, dívidas, projeções, Health Score, insights, simulação segura de
pagamentos e fluxos PJ. O dashboard oferece cadastro e leitura desses domínios.

A iniciação real de pagamentos permanece desativada por feature flag e kill switch.
O assistente possui registry somente de leitura/simulação; chamadas por LLM dependem
de credencial e aprovação de privacidade. Gmail permanece `DESIGN_ONLY`.

Evidências e bloqueios externos estão em
[`docs/implementation-status.md`](./docs/implementation-status.md).

## Requisitos

- Node.js 20.9 ou superior;
- Python 3.12 ou superior;
- Docker com Compose.

## Executar tudo com Docker

```bash
docker compose up --build
```

Serviços:

- Web: <http://localhost:3000>
- API health: <http://localhost:8000/api/v1/health>
- API readiness: <http://localhost:8000/api/v1/ready>
- OpenAPI: <http://localhost:8000/docs>

Os valores do `compose.yaml` são exclusivos para desenvolvimento local.

## Configurar login Google

Crie um cliente OAuth do tipo aplicação web no Google Cloud e registre:

```text
http://localhost:8000/api/v1/auth/google/callback
```

Copie `.env.example` para `.env` e preencha `RAYO_GOOGLE_CLIENT_ID` e
`RAYO_GOOGLE_CLIENT_SECRET`. Sem esses valores, a tela de login permanece
disponível e informa corretamente “Pendente de credencial”, sem simular autenticação.

O backend solicita apenas `openid email profile`. Tokens Google não são persistidos:
após validar o ID token, a Rayo cria sua própria sessão opaca.

## Executar sem Docker

### API

```bash
cd apps/api
python -m venv .venv
# PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m alembic upgrade head
uvicorn app.main:app --reload
```

Para o readiness check ficar saudável, inicie PostgreSQL e defina `RAYO_DATABASE_URL` conforme `.env.example`.

### Web

```bash
cd apps/web
npm install
npm run dev
```

No Windows com execução de scripts PowerShell desabilitada, use `npm.cmd` no lugar de `npm`.

## Qualidade

```bash
# Frontend
cd apps/web
npm run lint
npm run typecheck
npm run build

# Backend
cd apps/api
python -m ruff check .
python -m ruff format --check .
python -m mypy app
python -m pytest
```

O teste de integração com PostgreSQL é ativado com `RAYO_RUN_INTEGRATION=1`.

## Documentação

- [Plano de produto e arquitetura](./plan.md)
- [Backlog incremental](./todo.md)
- [Decisões técnicas](./decisions.md)
- [Arquitetura](./docs/architecture.md)
- [Banco de dados](./docs/database.md)
- [Segurança](./docs/security.md)
- [IA](./docs/ai.md)
- [Open Finance](./docs/open-finance.md)
- [Pagamentos](./docs/payments.md)
- [Estado de implementação](./docs/implementation-status.md)
- [Mapa de dados e LGPD](./docs/data-map-lgpd.md)
- [Threat model](./docs/threat-model.md)
- [Operação e runbooks](./docs/operations.md)
