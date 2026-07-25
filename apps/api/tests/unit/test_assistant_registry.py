from app.modules.assistant.registry import assistant_tools


def test_assistant_registry_is_read_or_simulate_only() -> None:
    tools = assistant_tools()
    names = {tool.name for tool in tools}

    assert tools
    assert {tool.mode for tool in tools} <= {"READ", "SIMULATE"}
    assert not names.intersection({"execute_payment", "initiate_payment", "send_pix", "pay_bill"})
    assert "simulate_payment" in names
