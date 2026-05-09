# ComfyUI Harness 实现检查清单

## Phase 1: 核心框架

### 项目结构
- [ ] 项目目录结构符合规格：`api/`, `orchestrator/`, `executor/`, `state/`, `feedback/`, `storage/`, `tests/`
- [ ] 依赖配置文件存在且完整 (pyproject.toml/requirements.txt)
- [ ] 配置文件模板包含所有必需配置项

### API 网关
- [ ] FastAPI 应用正确初始化并可启动
- [ ] POST `/api/v1/generate` 端点正确处理请求并返回任务 ID
- [ ] GET `/api/v1/task/{task_id}` 端点正确返回任务状态
- [ ] DELETE `/api/v1/task/{task_id}` 端点正确取消任务
- [ ] 请求参数验证正确实现
- [ ] 错误处理返回标准错误格式
- [ ] API 路由配置符合 RESTful 规范

### 状态管理器
- [ ] Redis 连接正确配置
- [ ] 任务状态模型包含：task_id, status, progress, created_at, updated_at, result
- [ ] 状态存储服务正确保存和读取状态
- [ ] WebSocket 连接管理器正确实现
- [ ] 进度推送功能正常
- [ ] 状态转换正确：pending → processing → completed/failed

### ComfyUI 执行器
- [ ] ComfyUI API 客户端正确封装
- [ ] 工作流 JSON 解析器正确处理 ComfyUI 格式
- [ ] 任务执行调用 ComfyUI API
- [ ] 结果回调正确通知状态管理器
- [ ] 超时机制正确触发
- [ ] 重试机制在失败时正确执行

## Phase 2: 编排能力

### AI 编排器
- [ ] 决策引擎根据请求类型选择正确的工作流
- [ ] 文生图工作流生成器生成正确的 JSON 结构
- [ ] 图生图工作流生成器包含 ControlNet 节点
- [ ] 工作流参数正确注入（模型、步数、分辨率等）
- [ ] 编排器输出的 JSON 符合 ComfyUI schema

### 工作流模板
- [ ] 模板存储结构支持模板的增删改查
- [ ] 模板加载服务正确渲染变量
- [ ] 基础模板存在：文生图、图生图、高清修复
- [ ] 模板版本管理正确实现

### 动态 LoRA 组装
- [ ] LoRA 标签体系完整定义
- [ ] 组合策略根据标签正确选择 LoRA
- [ ] LoRA 冲突检测防止不兼容组合
- [ ] 工作流中正确插入 LoRA 节点

## Phase 3: 反馈闭环

### 质量评估
- [ ] 质量评估接口正确设计
- [ ] 图像质量评估模型正确集成
- [ ] NSFW 检测功能正确执行
- [ ] 评分结果正确存储

### 反馈处理器
- [ ] 反馈数据收集机制完整
- [ ] 异常检测规则正确配置
- [ ] 告警机制正确触发
- [ ] 工作流回滚逻辑正确实现
- [ ] 反馈数据正确写入数据层

## Phase 4: 生产部署

### Docker 容器化
- [ ] Dockerfile 正确配置 Python 环境和依赖
- [ ] docker-compose.yml 包含所有必需服务
- [ ] 环境变量正确配置和管理
- [ ] 容器间网络连接正确设置

### K8s 集群配置
- [ ] Deployment 配置正确的副本数和资源限制
- [ ] Service 配置正确暴露 API
- [ ] Ingress 配置正确的路由规则
- [ ] HPA 自动扩缩容正确配置
- [ ] ConfigMap 和 Secret 正确管理敏感配置

### 监控与告警
- [ ] Prometheus 指标端点正确暴露
- [ ] 关键指标（任务数、成功率、延迟）正确采集
- [ ] Grafana 看板正确展示监控数据
- [ ] AlertManager 告警规则正确配置
- [ ] 告警通知渠道正确设置

## 端到端集成
- [ ] 完整请求链路：API → 编排 → 执行 → 存储 → 反馈
- [ ] WebSocket 实时推送全链路正常工作
- [ ] 错误场景下优雅降级
- [ ] 系统在高负载下表现稳定

## 文档与规范
- [ ] 代码注释完整且清晰
- [ ] API 文档（OpenAPI/Swagger）正确生成
- [ ] 部署文档包含完整步骤
- [ ] 运维手册包含常见问题处理
