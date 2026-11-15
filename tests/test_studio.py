import pytest

import server
from server import app, clean_storyboard


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


def test_clean_storyboard_keeps_only_safe_text():
    result = clean_storyboard({
        "title": "Promo",
        "scenes": [
            {"kicker": "Intro", "title": "<strong>Bienvenue</strong>", "subtitle": "Découvrez"},
            {"kicker": "Offre", "title": "Collection", "subtitle": "Disponible"},
            {"kicker": "Fin", "title": "Commandez", "subtitle": "Maintenant"},
        ],
    })
    assert len(result["scenes"]) == 3
    assert "<" not in result["scenes"][0]["title"]
    assert "Bienvenue" in result["scenes"][0]["title"]


def test_clean_storyboard_rejects_too_few_scenes():
    with pytest.raises(ValueError):
        clean_storyboard({"title": "Promo", "scenes": [{"title": "Une seule"}]})


def test_studio_health_does_not_expose_secrets(client, monkeypatch):
    monkeypatch.setattr(server, "VIDEO_RENDERER_URL", "https://renderer.example")
    monkeypatch.setattr(server, "VIDEO_RENDERER_TOKEN", "private-token")
    monkeypatch.setattr(server, "VIDEO_STUDIO_CODE", "private-code")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-private")
    response = client.get("/studio/health")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["configured"] is True
    assert "private-token" not in response.get_data(as_text=True)
    assert "private-code" not in response.get_data(as_text=True)
    assert "gemini-private" not in response.get_data(as_text=True)


def test_studio_generation_is_disabled_without_studio_code(client, monkeypatch):
    monkeypatch.setattr(server, "VIDEO_STUDIO_CODE", "")
    response = client.post("/studio/videos", json={"prompt": "Une publicité"})
    assert response.status_code == 503
    assert "désactivé" in response.get_json()["erreur"]


def test_client_ip_uses_nearest_proxy_not_leftmost_forwarded_value(client, monkeypatch):
    captured = {}
    monkeypatch.setattr(server, "rate_limited", lambda ip: captured.setdefault("ip", ip) and False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    client.post(
        "/commande",
        json={"texte": "Bonjour"},
        headers={"X-Forwarded-For": "198.51.100.77, 203.0.113.9"},
        environ_base={"REMOTE_ADDR": "10.0.0.5"},
    )
    assert captured["ip"] == "203.0.113.9"


def test_studio_page_is_available(client):
    response = client.get("/studio")
    assert response.status_code == 200
    assert b"Studio Motion Design" in response.data
