# ComfyUI Harness 源码改造任务清单

## Phase 1: 核心改造（必须）

### 任务 1: 项目结构初始化
- [ ] 1.1 创建 `comfy/harness/` 目录结构
- [ ] 1.2 创建 `comfy/harness/__init__.py`（Harness 启用控制）
- [ ] 1.3 设计配置项（`comfy/harness/config.py`）
- [ ] 1.4 确保向后兼容性机制

### 任务 2: 改造 `comfy/execution.py` - 状态追踪
- [ ] 2.1 分析现有 `execution.py` 执行流程
- [ ] 2.2 设计状态追踪钩子接口
- [ ] 2.3 在任务开始时注入状态更新逻辑
- [ ] 2.4 在任务完成时注入回调逻辑
- [ ] 2.5 添加进度上报机制
- [ ] 2.6 添加任务取消支持
- [ ] 2.7 编写单元测试

### 任务 3: 改造 `comfy/server.py` - WebSocket 增强
- [ ] 3.1 分析现有 WebSocket 实现
- [ ] 3.2 设计进度推送消息格式
- [ ] 3.3 实现任务进度订阅功能
- [ ] 3.4 实现任务完成通知
- [ ] 3.5 添加 Harness 模式下的 WebSocket 路由
- [ ] 3.6 编写单元测试

### 任务 4: 新增 `comfy/harness/state/` - 状态管理器
- [ ] 4.1 创建 `state/__init__.py`
- [ ] 4.2 设计任务状态数据模型 (`models.py`)
  - task_id, status, progress, created_at, updated_at, result, error
- [ ] 4.3 实现 Redis 连接客户端 (`redis_client.py`)
- [ ] 4.4 实现状态存储服务 (`manager.py`)
- [ ] 4.5 实现状态查询接口
- [ ] 4.6 实现任务取消逻辑
- [ ] 4.7 编写单元测试

### 任务 5: 新增 `comfy/harness/api/` - API 网关
- [ ] 5.1 创建 `api/__init__.py`
- [ ] 5.2 设计请求/响应数据模型 (`schemas.py`)
- [ ] 5.3 实现 POST `/api/v1/generate` 端点
- [ ] 5.4 实现 GET `/api/v1/task/{task_id}` 端点
- [ ] 5.5 实现 DELETE `/api/v1/task/{task_id}` 端点
- [ ] 5.6 实现 GET `/api/v1/tasks` 端点（列表）
- [ ] 5.7 添加请求验证与错误处理
- [ ] 5.8 编写单元测试

## Phase 2: 编排能力

### 任务 6: 新增 `comfy/harness/orchestrator/` - AI 编排器
- [ ] 6.1 创建 `orchestrator/__init__.py`
- [ ] 6.2 设计编排引擎核心 (`engine.py`)
- [ ] 6.3 实现场景决策逻辑（文生图/图生图/视频）
- [ ] 6.4 实现 `workflow_gen.py` - 工作流生成器
  - 文生图工作流生成
  - 图生图工作流生成
  - ControlNet 引导生成
- [ ] 6.5 创建预置模板目录 `orchestrator/templates/`
- [ ] 6.6 编写单元测试

### 任务 7: 改造 `comfy/model_management.py` - 增强模型管理
- [ ] 7.1 分析现有模型加载机制
- [ ] 7.2 设计模型加载钩子接口
- [ ] 7.3 实现动态模型路径解析
- [ ] 7.4 添加模型加载回调支持
- [ ] 7.5 编写单元测试

### 任务 8: 新增 `comfy/harness/model_store/` - 模型仓库
- [ ] 8.1 创建 `model_store/__init__.py`
- [ ] 8.2 实现模型注册表 (`registry.py`)
- [ ] 8.3 实现动态模型加载器 (`loader.py`)
- [ ] 8.4 实现 LoRA 管理器 (`lora_manager.py`)
  - LoRA 标签体系设计
  - LoRA 组合策略
  - LoRA 冲突检测
- [ ] 8.5 集成 S3/NFS 存储支持
- [ ] 8.6 编写单元测试

## Phase 3: 反馈闭环

### 任务 9: 新增 `comfy/harness/feedback/` - 反馈处理器
- [ ] 9.1 创建 `feedback/__init__.py`
- [ ] 9.2 设计反馈数据模型
- [ ] 9.3 实现质量评估模块 (`evaluator.py`)
  - 图像美学评分
  - NSFW 检测
  - 评分阈值判断
- [ ] 9.4 实现异常检测模块 (`detector.py`)
  - 失败率统计
  - 异常模式识别
  - 告警触发
- [ ] 9.5 实现回滚机制 (`rollback.py`)
  - 工作流版本管理
  - 自动回滚逻辑
- [ ] 9.6 编写单元测试

### 任务 10: 集成质量评估模型
- [ ] 10.1 选型质量评估模型（LAION Aesthetic Score / CLIP Score）
- [ ] 10.2 集成评估模型到 `evaluator.py`
- [ ] 10.3 实现批量评估功能
- [ ] 10.4 编写集成测试

## Phase 4: 集成与部署

### 任务 11: Harness 模块集成
- [ ] 11.1 在 ComfyUI 启动流程中集成 Harness
- [ ] 11.2 实现优雅降级（Harness 禁用时保持原有行为）
- [ ] 11.3 添加健康检查端点
- [ ] 11.4 端到端功能测试

### 任务 12: 部署配置
- [ ] 12.1 创建 Docker 配置文件
- [ ] 12.2 创建 docker-compose.yml（包含 Redis）
- [ ] 12.3 编写 K8s 部署配置
- [ ] 12.4 编写部署文档

## 任务依赖关系

```
Phase 1 (必须先完成)
├── 任务 1 → 任务 2, 3, 4, 5
├── 任务 2 (execution.py 改造) → 任务 4 (状态管理需要钩子)
├── 任务 3 (server.py 改造) → 任务 4 (WebSocket 推送)
└── 任务 4, 5 → 相互独立，可并行

Phase 2
├── 任务 6 → 任务 5 (需要 API 端点)
├── 任务 7 → 任务 4 (模型管理需要状态追踪)
└── 任务 8 → 任务 7 (模型仓库依赖模型管理)

Phase 3
├── 任务 9 → 任务 4 (需要状态管理)
└── 任务 10 → 任务 9 (质量评估是反馈的一部分)

Phase 4
└── 任务 11, 12 → Phase 1, 2, 3
```

## 源码改造文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `comfy/execution.py` | 改造 | 添加状态追踪、进度上报 |
| `comfy/server.py` | 改造 | 增强 WebSocket |
| `comfy/model_management.py` | 改造 | 增强模型加载 |
| `comfy/harness/__init__.py` | 新增 | 模块入口 |
| `comfy/harness/config.py` | 新增 | 配置管理 |
| `comfy/harness/api/__init__.py` | 新增 | API 模块 |
| `comfy/harness/api/routes.py` | 新增 | API 路由 |
| `comfy/harness/api/schemas.py` | 新增 | 数据模型 |
| `comfy/harness/orchestrator/__init__.py` | 新增 | 编排器模块 |
| `comfy/harness/orchestrator/engine.py` | 新增 | 编排引擎 |
| `comfy/harness/orchestrator/workflow_gen.py` | 新增 | 工作流生成 |
| `comfy/harness/state/__init__.py` | 新增 | 状态模块 |
| `comfy/harness/state/manager.py` | 新增 | 状态管理 |
| `comfy/harness/state/redis_client.py` | 新增 | Redis 客户端 |
| `comfy/harness/state/models.py` | 新增 | 状态模型 |
| `comfy/harness/feedback/__init__.py` | 新增 | 反馈模块 |
| `comfy/harness/feedback/evaluator.py` | 新增 | 质量评估 |
| `comfy/harness/feedback/detector.py` | 新增 | 异常检测 |
| `comfy/harness/feedback/rollback.py` | 新增 | 回滚机制 |
| `comfy/harness/model_store/__init__.py` | 新增 | 模型仓库模块 |
| `comfy/harness/model_store/loader.py` | 新增 | 模型加载器 |
| `comfy/harness/model_store/lora_manager.py` | 新增 | LoRA 管理 |
| `comfy/harness/model_store/registry.py` | 新增 | 模型注册表 |
