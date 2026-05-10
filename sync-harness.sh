#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

log_info "=== ComfyUI + Harness 同步脚本 ==="
log_info "策略：以你的代码为主，合并官方更新"
echo ""

log_step "1. 检查并添加 remote 仓库..."

# 添加你的仓库
if ! git remote get-url origin &>/dev/null; then
    git remote add origin https://github.com/jzj2621899857/ComfyUI.git
    log_info "已添加 origin: jzj2621899857/ComfyUI"
else
    log_info "origin 已存在: $(git remote get-url origin)"
fi

# 添加官方仓库
if ! git remote get-url upstream &>/dev/null; then
    git remote add upstream https://github.com/comfyanonymous/ComfyUI.git
    log_info "已添加 upstream: comfyanonymous/ComfyUI"
else
    log_info "upstream 已存在: $(git remote get-url upstream)"
fi

echo ""
log_step "2. 获取最新代码..."

# 确保在 master 分支
git checkout master

# 拉取你自己的最新代码
log_info "拉取你的仓库最新代码..."
git pull origin master --no-edit || log_warn "origin 拉取失败或没有更新"

# 获取官方最新代码
log_info "获取官方 ComfyUI 最新代码..."
git fetch upstream

# 检查官方是否有新提交
UPSTREAM_LOG=$(git log HEAD..upstream/master --oneline)
if [ -z "$UPSTREAM_LOG" ]; then
    log_info "官方没有新更新，无需合并"
    echo ""
    log_info "=== 同步完成 ==="
    git log --oneline -1
    exit 0
fi

echo ""
log_info "官方有 $(echo "$UPSTREAM_LOG" | wc -l) 个新提交:"
echo "$UPSTREAM_LOG" | head -5
[ $(echo "$UPSTREAM_LOG" | wc -l) -gt 5 ] && echo "..."

echo ""
log_step "3. 合并官方更新（以你为主）..."

# 尝试合并，冲突时使用我们的版本
log_info "执行合并..."
if git merge upstream/master -X ours --no-edit 2>/dev/null; then
    log_info "合并成功！"
else
    log_warn "存在冲突，自动使用你的版本解决..."
    # 冲突时全部选择我们的
    git checkout --ours .
    git add .
    git commit -m "Merge upstream/master - resolved conflicts with ours"
    log_info "冲突已解决（使用你的代码）"
fi

echo ""
log_step "4. 推送到你的仓库..."

git push origin master

echo ""
log_info "=== 同步完成 ==="
log_info "当前版本: $(git log --oneline -1)"
log_info "官方同步至: $(git log upstream/master --oneline -1 | head -1)"
