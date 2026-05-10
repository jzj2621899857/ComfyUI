#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_command() {
    if ! command -v "$1" &> /dev/null; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y "$2"
        elif command -v yum &> /dev/null; then
            sudo yum install -y "$2"
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y "$2"
        elif command -v pacman &> /dev/null; then
            sudo pacman -S --noconfirm "$2"
        elif command -v apk &> /dev/null; then
            sudo apk add --no-cache "$2"
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
        log_warn "pip not found. Installing python3-pip..."
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
        fi
        command -v pip3 &> /dev/null && echo "pip3" || echo "pip"
    fi
}

run_pip() {
    PIP_CMD=$(find_pip)
    $PIP_CMD "$@"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log_info "=========================================="
log_info "   ComfyUI Harness Updater"
log_info "=========================================="

STASHED=false

check_git_status() {
    log_info "Checking git status..."
    
    if git rev-parse --git-dir > /dev/null 2>&1; then
        HAS_CHANGES=false
        while IFS= read -r line; do
            STATUS="${line:0:2}"
            FILE="${line:3}"
            if [[ "$FILE" != "models/"* && "$FILE" != "venv/"* && "$FILE" != ".venv/"* ]]; then
                if [[ "$STATUS" =~ [MADRC] ]]; then
                    HAS_CHANGES=true
                    break
                fi
            fi
        done < <(git status --porcelain 2>/dev/null)
        
        if [ "$HAS_CHANGES" = true ]; then
            log_warn "You have uncommitted changes (excluding models/ and venv/)."
            log_info "Stashing changes..."
            git stash push -m "Auto-stash before harness update $(date)" -- . ':!venv' ':!.venv' ':!models' 2>/dev/null || true
            STASHED=true
            log_info "Changes stashed."
        else
            log_info "No significant changes to stash."
        fi
        
        log_info "Git repository detected. Pulling latest changes..."
        DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/origin/||')
        DEFAULT_BRANCH=${DEFAULT_BRANCH:-master}
        git pull origin "$DEFAULT_BRANCH" || log_warn "Failed to pull, will use local files"
        
        if [ "$STASHED" = true ]; then
            log_info "Restoring your changes..."
            git stash pop 2>/dev/null || log_warn "Failed to restore stashed changes"
        fi
    else
        log_warn "No git repository detected. Skipping git pull."
    fi
}

check_git_status

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
[ -f "requirements.txt" ] && run_pip install -r requirements.txt --upgrade
[ -f "manager_requirements.txt" ] && run_pip install -r manager_requirements.txt --upgrade

log_info "Checking custom nodes dependencies..."
[ -d "custom_nodes" ] && for node_dir in custom_nodes/*/; do
    [ -f "$node_dir/requirements.txt" ] && {
        log_info "Updating requirements for $(basename "$node_dir")..."
        run_pip install -r "$node_dir/requirements.txt" --upgrade
    }
done

log_info "Running database migrations..."
if [ -d "alembic_db" ]; then
    run_pip install alembic 2>/dev/null || true
    alembic upgrade head 2>/dev/null || log_warn "Alembic migration skipped"
fi

log_info "=========================================="
log_info "   Update Complete!"
log_info "=========================================="
log_info "To start the server with Harness, run:"
log_info "  source venv/bin/activate"
log_info "  python start_with_harness.py --listen 0.0.0.0 --port 8188"
log_info ""
log_info "To start the server without Harness, run:"
log_info "  python main.py --listen 0.0.0.0 --port 8188"