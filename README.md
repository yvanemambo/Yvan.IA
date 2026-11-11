# Yvan.IA

Yvan.IA est un assistant personnel en français, avec une interface web et un serveur Python/Flask connecté à l'API Anthropic.

## Fonctionnalités actuelles

- Conversation avec un modèle Anthropic configurable.
- Historique récent des échanges conservé en mémoire pendant l'exécution du serveur (limité à 200 conversations).
- Lecture de fichiers TXT, MD et CSV placés dans `dossier_mbo/`.
- Liste des dossiers et fichiers autorisés.
- Rédaction de brouillons d'e-mails enregistrés dans `dossier_mbo/brouillons/` (aucun e-mail n'est envoyé).
- Code d'accès à l'application.

> Les commandes vocales ne sont pas encore implémentées dans cette version. L'historique en mémoire est effacé au redémarrage du serveur.

## Structure du projet

- `server.py` : serveur Flask, connexion à Anthropic et outils de fichiers.
- `index.html` : interface web de Yvan.IA.
- `requirements.txt` : dépendances Python.
- `dossier_mbo/` : fichiers que l'assistant peut consulter.
- `dossier_mbo/brouillons/` : brouillons générés.

## Installation (Windows / PowerShell)

1. Installe Python 3.10 ou une version plus récente.
2. Ouvre PowerShell dans le dossier du projet.
3. Installe les dépendances :

```powershell
python -m pip install -r requirements.txt
```

4. Configure les variables d'environnement dans la fenêtre PowerShell :

```powershell
$env:ANTHROPIC_API_KEY="ta_cle_api_anthropic"
$env:MBO_CODE="choisis-un-code-secret"
$env:MBO_MODEL="claude-sonnet-4-5"
```

5. Lance le serveur :

```powershell
python server.py
```

6. Ouvre http://127.0.0.1:5000 dans ton navigateur.

Pour utiliser l'application depuis un téléphone connecté au même Wi-Fi, ouvre l'adresse IP locale de l'ordinateur qui exécute le serveur.

## Configuration sur un hébergeur

Ajoute ces variables dans les paramètres de ton service :

| Variable | Obligatoire | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Oui | Clé API Anthropic, à garder secrète |
| `MBO_CODE` | Oui | Code d'accès à Yvan.IA |
| `MBO_MODEL` | Non | Modèle Anthropic (défaut : `claude-sonnet-4-5`) |
| `PORT` | Non | Port fourni par l'hébergeur (défaut local : `5000`) |

L'endpoint `/sante` permet de vérifier que le serveur répond.

## Sécurité et limites

- Ne publie jamais une clé API ou un code d'accès dans GitHub.
- Configure les secrets uniquement dans l'environnement local ou dans les paramètres secrets de l'hébergeur.
- Les conversations sont conservées temporairement en mémoire et ne sont pas persistantes.
- Les fichiers accessibles par l'assistant doivent rester dans `dossier_mbo/`.
- Ce projet est indépendant de STARS AI.
