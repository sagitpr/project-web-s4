#!/bin/bash
# =============================================================================
# Warungio Marketplace — Database Backup Script
# =============================================================================
# Automated MariaDB backup with rotation, compression, and optional S3 upload.
#
# Usage:
#   ./scripts/backup.sh                    # Manual backup (keeps last 7 days)
#   ./scripts/backup.sh --upload           # Backup + upload to cloud storage
#   ./scripts/backup.sh --list             # List available backups
#   ./scripts/backup.sh --restore <file>   # Restore from backup file
#
# Cron (add via crontab -e):
#   0 3 * * * /root/project-web-s4/scripts/backup.sh --upload
# =============================================================================

set -e

# ─── Configuration ──────────────────────────────────────────────────────────
BACKUP_DIR="${BACKUP_DIR:-/backups/warungio}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
DB_CONTAINER="${DB_CONTAINER:-warungio-mysql}"
DB_NAME="${DB_NAME:-warungio_db}"
COMPOSE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/warungio_$TIMESTAMP.sql.gz"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

# ─── Ensure backup directory exists ────────────────────────────────────────
mkdir -p "$BACKUP_DIR"

# ─── Check Docker container ────────────────────────────────────────────────
if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    echo -e "${RED}❌ Database container '$DB_CONTAINER' not running.${NC}"
    echo "   Available containers:"
    docker ps --format '{{.Names}}' 2>/dev/null
    exit 1
fi

# ─── Functions ──────────────────────────────────────────────────────────────
do_backup() {
    echo -e "${BLUE}📦 Backing up $DB_NAME from $DB_CONTAINER...${NC}"
    
    # Get DB credentials from container environment
    local DB_USER=$(docker exec "$DB_CONTAINER" env | grep MYSQL_USER= | cut -d= -f2)
    local DB_PASS=$(docker exec "$DB_CONTAINER" env | grep MYSQL_PASSWORD= | cut -d= -f2)
    local DB_ROOT_PASS=$(docker exec "$DB_CONTAINER" env | grep MYSQL_ROOT_PASSWORD= | cut -d= -f2)
    
    # Use root password if available (has full access), otherwise user password
    local PASS="${DB_ROOT_PASS:-$DB_PASS}"
    local USER="${DB_ROOT_PASS:+root}"
    USER="${USER:-$DB_USER}"
    
    echo "   Database: $DB_NAME"
    echo "   User: $USER"
    echo "   Output: $BACKUP_FILE"
    
    # Dump and compress in one pipeline (avoids writing uncompressed temp file)
    if docker exec "$DB_CONTAINER" mysqldump \
        -u"$USER" \
        -p"$PASS" \
        --single-transaction \
        --routines \
        --triggers \
        --events \
        --skip-lock-tables \
        "$DB_NAME" 2>/dev/null | gzip > "$BACKUP_FILE"; then
        
        local SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        echo -e "${GREEN}✅ Backup created: $BACKUP_FILE ($SIZE)${NC}"
        
        # Verify backup integrity
        echo "   Verifying backup integrity..."
        if gzip -t "$BACKUP_FILE" 2>/dev/null; then
            echo -e "${GREEN}✅ Backup integrity verified${NC}"
        else
            echo -e "${RED}❌ Backup corrupted! Removing...${NC}"
            rm -f "$BACKUP_FILE"
            exit 1
        fi
    else
        echo -e "${RED}❌ Backup failed!${NC}"
        rm -f "$BACKUP_FILE" 2>/dev/null
        exit 1
    fi
}

do_rotation() {
    echo -e "${BLUE}🧹 Cleaning backups older than $RETENTION_DAYS days...${NC}"
    
    local COUNT=$(find "$BACKUP_DIR" -name "warungio_*.sql.gz" -type f -mtime "+$RETENTION_DAYS" | wc -l)
    if [ "$COUNT" -gt 0 ]; then
        find "$BACKUP_DIR" -name "warungio_*.sql.gz" -type f -mtime "+$RETENTION_DAYS" -delete
        echo -e "${GREEN}✅ Removed $COUNT old backup(s)${NC}"
    else
        echo "   No backups older than $RETENTION_DAYS days to remove."
    fi
}

do_list() {
    echo -e "${BLUE}📋 Available backups in $BACKUP_DIR:${NC}"
    echo ""
    
    local TOTAL=0
    while IFS= read -r file; do
        local SIZE=$(du -h "$file" | cut -f1)
        local DATE=$(stat -c '%y' "$file" | cut -d. -f1)
        echo "   $DATE  $SIZE  $(basename "$file")"
        TOTAL=$((TOTAL + 1))
    done < <(find "$BACKUP_DIR" -name "warungio_*.sql.gz" -type f | sort -r)
    
    if [ "$TOTAL" -eq 0 ]; then
        echo "   (No backups found)"
    else
        echo ""
        echo "   Total: $TOTAL backup(s)"
    fi
}

do_restore() {
    local RESTORE_FILE="$1"
    
    if [ ! -f "$RESTORE_FILE" ]; then
        echo -e "${RED}❌ Backup file not found: $RESTORE_FILE${NC}"
        echo "   Available backups:"
        do_list
        exit 1
    fi
    
    echo -e "${YELLOW}⚠️  WARNING: Restoring will REPLACE the current database!${NC}"
    echo -e "${YELLOW}   Source: $RESTORE_FILE${NC}"
    echo -e "${YELLOW}   Target: $DB_CONTAINER / $DB_NAME${NC}"
    echo ""
    read -p "   Type 'YES' to confirm: " CONFIRM
    
    if [ "$CONFIRM" != "YES" ]; then
        echo -e "${YELLOW}   Restore cancelled.${NC}"
        exit 0
    fi
    
    # Get DB credentials (same as backup)
    local DB_USER=$(docker exec "$DB_CONTAINER" env | grep MYSQL_USER= | cut -d= -f2)
    local DB_PASS=$(docker exec "$DB_CONTAINER" env | grep MYSQL_PASSWORD= | cut -d= -f2)
    local DB_ROOT_PASS=$(docker exec "$DB_CONTAINER" env | grep MYSQL_ROOT_PASSWORD= | cut -d= -f2)
    local PASS="${DB_ROOT_PASS:-$DB_PASS}"
    local USER="${DB_ROOT_PASS:+root}"
    USER="${USER:-$DB_USER}"
    
    echo -e "${BLUE}🔄 Restoring database...${NC}"
    
    if gunzip -c "$RESTORE_FILE" | docker exec -i "$DB_CONTAINER" mysql \
        -u"$USER" \
        -p"$PASS" \
        "$DB_NAME" 2>/dev/null; then
        echo -e "${GREEN}✅ Database restored from: $(basename "$RESTORE_FILE")${NC}"
    else
        echo -e "${RED}❌ Restore failed!${NC}"
        exit 1
    fi
}

do_upload() {
    # Optional: upload to cloud storage (S3-compatible, GCS, etc.)
    # Configure by setting UPLOAD_COMMAND env var
    if [ -n "${UPLOAD_COMMAND}" ]; then
        echo -e "${BLUE}☁️  Uploading to cloud storage...${NC}"
        eval "${UPLOAD_COMMAND}" "$BACKUP_FILE" && \
            echo -e "${GREEN}✅ Upload complete${NC}" || \
            echo -e "${YELLOW}⚠️  Upload failed (non-fatal)${NC}"
    else
        echo -e "${YELLOW}⚠️  No UPLOAD_COMMAND configured. Skipping cloud upload.${NC}"
        echo "   To enable, set: export UPLOAD_COMMAND='rclone copy {} gdrive:warungio-backups/'"
    fi
}

# ─── Main ───────────────────────────────────────────────────────────────────
case "${1:-}" in
    --upload)
        do_backup
        do_upload
        do_rotation
        ;;
    --list)
        do_list
        ;;
    --restore)
        if [ -z "$2" ]; then
            echo -e "${RED}❌ Usage: $0 --restore <backup_file>${NC}"
            do_list
            exit 1
        fi
        do_restore "$2"
        ;;
    --help|-h)
        echo "Warungio Database Backup Script"
        echo ""
        echo "Usage:"
        echo "  $0                    Manual backup (keeps last $RETENTION_DAYS days)"
        echo "  $0 --upload           Backup + upload to cloud storage"
        echo "  $0 --list             List available backups"
        echo "  $0 --restore <file>   Restore from backup file"
        echo "  $0 --help             Show this help"
        ;;
    *)
        do_backup
        do_rotation
        ;;
esac

echo ""
echo -e "${GREEN}✅ Backup complete: $(date)${NC}"
