#!/bin/bash
# =============================================================================
# Warungio — Auto Swap Setup (2GB)
# =============================================================================
# This script checks if any swap is active, and if not, creates a 2GB swap file
# and enables it persistently via /etc/fstab.
#
# Usage:
#   chmod +x scripts/setup-swap.sh
#   sudo ./scripts/setup-swap.sh
# =============================================================================

set -euo pipefail

SWAP_FILE="${SWAP_FILE:-/swapfile}"
SWAP_SIZE_MB="${SWAP_SIZE_MB:-2048}"  # 2GB default

echo "================================================"
echo "  Warungio — Swap Setup"
echo "================================================"

# ── Check if swap is already active ──
EXISTING_SWAP=$(swapon --show 2>/dev/null | tail -n +2 | wc -l)
if [ "$EXISTING_SWAP" -gt 0 ]; then
    echo "✅ Swap sudah aktif:"
    swapon --show
    echo ""
    echo "Tidak perlu membuat swap baru."
    exit 0
fi

# ── Check if swap file already exists but not enabled ──
if [ -f "$SWAP_FILE" ]; then
    echo "⚠️  File $SWAP_FILE sudah ada tapi belum aktif."
    echo "   Mengaktifkan..."
    sudo swapon "$SWAP_FILE"
    echo "✅ Swap diaktifkan."
    exit 0
fi

echo "📝 Membuat swap file ${SWAP_SIZE_MB}MB di ${SWAP_FILE}..."

# ── Allocate swap file ──
sudo fallocate -l "${SWAP_SIZE_MB}M" "$SWAP_FILE"
if [ $? -ne 0 ]; then
    # fallocate might not work on some filesystems (e.g., ZFS), fall back to dd
    echo "   fallocate gagal, menggunakan dd sebagai fallback..."
    sudo dd if=/dev/zero of="$SWAP_FILE" bs=1M count="$SWAP_SIZE_MB" status=progress
fi

# ── Set correct permissions ──
sudo chmod 600 "$SWAP_FILE"

# ── Format as swap ──
sudo mkswap "$SWAP_FILE"

# ── Enable swap ──
sudo swapon "$SWAP_FILE"

echo "✅ Swap ${SWAP_SIZE_MB}MB aktif."

# ── Make persistent ──
if ! grep -q "$SWAP_FILE" /etc/fstab 2>/dev/null; then
    echo "📝 Menambahkan ke /etc/fstab..."
    echo "$SWAP_FILE none swap sw 0 0" | sudo tee -a /etc/fstab > /dev/null
    echo "✅ Swap persistence ditambahkan ke /etc/fstab."
else
    echo "✅ Swap sudah terdaftar di /etc/fstab."
fi

echo ""
echo "================================================"
echo "  Status Swap:"
swapon --show
echo "================================================"
echo ""
echo "🟢 Selesai! VPS sekarang memiliki ${SWAP_SIZE_MB}MB swap."
