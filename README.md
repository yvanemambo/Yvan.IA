# Yvan.IA

Assistant IA vocal personnel en français.

## Structure du projet

- `server.py` : serveur Flask et connexion à l'API Anthropic.
- `index.html` : interface web et commandes vocales.
- `requirements.txt` : dépendances Python.
- `dossier_mbo/` : fichiers que l'assistant peut consulter.
- `dossier_mbo/brouillons/` : brouillons d'e-mails générés (non envoyés).

## Installation (Windows / PowerShell)

```powershell
python -m pip install -r requirements.txt
$env:ANTHROPIC_API_KEY="ta_cle_api"
$env:MBO_CODE="choisis-un-code-secret"
python server.py
```

Le serveur affiche l'adresse locale à ouvrir depuis un téléphone connecté au même Wi-Fi.

## Configuration

- `ANTHROPIC_API_KEY` : clé API Anthropic (ne jamais la publier).
- `MBO_CODE` : code d'accès à l'application.
- `MBO_MODEL` : modèle Anthropic à utiliser (valeur par défaut définie dans `server.py`).

## Sécurité

Ne publie jamais de clé API ni de mot de passe dans le dépôt. Configure-les dans les variables d'environnement de ta machine ou de ton hébergeur.

Ce projet est indépendant de STARS AI.
