import hmac
import os
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from google import genai
from google.genai import types

BASE = Path(__file__).resolve().parent
DATA = (BASE / "dossier_mbo").resolve()
PUBLIC = BASE / "public"
IS_VERCEL = os.getenv("VERCEL") == "1"
DRAFTS = (Path("/tmp/yvan-ia/brouillons") if IS_VERCEL else DATA / "brouillons").resolve()
DRAFTS.mkdir(parents=True, exist_ok=True)

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
MAX_CONVERSATIONS = 200
MAX_HISTORY_MESSAGES = 16

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024
histories = {}

SYSTEM = """Tu es Yvan.IA, un assistant personnel qui répond en français.
Sois utile, clair et honnête. Ne prétends pas avoir effectué une action qui n'a pas été réalisée.
Tu peux consulter les fichiers autorisés et enregistrer des brouillons, mais tu n'envoies aucun e-mail."""

def safe_path(relative):
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError("Chemin manquant.")
    path = (DATA / relative).resolve()
    if path != DATA and DATA not in path.parents:
        raise ValueError("Chemin interdit.")
    return path

def lister_dossier(chemin: str) -> str:
    """Liste les fichiers et sous-dossiers d'un chemin situé dans dossier_mbo. Utilise '.' pour la racine."""
    path = safe_path(chemin)
    if not path.is_dir():
        return "Ce dossier n'existe pas."
    entries = sorted(path.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
    return "\n".join(("[dossier] " if item.is_dir() else "") + item.name for item in entries) or "(vide)"

def lire_fichier(chemin: str) -> str:
    """Lit le contenu d'un fichier TXT, MD ou CSV situé dans dossier_mbo."""
    path = safe_path(chemin)
    if not path.is_file() or path.suffix.lower() not in {".txt", ".md", ".csv"}:
        return "Fichier absent ou format non autorisé (TXT, MD, CSV uniquement)."
    if path.stat().st_size > 2_000_000:
        return "Fichier trop volumineux (maximum 2 Mo)."
    return path.read_text(encoding="utf-8", errors="replace")[:10000]

def rediger_brouillon(destinataire: str, objet: str, corps: str) -> str:
    """Enregistre un brouillon d'e-mail sans l'envoyer. Demande le destinataire, l'objet et le corps."""
    recipient = str(destinataire).strip()[:200]
    subject = str(objet).strip()[:200]
    body = str(corps).strip()[:10000]
    if not recipient or not subject or not body:
        return "Destinataire, objet et contenu sont obligatoires."
    target = DRAFTS / f"brouillon_{uuid.uuid4().hex[:10]}.txt"
    target.write_text(f"À : {recipient}\nObjet : {subject}\n\n{body}\n", encoding="utf-8")
    if IS_VERCEL:
        return "Brouillon créé temporairement. Vercel ne conserve pas ce fichier durablement."
    return f"Brouillon enregistré dans brouillons/{target.name}. Aucun e-mail n'a été envoyé."

GEMINI_TOOLS = [lister_dossier, lire_fichier, rediger_brouillon]

@app.get("/")
def home():
    return send_from_directory(PUBLIC, "index.html")

@app.get("/sante")
def health():
    return jsonify(status="ok", app="Yvan.IA", provider="Gemini", model=MODEL or "non configuré", platform="Vercel" if IS_VERCEL else "local")

@app.post("/commande")
def command():
    access_code = os.getenv("MBO_CODE", "")
    if not access_code:
        return jsonify(erreur="Configure MBO_CODE dans les variables d'environnement Vercel."), 503
    if not hmac.compare_digest(request.headers.get("X-Code", ""), access_code):
        return jsonify(erreur="Code d'accès incorrect."), 401

    data = request.get_json(silent=True) or {}
    prompt = data.get("texte")
    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify(erreur="Écris un message avant d'envoyer."), 400
    prompt = prompt.strip()
    if len(prompt) > 8000:
        return jsonify(erreur="Message trop long (maximum 8 000 caractères)."), 413

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return jsonify(erreur="La clé GEMINI_API_KEY n'est pas configurée dans Vercel."), 503
    if not MODEL:
        return jsonify(erreur="Configure GEMINI_MODEL avec un modèle Gemini valide."), 503

    raw_id = request.headers.get("X-Conversation-ID", "")
    try:
        conversation_id = str(uuid.UUID(raw_id))
    except (ValueError, TypeError, AttributeError):
        conversation_id = str(uuid.uuid4())

    if conversation_id not in histories and len(histories) >= MAX_CONVERSATIONS:
        histories.pop(next(iter(histories)))
    previous = histories.get(conversation_id, [])[-MAX_HISTORY_MESSAGES:]
    contents = [
        types.Content(role=item["role"], parts=[types.Part.from_text(text=item["text"])])
        for item in previous
    ]
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]))

    try:
        with genai.Client(api_key=api_key) as client:
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM,
                    tools=GEMINI_TOOLS,
                    max_output_tokens=1400,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        maximum_remote_calls=6
                    ),
                ),
            )
        answer = (response.text or "").strip()
        if not answer:
            answer = "Je n'ai pas reçu de réponse exploitable. Réessaie."
        histories[conversation_id] = (
            previous
            + [{"role": "user", "text": prompt}, {"role": "model", "text": answer}]
        )[-MAX_HISTORY_MESSAGES:]
        return jsonify(reponse=answer, conversation_id=conversation_id)

    except Exception as exc:
        app.logger.exception("Erreur Gemini")
        message = str(exc).lower()
        if "api_key_invalid" in message or "invalid api key" in message or "unauthorized" in message:
            return jsonify(erreur="Clé Gemini invalide. Vérifie GEMINI_API_KEY dans Vercel."), 502
        if "not_found" in message or "404" in message:
            return jsonify(erreur="Modèle Gemini introuvable. Vérifie GEMINI_MODEL dans Vercel."), 502
        return jsonify(erreur="Le service Gemini n'a pas pu répondre. Vérifie la clé, le modèle et les journaux Vercel."), 502

if __name__ == "__main__":
    print("Yvan.IA : ouvre http://127.0.0.1:5000 sur cet ordinateur.")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
