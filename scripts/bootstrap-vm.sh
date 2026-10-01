#!/usr/bin/env bash
# Préparation initiale uniquement, sur une VM Ubuntu 24.04 x64.
set -euo pipefail
if [[ "$EUID" -ne 0 ]]; then
  printf '%s\n' 'Exécuter avec sudo bash scripts/bootstrap-vm.sh.' >&2
  exit 1
fi
. /etc/os-release
[[ "$ID" == ubuntu ]] || { printf '%s\n' 'Ubuntu est requis.' >&2; exit 1; }
apt-get update
apt-get install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${UBUNTU_CODENAME:-$VERSION_CODENAME}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
docker version
docker compose version
