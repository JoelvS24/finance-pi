#!/usr/bin/env bash
# Idempotent first-run setup script for the Raspberry Pi.
# Assumes you've already SSH'd in and cloned the repo.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Updating system..."
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y git vim htop curl unzip ufw fail2ban

echo "==> Setting up firewall..."
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw --force enable

echo "==> Setting timezone..."
sudo timedatectl set-timezone Europe/Amsterdam

if ! command -v docker &> /dev/null; then
    echo "==> Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
    echo "!! Log out and back in, then re-run this script."
    exit 0
fi

if ! command -v tailscale &> /dev/null; then
    echo "==> Installing Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh
    if [[ -n "${TAILSCALE_AUTHKEY:-}" ]]; then
        sudo tailscale up --authkey="$TAILSCALE_AUTHKEY"
    else
        echo "!! Run 'sudo tailscale up' to authenticate."
    fi
fi

echo "==> Checking secrets..."
if [[ ! -f secrets/.env ]]; then
    echo "!! secrets/.env not found. Copy secrets/.env.example to secrets/.env and fill in values."
    exit 1
fi

if [[ ! -f secrets/enable_banking.pem ]]; then
    echo "==> Generating Enable Banking key pair..."
    openssl genrsa -out secrets/enable_banking.pem 2048
    openssl rsa -in secrets/enable_banking.pem -pubout -out secrets/enable_banking_public.pem
    chmod 600 secrets/enable_banking.pem
    echo "!! Upload secrets/enable_banking_public.pem to your Enable Banking application,"
    echo "   paste the returned APP_ID into secrets/.env, then re-run this script."
    exit 0
fi

echo "==> Starting Docker stack..."
docker compose -f compose/docker-compose.yml up -d postgres

echo "==> Waiting for Postgres to be healthy..."
sleep 5
until docker compose -f compose/docker-compose.yml exec -T postgres pg_isready -U finance; do
    sleep 2
done

echo "==> Applying schema..."
docker compose -f compose/docker-compose.yml exec -T postgres \
    psql -U finance -d finance < app/sql/001_init.sql || true
docker compose -f compose/docker-compose.yml exec -T postgres \
    psql -U finance -d finance < app/sql/002_seed_rules.sql || true

echo "==> Building app container..."
docker compose -f compose/docker-compose.yml build app

echo "==> Starting all services..."
docker compose -f compose/docker-compose.yml up -d

echo ""
echo "==> Setup done."
echo ""
echo "Next steps:"
echo "  1. Bootstrap Enable Banking (one-time, do this in the next 90 days):"
echo "       docker compose -f compose/docker-compose.yml run --rm -it app python -m src.bootstrap_eb"
echo ""
echo "  2. Bootstrap Trade Republic (one-time):"
echo "       docker compose -f compose/docker-compose.yml run --rm -it app pytr login"
echo ""
echo "  3. Visit the dashboard:    http://$(hostname).local:8501"
echo "     Visit Grafana:          http://$(hostname).local:3000"
echo ""
echo "  4. Enable the daily sync timer:"
echo "       sudo cp scripts/finance-sync.{service,timer} /etc/systemd/system/"
echo "       sudo systemctl enable --now finance-sync.timer"
