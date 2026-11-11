# Yvan.IA

Yvan.IA est un assistant personnel en français, construit avec Flask et Google Gemini. Le projet est préparé pour Vercel.

## Fonctionnalités
- Chat avec Gemini (modèle configurable).
- Historique local, limité et nettoyé avant envoi à l'API.
- Dictée vocale selon les capacités et autorisations du navigateur.
- Lecture des fichiers TXT, MD, CSV et PDF placés dans `dossier_mbo/`.
- Liste des dossiers autorisés.
- Préparation de brouillons d'e-mails sans envoi automatique.
- Code d'accès privé et vérification de l'état de configuration.
- Interface responsive pour ordinateur et mobile.

## Structure
- `server.py` : application Flask et connexion Gemini.
- `api/index.py` : point d'entrée Vercel.
- `public/index.html` : interface web.
- `vercel.json` : routage vers la fonction Python.
- `requirements.txt` : dépendances.
- `dossier_mbo/` : fichiers consultables en lecture seule.

## Variables d'environnement
Dans les paramètres du projet Vercel, configure :
- `GEMINI_API_KEY` : clé privée Google AI Studio.
- `MBO_CODE` : code d'accès privé.
- `GEMINI_MODEL` : modèle disponible sur ton compte. Valeur par défaut : `gemini-3.8-flash`.

Ne place jamais les vraies clés dans GitHub, dans le code ou dans un message. Le fichier `.env.example` ne contient que des exemples vides.

## Vérification
- `/sante` indique si la clé Gemini et le code d'accès sont configurés (sans révéler leurs valeurs).
- Envoie un message depuis l'interface pour tester réellement la clé et le modèle.
- Teste la dictée vocale dans un navigateur compatible avec l'autorisation micro.

## Limites à connaître
- L'historique est conservé dans le stockage local du navigateur. Il n'est pas synchronisé entre appareils et peut disparaître si les données du navigateur sont supprimées.
- Sur Vercel, le système de fichiers de la fonction n'est pas un stockage permanent. Les brouillons y sont donc renvoyés à l'écran pour être copiés, pas enregistrés durablement.
- Les fichiers de `dossier_mbo/` sont ceux du dépôt et sont accessibles en lecture seule. L'application ne peut pas parcourir les dossiers du PC personnel de l'utilisateur.
- Les PDF scannés sans couche texte ne peuvent pas être lus sans OCR.
- La dictée vocale dépend du navigateur et de ses autorisations micro.
- Le code d'accès simple convient à un usage privé limité. Une application publique multi-utilisateurs nécessitera des comptes, une base de données et une protection anti-abus persistante.

## Développement local (Windows / PowerShell)
```powershell
python -m pip install -r requirements.txt
$env:GEMINI_API_KEY="ta_cle_gemini"
$env:MBO_CODE="ton-code-secret"
$env:GEMINI_MODEL="gemini-3.8-flash"
python server.py
```
Puis ouvre http://127.0.0.1:5000.
