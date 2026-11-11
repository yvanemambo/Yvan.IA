import os

import pytest

os.environ.setdefault("MBO_CODE", "test-secret")
from server import app, safe_path


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/sante")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["provider"] == "Gemini"


def test_command_rejects_wrong_access_code(client, monkeypatch):
    monkeypatch.setenv("MBO_CODE", "test-secret")
    response = client.post(
        "/commande",
        json={"texte": "Bonjour"},
        headers={"X-Code": "wrong"},
    )
    assert response.status_code == 401


def test_command_requires_gemini_key(client, monkeypatch):
    monkeypatch.setenv("MBO_CODE", "test-secret")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    response = client.post(
        "/commande",
        json={"texte": "Bonjour"},
        headers={"X-Code": "test-secret"},
    )
    assert response.status_code == 503
    assert "GEMINI_API_KEY" in response.get_json()["erreur"]


def test_safe_path_rejects_parent_traversal():
    with pytest.raises(ValueError):
        safe_path("../secret.txt")
