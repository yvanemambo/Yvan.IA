# Yvan.IA

Yvan.IA est un assistant personnel en français, construit avec Flask et Google Gemini. Le déploiement cible Vercel.

## Fonctionnalités
- Chat avec Gemini (modèle configurable).
- Historique des conversations conservé dans le navigateur de l'utilisateur.
- Dictée vocale lorsque le navigateur prend en charge Web Speech API.
- Lecture de fichiers TXT, MD et CSV placés dans `dossier_mbo/`.
- Liste des dossiers et fichiers autorisés.
- Création de brouillons d'e-mails (aucun e-mail n'est envoyé).
- Code d'accès privé.
- Interface responsive pour ordinateur et mobile.

## Structure
- `server.py` : application Flask et connexion Gemini.
- `api/index.py` : point d'entrée Vercel.
- `public/index.html` : interface web.
- `vercel.json` : routage vers la fonction Python.
- `requirements.txt` : dépendances.
- `dossier_mbo/` : fichiers consultables en lecture seule.

## Variables Vercel obligatoires
Dans **Project → Settings → Environment Variables**, ajoute les variables suivantes pour Production, Preview et Development :
- `GEMINI_API_KEY` : clé privée Google AI Studio.
- `MBO_CODE` : code d'accès privé choisi par le propriétaire.
- `GEMINI_MODEL` : modèle disponible sur le compte, par défaut `gemini-2.5-flash`.

Ne place jamais les vraies clés dans GitHub, dans le code ou dans un message.

## Déploiement
Le projet doit être relié au dépôt GitHub `yvanemambo/Yvan.IA`. La branche de production est `main`. Après connexion Git, fusionner les changements dans `main` déclenche le déploiement Vercel.

## Vérification
- `/sante` doit renvoyer un JSON avec `status: ok` et `provider: Gemini`.
- Envoie un message depuis l'interface pour tester la clé et le modèle.
- Teste le bouton micro avec un navigateur compatible et l'autorisation micro.

## Limites importantes
- L'historique est conservé dans le stockage local du navigateur. Il n'est pas synchronisé entre appareils et peut être effacé si les données du navigateur sont supprimées.
- Vercel n'offre pas de disque persistant à la fonction. Les brouillons créés sur Vercel sont temporaires.
- Les fichiers de `dossier_mbo/` sont ceux du dépôt et sont accessibles en lecture seule. L'application ne peut pas parcourir les dossiers du PC personnel de l'utilisateur.
- La dictée vocale dépend du navigateur et de ses autorisations micro.
- Le code d'accès simple protège l'API, mais pour une application publique multi-utilisateurs, il faudra ajouter un vrai système de comptes et une base de données.

## Développement local (Windows / PowerShell)
```powershell
python -m pip install -r requirements.txt
$env:GEMINI_API_KEY="ta_cle_gemini"
$env:MBO_CODE="ton-code-secret"
$env:GEMINI_MODEL="gemini-2.5-flash"
python server.py
```
Puis ouvre http://127.0.0.1:5000.
