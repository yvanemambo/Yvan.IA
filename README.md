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
- `server.py` : point d'entrée Flask utilisé par l'hébergement configuré.
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

## Version de fiabilité — novembre 2026
- Les limites de requêtes utilisent désormais l'adresse client résolue par le proxy de confiance le plus proche (`ProxyFix`) plutôt que la première valeur de `X-Forwarded-For`, qui peut être falsifiée par un visiteur.
- Les limites par adresse restent en mémoire dans chaque processus : elles ne constituent pas une protection globale entre plusieurs instances. Pour une limite globale, connecter un stockage partagé (Redis ou base de données) avant une ouverture publique à grande échelle.
- Le Studio conserve son architecture séparée : aucun secret du moteur vidéo n'est envoyé au navigateur.

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


## Studio Motion Design GiveMotion

Le Studio est accessible sur `/studio`. Il prépare un storyboard avec le modèle Gemini déjà configuré, puis transmet uniquement des scènes structurées (jamais du HTML libre) au moteur GiveMotion.

### Architecture double hébergement
- Render héberge un service Docker Node.js séparé dans `video-renderer/` ; il exécute GiveMotion, Chromium et FFmpeg.
- L'application Flask (Render et/ou Vercel) transmet les demandes au service via `VIDEO_RENDERER_URL`.
- Le navigateur ne reçoit jamais le jeton du moteur vidéo.

### Variables à configurer
Sur le service Flask de Render **et** sur Vercel :
- `VIDEO_RENDERER_URL` : URL HTTPS publique du service de rendu Render.
- `VIDEO_RENDERER_TOKEN` : secret partagé avec le service vidéo.
- `VIDEO_STUDIO_CODE` : code d'accès privé saisi dans le Studio.

Sur le service de rendu Render :
- `VIDEO_RENDERER_TOKEN` : exactement le même secret.
- `PORT` est fourni automatiquement par Render.

Génère deux secrets longs et uniques. Ne les ajoute jamais au dépôt GitHub. Le service de rendu accepte seulement des storyboards JSON validés et construit lui-même les pages HTML de rendu. Il n'exécute pas du HTML fourni par les visiteurs.

### Déploiement du moteur (à faire séparément, aucun déploiement automatique)
Créer un nouveau service Render de type **Web Service**, choisir l'environnement **Docker**, utiliser la racine du dépôt comme contexte et `video-renderer/Dockerfile` comme Dockerfile. Ajouter `VIDEO_RENDERER_TOKEN` dans les variables du service. Après son premier déploiement, copier son URL HTTPS dans `VIDEO_RENDERER_URL` sur les deux hébergements de l'application.

### Limites de la première version
- Formats 9:16, 16:9 et carré ; durées de 10, 15 ou 20 secondes.
- Deux créations par heure et par adresse IP côté application ; une seule vidéo rendue à la fois côté moteur.
- Les tâches et MP4 sont conservés temporairement sur le disque du service de rendu (24 h). Le stockage Render gratuit est éphémère : un redémarrage peut donc effacer les vidéos. Un stockage durable (par exemple Supabase Storage) sera nécessaire avant une mise en production avec historique permanent.
- Le moteur GiveMotion est open source MIT, mais le calcul vidéo consomme les ressources du service Render. Le forfait gratuit peut être lent, s'endormir ou manquer de mémoire sur les vidéos longues.
- Le Studio utilise Gemini pour préparer le scénario : les quotas gratuits du compte Gemini s'appliquent. Aucun nouveau fournisseur payant n'est ajouté.

Le Studio reste indisponible tant que les trois variables `VIDEO_RENDERER_URL`, `VIDEO_RENDERER_TOKEN` et `VIDEO_STUDIO_CODE` ne sont pas configurées.
