#!/bin/bash
# =============================================================================
# Warungio Marketplace — VPS Setup Script (1GB RAM Optimized)
# =============================================================================
# Usage: sudo bash scripts/setup-vps.sh
# Target: Ubuntu 22.04/24.04 LTS, 1 vCPU, 1GB RAM, 20GB SSD
# =============================================================================

set -euo pipefail

echo "=============================================="
echo "  Warungio VPS Setup — 1GB RAM Optimization"
echo "=============================================="

# ─── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ══════════════════════════════════════════════════════════════════════════════
# 1. SYSTEM UPDATE
# ══════════════════════════════════════════════════════════════════════════════
info "Updating system packages..."
apt-get update && apt-get upgrade -y

# ══════════════════════════════════════════════════════════════════════════════
# 2. SWAP FILE — CRITICAL FOR 1GB RAM
# ══════════════════════════════════════════════════════════════════════════════
# Tanpa SWAP, OOM Killer akan membunuh container saat memory puncak.
# SWAP 1GB = safety net untuk mencegah crash.
if [ $(swapon --show | wc -l) -eq 0 ]; then
    info "Creating 1GB swap file..."
    fallocate -l 1G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    
    # Turunkan swappiness agar jarang pindah ke swap
    echo 'vm.swappiness=10' >> /etc/sysctl.d/99-warungio.conf
    sysctl -p /etc/sysctl.d/99-warungio.conf
    info "Swap 1GB created. Swappiness=10."
else
    info "Swap already exists. Skipping."
fi

# ══════════════════════════════════════════════════════════════════════════════
# 3. SYSTEM TUNABLES — OOM, memory, network
# ══════════════════════════════════════════════════════════════════════════════
info "Applying system tunables for 1GB RAM..."

cat >> /etc/sysctl.d/99-warungio.conf << 'EOF'

# ── OOM Tuning ──
# (default 0=oom_kill, 1=panic, 2=panic with timeout) — keep default
# vm.panic_on_oom = 0

# ── Memory ──
# Kurangi pressure pada page cache
vm.vfs_cache_pressure = 50
# Meningkatkan ketersediaan memory untuk aplikasi
vm.min_free_kbytes = 65536

# ── Network ──
# TCP optimization untuk koneksi banyak
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 1024
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_tw_reuse = 1
EOF

sysctl -p /etc/sysctl.d/99-warungio.conf

# ══════════════════════════════════════════════════════════════════════════════
# 4. DOCKER INSTALL (jika belum ada)
# ══════════════════════════════════════════════════════════════════════════════
if ! command -v docker &>/dev/null; then
    info "Installing Docker..."
    apt-get install -y ca-certificates curl gnupg lsb-release
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
        gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
        tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable docker
    info "Docker installed."
else
    info "Docker already installed. Checking version..."
    docker --version
fi

# ══════════════════════════════════════════════════════════════════════════════
# 5. DOCKER DAEMON — Resource Limits
# ══════════════════════════════════════════════════════════════════════════════
info "Configuring Docker daemon resource limits..."

mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    },
    "max-concurrent-downloads": 3,
    "max-concurrent-uploads": 3,
    "default-shm-size": "32M",
    "experimental": false,
    "metrics-addr": "",
    "live-restore": true
}
EOF

systemctl restart docker

# ══════════════════════════════════════════════════════════════════════════════
# 6. CLEANUP
# ══════════════════════════════════════════════════════════════════════════════
info "Removing unused packages..."
apt-get autoremove -y
apt-get autoclean -y

# ══════════════════════════════════════════════════════════════════════════════
# 7. SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
echo ""
echo "=============================================="
echo "  VPS Setup Complete!"
echo "=============================================="
echo ""
echo "Memory status:"
free -h
echo ""
echo "Swap status:"
swapon --show
echo ""
echo "Docker status:"
systemctl is-active docker && echo "  Docker: RUNNING" || echo "  Docker: STOPPED"
echo ""
echo "Next steps:"
echo "  1. Clone repository: git clone <repo-url> /opt/warungio"
echo "  2. Copy .env file: cp .env.example .env (edit credentials)"
echo "  3. Start services: docker compose up -d"
echo "  4. Check logs: docker compose logs -f"
echo "  5. Setup SSL: docker compose run --rm certbot certonly"
echo ""
echo "=============================================="
