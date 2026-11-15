# Yvan.IA — GiveMotion renderer

Service Node.js séparé qui reçoit un storyboard JSON validé depuis Flask et génère un MP4 avec GiveMotion 0.1.6.

## Local
- Node.js 20+
- FFmpeg
- Chromium headless (installé par `npx givemotion install`)

```powershell
npm install
npx givemotion install
$env:VIDEO_RENDERER_TOKEN="un-secret-long-et-aleatoire"
npm start
```

Le service écoute sur `PORT` (10000 par défaut). `GET /health` vérifie la disponibilité. Les routes `POST /jobs`, `GET /jobs/:id` et `GET /jobs/:id/video` exigent `Authorization: Bearer VIDEO_RENDERER_TOKEN`.

## Render
Créer un nouveau Web Service Docker depuis le dépôt principal :
- Root Directory : `video-renderer`
- Dockerfile : `Dockerfile`
- Environment : `VIDEO_RENDERER_TOKEN` (secret long et aléatoire)
- Health Check Path : `/health`

Après déploiement, copier l'URL HTTPS Render dans `VIDEO_RENDERER_URL` des services Flask sur Render et Vercel. Définir le même secret `VIDEO_RENDERER_TOKEN` sur les trois services. Définir aussi `VIDEO_STUDIO_CODE` sur les services Flask.

## Sécurité et limites
Le moteur n'accepte jamais du HTML fourni par l'utilisateur. Il valide un petit storyboard JSON, échappe les textes et construit lui-même la composition. Les exports et la file de tâches sont en mémoire / dans le disque local du service ; les MP4 expirent au bout de 24 heures. Le système de fichiers d'une instance Render gratuite est éphémère et peut être effacé lors d'un redémarrage. Prévoir un stockage objet durable avant de promettre un historique permanent.


## Qualité motion design

Le moteur construit un spot animé multi-scènes : visuels vectoriels choisis par Gemini (orbites, graphiques, produit stylisé, interface mobile, formes), typographie cinétique mot par mot, mouvements de caméra, transitions directionnelles et motion blur. Avant chaque export, GiveMotion exécute un contrôle de composition et de mouvement, puis produit une planche de vérification des scènes. Les fichiers MP4 sont exportés en qualité haute et contrôlés avec FFprobe.

**Limite actuelle :** GiveMotion est un moteur de motion graphics HTML/CSS/SVG ; il ne génère pas de séquences filmées photoréalistes. Pour des plans vidéo réalistes générés par IA, il faudra intégrer un fournisseur vidéo dédié, avec ses propres coûts et limites.
