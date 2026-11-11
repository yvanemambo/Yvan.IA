import os
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
import anthropic

BASE = Path(__file__).resolve().parent
DATA = (BASE / "dossier_mbo").resolve()
DRAFTS = DATA / "brouillons"
DRAFTS.mkdir(parents=True, exist_ok=True)

MODEL = os.getenv("MBO_MODEL", "claude-sonnet-4-5")
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024
histories = {}

SYSTEM = """Tu es MBO.IA, un assistant personnel qui répond en français.
Sois utile, clair et honnête. Ne prétends pas avoir effectué une action qui n'a pas été réalisée.
Tu peux consulter les fichiers autorisés et enregistrer des brouillons, mais tu n'envoies aucun e-mail."""

def safe_path(relative):
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError("Chemin manquant.")
    path = (DATA / relative).resolve()
    if path != DATA and DATA not in path.parents:
        raise ValueError("Chemin interdit.")
    return path

def run_tool(name, args):
    if name == "lister_dossier":
        path = safe_path(args.get("chemin", "."))
        if not path.is_dir():
            return "Ce dossier n'existe pas."
        return "\n".join(("[dossier] " if p.is_dir() else "") + p.name for p in sorted(path.iterdir())) or "(vide)"
    if name == "lire_fichier":
        path = safe_path(args.get("chemin", ""))
        if not path.is_file() or path.suffix.lower() not in {".txt", ".md", ".csv"}:
            return "Fichier absent ou format non autorisé (TXT, MD, CSV uniquement)."
        if path.stat().st_size > 2_000_000:
            return "Fichier trop volumineux (maximum 2 Mo)."
        return path.read_text(encoding="utf-8", errors="replace")[:10000]
    if name == "rediger_brouillon":
        recipient = str(args.get("destinataire", "")).strip()[:200]
        subject = str(args.get("objet", "")).strip()[:200]
        body = str(args.get("corps", "")).strip()[:10000]
        if not recipient or not subject or not body:
            return "Destinataire, objet et contenu sont obligatoires."
        target = DRAFTS / f"brouillon_{uuid.uuid4().hex[:10]}.txt"
        target.write_text(f"À : {recipient}\nObjet : {subject}\n\n{body}\n", encoding="utf-8")
        return f"Brouillon enregistré dans brouillons/{target.name}. Aucun e-mail n'a été envoyé."
    return "Outil inconnu."

TOOLS = [
    {"name":"lister_dossier","description":"Liste un dossier dans dossier_mbo.","input_schema":{"type":"object","properties":{"chemin":{"type":"string"}},"required":["chemin"]}},
    {"name":"lire_fichier","description":"Lit un fichier TXT, MD ou CSV dans dossier_mbo.","input_schema":{"type":"object","properties":{"chemin":{"type":"string"}},"required":["chemin"]}},
    {"name":"rediger_brouillon","description":"Enregistre un brouillon d'e-mail sans l'envoyer.","input_schema":{"type":"object","properties":{"destinataire":{"type":"string"},"objet":{"type":"string"},"corps":{"type":"string"}},"required":["destinataire","objet","corps"]}}
]

@app.get("/")
def home():
    return send_from_directory(BASE, "index.html")

@app.get("/sante")
def health():
    return jsonify(status="ok", app="MBO.IA", model=MODEL)

@app.post("/commande")
def command():
    access_code = os.getenv("MBO_CODE", "")
    if not access_code:
        return jsonify(erreur="Configure MBO_CODE dans les variables d'environnement."), 503
    if request.headers.get("X-Code", "") != access_code:
        return jsonify(erreur="Code d'accès incorrect."), 401
    data = request.get_json(silent=True) or {}
    prompt = data.get("texte")
    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify(erreur="Écris un message avant d'envoyer."), 400
    if len(prompt) > 8000:
        return jsonify(erreur="Message trop long (maximum 8 000 caractères)."), 413
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return jsonify(erreur="La clé ANTHROPIC_API_KEY n'est pas configurée."), 503
    conversation = request.headers.get("X-Conversation-ID", "default")[:80]
    messages = histories.setdefault(conversation, [])[-16:] + [{"role":"user","content":prompt.strip()}]
    try:
        client = anthropic.Anthropic(api_key=api_key, timeout=45, max_retries=2)
        for _ in range(6):
            response = client.messages.create(model=MODEL, max_tokens=1400, system=SYSTEM, tools=TOOLS, messages=messages)
            if response.stop_reason != "tool_use":
                answer = "\n".join(block.text for block in response.content if getattr(block, "type", "") == "text").strip()
                if not answer:
                    answer = "Je n'ai pas reçu de réponse exploitable. Réessaie."
                histories[conversation] = (messages + [{"role":"assistant","content":answer}])[-16:]
                return jsonify(reponse=answer)
            messages.append({"role":"assistant","content":response.content})
            results = []
            for block in response.content:
                if getattr(block, "type", "") == "tool_use":
                    try:
                        output = run_tool(block.name, block.input)
                    except Exception as exc:
                        output = f"Action impossible : {exc}"
                    results.append({"type":"tool_result","tool_use_id":block.id,"content":output})
            messages.append({"role":"user","content":results})
        return jsonify(erreur="La demande a dépassé le nombre d'étapes autorisé. Reformule-la."), 502
    except anthropic.AuthenticationError:
        return jsonify(erreur="Clé API Anthropic invalide. Vérifie ANTHROPIC_API_KEY."), 502
    except anthropic.APIConnectionError:
        app.logger.exception("Connexion Anthropic impossible")
        return jsonify(erreur="Connexion au service IA impossible. Vérifie Internet."), 502
    except anthropic.APIStatusError as exc:
        app.logger.exception("Erreur API Anthropic")
        return jsonify(erreur=f"Erreur du service IA (HTTP {exc.status_code}). Vérifie le modèle et ta clé API."), 502
    except Exception:
        app.logger.exception("Erreur inattendue MBO.IA")
        return jsonify(erreur="Une erreur inattendue est survenue. Consulte le terminal du serveur."), 500

if __name__ == "__main__":
    print("MBO.IA : ouvre http://127.0.0.1:5000 sur cet ordinateur.")
    print("Pour un téléphone, utilise l'adresse IP locale de cet ordinateur sur le même Wi-Fi.")
    app.run(host="0.0.0.0", port=5000, debug=False)
