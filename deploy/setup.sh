#!/usr/bin/env bash
# One-time setup for an Ubuntu server (tested target: Oracle Cloud Always Free, Ampere A1).
# Run from the repo root:  bash deploy/setup.sh
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v docker >/dev/null; then
  echo "==> Installing Docker"
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
fi

echo "==> Opening ports 80 and 443 in the server firewall"
# Oracle's Ubuntu images block everything except SSH with iptables rules.
for port in 80 443; do
  sudo iptables -C INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null ||
    sudo iptables -I INPUT 5 -p tcp --dport "$port" -j ACCEPT
done
if command -v netfilter-persistent >/dev/null; then sudo netfilter-persistent save; fi

if [ ! -f .env ]; then
  ip=$(curl -fsS https://api.ipify.org)
  read -rp "Username for the app [coach]: " user
  read -rsp "Password for the app: " password; echo
  hash=$(sudo docker run --rm caddy:2 caddy hash-password --plaintext "$password")
  cat > .env <<ENV
DOMAIN=${ip}.sslip.io
COACH_USER=${user:-coach}
COACH_PASSWORD_HASH='${hash}'
COACH_MODEL=qwen3:4b
COACH_STT_MODEL=base
ENV
  echo "==> Wrote deploy/.env for https://${ip}.sslip.io"
fi

echo "==> Building and starting the coach (first build takes a few minutes)"
sudo docker compose up -d --build

model=$(grep '^COACH_MODEL=' .env | cut -d= -f2 || true)
model=${model:-qwen3:4b}
echo "==> Downloading the model ${model} (about 2.5 GB)"
sudo docker compose exec ollama ollama pull "$model"
sudo docker compose restart backend

domain=$(grep '^DOMAIN=' .env | cut -d= -f2 || true)
echo
echo "Done. Open https://${domain} and sign in with your username and password."
