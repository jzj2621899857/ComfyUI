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
        local install_cmd=""
        if command -v apt-get &> /dev/null; then
            install_cmd="sudo apt-get update && sudo apt-get install -y $2"
        elif command -v yum &> /dev/null; then
            install_cmd="sudo yum install -y $2"
        elif command -v dnf &> /dev/null; then
            install_cmd="sudo dnf install -y $2"
        elif command -v pacman &> /dev/null; then
            install_cmd="sudo pacman -S --noconfirm $2"
        elif command -v apk &> /dev/null; then
            install_cmd="sudo apk add --no-cache $2"
        fi
        
        if [ -n "$install_cmd" ]; then
            log_warn "Command $1 not found. Attempting to install..."
            eval "$install_cmd" || {
                log_error "Failed to install $1. Please install $2 manually."
                exit 1
            }
        else
            log_error "Command $1 not found. Please install $2 first."
            exit 1
        fi
    fi
}

install_pkg_if_missing() {
    local pkg="$1"
    if ! command -v "$pkg" &> /dev/null; then
        log_warn "Installing $pkg..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y "$pkg"
        elif command -v yum &> /dev/null; then
            sudo yum install -y "$pkg"
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y "$pkg"
        elif command -v pacman &> /dev/null; then
            sudo pacman -S --noconfirm "$pkg"
        elif command -v apk &> /dev/null; then
            sudo apk add --no-cache "$pkg"
        fi
    fi
}

find_pip() {
    if command -v pip3 &> /dev/null; then
        echo "pip3"
    elif command -v pip &> /dev/null; then
        echo "pip"
    elif python3 -m pip --version &> /dev/null; then
        echo "python3 -m pip"
    else
        log_warn "pip not found. Attempting to install python3-pip..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y python3-pip
        elif command -v yum &> /dev/null; then
            sudo yum install -y python3-pip
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y python3-pip
        elif command -v pacman &> /dev/null; then
            sudo pacman -S --noconfirm python-pip
        elif command -v apk &> /dev/null; then
            sudo apk add --no-cache py3-pip
        else
            log_error "Cannot auto-install pip. Please install python3-pip manually."
            exit 1
        fi
        
        if command -v pip3 &> /dev/null; then
            echo "pip3"
        elif command -v pip &> /dev/null; then
            echo "pip"
        else
            log_error "Failed to install pip."
            exit 1
        fi
    fi
}

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

log_info "Starting update in $PROJECT_DIR"

check_command git git
check_command python3 python3

PIP_CMD=$(find_pip)
log_info "Using pip: $PIP_CMD"

run_pip() {
    if [ "$PIP_CMD" = "python3 -m pip" ]; then
        python3 -m pip "$@"
    else
        $PIP_CMD "$@"
    fi
}

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
run_pip install --upgrade pip

log_info "Updating requirements..."
if [ -f "requirements.txt" ]; then
    run_pip install -r requirements.txt --upgrade
fi

if [ -f "manager_requirements.txt" ]; then
    run_pip install -r manager_requirements.txt --upgrade
fi

log_info "Checking custom nodes dependencies..."
if [ -d "custom_nodes" ]; then
    for node_dir in custom_nodes/*/; do
        if [ -f "$node_dir/requirements.txt" ]; then
            log_info "Updating requirements for $(basename "$node_dir")..."
            run_pip install -r "$node_dir/requirements.txt" --upgrade
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
