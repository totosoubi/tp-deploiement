# Préparation initiale, avant le premier push de déploiement

Ces opérations configurent l'infrastructure et les secrets une fois. Les
déploiements applicatifs suivants sont intégralement exécutés par GitHub Actions.

## 1. Dépôt GitHub et Docker Hub

Le **contenu de `TP déploiement` doit être la racine du dépôt GitHub** :
GitHub doit trouver `.github/workflows/cicd.yml` à cette racine.
Le dossier possède son propre dépôt Git, indépendant des autres TP.

Créer un repository Docker Hub nommé `tp-deploiement`, sous le compte utilisé
par `DOCKERHUB_USERNAME`. Générer un token d'accès avec les droits de lecture
et d'écriture et le stocker dans `DOCKERHUB_TOKEN` sur GitHub.
L'image peut être privée : le script s'authentifie aussi sur la VM pour la lire.

## 2. VM Azure

Dans le portail Azure, créer une VM Ubuntu Server **24.04 LTS x64** avec une
IP publique et une authentification par clé SSH. Conserver la clé privée
hors du dépôt. La clé utilisée par Actions doit être utilisable sans saisie
de passphrase et sa clé publique doit être autorisée pour l'utilisateur SSH.

Autoriser le TCP `80` pour la page publique et le TCP `22` pour la connexion
SSH des runners GitHub dans le groupe de sécurité réseau Azure. Vérifier
également le pare-feu Ubuntu s'il est activé. Une règle SSH limitée uniquement
à l'IP de ton Mac ne permet pas aux runners GitHub hébergés de se connecter.

Cette préparation ne crée pas de VM automatiquement depuis le workflow.
[Créer une VM Linux sur Azure](https://learn.microsoft.com/en-us/azure/virtual-machines/linux/quick-create-portal).

## 3. Installer Docker sur la VM une seule fois

Depuis le dossier du projet, adapter les variables ci-dessous :

```bash
export AZURE_HOST='IP_PUBLIQUE_VM'
export AZURE_USER='UTILISATEUR_SSH'
export AZURE_KEY='/chemin/hors-du-depot/cle-privee.pem'
```

Lors de la première connexion, comparer l'empreinte SSH du serveur à celle
obtenue depuis une console Azure de confiance avant de l'accepter.

```bash
scp -i "$AZURE_KEY" scripts/bootstrap-vm.sh "$AZURE_USER@$AZURE_HOST:bootstrap-vm.sh"
ssh -i "$AZURE_KEY" "$AZURE_USER@$AZURE_HOST" 'sudo -n bash bootstrap-vm.sh'
```

Le script installe Docker et le plugin Compose depuis le dépôt officiel Docker.
L'utilisateur Azure doit pouvoir utiliser Docker directement ou via
`sudo -n docker` (sans demande de mot de passe).
[Installation officielle Docker sur Ubuntu](https://docs.docker.com/engine/install/ubuntu/).

## 4. Vérifier la clé d'hôte SSH

Dans **Azure → VM → Run command → RunShellScript**, afficher l'empreinte
publique de la clé d'hôte :

```bash
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Sur le Mac, collecter la ligne et comparer son empreinte à celle d'Azure :

```bash
ssh-keyscan -t ed25519 "$AZURE_HOST" > /tmp/tp-deploiement-known-hosts
ssh-keygen -lf /tmp/tp-deploiement-known-hosts
```

Après comparaison, le contenu de ce fichier constitue `AZURE_KNOWN_HOSTS`.
Le workflow utilise `StrictHostKeyChecking=yes`, sans nouvelle acceptation
interactive à chaque push.

## 5. Renseigner les secrets GitHub

Dans les paramètres du dépôt, créer les six **Repository secrets** listés
dans le README. La clé privée entière, y compris ses lignes BEGIN/END, va dans
`AZURE_SSH_PRIVATE_KEY`. Aucun de ces fichiers ne doit être commité.

Avec GitHub CLI authentifié, on peut aussi utiliser ces commandes depuis le
dépôt ; les deux premières demandent les valeurs de façon interactive :

```bash
gh secret set DOCKERHUB_USERNAME
gh secret set DOCKERHUB_TOKEN
printf '%s' "$AZURE_HOST" | gh secret set AZURE_HOST
printf '%s' "$AZURE_USER" | gh secret set AZURE_USER
gh secret set AZURE_SSH_PRIVATE_KEY < "$AZURE_KEY"
gh secret set AZURE_KNOWN_HOSTS < /tmp/tp-deploiement-known-hosts
gh secret list
```

## 6. Déclencher et vérifier

Une fois la préparation terminée, pousser un commit sur `main` :

```bash
git push origin main
```

Les quatre jobs doivent réussir dans l'onglet **Actions**. Ouvrir ensuite
`http://<IP_PUBLIQUE_VM>` et récupérer l'artefact `azure-<SHA>` dans ce run.
Le workflow effectue lui-même les tests publics et la capture ; aucune
connexion manuelle à la VM n'est nécessaire après le push.

Si le premier push a précédé la configuration des secrets, le workflow échoue
explicitement sur le secret manquant. Une fois la préparation terminée, un
nouveau push sur `main` déclenche la chaîne complète.
