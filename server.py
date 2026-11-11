import hmac
import os
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from google import genai
from google.genai import types
from pypdf import PdfReader

BASE = Path(__file__).resolve().parent
DATA = (BASE / "dossier_mbo").resolve()
PUBLIC = BASE / "public"
IS_VERCEL = os.getenv("VERCEL") == "1"
PLATFORM = "Render" if os.getenv("RENDER") else ("Vercel" if IS_VERCEL else "local")
DRAFTS = (Path("/tmp/yvan-ia/brouillons") if IS_VERCEL else DATA / "brouillons").resolve()
DRAFTS.mkdir(parents=True, exist_ok=True)

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
MAX_HISTORY_MESSAGES = 16
MAX_HISTORY_CHARS = 24000
MAX_HISTORY_ITEM_CHARS = 4000
MAX_MESSAGE_LENGTH = 8000
RATE_WINDOW_SECONDS = 60
RATE_LIMIT = 20
requests_by_ip = defaultdict(deque)

# Compteurs temporaires du processus : ils repartent à zéro au redémarrage
# et ne représentent pas des statistiques globales ou persistantes.
metrics = {
    "started_at": datetime.now(timezone.utc).isoformat(),
    "requests": 0,
    "successes": 0,
    "errors": 0,
    "last_request_at": None,
    "last_error_at": None,
    "last_error": None,
}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 48 * 1024

SYSTEM = """Tu es Yvan.IA, un assistant personnel intelligent qui répond en français par défaut.
Tu es chaleureux, précis, pédagogique et honnête. Adapte la longueur de tes réponses à la demande.
Pour les sujets techniques, explique les étapes clairement et signale les limites ou incertitudes.
Ne prétends jamais avoir effectué une action externe que tu n'as pas réellement effectuée.
Tu peux consulter les fichiers autorisés dans dossier_mbo et préparer des brouillons d'e-mails.
Tu ne peux pas envoyer d'e-mails, accéder à l'ordinateur personnel de l'utilisateur, ni inventer le contenu d'un fichier.
Quand une demande est ambiguë, pose une seule question utile."""

def safe_path(relative):
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError("Chemin manquant.")
    path = (DATA / relative).resolve()
    if path != DATA and DATA not in path.parents:
        raise ValueError("Chemin interdit.")
    return path

def lister_dossier(chemin: str) -> str:
    """Liste les fichiers et sous-dossiers situés dans dossier_mbo.

    Args:
        chemin: Chemin relatif à dossier_mbo ; utiliser '.' pour la racine.
    """
    try:
        path = safe_path(chemin)
        if not path.is_dir():
            return "Ce dossier n'existe pas."
        entries = sorted(path.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
        return "\n".join(("[dossier] " if item.is_dir() else "") + item.name for item in entries) or "(vide)"
    except (OSError, ValueError) as exc:
        return f"Accès refusé : {exc}"

def lire_fichier(chemin: str) -> str:
    """Lit un fichier texte ou PDF situé dans dossier_mbo.

    Args:
        chemin: Chemin relatif du fichier dans dossier_mbo.
    """
    try:
        path = safe_path(chemin)
        if not path.is_file() or path.suffix.lower() not in {".txt", ".md", ".csv", ".pdf"}:
            return "Fichier absent ou format non autorisé (TXT, MD, CSV, PDF uniquement)."
        if path.stat().st_size > 5_000_000:
            return "Fichier trop volumineux (maximum 5 Mo)."
        if path.suffix.lower() == ".pdf":
            reader = PdfReader(str(path))
            if reader.is_encrypted:
                return "Ce PDF est protégé par mot de passe et ne peut pas être lu."
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return text[:12000] or "Aucun texte extractible dans ce PDF (il est peut-être scanné)."
        return path.read_text(encoding="utf-8", errors="replace")[:12000]
    except (OSError, ValueError) as exc:
        return f"Lecture impossible : {exc}"
    except Exception:
        return "Lecture impossible : le fichier est endommagé ou son format n'est pas pris en charge."

def rediger_brouillon(destinataire: str, objet: str, corps: str) -> str:
    """Prépare un brouillon d'e-mail sans l'envoyer.

    Args:
        destinataire: Adresse ou nom du destinataire.
        objet: Objet du message.
        corps: Texte complet du brouillon.
    """
    recipient = str(destinataire).strip()[:200]
    subject = str(objet).strip()[:200]
    body = str(corps).strip()[:10000]
    if not recipient or not subject or not body:
        return "Destinataire, objet et contenu sont obligatoires."
    draft = f"À : {recipient}\nObjet : {subject}\n\n{body}\n"
    if IS_VERCEL:
        return "Voici le brouillon prêt à copier (aucun e-mail envoyé) :\n" + draft
    target = DRAFTS / f"brouillon_{uuid.uuid4().hex[:10]}.txt"
    target.write_text(draft, encoding="utf-8")
    return f"Brouillon enregistré dans brouillons/{target.name}. Aucun e-mail n'a été envoyé."

GEMINI_TOOLS = [lister_dossier, lire_fichier, rediger_brouillon]

def rate_limited(ip):
    now = time.monotonic()
    bucket = requests_by_ip[ip]
    while bucket and now - bucket[0] > RATE_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT:
        return True
    bucket.append(now)
    return False

def clean_history(raw):
    if not isinstance(raw, list):
        return []
    cleaned = []
    remaining = MAX_HISTORY_CHARS
    for item in raw[-MAX_HISTORY_MESSAGES:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("text")
        if role not in {"user", "model"} or not isinstance(content, str):
            continue
        content = content.strip()
        if not content or remaining <= 0:
            continue
        content = content[-min(MAX_HISTORY_ITEM_CHARS, remaining):]
        cleaned.append({"role": role, "text": content})
        remaining -= len(content)
    return cleaned

def admin_authorized():
    admin_code = os.getenv("ADMIN_CODE", "").strip()
    supplied = request.headers.get("X-Admin-Code", "")
    return bool(admin_code and supplied and hmac.compare_digest(supplied, admin_code))

@app.after_request
def secure_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Frame-Options", "DENY")
    if request.path.startswith(("/commande", "/sante", "/admin")):
        response.headers["Cache-Control"] = "no-store"
    return response

@app.get("/")
def home():
    return send_from_directory(PUBLIC, "index.html")

@app.get("/admin")
def admin_page():
    return send_from_directory(PUBLIC, "admin.html")

@app.get("/sante")
def health():
    gemini_ready = bool(os.getenv("GEMINI_API_KEY", "").strip() and MODEL)
    access_ready = bool(os.getenv("MBO_CODE", "").strip())
    return jsonify(
        status="ok",
        app="Yvan.IA",
        provider="Gemini",
        model=MODEL,
        platform=PLATFORM,
        gemini_configured=gemini_ready,
        access_configured=access_ready,
        admin_configured=bool(os.getenv("ADMIN_CODE", "").strip()),
        ready=gemini_ready and access_ready,
    )

@app.get("/admin/metrics")
def admin_metrics():
    if not os.getenv("ADMIN_CODE", "").strip():
        return jsonify(erreur="Le tableau de bord n'est pas configuré. Ajoute ADMIN_CODE dans les variables d’environnement de Render."), 503
    if not admin_authorized():
        return jsonify(erreur="Code administrateur incorrect."), 401

    gemini_ready = bool(os.getenv("GEMINI_API_KEY", "").strip() and MODEL)
    return jsonify(
        app="Yvan.IA",
        provider="Gemini",
        model=MODEL,
        gemini_configured=gemini_ready,
        access_configured=bool(os.getenv("MBO_CODE", "").strip()),
        admin_configured=True,
        platform=PLATFORM,
        metrics=dict(metrics),
        metrics_scope="Ce processus uniquement : compteurs temporaires, remis à zéro lors d'un redémarrage ou d'un changement d'instance.",
    )

@app.post("/commande")
def command():
    access_code = os.getenv("MBO_CODE", "").strip()
    if not access_code:
        return jsonify(erreur="L'accès n'est pas encore configuré. Ajoute MBO_CODE dans les variables d’environnement de Render."), 503
    if not hmac.compare_digest(request.headers.get("X-Code", ""), access_code):
        return jsonify(erreur="Code d'accès incorrect."), 401
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    if rate_limited(ip):
        return jsonify(erreur="Trop de demandes en peu de temps. Attends une minute puis réessaie."), 429

    data = request.get_json(silent=True) or {}
    prompt = data.get("texte")
    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify(erreur="Écris un message avant d'envoyer."), 400
    prompt = prompt.strip()
    if len(prompt) > MAX_MESSAGE_LENGTH:
        return jsonify(erreur="Message trop long (maximum 8 000 caractères)."), 413

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        metrics["errors"] += 1
        metrics["last_error_at"] = datetime.now(timezone.utc).isoformat()
        metrics["last_error"] = "Clé Gemini non configurée"
        return jsonify(erreur="La clé GEMINI_API_KEY n’est pas configurée dans les variables d’environnement de Render."), 503
    if not MODEL:
        metrics["errors"] += 1
        metrics["last_error_at"] = datetime.now(timezone.utc).isoformat()
        metrics["last_error"] = "Modèle Gemini non configuré"
        return jsonify(erreur="Configure GEMINI_MODEL avec un modèle Gemini disponible."), 503

    metrics["requests"] += 1
    metrics["last_request_at"] = datetime.now(timezone.utc).isoformat()
    previous = clean_history(data.get("historique"))
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
                    max_output_tokens=1800,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        maximum_remote_calls=6
                    ),
                ),
            )
        answer = (response.text or "").strip()
        if not answer:
            answer = "Je n'ai pas reçu de réponse exploitable. Peux-tu reformuler ta demande ?"
        metrics["successes"] += 1
        return jsonify(reponse=answer)
    except Exception as exc:
        app.logger.exception("Erreur Gemini")
        metrics["errors"] += 1
        metrics["last_error_at"] = datetime.now(timezone.utc).isoformat()
        message = str(exc).lower()
        if "api_key_invalid" in message or "invalid api key" in message or "unauthorized" in message:
            metrics["last_error"] = "Clé Gemini invalide ou refusée"
            return jsonify(erreur="La clé Gemini semble invalide. Vérifie GEMINI_API_KEY dans les variables d’environnement de Render."), 502
        if "not_found" in message or "404" in message or ("model" in message and "not" in message):
            metrics["last_error"] = "Modèle Gemini introuvable ou indisponible"
            return jsonify(erreur="Le modèle Gemini configuré est introuvable ou indisponible. Vérifie GEMINI_MODEL."), 502
        metrics["last_error"] = "Erreur du fournisseur Gemini"
        return jsonify(erreur="Gemini n'a pas pu répondre. Vérifie la clé et les journaux du service Render, puis réessaie."), 502

@app.errorhandler(413)
def request_too_large(_error):
    return jsonify(erreur="La requête est trop volumineuse."), 413

if __name__ == "__main__":
    print("Yvan.IA : ouvre http://127.0.0.1:5000 sur cet ordinateur.")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
