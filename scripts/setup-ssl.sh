#!/bin/bash
# =============================================================================
# Warungio Marketplace — SSL Certificate Setup (Let's Encrypt)
# =============================================================================
# Usage:
#   sudo bash scripts/setup-ssl.sh                    # Interactive setup
#   sudo bash scripts/setup-ssl.sh --renew            # Renew existing certs
#   sudo bash scripts/setup-ssl.sh --domain DOMAIN    # Custom domain
#
# Prerequisites:
#   - Server must be publicly accessible on port 80 (HTTP)
#   - DNS A record pointing to this server's IP
#   - Docker & Docker Compose installed
# =============================================================================
# This script:
#   1. Installs Certbot if not present
#   2. Obtains Let's Encrypt SSL certificate for warungio.web.id
#   3. Converts certs to Nginx format (warungio.crt + warungio.key)
#   4. Restarts Nginx with SSL enabled
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
step()  { echo -e "\n${CYAN}▶ $1${NC}"; }

# ─── Defaults ────────────────────────────────────────────────────────────────
DOMAIN="warungio.web.id"
EMAIL="admin@warungio.com"
SSL_DIR="$(cd "$(dirname "$0")/.." && pwd)/nginx/ssl"
COMPOSE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILES=(-f docker-compose.yml -f docker-compose.prod.yml)

# ─── Parse arguments ─────────────────────────────────────────────────────────
RENEW_MODE=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --domain)   DOMAIN="$2"; shift 2 ;;
        --email)    EMAIL="$2"; shift 2 ;;
        --renew)    RENEW_MODE=true; shift ;;
        --help|-h)
            echo "Usage: sudo bash $0 [--domain DOMAIN] [--email EMAIL] [--renew]"
            echo ""
            echo "  --domain DOMAIN   Domain to get certificate for (default: warungio.web.id)"
            echo "  --email EMAIL     Email for Let's Encrypt notifications (default: admin@warungio.com)"
            echo "  --renew           Renew existing certificate instead of creating new one"
            echo "  --help            Show this help"
            exit 0
            ;;
        *)          error "Unknown option: $1"; exit 1 ;;
    esac
done

# ─── Check root ──────────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root (sudo)."
    echo "  sudo bash $0"
    exit 1
fi

# ─── Banner ──────────────────────────────────────────────────────────────────
echo ""
echo "╔═══════════════════════════════════════════════╗"
echo "║   Warungio SSL Setup — Let's Encrypt          ║"
echo "╚═══════════════════════════════════════════════╝"
echo ""
echo "  Domain:       $DOMAIN"
echo "  Email:        $EMAIL"
echo "  SSL target:   $SSL_DIR"
echo "  Mode:         $( $RENEW_MODE && echo 'Renew' || echo 'New certificate' )"
echo ""

# ══════════════════════════════════════════════════════════════════════════════
# 1. Install Certbot
# ══════════════════════════════════════════════════════════════════════════════
step "1. Checking/installing Certbot..."

if ! command -v certbot &>/dev/null; then
    info "Installing Certbot..."
    apt-get update -qq
    apt-get install -y -qq certbot 2>&1 | tail -1
    info "Certbot installed: $(certbot --version 2>&1)"
else
    info "Certbot already installed: $(certbot --version 2>&1)"
fi

# ══════════════════════════════════════════════════════════════════════════════
# 2. Ensure SSL directory exists
# ══════════════════════════════════════════════════════════════════════════════
step "2. Ensuring SSL directory exists..."
mkdir -p "$SSL_DIR"
info "SSL directory: $SSL_DIR"

# ══════════════════════════════════════════════════════════════════════════════
# 3. Free port 80 for Certbot standalone mode (only for new certs)
# ══════════════════════════════════════════════════════════════════════════════
if [ "$RENEW_MODE" = false ]; then
    step "3. Freeing port 80 for certificate challenge..."

    # Check if Docker Nginx is running
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q warungio-nginx; then
        warn "Stopping Nginx container to free port 80..."
        cd "$COMPOSE_DIR"
        docker compose "${COMPOSE_FILES[@]}" stop nginx
        info "Nginx container stopped. Other services remain running."
    fi

    # Check if port 80 is still in use by anything else
    if ss -tlnp 2>/dev/null | grep -q ':80 '; then
        PORT_80_PROC=$(ss -tlnp 2>/dev/null | grep ':80 ' | head -1)
        error "Port 80 is still in use by: $PORT_80_PROC"
        error "Certbot standalone mode requires exclusive access to port 80."
        error "Please stop the other service first, then re-run this script."
        exit 1
    fi

    info "Port 80 is free."
else
    step "3. Skipping port checks (renew mode uses existing config)"
fi

# ══════════════════════════════════════════════════════════════════════════════
# 4. Obtain SSL Certificate
# ══════════════════════════════════════════════════════════════════════════════
step "4. Obtaining Let's Encrypt certificate..."

if [ "$RENEW_MODE" = true ]; then
    info "Renewing existing certificate..."
    certbot renew --non-interactive --agree-tos --email "$EMAIL"
else
    info "Requesting new certificate for $DOMAIN..."
    certbot certonly --standalone \
        --non-interactive \
        --agree-tos \
        --email "$EMAIL" \
        -d "$DOMAIN" \
        -d "www.$DOMAIN"
fi

# ══════════════════════════════════════════════════════════════════════════════
# 5. Copy certificates to Nginx SSL directory
# ══════════════════════════════════════════════════════════════════════════════
step "5. Copying certificates to Nginx SSL directory..."

LETSENCRYPT_DIR="/etc/letsencrypt/live/$DOMAIN"

if [ ! -f "$LETSENCRYPT_DIR/fullchain.pem" ]; then
    error "Certificate not found at $LETSENCRYPT_DIR"
    error "Let's Encrypt may have failed. Check the output above."
    exit 1
fi

# Copy fullchain.pem → warungio.crt
cp "$LETSENCRYPT_DIR/fullchain.pem" "$SSL_DIR/warungio.crt"
chmod 644 "$SSL_DIR/warungio.crt"
info "Copied: fullchain.pem -> warungio.crt"

# Copy privkey.pem → warungio.key
cp "$LETSENCRYPT_DIR/privkey.pem" "$SSL_DIR/warungio.key"
chmod 600 "$SSL_DIR/warungio.key"
info "Copied: privkey.pem -> warungio.key"

# Verify certificates
echo ""
info "Certificate details:"
openssl x509 -in "$SSL_DIR/warungio.crt" -noout -subject -dates -issuer 2>&1
echo ""

# ══════════════════════════════════════════════════════════════════════════════
# 6. Restart Nginx with SSL
# ══════════════════════════════════════════════════════════════════════════════
step "6. Restarting Nginx with SSL enabled..."

cd "$COMPOSE_DIR"

# Start the full stack (in case nginx was stopped earlier)
info "Starting all services..."
docker compose "${COMPOSE_FILES[@]}" up -d

# Wait for health check (django port, proxied through nginx)
info "Waiting for health check..."
for i in $(seq 1 30); do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/health/" 2>/dev/null || echo "000")
    if [ "$STATUS" = "200" ]; then
        echo ""
        info "Health check passed! (HTTP $STATUS)"
        break
    fi
    echo -n "."
    sleep 3
done
echo ""

# Verify nginx syntax — fail loudly if config is invalid
info "Verifying nginx configuration..."
if ! docker compose "${COMPOSE_FILES[@]}" exec nginx nginx -t 2>&1; then
    error "Nginx configuration is invalid! Check the errors above."
    error "Run: docker compose ${COMPOSE_FILES[*]} exec nginx nginx -t"
    exit 1
fi

# ══════════════════════════════════════════════════════════════════════════════
# 7. Verify HTTPS
# ══════════════════════════════════════════════════════════════════════════════
step "7. Verifying HTTPS access..."

sleep 2

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://$DOMAIN/" 2>/dev/null || echo "FAIL")
HTTPS_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN/" 2>/dev/null || echo "FAIL")
SSL_EXPIRY=$(openssl x509 -in "$SSL_DIR/warungio.crt" -noout -enddate 2>/dev/null | cut -d= -f2 || echo "unknown")

# Check for existing certbot auto-renewal timer
CERTBOT_TIMER=$(systemctl list-timers 2>/dev/null | grep certbot || echo "")

echo ""
echo "╔═══════════════════════════════════════════════╗"
echo "║   SSL Setup Summary                           ║"
echo "╚═══════════════════════════════════════════════╝"
echo ""
echo "  Domain:              $DOMAIN"
printf "  HTTP (port 80):      "
if [ "$HTTP_CODE" = "200" ]; then echo -e "${GREEN}OK${NC}"; else echo -e "${RED}FAIL ($HTTP_CODE)${NC}"; fi
printf "  HTTPS (port 443):    "
if [ "$HTTPS_CODE" = "200" ]; then echo -e "${GREEN}OK${NC}"; else echo -e "${RED}FAIL ($HTTPS_CODE)${NC}"; fi
echo "  SSL certificate:     $SSL_DIR/warungio.crt"
echo "  SSL key:             $SSL_DIR/warungio.key"
echo "  Certificate expiry:  $SSL_EXPIRY"
echo ""

# ─── Auto-renewal info ───────────────────────────────────────────────────────
if [ -n "$CERTBOT_TIMER" ]; then
    echo -e "  ${GREEN}Certbot auto-renewal timer is active:${NC}"
    echo "  $CERTBOT_TIMER"
else
    echo -e "  ${YELLOW}No certbot auto-renewal timer detected.${NC}"
    echo "  Install it manually with one of:"
    echo ""
    echo "  Option A — Systemd timer (recommended):"
    echo "    sudo systemctl enable certbot.timer"
    echo "    sudo systemctl start certbot.timer"
    echo ""
    echo "  Option B — Cron job:"
    echo "    echo '0 3 * * * root certbot renew --quiet && docker exec warungio-nginx nginx -s reload' |"
    echo "      sudo tee /etc/cron.d/warungio-ssl-renew"
fi
echo ""

# ─── Final status ────────────────────────────────────────────────────────────
if [ "$HTTPS_CODE" = "200" ]; then
    echo -e "  ${GREEN}SUCCESS: HTTPS is working!${NC}"
    echo ""
    echo "  Verify at: https://$DOMAIN"
elif [ "$HTTPS_CODE" = "FAIL" ]; then
    echo -e "  ${YELLOW}HTTPS check returned connection error. Check Nginx logs:${NC}"
    echo "     docker compose ${COMPOSE_FILES[*]} logs nginx"
    echo "     docker compose ${COMPOSE_FILES[*]} exec nginx nginx -t"
    echo ""
    echo "  The app is still accessible via HTTP at http://$DOMAIN"
else
    echo -e "  ${YELLOW}HTTPS check returned HTTP $HTTPS_CODE. Check the output above.${NC}"
fi

echo ""
exit 0
