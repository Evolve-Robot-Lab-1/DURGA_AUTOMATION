#!/bin/bash

# DURGA Automation Services Startup Script
# =========================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}"
    echo "============================================="
    echo "  DURGA AI - Automation Services"
    echo "============================================="
    echo -e "${NC}"
}

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

check_prerequisites() {
    echo "Checking prerequisites..."

    # Check Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js not found. Please install Node.js 18+"
        exit 1
    fi
    print_status "Node.js $(node -v)"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 not found. Please install Python 3.11+"
        exit 1
    fi
    print_status "Python $(python3 --version)"

    # Check Claude CLI
    if ! command -v claude &> /dev/null; then
        print_warning "Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code"
        print_warning "Then authenticate with: claude login"
    else
        print_status "Claude CLI found"
    fi

    echo ""
}

start_claude_bridge() {
    echo "Starting Claude Bridge on port 3003..."
    cd "$ROOT_DIR/claude-bridge"

    if [ ! -d "node_modules" ]; then
        print_warning "Installing Claude Bridge dependencies..."
        npm install
    fi

    node server.js &
    BRIDGE_PID=$!
    echo $BRIDGE_PID > /tmp/durga_bridge.pid
    print_status "Claude Bridge started (PID: $BRIDGE_PID)"
}

start_browser_automation() {
    echo "Setting up Browser Automation..."
    cd "$ROOT_DIR/browser_automation"

    if [ ! -d "venv" ]; then
        print_warning "Creating Python virtual environment..."
        python3 -m venv venv
    fi

    source venv/bin/activate

    if ! pip show playwright &> /dev/null; then
        print_warning "Installing Python dependencies..."
        pip install -r requirements.txt
        playwright install chromium
    fi

    print_status "Browser Automation ready"
}

stop_services() {
    echo "Stopping DURGA services..."

    if [ -f /tmp/durga_bridge.pid ]; then
        kill $(cat /tmp/durga_bridge.pid) 2>/dev/null || true
        rm /tmp/durga_bridge.pid
        print_status "Claude Bridge stopped"
    fi

    # Clean up any orphaned processes
    pkill -f "node.*server.js" 2>/dev/null || true

    print_status "All services stopped"
}

show_status() {
    echo "Service Status:"
    echo "---------------"

    # Check Claude Bridge
    if curl -s http://localhost:3003/health > /dev/null 2>&1; then
        print_status "Claude Bridge (3003): Running"
    else
        print_error "Claude Bridge (3003): Not running"
    fi

    # Check if browser automation venv exists
    if [ -d "$ROOT_DIR/browser_automation/venv" ]; then
        print_status "Browser Automation: Ready"
    else
        print_warning "Browser Automation: Not setup"
    fi

    echo ""
}

show_help() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start     Start all automation services"
    echo "  stop      Stop all services"
    echo "  status    Show service status"
    echo "  bridge    Start only Claude Bridge"
    echo "  setup     Setup Python environment"
    echo "  help      Show this help"
    echo ""
}

# Main script
print_header

case "${1:-start}" in
    start)
        check_prerequisites
        start_claude_bridge
        start_browser_automation
        echo ""
        print_status "All services started!"
        echo ""
        echo "Claude Bridge:      http://localhost:3003"
        echo "Health check:       curl http://localhost:3003/health"
        echo ""
        echo "To run automation scripts:"
        echo "  cd browser_automation"
        echo "  source venv/bin/activate"
        echo "  python campaign_auto.py scan"
        ;;
    stop)
        stop_services
        ;;
    status)
        show_status
        ;;
    bridge)
        check_prerequisites
        start_claude_bridge
        ;;
    setup)
        check_prerequisites
        start_browser_automation
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
