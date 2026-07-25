from app.cli.register_pluggy_webhook import _webhook_rows


def test_webhook_rows_supports_known_list_shapes() -> None:
    row = {"id": "one", "event": "all"}

    assert _webhook_rows([row]) == [row]
    assert _webhook_rows({"results": [row]}) == [row]
    assert _webhook_rows({"webhooks": [row]}) == [row]
    assert _webhook_rows({"data": [row]}) == [row]
    assert _webhook_rows({"data": "invalid"}) == []
