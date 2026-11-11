# Yvan.IA

Yvan.IA est un assistant personnel en français, construit avec Flask et connecté à l'API Anthropic. Le projet est préparé pour un déploiement sur **Vercel** à partir de GitHub.

## Fonctionnalités actuelles

- Conversation avec un modèle Anthropic configurable.
- Historique récent conservé temporairement en mémoire d'instance.
- Lecture de fichiers TXT, MD et CSV placés dans `dossier_mbo/`.
- Liste des dossiers et fichiers autorisés.
- Rédaction de brouillons d'e-mails (aucun e-mail n'est envoyé).
- Code d'accès à l'application.

> Les commandes vocales ne sont pas encore implémentées. L'historique en mémoire peut être perdu lorsqu'une fonction Vercel redémarre ou change d'instance. Les brouillons écrits sur Vercel sont temporaires. Pour conserver durablement les conversations et les brouillons, il faudra connecter une base de données ou un stockage persistant.

## Structure du projet

- `server.py` : application Flask, API et connexion à Anthropic.
- `public/index.html` : interface web servie par Vercel.
- `vercel.json` : configuration des fonctions Vercel.
- `requirements.txt` : dépendances Python.
- `dossier_mbo/` : fichiers de référence consultables par l'assistant.

## Déployer sur Vercel depuis GitHub

1. Ouvre [Vercel](https://vercel.com/) et connecte-toi.
2. Clique sur **Add New → Project**.
3. Importe le dépôt **yvanemambo/Yvan.IA**.
4. Garde les paramètres de build détectés automatiquement. Ne choisis pas Render.
5. Dans **Environment Variables**, ajoute les variables suivantes avant le déploiement :

| Variable | Obligatoire | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Oui | Clé API Anthropic, gardée secrète |
| `MBO_CODE` | Oui | Code secret pour accéder à Yvan.IA |
| `MBO_MODEL` | Non | Modèle Anthropic (défaut : `claude-sonnet-4-5`) |

6. Clique sur **Deploy**.

Après chaque nouveau commit sur la branche connectée, Vercel pourra lancer un nouveau déploiement automatiquement.

## Vérification

- Ouvre l'adresse de ton projet Vercel pour afficher l'interface.
- Ouvre `https://TON-DOMAINE.vercel.app/sante` pour vérifier l'API. La réponse attendue contient `"status":"ok"`.
- Envoie un message depuis l'interface après avoir configuré `ANTHROPIC_API_KEY`, `MBO_CODE` et un modèle valide si tu en as choisi un.

## Lancer localement sur Windows / PowerShell

1. Installe Python 3.10 ou une version plus récente.
2. Ouvre PowerShell dans le dossier du projet.
3. Installe les dépendances :

```powershell
python -m pip install -r requirements.txt
```

4. Configure les variables :

```powershell
$env:ANTHROPIC_API_KEY="ta_cle_api_anthropic"
$env:MBO_CODE="choisis-un-code-secret"
$env:MBO_MODEL="claude-sonnet-4-5"
```

5. Lance :

```powershell
python server.py
```

6. Ouvre http://127.0.0.1:5000.

## Sécurité et limites

- Ne publie jamais une clé API ou un code d'accès dans GitHub.
- Configure les secrets uniquement dans les variables d'environnement Vercel ou dans ton environnement local.
- Les fichiers de `dossier_mbo/` sont intégrés au déploiement en lecture seule.
- Vercel ne fournit pas un disque persistant à l'application : les fichiers temporaires et l'historique en mémoire ne sont pas une solution de stockage durable.
- Ce projet est indépendant de STARS AI.
