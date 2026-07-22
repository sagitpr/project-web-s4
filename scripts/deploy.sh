#!/bin/bash
# =============================================================================
# Warungio Marketplace — Deployment Script
# =============================================================================
# Usage:
#   ./scripts/deploy.sh                      # Deploy with latest code
#   ./scripts/deploy.sh --build              # Force rebuild with cache
#   ./scripts/deploy.sh --no-cache           # Rebuild from scratch
#   ./scripts/deploy.sh --check              # Health check only
#   ./scripts/deploy.sh --validate           # Full endpoint validation only
#
# Changelog:
#   - Auto-generates self-signed SSL certs if Let's Encrypt certs missing
#   - Auto-detects Let's Encrypt certs and copies to nginx/ssl/
#   - Validates nginx config before starting
#   - Checks /etc/hosts for incorrect domain→localhost mapping
#   - Verifies production config is used (not dev override)
#   - Runs full endpoint validation after deploy (/, /robots.txt, etc.)
#   - Checks firewall and reports port status
# =============================================================================

set -e  # Exit on any error

# ─── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ─── Defaults ────────────────────────────────────────────────────────────────
# CRITICAL: Always use explicit -f flags to prevent docker-compose.override.yml
# from being auto-loaded in production. Base docker-compose.yml now uses
# warungio.conf (production SSL config) by default.
COMPOSE_FILES=(-f docker-compose.yml -f docker-compose.prod.yml)
SERVICE_NAME="django"
HEALTH_CHECK_URL="http://localhost:8000/health/"
HEALTH_RETRIES=30
HEALTH_DELAY=5
DOMAIN="warungio.web.id"

SSL_DIR="$(cd "$(dirname "$0")/.." && pwd)/nginx/ssl"

# Disable colors if not a terminal
if [ ! -t 1 ]; then
    RED=''; GREEN=''; YELLOW=''; BLUE=''; NC=''
fi

# ─── Auto-generate self-signed SSL certs if missing ───────────────────────────
generate_selfsigned_certs() {
    if [ -f "$SSL_DIR/warungio.crt" ] && [ -f "$SSL_DIR/warungio.key" ]; then
        echo -e "  ${GREEN}✅ SSL certificates found in $SSL_DIR${NC}"
        return 0
    fi

    echo -e "  ${YELLOW}⚠️  SSL certificates not found! Generating self-signed...${NC}"
    mkdir -p "$SSL_DIR"

    # Create OpenSSL config
    local CONFIG_FILE="$SSL_DIR/openssl-tmp.cnf"
    cat > "$CONFIG_FILE" << 'EOF'
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no
[req_distinguished_name]
C = ID
ST = Jakarta
L = Jakarta
O = Warungio
CN = warungio.web.id
[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names
[alt_names]
DNS.1 = warungio.web.id
DNS.2 = www.warungio.web.id
EOF

    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$SSL_DIR/warungio.key" \
        -out "$SSL_DIR/warungio.crt" \
        -config "$CONFIG_FILE" 2>&1
    rm -f "$CONFIG_FILE"

    echo -e "  ${GREEN}✅ Self-signed certificates generated:${NC}"
    echo -e "     Cert: $SSL_DIR/warungio.crt"
    echo -e "     Key:  $SSL_DIR/warungio.key"
    echo -e "  ${YELLOW}⚠️  Replace with Let's Encrypt certs for production:${NC}"
    echo -e "     sudo bash scripts/setup-ssl.sh"
}

# ─── Auto-detect Let's Encrypt certs (preferred over self-signed) ────────────
setup_letsencrypt_certs() {
    local LE_DIR="/etc/letsencrypt/live/$DOMAIN"
    if [ -f "$LE_DIR/fullchain.pem" ] && [ -f "$LE_DIR/privkey.pem" ]; then
        echo -e "  ${BLUE}   Let's Encrypt certificates found at $LE_DIR${NC}"
        echo "   Copying to $SSL_DIR/ for nginx..."
        cp "$LE_DIR/fullchain.pem" "$SSL_DIR/warungio.crt"
        cp "$LE_DIR/privkey.pem" "$SSL_DIR/warungio.key"
        chmod 644 "$SSL_DIR/warungio.crt"
        chmod 600 "$SSL_DIR/warungio.key"
        echo -e "  ${GREEN}✅ Let's Encrypt certs deployed to nginx/ssl/${NC}"
        return 0
    fi
    return 1
}

# ─── Check /etc/hosts for incorrect warungio.web.id → 127.0.0.1 mapping ────
check_hosts_file() {
    echo ""
    echo -e "${BLUE}   Checking /etc/hosts for domain misconfiguration...${NC}"

    if grep -E '^127\.0\.0\.1.*warungio\.web\.id' /etc/hosts 2>/dev/null; then
        echo -e "  ${RED}❌ CRITICAL: /etc/hosts maps $DOMAIN → 127.0.0.1!${NC}"
        echo "     This causes the public domain to resolve to localhost."
        echo ""
        echo -e "  ${YELLOW}   Auto-fixing: removing $DOMAIN from 127.0.0.1 line...${NC}"
        sed -i "s/127\\.0\\.0\\.1.*$DOMAIN/127.0.0.1 localhost/" /etc/hosts
        echo -e "  ${GREEN}✅ /etc/hosts fixed.${NC}"
        echo ""
        echo "  To verify:"
        echo "     getent hosts $DOMAIN"
        return 1
    fi

    # Also check if domain resolves to expected IP
    local DNS_IP=$(getent hosts "$DOMAIN" 2>/dev/null | awk '{print $1}')
    if [ -n "$DNS_IP" ] && [ "$DNS_IP" != "127.0.0.1" ] && [ "$DNS_IP" != "::1" ]; then
        echo -e "  ${GREEN}✅ Domain $DOMAIN resolves to $DNS_IP (not localhost)${NC}"
    elif [ -z "$DNS_IP" ]; then
        echo -e "  ${YELLOW}   ⚠️  Could not resolve $DOMAIN (DNS may not be configured)${NC}"
    else
        echo -e "  ${YELLOW}   ⚠️  $DOMAIN resolves to $DNS_IP (localhost) — check /etc/hosts${NC}"
    fi
}

# ─── Verify production nginx config is used (not dev override) ──────────────
check_production_config() {
    echo ""
    echo -e "${BLUE}   Verifying production nginx config...${NC}"

    if docker compose "${COMPOSE_FILES[@]}" ps 2>/dev/null | grep -q "nginx.*Up"; then
        local MOUNTED_CONF=$(docker compose "${COMPOSE_FILES[@]}" exec -T nginx cat /etc/nginx/conf.d/warungio.conf 2>/dev/null | grep -c "warungio.web.id" || echo 0)
        if [ "$MOUNTED_CONF" -gt 0 ]; then
            echo -e "  ${GREEN}✅ Production config confirmed (contains warungio.web.id server_name)${NC}"
        else
            echo -e "  ${RED}❌ PRODUCTION CONFIG NOT DETECTED!${NC}"
            echo "     The mounted warungio.conf does not contain production server_name."
            echo "     This means docker-compose.override.yml is overriding with dev config!"
            echo ""
            echo "  Run with explicit -f flags:"
            echo "     docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d"
            return 1
        fi
    fi
}

# ─── Validate nginx config + show container/logs status ─────────────────────
validate_nginx_config() {
    echo -e "${BLUE}   Validating nginx configuration...${NC}"
    if docker compose "${COMPOSE_FILES[@]}" exec -T nginx nginx -t 2>&1; then
        echo -e "  ${GREEN}✅ Nginx config syntax: VALID${NC}"
    else
        echo -e "${RED}  ❌ Nginx config has errors!${NC}"
        echo "     Check: docker compose ${COMPOSE_FILES[*]} exec nginx nginx -t"
        echo "     Common issues:"
        echo "       - SSL cert paths wrong (check nginx/warungio.conf)"
        echo "       - server_name mismatch (check nginx/warungio.conf)"
        return 1
    fi

    # Show container status
    echo ""
    echo -e "${BLUE}   === Container Status (docker compose ps) ===${NC}"
    docker compose "${COMPOSE_FILES[@]}" ps

    # Show nginx logs
    echo ""
    echo -e "${BLUE}   === Nginx Logs (last 30 lines) ===${NC}"
    docker compose "${COMPOSE_FILES[@]}" logs nginx --tail=30 2>&1 || echo "   (No logs yet)"
}

# ─── Full endpoint validation ────────────────────────────────────────────────
validate_endpoints() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
    echo -e "${BLUE}   Production Endpoint Validation${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
    echo ""

    local ALL_OK=true

    # Test HTTP (should redirect to HTTPS)
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://$DOMAIN/" 2>/dev/null || echo "FAIL")
    HTTP_REDIRECT=$(curl -s -o /dev/null -w "%{redirect_url}" "http://$DOMAIN/" 2>/dev/null || echo "")
    if [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "308" ]; then
        printf "  %-25s %s\n" "HTTP → HTTPS redirect:" "${GREEN}✅ $HTTP_CODE${NC}"
    else
        printf "  %-25s %s\n" "HTTP → HTTPS redirect:" "${RED}❌ $HTTP_CODE${NC}"
        ALL_OK=false
    fi

    # Test HTTPS /
    HTTPS_CODE=$(curl -sk -o /dev/null -w "%{http_code}" "https://$DOMAIN/" 2>/dev/null || echo "FAIL")
    if [ "$HTTPS_CODE" = "200" ]; then
        printf "  %-25s %s\n" "HTTPS /:" "${GREEN}✅ $HTTPS_CODE${NC}"
    else
        printf "  %-25s %s\n" "HTTPS /:" "${RED}❌ $HTTPS_CODE${NC}"
        ALL_OK=false
    fi

    # Test /robots.txt
    ROBOTS_CODE=$(curl -sk -o /dev/null -w "%{http_code}" "https://$DOMAIN/robots.txt" 2>/dev/null || echo "FAIL")
    if [ "$ROBOTS_CODE" = "200" ]; then
        printf "  %-25s %s\n" "HTTPS /robots.txt:" "${GREEN}✅ $ROBOTS_CODE${NC}"
    else
        printf "  %-25s %s\n" "HTTPS /robots.txt:" "${RED}❌ $ROBOTS_CODE${NC}"
        ALL_OK=false
    fi

    # Test /sitemap.xml
    SITEMAP_CODE=$(curl -sk -o /dev/null -w "%{http_code}" "https://$DOMAIN/sitemap.xml" 2>/dev/null || echo "FAIL")
    if [ "$SITEMAP_CODE" = "200" ]; then
        printf "  %-25s %s\n" "HTTPS /sitemap.xml:" "${GREEN}✅ $SITEMAP_CODE${NC}"
    else
        printf "  %-25s %s\n" "HTTPS /sitemap.xml:" "${RED}❌ $SITEMAP_CODE${NC}"
        ALL_OK=false
    fi

    # Test /health/
    HEALTH_CODE=$(curl -sk -o /dev/null -w "%{http_code}" "https://$DOMAIN/health/" 2>/dev/null || echo "FAIL")
    if [ "$HEALTH_CODE" = "200" ]; then
        printf "  %-25s %s\n" "HTTPS /health/:" "${GREEN}✅ $HEALTH_CODE${NC}"
    else
        printf "  %-25s %s\n" "HTTPS /health/:" "${RED}❌ $HEALTH_CODE${NC}"
        ALL_OK=false
    fi

    # SSL cert info
    SSL_EXPIRY=$(openssl s_client -connect "$DOMAIN:443" -servername "$DOMAIN" 2>/dev/null </dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2 || echo "unknown")
    if [ "$SSL_EXPIRY" != "unknown" ]; then
        printf "  %-25s %s\n" "SSL certificate expiry:" "$SSL_EXPIRY"
    fi

    echo ""
    if [ "$ALL_OK" = true ]; then
        echo -e "${GREEN}  ✅ ALL ENDPOINTS PASSED — Production server is LIVE!${NC}"
        return 0
    else
        echo -e "${RED}  ❌ Some endpoints failed. Check nginx logs:${NC}"
        echo "     docker compose ${COMPOSE_FILES[*]} logs nginx --tail=30"
        return 1
    fi
}

# ─── Check monitoring containers (profile-based, not started by default) ──
check_monitoring() {
    echo ""
    echo -e "${BLUE}   Checking monitoring services...${NC}"
    local MON_COUNT=$(docker compose "${COMPOSE_FILES[@]}" ps 2>/dev/null | grep -c -E 'prometheus|node_exporter|cadvisor' || echo 0)
    if [ "$MON_COUNT" -gt 0 ]; then
        echo -e "  ${GREEN}✅ Monitoring containers: ${MON_COUNT} running${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Monitoring containers not running (profile-based, start manually with --profile monitoring)${NC}"
        echo "     docker compose --profile monitoring up -d"
    fi
}

# ─── Setup UFW firewall (run once per machine, idempotent) ────────────────
setup_firewall() {
    echo ""
    echo -e "${BLUE}   Setting up UFW firewall...${NC}"

    if ! command -v ufw &>/dev/null; then
        echo -e "  ${YELLOW}   ⚠️  UFW not available. Install with: apt-get install -y ufw${NC}"
        return 0
    fi

    # Check if UFW is already active with correct rules
    local UFW_STATUS=$(sudo ufw status 2>&1)
    if echo "$UFW_STATUS" | grep -q "Status: active"; then
        echo -e "  ${GREEN}✅ UFW already active${NC}"
        echo "   $(sudo ufw status verbose 2>&1 | head -10)"
        return 0
    fi

    echo -e "  ${YELLOW}   Configuring UFW rules...${NC}"

    # Default deny incoming, allow outgoing
    sudo ufw default deny incoming 2>/dev/null || true
    sudo ufw default allow outgoing 2>/dev/null || true

    # Allow essential ports
    sudo ufw allow 22/tcp comment 'SSH'
    sudo ufw allow 80/tcp comment 'HTTP'
    sudo ufw allow 443/tcp comment 'HTTPS'

    # Enable UFW (non-interactive)
    echo "y" | sudo ufw enable 2>&1 || true

    echo -e "  ${GREEN}✅ UFW configured: SSH(22), HTTP(80), HTTPS(443) allowed${NC}"
    echo "   $(sudo ufw status verbose 2>&1 | head -15)"
}

# ─── Firewall check ──────────────────────────────────────────────────────────
check_firewall() {
    echo ""
    echo -e "${BLUE}   Checking firewall/port status...${NC}"

    if command -v ufw &>/dev/null; then
        echo "   $(sudo ufw status 2>&1)"
    elif command -v iptables &>/dev/null; then
        echo "   $(sudo iptables -L -n 2>/dev/null | grep -E '80|443|ACCEPT|DROP' || echo 'No rules found for 80/443')"
    elif command -v firewall-cmd &>/dev/null; then
        echo "   $(sudo firewall-cmd --list-all 2>&1)"
    else
        echo -e "  ${YELLOW}   ⚠️  No firewall tool detected. Check cloud provider firewall manually.${NC}"
    fi

    # Check if ports are listening from inside Docker
    if docker compose "${COMPOSE_FILES[@]}" ps 2>/dev/null | grep -q nginx; then
        echo "   Checking port bindings..."
        docker compose "${COMPOSE_FILES[@]}" ps nginx 2>/dev/null | grep -E '80|443'
    fi
}

# ══════════════════════════════════════════════════════════════════════════════
# MAIN DEPLOYMENT FLOW
# ══════════════════════════════════════════════════════════════════════════════

# ─── Parse arguments ─────────────────────────────────────────────────────────
BUILD_FLAG=""
case "${1:-}" in
    --build)
        BUILD_FLAG="--build"
        echo -e "${BLUE}▶  Rebuilding with cache...${NC}"
        ;;
    --no-cache)
        BUILD_FLAG="--no-cache --pull"
        echo -e "${YELLOW}▶  Rebuilding from scratch (no cache)...${NC}"
        ;;
    --validate)
        validate_endpoints
        exit $?
        ;;
    --check)
        echo -e "${BLUE}▶  Health check only...${NC}"
        ./scripts/deploy.sh --health-check
        exit $?
        ;;
    --health-check)
        echo -e "${BLUE}Checking service health...${NC}"
        for i in $(seq 1 $HEALTH_RETRIES); do
            STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_CHECK_URL" 2>/dev/null || echo "000")
            if [ "$STATUS" = "200" ]; then
                echo -e "${GREEN}✅ Service is healthy (HTTP 200)${NC}"
                exit 0
            fi
            echo "   Waiting for service... ($i/$HEALTH_RETRIES)"
            sleep $HEALTH_DELAY
        done
        echo -e "${RED}❌ Service health check failed after $HEALTH_RETRIES retries${NC}"
        exit 1
        ;;
    *)
        echo -e "${BLUE}▶  Standard deployment...${NC}"
        ;;
esac

# ─── Step 0: SSL certificates (Let's Encrypt first, then self-signed) ────────
echo ""
echo "╔═══════════════════════════════════════════════╗"
echo "║   Warungio Deployment                         ║"
echo "╚═══════════════════════════════════════════════╝"
echo ""

echo -e "${BLUE}[0/7]${NC} Checking SSL certificates..."
# Try Let's Encrypt first (preferred for production)
setup_letsencrypt_certs
# Fall back to self-signed if no LE certs
generate_selfsigned_certs

# ─── Step 1: Git Pull ────────────────────────────────────────────────────────
echo -e "${BLUE}[1/7]${NC} Pulling latest code from Git..."
git pull --ff-only
echo -e "${GREEN}  ✅ Git pull complete.${NC}"

# ─── Step 2: Log Environment Info ────────────────────────────────────────────
echo ""
echo -e "${BLUE}[2/7]${NC} Checking environment..."
echo "  Branch:   $(git rev-parse --abbrev-ref HEAD)"
echo "  Commit:   $(git rev-parse --short HEAD)"
echo "  Time:     $(date '+%Y-%m-%d %H:%M:%S')"

# Verify .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}  ❌ .env file not found! Create it from .env.example${NC}"
    exit 1
fi
echo -e "${GREEN}  ✅ .env file found.${NC}"

# ─── Step 3: Build Docker Images ─────────────────────────────────────────────
echo ""
echo -e "${BLUE}[3/7]${NC} Building Docker images..."
if [ "${BUILD_FLAG}" = "--no-cache --pull" ]; then
    docker compose "${COMPOSE_FILES[@]}" build --no-cache --pull
elif [ "${BUILD_FLAG}" = "--build" ]; then
    docker compose "${COMPOSE_FILES[@]}" build
else
    echo "  Building with cache..."
    docker compose "${COMPOSE_FILES[@]}" build
fi
echo -e "${GREEN}  ✅ Build complete.${NC}"

# ─── Step 4: Start Services ─────────────────────────────────────────────────
echo ""
echo -e "${BLUE}[4/7]${NC} Starting services..."
echo "  Running: docker compose ${COMPOSE_FILES[*]} up -d"

docker compose "${COMPOSE_FILES[@]}" up -d

echo -e "${GREEN}  ✅ Services started.${NC}"

# ─── Step 5: Wait for Health Check ───────────────────────────────────────────
echo ""
echo -e "${BLUE}[5/7]${NC} Waiting for health check..."
for i in $(seq 1 $HEALTH_RETRIES); do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_CHECK_URL" 2>/dev/null || echo "000")
    if [ "$STATUS" = "200" ]; then
        echo -e "${GREEN}  ✅ Service is healthy (HTTP 200)${NC}"
        break
    fi
    echo "   Waiting... ($i/$HEALTH_RETRIES)"
    sleep $HEALTH_DELAY
done

if [ "$STATUS" != "200" ]; then
    echo -e "${RED}  ❌ Health check failed after $HEALTH_RETRIES retries.${NC}"
    echo ""
    echo "Checking logs..."
    docker compose "${COMPOSE_FILES[@]}" logs --tail=30 "$SERVICE_NAME"
    exit 1
fi

# ─── Step 6: Full validation ────────────────────────────────────────────────
echo ""
echo -e "${BLUE}[6/7]${NC} Validating deployment..."

check_hosts_file
check_production_config
validate_nginx_config
check_monitoring
setup_firewall
check_firewall

# ─── Step 7: Endpoint validation ─────────────────────────────────────────────
echo ""
echo -e "${BLUE}[7/7]${NC} Checking endpoints..."
validate_endpoints

# ─── Summary ──────────────────────────────────────────────────────────────────
STATUS=$?
echo ""
echo "╔═══════════════════════════════════════════════╗"
echo "║   Deployment Complete!                        ║"
echo "╚═══════════════════════════════════════════════╝"
echo ""
echo -e "  ${GREEN}✅${NC} Git pull:            done"
echo -e "  ${GREEN}✅${NC} SSL certs:           ready"
echo -e "  ${GREEN}✅${NC} Docker build:        done"
echo -e "  ${GREEN}✅${NC} Services up:         done"
echo -e "  ${GREEN}✅${NC} Health check:        passed"
echo -e "  ${GREEN}✅${NC} Nginx config:        validated"
echo -e "  ${GREEN}✅${NC} Config check:        production config confirmed"
echo -e "  ${GREEN}✅${NC} Endpoints:           validated"
echo ""

if [ $STATUS -eq 0 ]; then
    echo -e "${GREEN}  🚀 https://$DOMAIN is LIVE!${NC}"
else
    echo -e "${YELLOW}  ⚠️  Some checks failed. Review output above.${NC}"
fi
echo ""
echo "  Quick commands:"
echo "    docker compose ps                    # Container status"
echo "    docker compose logs nginx --tail=20  # Nginx logs"
echo "    docker compose logs django --tail=20 # Django logs"
echo "    ./scripts/deploy.sh --validate       # Re-run validation"
echo ""

# ══════════════════════════════════════════════════════════════════════════════
# Quick deployment one-liner (after initial setup):
#   git pull && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
# ══════════════════════════════════════════════════════════════════════════════
