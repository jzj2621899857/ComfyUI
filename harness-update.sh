#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "Command $1 not found. Please install it first."
        exit 1
    fi
}

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

log_info "Starting update in $PROJECT_DIR"

check_command git
check_command python3

log_info "Checking git status..."
if [ -n "$(git status --porcelain)" ]; then
    log_warn "You have uncommitted changes. Stashing them temporarily..."
    git stash push -m "auto-stash before update"
    STASHED=true
fi

log_info "Checking for git repository..."
if git rev-parse --git-dir > /dev/null 2>&1; then
    log_info "Git repository detected. Pulling latest changes..."
    git fetch origin
    git pull origin main
else
    log_info "No git repository detected. Skipping git pull."
    log_warn "If you're uploading new code, please re-run harness-deploy.sh after uploading."
fi

if [ "$STASHED" = true ]; then
    if git rev-parse --git-dir > /dev/null 2>&1; then
        log_info "Restoring your changes..."
        git stash pop || true
    else
        log_warn "Cannot restore stashed changes without git repository"
    fi
fi

log_info "Activating virtual environment..."
if [ -d "venv" ]; then
    source venv/bin/activate
else
    log_error "Virtual environment not found. Please run harness-deploy.sh first."
    exit 1
fi

log_info "Upgrading pip..."
pip install --upgrade pip

log_info "Updating requirements..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --upgrade
fi

if [ -f "manager_requirements.txt" ]; then
    pip install -r manager_requirements.txt --upgrade
fi

log_info "Checking custom nodes dependencies..."
if [ -d "custom_nodes" ]; then
    for node_dir in custom_nodes/*/; do
        if [ -f "$node_dir/requirements.txt" ]; then
            log_info "Updating requirements for $(basename "$node_dir")..."
            pip install -r "$node_dir/requirements.txt" --upgrade
        fi
    done
fi

log_info "Running database migrations..."
if [ -f "alembic.ini" ]; then
    alembic upgrade head
fi

log_info "Update complete!"
log_info "To restart the server, you may need to stop the current process first"
log_info "Then run:"
log_info "  source venv/bin/activate"
log_info "  python main.py"
