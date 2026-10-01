# TP Déploiement — CI/CD sur Azure

**Thomas Soubirou-Pouey** · Flask, Gunicorn, pytest, Docker et GitHub Actions.

Dépôt du rendu : <https://github.com/totosoubi/tp-deploiement>.

## Fonctionnement

Chaque **push sur `main`** lance [.github/workflows/cicd.yml](.github/workflows/cicd.yml) :

```text
Tests unitaires → Tests E2E HTTP → Build et push Docker Hub
    → Déploiement SSH sur Azure → Tests HTTP publics → Capture d'écran
```

Un échec bloque les étapes suivantes. Une pull request exécute uniquement les
tests. Après la configuration initiale de la VM et des secrets, **aucune
intervention ni approbation manuelle n'est demandée après le push**.

## Exécuter localement

Depuis ce dossier, avec Docker Desktop démarré :

```bash
docker compose up -d --build --wait
```

Application : <http://localhost:8091>.

| Route GET | Réponse |
| --- | --- |
| `/` | Page d'accueil avec liens vers les endpoints. |
| `/health` | HTTP `200`, `{"status":"ok"}`. |
| `/who` | HTTP `200`, texte `Thomas Soubirou-Pouey`. |
| `/version` | Version embarquée dans l'image : SHA du commit en CI, `local` ici. |

Le conteneur expose `8080`. Compose publie `8091` sur le Mac et le port attribué
**8029** sur la VM.

Pour lancer directement l'image Docker Hub sur le port attribué (y compris
sur un Mac Apple Silicon) :

```bash
docker run -d --platform linux/amd64 --name soubirou-pouey_thomas \
  --restart unless-stopped -p 8029:8080 tomsoubi/tp-deploiement:latest
```

Vérification locale : <http://localhost:8029/health>. Si ce conteneur existe
déjà et est arrêté, le relancer avec `docker start soubirou-pouey_thomas`.

## Tests

Installer les dépendances une fois dans un environnement isolé :

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Commandes identiques à celles de la CI :

```bash
python -m pytest tests/unit -q
bash scripts/test-e2e.sh
```

Les **19 tests unitaires** vérifient les contrats HTTP et les chemins du script
de déploiement avec Docker simulé (succès, échec de téléchargement et retour
à la version précédente, avec ou sans `sudo`). Les **5 tests E2E** utilisent
de vraies requêtes HTTP vers Gunicorn : `/health`, parcours accueil → `/who`,
version, page inconnue et refus de `POST /who`.

Pour exécuter les E2E contre le conteneur démarré :

```bash
BASE_URL=http://127.0.0.1:8091 EXPECTED_VERSION=local bash scripts/test-e2e.sh
```

## Activer Docker Hub et Azure

Utiliser la **VM Ubuntu fournie pour le TP**, avec Docker et Compose, un accès
SSH par clé sur le port `22` et le port applicatif **8029** accessible depuis
Internet. L'image est publiée dans `tomsoubi/tp-deploiement`. Le
[guide de préparation](docs/azure-setup.md) détaille la configuration initiale.

Dans **Settings → Secrets and variables → Actions → Repository secrets** du
dépôt GitHub, renseigner :

| Secret | Valeur |
| --- | --- |
| `DOCKERHUB_USERNAME` | Identifiant Docker Hub. |
| `DOCKERHUB_TOKEN` | Token Docker Hub avec lecture et écriture. |
| `AZURE_HOST` | IP publique ou nom DNS de la VM, sans `http://`. |
| `AZURE_USER` | Utilisateur SSH de la VM. |
| `AZURE_SSH_PRIVATE_KEY` | Clé privée SSH dédiée au déploiement, sans passphrase. |
| `AZURE_KNOWN_HOSTS` | Ligne `known_hosts` vérifiée de cette VM. |

Les identifiants restent dans GitHub Secrets et ne sont pas copiés dans
l'image. Aucun secret réel n'est inclus dans ce dépôt.

## Choix techniques

- **Flask + Gunicorn**, sans base de données : cette application vérifie
  l'identité et la disponibilité du service ; aucun stockage n'est nécessaire.
- Dépendances directes figées et actions GitHub référencées par commit.
- Image publiée avec `sha-<SHA complet du commit>` et `latest`. Le déploiement
  utilise le **digest SHA-256** renvoyé par la publication, et `/version`
  permet de contrôler que le commit attendu est réellement servi.
- Un seul conteneur nommé `soubirou-pouey_thomas`, géré par le projet Compose
  `tp-deploiement-thomas-soubirou-pouey` dans le dossier du même nom sur la VM.
  Le port `8029` et ces noms propres au TP permettent un déploiement sur un
  serveur partagé. Relancer le même digest conserve le conteneur sain
  existant. Les workflows sont sérialisés.
- L'image est téléchargée avant de modifier le service. En cas d'échec du
  healthcheck au démarrage, le script restaure l'image précédente et la CI
  reste en échec. Le remplacement peut provoquer une brève interruption.
- SSH vérifie la clé du serveur. Le token Docker Hub transite par l'entrée
  standard SSH et sa configuration temporaire sur la VM est supprimée.
- Le conteneur utilise un utilisateur non root, un système de fichiers en
  lecture seule sur la VM et un contrôle de santé intégré.

## Rendu

Après un workflow entièrement réussi, l'application est accessible à
`http://<IP_PUBLIQUE_VM>:8029`. L'artefact GitHub Actions **`azure-<SHA>`** contient
`azure-public.png` (capture avec l'adresse réelle et la version visibles)
et `deployment.txt` (URL et version vérifiées).

Les [sorties de validation locale](docs/validation-locale.log) confirment les
tests, le fonctionnement dans Docker et la conservation du même conteneur
après deux lancements de la configuration de déploiement.

**État de préparation :** tests unitaires et E2E réussis dans GitHub Actions,
image publiée sur Docker Hub, conteneur local vérifié sur le port `8029`.
Le résultat du déploiement distant et sa capture sont consultables dans
[GitHub Actions](https://github.com/totosoubi/tp-deploiement/actions).
Une capture locale ne constitue pas la preuve du déploiement Azure.

Références : [publication Docker avec Actions](https://docs.docker.com/build/ci/github-actions/),
[GitHub Secrets](https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions).
