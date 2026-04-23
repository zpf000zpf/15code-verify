#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# 15code Verify — one-command remote install
#
# Usage (on a fresh Ubuntu 22.04+ server, as root):
#   curl -fsSL https://raw.githubusercontent.com/15code/verify/main/deploy/install/remote-install.sh | sudo bash
#
# Options (env vars):
#   DOMAIN       — public domain, default: verify.15code.com
#   EMAIL        — Let's Encrypt email, default: ops@15code.com
#   INSTALL_DIR  — default: /opt/15code-verify
#   BRANCH       — git branch, default: main
#   SKIP_SSL     — set to 1 to skip cert, default: 0
# ═══════════════════════════════════════════════════════════════════════
set -euo pipefail

DOMAIN="${DOMAIN:-verify.15code.com}"
EMAIL="${EMAIL:-ops@15code.com}"
INSTALL_DIR="${INSTALL_DIR:-/opt/15code-verify}"
BRANCH="${BRANCH:-main}"
SKIP_SSL="${SKIP_SSL:-0}"

log()  { echo -e "\033[1;36m[15code-verify]\033[0m $*"; }
warn() { echo -e "\033[1;33m[warn]\033[0m $*"; }
die()  { echo -e "\033[1;31m[error]\033[0m $*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Must run as root (use sudo)."

log "Starting deployment on $(hostname)"
log "  Domain      : $DOMAIN"
log "  Install dir : $INSTALL_DIR"
log "  Branch      : $BRANCH"

# ─── 1. System deps ───────────────────────────────────────────────────
log "Installing system dependencies..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
  ca-certificates curl gnupg lsb-release \
  git nginx certbot python3-certbot-nginx \
  ufw unattended-upgrades

# ─── 2. Docker ────────────────────────────────────────────────────────
if ! command -v docker >/dev/null 2>&1; then
  log "Installing Docker..."
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
else
  log "Docker already installed: $(docker --version)"
fi

# ─── 3. Clone / pull source ───────────────────────────────────────────
log "Fetching source (branch: $BRANCH)..."
if [[ -d "$INSTALL_DIR/.git" ]]; then
  cd "$INSTALL_DIR"
  git fetch --all
  git checkout "$BRANCH"
  git pull --ff-only
else
  mkdir -p "$(dirname "$INSTALL_DIR")"
  git clone -b "$BRANCH" https://github.com/15code/verify.git "$INSTALL_DIR"
  cd "$INSTALL_DIR"
fi

# ─── 4. Env file ──────────────────────────────────────────────────────
ENV_FILE="$INSTALL_DIR/deploy/docker/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  log "Writing default env file at $ENV_FILE"
  cp "$INSTALL_DIR/deploy/docker/.env.example" "$ENV_FILE"
  sed -i "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=https://$DOMAIN|" "$ENV_FILE"
  sed -i "s|CORS_ORIGINS=.*|CORS_ORIGINS=https://$DOMAIN|" "$ENV_FILE"
fi

# ─── 5. Build + run containers ────────────────────────────────────────
log "Building & starting services..."
cd "$INSTALL_DIR/deploy/docker"
docker compose pull 2>/dev/null || true
docker compose up -d --build

# Wait for containers to be healthy
log "Waiting for services to come up..."
for i in {1..30}; do
  if curl -fs http://localhost:8000/health >/dev/null 2>&1 &&
     curl -fs http://localhost:3000/ >/dev/null 2>&1; then
    log "Services healthy ✓"
    break
  fi
  sleep 2
done

# ─── 6. Nginx reverse proxy ───────────────────────────────────────────
log "Configuring nginx..."
NGINX_CONF="/etc/nginx/sites-available/$DOMAIN"
cp "$INSTALL_DIR/deploy/nginx/verify.15code.com.conf" "$NGINX_CONF"
sed -i "s|verify.15code.com|$DOMAIN|g" "$NGINX_CONF"
ln -sf "$NGINX_CONF" "/etc/nginx/sites-enabled/$DOMAIN"
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

# ─── 7. Firewall ──────────────────────────────────────────────────────
log "Configuring firewall..."
ufw --force enable
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw reload

# ─── 8. HTTPS via Let's Encrypt ───────────────────────────────────────
if [[ "$SKIP_SSL" != "1" ]]; then
  log "Obtaining HTTPS certificate for $DOMAIN..."
  certbot --nginx -d "$DOMAIN" \
    --non-interactive --agree-tos -m "$EMAIL" --redirect || \
    warn "Certbot failed — check DNS and retry: sudo certbot --nginx -d $DOMAIN"
else
  warn "Skipping HTTPS setup (SKIP_SSL=1)"
fi

# ─── 9. Systemd unit for auto-restart ────────────────────────────────
log "Installing systemd unit for auto-restart on reboot..."
cp "$INSTALL_DIR/deploy/systemd/15code-verify.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable 15code-verify.service

# ─── 10. Summary ─────────────────────────────────────────────────────
cat <<SUMMARY

╭─────────────────────────────────────────────────────────────╮
│  ✅ 15code Verify deployed successfully                      │
│                                                              │
│   Web UI     : https://$DOMAIN
│   API        : https://$DOMAIN/api
│   Health     : curl https://$DOMAIN/health
│                                                              │
│   Install dir: $INSTALL_DIR
│   Env file   : $ENV_FILE
│                                                              │
│   Logs       : docker compose -f $INSTALL_DIR/deploy/docker/docker-compose.yml logs -f
│   Restart    : systemctl restart 15code-verify
│   Update     : cd $INSTALL_DIR && git pull && \\
│                docker compose -f deploy/docker/docker-compose.yml up -d --build
╰─────────────────────────────────────────────────────────────╯

Next steps:
  1) Visit https://$DOMAIN and verify the page loads
  2) Edit $ENV_FILE to add optional ANTHROPIC_API_KEY / OPENAI_API_KEY
     for ground-truth baseline collection
  3) Set up periodic baseline refresh: see docs/DEPLOYMENT.md

SUMMARY
