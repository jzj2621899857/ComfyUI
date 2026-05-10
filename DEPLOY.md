# ComfyUI + Harness 部署指南

## 一、首次部署

### 1.1 克隆代码

```bash
cd ~
git clone https://github.com/jzj2621899857/ComfyUI.git ComfyUI_Harness
cd ComfyUI_Harness
```

### 1.2 添加官方仓库（用于后续同步更新）

```bash
git remote add upstream https://github.com/comfyanonymous/ComfyUI.git
```

### 1.3 运行部署脚本

```bash
chmod +x harness-deploy.sh
./harness-deploy.sh
```

脚本会自动：
- 安装 python3-pip（如缺失）
- 创建 Python 虚拟环境
- 安装所有依赖
- 运行数据库迁移

### 1.4 启动服务

```bash
source venv/bin/activate
python main.py
```

---

## 二、日常更新

### 2.1 拉取最新代码

```bash
cd ~/ComfyUI_Harness
git pull origin master
```

### 2.2 更新依赖（如有新增）

```bash
./harness-update.sh
```

### 2.3 同步官方 ComfyUI 更新

```bash
./sync-harness.sh
```

此脚本会自动：
- 拉取你的最新代码
- 合并官方 ComfyUI 更新
- **冲突时以你的代码为主**
- 推送到你的仓库

---

## 三、脚本说明

| 脚本 | 用途 |
|------|------|
| `harness-deploy.sh` | 初次部署，安装环境 |
| `harness-update.sh` | 更新 Python 依赖和数据库 |
| `sync-harness.sh` | 同步官方 ComfyUI 更新 |

---

## 四、Harness 功能模块

| 模块 | 说明 |
|------|------|
| execution | 执行引擎带保险丝（Fuse Box、Fallback、Retry） |
| types | 类型安全与合约化 |
| observability | 可观测性（Tracing、黑匣子、监控看板） |
| resources | 自适应资源管理（显存预估、动态调度、精度自适应） |
| evolution | 工作流自进化（金丝雀部署、AI 裁判、闭环优化） |

默认全部关闭，保持原有行为。可通过环境变量启用：

```bash
export COMFYUI_HARNESS=true
export HARNESS_FUSE_BOX=true
export HARNESS_EVOLUTION=true
```

---

## 五、常见问题

### Q: 部署脚本报错 "pip not found"
A: 脚本已自动安装 python3-pip，如仍有问题手动执行：
```bash
sudo apt-get update && sudo apt-get install -y python3-pip
```

### Q: 如何查看 Harness 状态
```bash
curl http://localhost:8188/api/harness/status
```

### Q: 如何禁用 Harness
```bash
unset COMFYUI_HARNESS
# 或设置
export COMFYUI_HARNESS=false
```

### Q: 想回滚到官方 ComfyUI
```bash
git checkout upstream/master
```

---

## 六、目录结构

```
ComfyUI_Harness/
├── comfy/harness/          # Harness 核心模块
│   ├── execution/          # 执行引擎
│   ├── types/               # 类型系统
│   ├── observability/       # 可观测性
│   ├── resources/           # 资源管理
│   └── evolution/           # 自进化系统
├── harness-deploy.sh       # 部署脚本
├── harness-update.sh       # 更新脚本
├── sync-harness.sh         # 同步官方脚本
├── venv/                   # Python 虚拟环境（自动创建）
└── main.py                 # 启动入口
```
