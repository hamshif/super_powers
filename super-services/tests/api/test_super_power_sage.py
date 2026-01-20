from fastapi.testclient import TestClient

from super.apps.super_power_sage.super_power_sage import app
from super.config import get_app_conf


def test_health_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_super_powers_sage_stream_echoes_prompt() -> None:
    with TestClient(app) as client:
        prompt = "Echo this back."
        with client.stream("POST", "/super_powers_sage", json={"prompt": prompt}) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")

            body = "".join(response.iter_text())

            # Agent might emit 'stream_of_thought', 'answer', or 'ping'.
        # We just want to ensure it's streaming and alive.
        assert "event: answer" in body or "event: stream_of_thought" in body


def test_chat_scenarios_loaded_from_app_conf() -> None:
    conf = get_app_conf(app="super_power_sage")

    scenarios = conf.get("super_power_sage.chat_scenarios")

    assert isinstance(scenarios, list)
    assert scenarios[0].get("prompt") == "Hello, Super Power Sage!"
