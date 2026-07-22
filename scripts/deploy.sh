#!/bin/bash
# =============================================================================
# Warungio Marketplace — Deployment Script
# =============================================================================
# Usage:
#   ./scripts/deploy.sh               # Deploy with latest code
#   ./scripts/deploy.sh --build       # Force rebuild without cache
#   ./scripts/deploy.sh --no-cache    # Rebuild from scratch (no Docker cache)
#   ./scripts/deploy.sh --check       # Health check only
#
# Prerequisites:
#   - Docker & Docker Compose installed
#   - .env file configured in project root
#   - Git repository cloned
#
# Deployment Flow:
#   1. Pull latest code from Git
#   2. Build Docker images (cached by default)
#   3. Start services with Docker Compose
#   4. Wait for health check
#   5. Report status
#
# Inside the container, the entrypoint automatically runs:
#   sync_migrations → migrate → collectstatic → Daphne
# =============================================================================

set -e  # Exit on any error

# ─── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ─── Defaults ────────────────────────────────────────────────────────────────
COMPOSE_FILES=(-f docker-compose.yml -f docker-compose.prod.yml)
SERVICE_NAME="django"
HEALTH_CHECK_URL="http://localhost:8000/health/"
HEALTH_RETRIES=30
HEALTH_DELAY=5

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

# ─── Step 1: Git Pull ────────────────────────────────────────────────────────
echo ""
echo "╔═══════════════════════════════════════════════╗"
echo "║   Warungio Deployment                         ║"
echo "╚═══════════════════════════════════════════════╝"
echo ""

echo -e "${BLUE}[1/5]${NC} Pulling latest code from Git..."
git pull --ff-only
echo -e "${GREEN}  ✅ Git pull complete.${NC}"

# ─── Step 2: Log Environment Info ────────────────────────────────────────────
echo ""
echo -e "${BLUE}[2/5]${NC} Checking environment..."
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
echo -e "${BLUE}[3/5]${NC} Building Docker images..."
if [ "${BUILD_FLAG}" = "--no-cache --pull" ]; then
    docker compose "${COMPOSE_FILES[@]}" build --no-cache --pull
elif [ "${BUILD_FLAG}" = "--build" ]; then
    docker compose "${COMPOSE_FILES[@]}" build
else
    # Default: check if images need rebuilding
    echo "  Checking if rebuild is needed..."
    docker compose "${COMPOSE_FILES[@]}" build
fi
echo -e "${GREEN}  ✅ Build complete.${NC}"

# ─── Step 4: Deploy Services ─────────────────────────────────────────────────
echo ""
echo -e "${BLUE}[4/5]${NC} Starting services..."
echo "  Running: docker compose ${COMPOSE_FILES[*]} up -d"

docker compose "${COMPOSE_FILES[@]}" up -d

echo -e "${GREEN}  ✅ Services started.${NC}"

# ─── Step 5: Wait for Health Check ───────────────────────────────────────────
echo ""
echo -e "${BLUE}[5/5]${NC} Waiting for health check..."
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

# ─── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "╔═══════════════════════════════════════════════╗"
echo "║   Deployment Complete!                        ║"
echo "╚═══════════════════════════════════════════════╝"
echo ""
echo -e "  ${GREEN}✅${NC} Git pull:       done"
echo -e "  ${GREEN}✅${NC} Docker build:   done"
echo -e "  ${GREEN}✅${NC} Services up:    done"
echo -e "  ${GREEN}✅${NC} Health check:   passed"
echo ""
echo "  To check logs:  docker compose logs -f $SERVICE_NAME"
echo "  To restart:     docker compose restart $SERVICE_NAME"
echo "  To stop:        docker compose down"
echo ""

# ─── Quick deployment check: one-liner ───────────────────────────────────────
# The simplest deployment flow is:
#   git pull && docker compose up -d --build
#
# The entrypoint inside the container will automatically run:
#   sync_migrations → migrate → collectstatic → Daphne
# =============================================================================
