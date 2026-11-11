# Yvan.IA

Yvan.IA est un assistant personnel en français, construit avec Flask et Google Gemini. Le projet fonctionne avec Flask et peut être hébergé sur Render ou Vercel.

## Fonctionnalités
- Chat avec Gemini (modèle configurable).
- Historique local, limité et nettoyé avant envoi à l'API.
- Dictée vocale selon les capacités et autorisations du navigateur.
- Lecture des fichiers TXT, MD, CSV et PDF placés dans `dossier_mbo/`.
- Liste des dossiers autorisés.
- Préparation de brouillons d'e-mails sans envoi automatique.
- Tableau de bord administrateur à `/admin`, protégé par un code distinct `ADMIN_CODE`.
- Vérification de l'état de configuration et compteurs opérationnels temporaires.
- Interface responsive pour ordinateur et mobile.

## Structure
- `server.py` : application Flask, connexion Gemini et routes sécurisées.
- `api/index.py` : point d'entrée Vercel.
- `public/index.html` : interface de discussion.
- `public/admin.html` : tableau de bord administrateur.
- `vercel.json` : routage vers la fonction Python.
- `requirements.txt` : dépendances.
- `dossier_mbo/` : fichiers consultables en lecture seule.

## Variables d'environnement
Dans Render, ouvre le service Yvan.IA puis Environment et configure :
- `GEMINI_API_KEY` : clé privée Google AI Studio.
- `ADMIN_CODE` : code secret réservé à l'administrateur. Il doit être différent de `MBO_CODE`.
- `GEMINI_MODEL` : modèle disponible sur ton compte. Valeur par défaut : `gemini-3.8-flash`.

Configure `ADMIN_CODE` dans les variables d’environnement Render que tu souhaites tester (Preview/Production séparément). Choisis un code long et unique. Ne le mets jamais dans GitHub, dans le code source ou dans un message. Ne partage pas ce code avec les utilisateurs.

Ne place jamais les vraies clés dans GitHub, dans le code ou dans un message. Le fichier `.env.example` ne contient que des exemples vides.

## Tableau de bord administrateur
- Ouvre `/admin` sur le site.
- Entre la valeur de `ADMIN_CODE`, et non le nom de la variable.
- Le serveur vérifie le code dans l'en-tête `X-Admin-Code`.
- Les données affichées ne contiennent pas les clés API ni les codes secrets.
- Le code administrateur est conservé uniquement dans la session de l'onglet navigateur et n'est pas enregistré dans le stockage local permanent.

### Limites des statistiques
Les compteurs de requêtes/réponses/erreurs sont en mémoire dans un processus. Sur Render, plusieurs instances peuvent fonctionner en parallèle et les compteurs peuvent être remis à zéro au redémarrage. Ils ne sont donc ni un total global fiable, ni un historique de facturation. Le tableau de bord n'affiche pas encore les visiteurs uniques, les comptes clients, les abonnements ou les paiements. Pour ces statistiques, il faudra ajouter une base de données persistante et un système de comptes.

## Vérification
- `/sante` indique si Gemini et le code administrateur sont configurés (sans révéler leurs valeurs).
- `/admin/metrics` est protégé par `ADMIN_CODE`.
- Envoie un message depuis l'interface pour tester réellement la clé et le modèle.
- Teste la dictée vocale dans un navigateur compatible avec l'autorisation micro.

## Limites à connaître
- L'historique est conservé dans le stockage local du navigateur. Il n'est pas synchronisé entre appareils et peut disparaître si les données du navigateur sont supprimées.
- Sur Render, le système de fichiers de la fonction n'est pas un stockage permanent. Les brouillons y sont donc renvoyés à l'écran pour être copiés, pas enregistrés durablement.
- Les fichiers de `dossier_mbo/` sont ceux du dépôt et sont accessibles en lecture seule. L'application ne peut pas parcourir les dossiers du PC personnel de l'utilisateur.
- Les PDF scannés sans couche texte ne peuvent pas être lus sans OCR.
- La dictée vocale dépend du navigateur et de ses autorisations micro.

## Développement local (Windows / PowerShell)
```powershell
python -m pip install -r requirements.txt
$env:GEMINI_API_KEY="ta_cle_gemini"
$env:ADMIN_CODE="un-autre-code-secret-admin"
$env:GEMINI_MODEL="gemini-3.8-flash"
python server.py
```
Puis ouvre http://127.0.0.1:5000 et http://127.0.0.1:5000/admin.
