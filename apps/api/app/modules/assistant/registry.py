from __future__ import annotations

from app.modules.assistant.schemas import AssistantToolDescriptor

TOOL_REGISTRY = (
    AssistantToolDescriptor(
        name="get_dashboard_metrics",
        purpose="Ler métricas calculadas, cobertura e confiança.",
        mode="READ",
    ),
    AssistantToolDescriptor(
        name="get_free_balance",
        purpose="Ler saldo livre, compromissos e premissas.",
        mode="READ",
    ),
    AssistantToolDescriptor(
        name="list_bills",
        purpose="Ler contas e seus estados sem alterá-las.",
        mode="READ",
    ),
    AssistantToolDescriptor(
        name="list_goals",
        purpose="Ler metas, progresso e ritmo.",
        mode="READ",
    ),
    AssistantToolDescriptor(
        name="simulate_goal",
        purpose="Comparar cenários de meta sem mutação.",
        mode="SIMULATE",
    ),
    AssistantToolDescriptor(
        name="list_debts",
        purpose="Ler dívidas e qualidade dos dados.",
        mode="READ",
    ),
    AssistantToolDescriptor(
        name="simulate_debt",
        purpose="Simular amortização e pagamentos adicionais.",
        mode="SIMULATE",
    ),
    AssistantToolDescriptor(
        name="get_future",
        purpose="Ler patrimônio, projeções e score versionado.",
        mode="READ",
    ),
    AssistantToolDescriptor(
        name="list_insights",
        purpose="Ler recomendações determinísticas e evidências.",
        mode="READ",
    ),
    AssistantToolDescriptor(
        name="simulate_payment",
        purpose="Simular pagamentos sem iniciar movimentação externa.",
        mode="SIMULATE",
    ),
)


def assistant_tools() -> list[AssistantToolDescriptor]:
    tools = list(TOOL_REGISTRY)
    forbidden = {"execute_payment", "initiate_payment", "send_pix", "pay_bill"}
    if forbidden.intersection(tool.name for tool in tools):
        raise RuntimeError("Assistant registry contains a forbidden payment execution tool.")
    return tools
