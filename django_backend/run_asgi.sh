#!/bin/bash
# =============================================================================
# Run Warungio with Daphne ASGI Server (WebSocket + HTTP)
# =============================================================================
# Usage:
#   ./run_asgi.sh              # Run with Daphne (production-like)
#   ./run_asgi.sh --dev        # Run with runserver (development, HTTP only)
#   ./run_asgi.sh --help       # Show this help
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
cd "$PROJECT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     Warungio ASGI Server Launcher       ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo -e "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo -e "  ${GREEN}--dev${NC}     Run with Django runserver (HTTP only, no WebSocket)"
    echo -e "  ${GREEN}--help${NC}    Show this help message"
    echo ""
    echo "Default (no option): Run with Daphne (WebSocket + HTTP)"
    echo ""
    echo "Requirements:"
    echo "  pip install daphne channels channels-redis"
    echo ""
    echo "For WebSocket support, Redis must be running on localhost:6379."
    echo "Without Redis, the InMemoryChannelLayer will be used as fallback."
    exit 0
fi

if [ "$1" = "--dev" ]; then
    echo -e "${YELLOW}Starting in DEVELOPMENT mode (HTTP only)...${NC}"
    echo ""
    python manage.py runserver 0.0.0.0:8000
    exit $?
fi

# Check if daphne is installed
if ! command -v daphne &> /dev/null; then
    echo -e "${YELLOW}Daphne not found. Installing...${NC}"
    pip install daphne
    echo ""
fi

echo -e "${GREEN}Starting Warungio with Daphne ASGI server...${NC}"
echo -e "${GREEN}  URL:      http://localhost:8000${NC}"
echo -e "${GREEN}  WebSocket: ws://localhost:8000/ws/support/chat/${NC}"
echo -e "${GREEN}  Admin:    http://localhost:8000/admin/${NC}"
echo ""
echo -e "${YELLOW}Make sure Redis is running for full WebSocket support.${NC}"
echo -e "${YELLOW}Without Redis, InMemoryChannelLayer will be used (single-process only).${NC}"
echo ""

exec daphne -b 0.0.0.0 -p 8000 config.asgi:application
