# Yvan.IA

Yvan.IA est un assistant personnel en français, construit avec Flask et connecté à **Google Gemini**. Le projet est préparé pour un déploiement sur **Vercel** à partir de GitHub.

## Fonctionnalités actuelles

- Conversation avec un modèle Gemini configurable.
- Historique récent conservé temporairement en mémoire d'instance.
- Lecture de fichiers TXT, MD et CSV placés dans `dossier_mbo/`.
- Liste des dossiers et fichiers autorisés.
- Rédaction de brouillons d'e-mails (aucun e-mail n'est envoyé).
- Code d'accès à l'application.

> Les commandes vocales ne sont pas encore implémentées. L'historique en mémoire peut être perdu lorsqu'une fonction Vercel redémarre ou change d'instance. Les brouillons écrits sur Vercel sont temporaires. Pour conserver durablement les conversations et les brouillons, il faudra connecter une base de données ou un stockage persistant.

## Structure

- `server.py` : application Flask, API et connexion à Gemini.
- `public/index.html` : interface web.
- `vercel.json` : configuration Vercel.
- `requirements.txt` : dépendances Python.
- `dossier_mbo/` : fichiers consultables par l'assistant.

## Déploiement Vercel

1. Importe le dépôt `yvanemambo/Yvan.IA` dans Vercel.
2. Dans **Project → Settings → Environment Variables**, ajoute :
   - `GEMINI_API_KEY` : ta clé API créée dans Google AI Studio.
   - `MBO_CODE` : ton code secret d'accès.
   - `GEMINI_MODEL` : `gemini-3.8-flash` (ou un modèle disponible sur ton compte).
3. Redéploie le projet dans Vercel.

Cette version utilise uniquement Gemini.

## Vérification

- Ouvre ton domaine Vercel.
- Ouvre `https://TON-DOMAINE.vercel.app/sante` : la réponse doit contenir `"status":"ok"` et `"provider":"Gemini"`.
- Envoie un message depuis l'interface.

## Lancer localement sur Windows / PowerShell

```powershell
python -m pip install -r requirements.txt
$env:GEMINI_API_KEY="ta_cle_gemini"
$env:MBO_CODE="choisis-un-code-secret"
$env:GEMINI_MODEL="gemini-3.8-flash"
python server.py
```

Ouvre ensuite http://127.0.0.1:5000.

## Sécurité et limites

- Ne publie jamais `GEMINI_API_KEY` ni `MBO_CODE` dans GitHub.
- Configure les secrets dans les variables d'environnement Vercel.
- Les fichiers de `dossier_mbo/` sont intégrés au déploiement en lecture seule.
- Vercel ne fournit pas de disque persistant : l'historique en mémoire et les brouillons temporaires ne sont pas durables.
- Ce projet est indépendant de STARS AI.
