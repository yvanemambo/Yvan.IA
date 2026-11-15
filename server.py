import hmac
import json
import os
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context
from werkzeug.middleware.proxy_fix import ProxyFix
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
# Render et Vercel placent un proxy de confiance devant Flask. Ne retenir
# que l'adresse ajoutée par le proxy le plus proche, jamais la première valeur
# X-Forwarded-For fournie potentiellement par le visiteur.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
app.config["MAX_CONTENT_LENGTH"] = 48 * 1024

def client_ip():
    return request.remote_addr or "unknown"

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


# Studio Motion Design : le rendu est déporté vers un service Node.js GiveMotion.
VIDEO_RENDERER_URL = os.getenv("VIDEO_RENDERER_URL", "").strip().rstrip("/")
VIDEO_RENDERER_TOKEN = os.getenv("VIDEO_RENDERER_TOKEN", "").strip()
VIDEO_STUDIO_CODE = os.getenv("VIDEO_STUDIO_CODE", "").strip()
video_requests_by_ip = defaultdict(deque)
VIDEO_RATE_WINDOW_SECONDS = 3600
VIDEO_RATE_LIMIT = 2

def studio_authorized():
    supplied = request.headers.get("X-Studio-Code", "")
    return bool(VIDEO_STUDIO_CODE and supplied and hmac.compare_digest(supplied, VIDEO_STUDIO_CODE))

def studio_renderer_request(path, method="GET", payload=None, timeout=30):
    if not VIDEO_RENDERER_URL or not VIDEO_RENDERER_TOKEN:
        raise RuntimeError("Le moteur vidéo n'est pas encore configuré.")
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(
        VIDEO_RENDERER_URL + path,
        data=body,
        method=method,
        headers={"Authorization": "Bearer " + VIDEO_RENDERER_TOKEN, "Content-Type": "application/json"},
    )
    return urlopen(req, timeout=timeout)

def video_rate_limited(ip):
    now = time.monotonic()
    bucket = video_requests_by_ip[ip]
    while bucket and now - bucket[0] > VIDEO_RATE_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= VIDEO_RATE_LIMIT:
        return True
    bucket.append(now)
    return False

def clean_storyboard(raw):
    if not isinstance(raw, dict) or not isinstance(raw.get("scenes"), list):
        raise ValueError("Le scénario vidéo reçu est incomplet.")
    def clean_text(value, limit):
        if not isinstance(value, str):
            return ""
        return " ".join(value.replace("<", "").replace(">", "").split())[:limit]
    scenes = []
    for item in raw["scenes"][:5]:
        if not isinstance(item, dict):
            continue
        scene = {
            "kicker": clean_text(item.get("kicker"), 50),
            "title": clean_text(item.get("title"), 100),
            "subtitle": clean_text(item.get("subtitle"), 180),
        }
        if scene["title"]:
            scenes.append(scene)
    if not 3 <= len(scenes) <= 5:
        raise ValueError("Yvan.IA n'a pas réussi à préparer les scènes. Essaie une description plus précise.")
    return {"title": clean_text(raw.get("title"), 100), "scenes": scenes}


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
    if request.path.startswith(("/commande", "/sante", "/admin", "/studio")):
        response.headers["Cache-Control"] = "no-store"
    return response

@app.get("/")
def home():
    return send_from_directory(PUBLIC, "index.html")


@app.get("/studio")
def studio_page():
    return send_from_directory(PUBLIC, "studio.html")

@app.get("/studio/health")
def studio_health():
    configured = bool(VIDEO_RENDERER_URL and VIDEO_RENDERER_TOKEN and VIDEO_STUDIO_CODE and os.getenv("GEMINI_API_KEY", "").strip())
    return jsonify(
        configured=configured,
        renderer_configured=bool(VIDEO_RENDERER_URL and VIDEO_RENDERER_TOKEN),
        access_configured=bool(VIDEO_STUDIO_CODE),
        gemini_configured=bool(os.getenv("GEMINI_API_KEY", "").strip()),
        message="Le studio est prêt." if configured else "Le studio doit encore être configuré par l'administrateur.",
    )

@app.post("/studio/videos")
def studio_create_video():
    if not VIDEO_STUDIO_CODE:
        return jsonify(erreur="Le studio est désactivé. Configure VIDEO_STUDIO_CODE dans les variables d'environnement."), 503
    if not studio_authorized():
        return jsonify(erreur="Code d'accès au Studio incorrect."), 401
    if not VIDEO_RENDERER_URL or not VIDEO_RENDERER_TOKEN:
        return jsonify(erreur="Le moteur vidéo GiveMotion n'est pas encore configuré sur Render."), 503

    ip = client_ip()
    if video_rate_limited(ip):
        return jsonify(erreur="Limite atteinte : deux vidéos par heure pour cette adresse. Réessaie plus tard."), 429

    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify(erreur="Décris la vidéo que tu souhaites créer."), 400
    prompt = prompt.strip()
    if len(prompt) > 1200:
        return jsonify(erreur="La description doit faire au maximum 1 200 caractères."), 413

    aspect = data.get("aspect", "vertical")
    duration = data.get("duration", 15)
    style = data.get("style", "modern")
    if aspect not in {"vertical", "horizontal", "square"}:
        return jsonify(erreur="Format vidéo non reconnu."), 400
    if duration not in {10, 15, 20}:
        return jsonify(erreur="Choisis une durée de 10, 15 ou 20 secondes."), 400
    if style not in {"modern", "luxury", "bold", "minimal", "neon"}:
        return jsonify(erreur="Style graphique non reconnu."), 400

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or not MODEL:
        return jsonify(erreur="Gemini doit être configuré avant de créer une vidéo."), 503

    instructions = (
        "Tu es directeur artistique et scénariste motion design. Prépare un storyboard publicitaire "
        "professionnel en français à partir du brief. Retourne uniquement un JSON valide avec les clés "
        "title (string) et scenes (tableau de 3 à 5 objets). Chaque objet contient kicker, title et subtitle "
        "(chaînes courtes). Prévois une accroche immédiate, une progression visuelle et une conclusion/CTA. "
        "Ne mets aucun HTML, CSS, JavaScript, URL, marque ou chiffre non fourni par l'utilisateur. "
        "N'invente pas de caractéristiques de produit. Le texte doit être lisible à l'écran."
    )
    brief = f"Brief : {prompt}\nFormat : {aspect}\nDurée cible : {duration} secondes\nStyle visuel : {style}"
    try:
        with genai.Client(api_key=api_key) as client:
            generated = client.models.generate_content(
                model=MODEL,
                contents=brief,
                config=types.GenerateContentConfig(
                    system_instruction=instructions,
                    response_mime_type="application/json",
                    max_output_tokens=1400,
                ),
            )
        storyboard = clean_storyboard(json.loads(generated.text or "{}"))
        with studio_renderer_request("/jobs", method="POST", payload={
            **storyboard, "aspect": aspect, "duration": duration, "style": style,
        }, timeout=45) as upstream:
            result = json.loads(upstream.read().decode("utf-8"))
        return jsonify(job_id=result.get("id"), status=result.get("status", "queued")), 202
    except HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8")).get("error", "Le moteur vidéo a refusé la demande.")
        except Exception:
            detail = "Le moteur vidéo a refusé la demande."
        return jsonify(erreur=detail), exc.code if 400 <= exc.code < 500 else 502
    except URLError:
        return jsonify(erreur="Le moteur vidéo est momentanément inaccessible. Réessaie dans quelques instants."), 502
    except (ValueError, json.JSONDecodeError) as exc:
        return jsonify(erreur=str(exc) or "Impossible de préparer le scénario vidéo."), 422
    except Exception:
        app.logger.exception("Erreur de création vidéo")
        return jsonify(erreur="Yvan.IA n'a pas pu préparer cette vidéo. Réessaie avec une description plus simple."), 502

@app.get("/studio/jobs/<job_id>")
def studio_video_status(job_id):
    if not studio_authorized():
        return jsonify(erreur="Code d'accès au Studio incorrect."), 401
    if not job_id or len(job_id) > 64 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-" for c in job_id):
        return jsonify(erreur="Identifiant de vidéo invalide."), 400
    try:
        with studio_renderer_request("/jobs/" + job_id) as upstream:
            return jsonify(json.loads(upstream.read().decode("utf-8")))
    except HTTPError as exc:
        return jsonify(erreur="Vidéo introuvable ou expirée."), exc.code
    except Exception:
        return jsonify(erreur="Impossible de vérifier l'avancement de la vidéo."), 502

@app.get("/studio/jobs/<job_id>/video")
def studio_video_download(job_id):
    if not studio_authorized():
        return jsonify(erreur="Code d'accès au Studio incorrect."), 401
    if not job_id or len(job_id) > 64 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-" for c in job_id):
        return jsonify(erreur="Identifiant de vidéo invalide."), 400
    try:
        upstream = studio_renderer_request("/jobs/" + job_id + "/video", timeout=120)
        def video_chunks():
            try:
                while True:
                    chunk = upstream.read(65536)
                    if not chunk:
                        break
                    yield chunk
            finally:
                upstream.close()
        return Response(
            stream_with_context(video_chunks()),
            mimetype="video/mp4",
            headers={"Content-Disposition": 'attachment; filename="yvan-ia-motion.mp4"', "Cache-Control": "no-store"},
        )
    except HTTPError as exc:
        return jsonify(erreur="La vidéo n'est pas encore prête ou a expiré."), exc.code
    except Exception:
        return jsonify(erreur="Impossible de télécharger la vidéo pour le moment."), 502


@app.get("/admin")
def admin_page():
    return send_from_directory(PUBLIC, "admin.html")

@app.get("/sante")
def health():
    gemini_ready = bool(os.getenv("GEMINI_API_KEY", "").strip() and MODEL)
    return jsonify(
        status="ok",
        access_configured=bool(os.getenv("MBO_CODE", "").strip()),
        app="Yvan.IA",
        provider="Gemini",
        model=MODEL,
        platform=PLATFORM,
        gemini_configured=gemini_ready,
        admin_configured=bool(os.getenv("ADMIN_CODE", "").strip()),
        ready=gemini_ready,
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
        admin_configured=True,
        platform=PLATFORM,
        metrics=dict(metrics),
        metrics_scope="Ce processus uniquement : compteurs temporaires, remis à zéro lors d'un redémarrage ou d'un changement d'instance.",
    )

@app.post("/commande")
def command():
    required_code = os.getenv("MBO_CODE", "").strip()
    supplied_code = request.headers.get("X-Code", "")
    if required_code and supplied_code and not hmac.compare_digest(supplied_code, required_code):
        return jsonify(erreur="Code d’accès incorrect."), 401
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
