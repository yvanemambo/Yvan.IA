import os

import pytest

os.environ.setdefault("MBO_CODE", "test-secret")
from server import (
    MAX_HISTORY_CHARS,
    app,
    clean_history,
    lire_fichier,
    safe_path,
)


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


def test_health_reports_missing_configuration(client, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("MBO_CODE", raising=False)
    response = client.get("/sante")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["provider"] == "Gemini"
    assert payload["ready"] is False
    assert payload["gemini_configured"] is False
    assert payload["access_configured"] is False


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


def test_clean_history_is_bounded():
    history = [
        {"role": "user", "text": "A" * 4000}
        for _ in range(16)
    ]
    cleaned = clean_history(history)
    assert len(cleaned) <= 16
    assert sum(len(item["text"]) for item in cleaned) <= MAX_HISTORY_CHARS


def test_text_file_reader(tmp_path, monkeypatch):
    import server

    monkeypatch.setattr(server, "DATA", tmp_path)
    (tmp_path / "note.txt").write_text("Bonjour Yvan.IA", encoding="utf-8")
    assert lire_fichier("note.txt") == "Bonjour Yvan.IA"


def test_reader_rejects_unsupported_file(tmp_path, monkeypatch):
    import server

    monkeypatch.setattr(server, "DATA", tmp_path)
    (tmp_path / "script.py").write_text("print('no')", encoding="utf-8")
    assert "format non autorisé" in lire_fichier("script.py")
