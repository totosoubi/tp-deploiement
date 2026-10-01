#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

for variable in AZURE_HOST AZURE_USER AZURE_SSH_PRIVATE_KEY AZURE_KNOWN_HOSTS \
  DOCKERHUB_USERNAME DOCKERHUB_TOKEN IMAGE_REF; do
  if [[ -z "${!variable:-}" ]]; then
    printf 'Secret ou variable requis absent : %s\n' "$variable" >&2
    exit 1
  fi
done
[[ "$AZURE_HOST" =~ ^[a-zA-Z0-9][a-zA-Z0-9.-]*$ ]] || exit 1
[[ "$AZURE_USER" =~ ^[a-z_][a-z0-9_-]*$ ]] || exit 1

umask 077
ssh_dir="$(mktemp -d)"
trap 'rm -rf -- "$ssh_dir"' EXIT
printf '%s\n' "$AZURE_SSH_PRIVATE_KEY" > "$ssh_dir/key"
printf '%s\n' "$AZURE_KNOWN_HOSTS" > "$ssh_dir/known_hosts"
ssh-keygen -y -P '' -f "$ssh_dir/key" >/dev/null

# %q protège chaque valeur pour Bash ; le payload reste sur stdin SSH,
# sans être affiché dans les logs ni sauvegardé dans un script sur la VM.
{
  printf 'export IMAGE_REF=%q\n' "$IMAGE_REF"
  printf 'export DOCKERHUB_USERNAME=%q\n' "$DOCKERHUB_USERNAME"
  printf 'export DOCKERHUB_TOKEN=%q\n' "$DOCKERHUB_TOKEN"
  printf '%s\n' 'set -euo pipefail' 'export DEPLOY_DIR="$HOME/tp-deploiement"' \
    'mkdir -p "$DEPLOY_DIR"' 'cat > "$DEPLOY_DIR/compose.yaml" << '\''COMPOSE_CONTENT'\'''
  cat deploy/compose.yaml
  printf '\n%s\n' 'COMPOSE_CONTENT'
  cat scripts/deploy.sh
} | ssh -i "$ssh_dir/key" \
  -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes \
  -o "UserKnownHostsFile=$ssh_dir/known_hosts" -o ConnectTimeout=15 \
  -o ServerAliveInterval=15 -o ServerAliveCountMax=4 \
  "$AZURE_USER@$AZURE_HOST" 'bash -se'
