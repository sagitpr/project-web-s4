#!/bin/bash
# =============================================================================
# Warungio Marketplace — Generate Self-Signed SSL Certificates
# =============================================================================
# Use this when you need to start nginx with HTTPS before obtaining real
# Let's Encrypt certificates via setup-ssl.sh.
#
# Usage:
#   sudo bash scripts/generate-selfsigned-certs.sh
#
# After running, start the stack:
#   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
#
# To replace with real certificates later:
#   sudo bash scripts/setup-ssl.sh
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

SSL_DIR="$(cd "$(dirname "$0")/.." && pwd)/nginx/ssl"
mkdir -p "$SSL_DIR"

# Create OpenSSL config for self-signed cert
CONFIG_FILE="$SSL_DIR/openssl-tmp.cnf"
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

echo ""
echo "╔═══════════════════════════════════════════════╗"
echo "║   Generating Self-Signed SSL Certificates     ║"
echo "╚═══════════════════════════════════════════════╝"
echo ""
echo "  Output directory: $SSL_DIR"
echo ""

# Generate certificate and key
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$SSL_DIR/warungio.key" \
    -out "$SSL_DIR/warungio.crt" \
    -config "$CONFIG_FILE" 2>&1

# Clean up
rm -f "$CONFIG_FILE"

echo ""
info "Certificates generated successfully!"
echo ""
echo "  Certificate: $SSL_DIR/warungio.crt"
echo "  Key:         $SSL_DIR/warungio.key"
echo ""
echo "  To verify:"
echo "    openssl x509 -in $SSL_DIR/warungio.crt -noout -subject -dates"
echo ""
echo "  Now start the production stack:"
echo "    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d"
echo ""

# Verify
if openssl x509 -in "$SSL_DIR/warungio.crt" -noout -subject -dates 2>&1; then
    info "Certificate verification passed."
else
    error "Certificate verification failed!"
    exit 1
fi
