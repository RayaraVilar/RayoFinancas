from pathlib import Path

import yaml


def test_render_blueprint_wires_required_services_without_secrets() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    blueprint = yaml.safe_load((repository_root / "render.yaml").read_text(encoding="utf-8"))
    services = {service["name"]: service for service in blueprint["services"]}

    assert set(services) == {"rayo-api", "rayo-bank-worker", "rayo-redis", "rayo-web"}
    assert services["rayo-api"]["rootDir"] == "apps/api"
    assert services["rayo-web"]["rootDir"] == "apps/web"
    assert services["rayo-bank-worker"]["type"] == "worker"
    assert services["rayo-redis"]["type"] == "keyvalue"
    assert services["rayo-api"]["preDeployCommand"] == "alembic upgrade head"
    assert services["rayo-api"]["healthCheckPath"] == "/api/v1/ready"

    api_environment = {
        item["key"]: item for item in services["rayo-api"]["envVars"] if "key" in item
    }
    assert api_environment["RAYO_DATABASE_URL"]["fromDatabase"]["name"] == "rayo-db"
    assert api_environment["RAYO_PAYMENT_INITIATION_ENABLED"]["value"] == "false"
    assert api_environment["RAYO_PAYMENT_KILL_SWITCH"]["value"] == "true"
    for secret_name in (
        "RAYO_GOOGLE_CLIENT_SECRET",
        "RAYO_PLUGGY_CLIENT_ID",
        "RAYO_PLUGGY_CLIENT_SECRET",
    ):
        assert api_environment[secret_name] == {"key": secret_name, "sync": False}

    serialized = (repository_root / "render.yaml").read_text(encoding="utf-8")
    assert "replace-with" not in serialized
    assert "clientSecret:" not in serialized
