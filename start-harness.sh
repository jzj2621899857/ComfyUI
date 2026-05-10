#!/bin/bash
# ComfyUI Harness 快速启动脚本

export COMFYUI_HARNESS=true

cd "$(dirname "$0")"

echo "[Harness] Starting ComfyUI..."
source venv/bin/activate 2>/dev/null || true

python main.py --listen 0.0.0.0 --port 8188 "$@"
