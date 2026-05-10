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

log_info "Starting deployment in $PROJECT_DIR"

check_command git
check_command python3
check_command pip3

log_info "Checking Python version..."
python3 --version

log_info "Updating git repository..."
git pull origin main

log_info "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate

log_info "Upgrading pip..."
pip install --upgrade pip

log_info "Installing requirements..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

if [ -f "manager_requirements.txt" ]; then
    pip install -r manager_requirements.txt
fi

log_info "Checking for custom nodes dependencies..."
if [ -d "custom_nodes" ]; then
    for node_dir in custom_nodes/*/; do
        if [ -f "$node_dir/requirements.txt" ]; then
            log_info "Installing requirements for $(basename "$node_dir")..."
            pip install -r "$node_dir/requirements.txt"
        fi
    done
fi

log_info "Setting up database..."
if [ -f "alembic.ini" ]; then
    log_info "Running database migrations..."
    alembic upgrade head
fi

log_info "Deployment complete!"
log_info "To start the server, run:"
log_info "  source venv/bin/activate"
log_info "  python main.py"
