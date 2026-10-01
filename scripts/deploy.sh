#!/usr/bin/env bash
# Exécuté sur la VM par GitHub Actions, avec les secrets transmis sur stdin SSH.
set -euo pipefail

: "${IMAGE_REF:?IMAGE_REF manquant}"
: "${DOCKERHUB_USERNAME:?DOCKERHUB_USERNAME manquant}"
: "${DOCKERHUB_TOKEN:?DOCKERHUB_TOKEN manquant}"
: "${DEPLOY_DIR:?DEPLOY_DIR manquant}"

if [[ ! "$IMAGE_REF" =~ ^[a-z0-9._/-]+@sha256:[a-f0-9]{64}$ ]]; then
  printf '%s\n' 'Une référence Docker immuable avec digest SHA-256 est requise.' >&2
  exit 1
fi

docker_cmd=(docker)
if ! docker info >/dev/null 2>&1; then
  docker_cmd=(sudo -n docker)
  "${docker_cmd[@]}" info >/dev/null
fi
"${docker_cmd[@]}" compose version

# Le token ne reste pas dans la configuration Docker de l'utilisateur de la VM.
registry_config="$(mktemp -d)"
chmod 700 "$registry_config"
cleanup() {
  if [[ "${docker_cmd[0]}" == sudo ]]; then
    sudo -n rm -rf -- "$registry_config"
  else
    rm -rf -- "$registry_config"
  fi
}
trap cleanup EXIT
printf '%s' "$DOCKERHUB_TOKEN" | "${docker_cmd[@]}" --config "$registry_config" \
  login --username "$DOCKERHUB_USERNAME" --password-stdin
# Télécharger d'abord : un échec de connexion ne touche pas au service courant.
"${docker_cmd[@]}" --config "$registry_config" pull "$IMAGE_REF"
unset DOCKERHUB_TOKEN

previous_ref="$("${docker_cmd[@]}" inspect --format '{{.Config.Image}}' tp-deploiement 2>/dev/null || true)"
compose_cmd=("${docker_cmd[@]}" compose --project-name tp-deploiement --file "$DEPLOY_DIR/compose.yaml")
# sudo ne conserve pas nécessairement IMAGE_REF : fournir explicitement les
# seules variables de configuration, sans transmettre le token au conteneur.
compose() {
  if [[ "${docker_cmd[0]}" == sudo ]]; then
    sudo -n env IMAGE_REF="$IMAGE_REF" APP_PORT="${APP_PORT:-80}" \
      BIND_ADDRESS="${BIND_ADDRESS:-0.0.0.0}" docker compose \
      --project-name tp-deploiement --file "$DEPLOY_DIR/compose.yaml" "$@"
  else
    IMAGE_REF="$IMAGE_REF" APP_PORT="${APP_PORT:-80}" \
      BIND_ADDRESS="${BIND_ADDRESS:-0.0.0.0}" "${compose_cmd[@]}" "$@"
  fi
}

if ! compose up -d --no-build --pull never --wait --wait-timeout 90; then
  compose logs --tail=50 >&2 || true
  if [[ -n "$previous_ref" ]]; then
    printf '%s\n' 'Échec de la nouvelle version : restauration de la précédente.' >&2
    export IMAGE_REF="$previous_ref"
    compose up -d --no-build --pull never --wait --wait-timeout 90
  fi
  # La CI reste rouge même lorsque la restauration a réussi.
  exit 1
fi

# Un deuxième déploiement du même digest conserve le conteneur sain existant.
"${docker_cmd[@]}" exec tp-deploiement python healthcheck.py
compose ps
printf '%s\n' 'Déploiement terminé, conteneur sain.'
