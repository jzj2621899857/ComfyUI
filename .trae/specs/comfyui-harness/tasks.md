# ComfyUI Harness 源码改造任务清单

## Phase 1: 执行引擎可靠性（可控、可自愈）

### 任务 1: 项目结构初始化
- [x] 1.1 创建 `comfy/harness/` 目录结构
- [x] 1.2 创建 `comfy/harness/__init__.py`（Harness 启用控制）
- [x] 1.3 设计配置项（`comfy/harness/config.py`）
- [x] 1.4 确保向后兼容性机制

### 任务 2: 改造 `comfy/execution.py` - 集成 Fuse Box 模式
- [x] 2.1 分析现有 `execution.py` 递归执行流程
- [x] 2.2 设计 Fuse Box 输入校验层接口
- [x] 2.3 实现 `comfy/harness/execution/fuse_box.py`
  - 类型校验（tensor dtype, shape）
  - 数值范围校验（value range）
  - 异常前切断执行机制
- [x] 2.4 在 `execution.py` 中注入 Fuse Box 校验钩子
- [ ] 2.5 编写单元测试

### 任务 3: 实现 Fallback 机制
- [x] 3.1 设计节点 `optional` 标记机制
- [x] 3.2 实现 `comfy/harness/execution/fallback.py`
  - 非关键节点失败检测
  - 自动旁路逻辑（输入直通输出）
  - 配置项：bypass/abort/retry
- [x] 3.3 在节点注册时支持 `optional` 参数
- [ ] 3.4 编写单元测试

### 任务 4: 实现 Retry with Backoff
- [x] 4.1 设计重试策略接口
- [x] 4.2 实现 `comfy/harness/execution/retry.py`
  - 显存不足错误识别
  - 自动有限重试（指数退避）
  - 动态缩小批次大小
- [x] 4.3 在 `execution.py` 中集成重试逻辑
- [ ] 4.4 编写单元测试

## Phase 2: 类型安全与合约化（可控）

### 任务 5: 改造 `comfy/nodes.py` - 集成类型合约
- [ ] 5.1 分析现有 `NODE_CLASS_MAPPINGS` 结构
- [ ] 5.2 设计元数据合约格式（尺寸范围、色彩空间、数值精度等）
- [ ] 5.3 实现 `comfy/harness/types/contracts.py`
- [ ] 5.4 在节点注册时支持合约定义
- [ ] 5.5 编写单元测试

### 任务 6: 实现图编译阶段类型检查
- [ ] 6.1 设计图编译器架构
- [ ] 6.2 实现 `comfy/harness/types/compiler.py`
  - 工作流加载时静态类型检查
  - 连接兼容性验证
  - 编译期错误拦截
- [ ] 6.3 在工作流加载流程中集成编译器
- [ ] 6.4 编写单元测试

### 任务 7: 实现类型注册表
- [ ] 7.1 设计类型注册表结构
- [ ] 7.2 实现 `comfy/harness/types/registry.py`
  - 统一类型注册
  - 自定义类型扩展支持
- [ ] 7.3 实现 `comfy/harness/types/validators.py`
  - 输入校验器集合
- [ ] 7.4 编写单元测试

## Phase 3: 内建可观测性（可观测）

### 任务 8: 改造 `comfy/server.py` - 集成可观测性埋点
- [ ] 8.1 分析现有 `server.py` WebSocket 实现
- [ ] 8.2 设计可观测性埋点接口
- [ ] 8.3 在关键位置注入埋点钩子

### 任务 9: 实现 Tracing 层
- [ ] 9.1 设计 Tracing 数据模型
- [ ] 9.2 实现 `comfy/harness/observability/tracer.py`
  - 输入 tensor 统计特征记录（均值、方差、极值）
  - 执行耗时记录
  - 显存峰值记录
  - 输出 tensor 统计特征记录
- [ ] 9.3 在节点执行管线中嵌入 Tracing 层
- [ ] 9.4 编写单元测试

### 任务 10: 实现黑匣子记录器
- [ ] 10.1 设计执行轨迹存储格式
- [ ] 10.2 实现 `comfy/harness/observability/recorder.py`
  - 可回放执行轨迹生成
  - 异常回溯支持
  - 效果归因分析
- [ ] 10.3 在任务完成时触发记录
- [ ] 10.4 编写单元测试

### 任务 11: 实现 OpenTelemetry 埋点
- [ ] 11.1 研究 OpenTelemetry Python SDK
- [ ] 11.2 实现 `comfy/harness/observability/telemetry.py`
  - 轻量级埋点
  - 与 Tracing 层集成
- [ ] 11.3 编写单元测试

## Phase 4: 自适应资源管理（可控、可自愈）

### 任务 12: 改造 `comfy/model_management.py` - 集成资源管理器
- [ ] 12.1 分析现有模型加载机制
- [ ] 12.2 设计资源管理器接口
- [ ] 12.3 在模型加载流程中注入资源管理钩子

### 任务 13: 实现资源需求预估
- [ ] 13.1 设计资源预估算法
- [ ] 13.2 实现 `comfy/harness/resource/estimator.py`
  - 基于节点类型估算
  - 基于输入尺寸估算
  - 显存与计算时间预测
- [ ] 13.3 在工作流执行前调用预估
- [ ] 13.4 编写单元测试

### 任务 14: 实现动态调度器
- [ ] 14.1 设计调度策略
- [ ] 14.2 实现 `comfy/harness/resource/scheduler.py`
  - CUDA Stream 动态分配
  - Model Offloading 策略选择
  - Latent 切片策略选择
- [ ] 14.3 在节点执行时应用调度策略
- [ ] 14.4 编写单元测试

### 任务 15: 实现精度自适应
- [ ] 15.1 设计精度切换策略
- [ ] 15.2 实现 `comfy/harness/resource/adaptive_precision.py`
  - 负载检测
  - fp32→fp16 自动降级
  - 轻负载全精度恢复
- [ ] 15.3 在模型推理时集成精度切换
- [ ] 15.4 编写单元测试

## Phase 5: 自进化系统（可进化）

### 任务 16: 实现工作流版本管理
- [ ] 16.1 设计版本管理架构
- [ ] 16.2 实现 `comfy/harness/evolution/versioning.py`
  - 工作流版本标记（`v1-stable`, `v2-canary`）
  - 版本存储与检索
  - Git-like 版本系统
- [ ] 16.3 在前端/API 层支持版本管理
- [ ] 16.4 编写单元测试

### 任务 17: 实现金丝雀部署
- [ ] 17.1 设计金丝雀部署流程
- [ ] 17.2 实现 `comfy/harness/evolution/canary.py`
  - 同一批输入推送到稳定版与灰度版
  - 并行执行管理
  - 结果对比
- [ ] 17.3 在生成任务中集成金丝雀逻辑
- [ ] 17.4 编写单元测试

### 任务 18: 实现 AI 裁判评分
- [ ] 18.1 选型质量评估模型（LAION Aesthetic Score / CLIP Score）
- [ ] 18.2 实现 `comfy/harness/evolution/referee.py`
  - AI 裁判自动评分
  - 质量阈值判断
  - 自动提升稳定版逻辑
- [ ] 18.3 在金丝雀部署后触发评分
- [ ] 18.4 编写单元测试

### 任务 19: 实现闭环优化器
- [ ] 19.1 设计优化策略
- [ ] 19.2 实现 `comfy/harness/evolution/optimizer.py`
  - 反馈数据收集
  - 工作流参数自动优化
  - "生成更高质量"闭环
- [ ] 19.3 在收集足够反馈后触发优化
- [ ] 19.4 编写单元测试

## 任务依赖关系

```
Phase 1 (必须先完成)
├── 任务 1 → 任务 2, 3, 4
├── 任务 2 (execution.py 改造) → Phase 2, 3, 4
└── 任务 3, 4 → 相互独立，可并行

Phase 2
├── 任务 5 → 任务 6, 7
└── 任务 6, 7 → 相互独立

Phase 3
├── 任务 8 → 任务 9, 10, 11
└── 任务 9, 10, 11 → 相互独立

Phase 4
├── 任务 12 → 任务 13, 14, 15
└── 任务 13, 14, 15 → 相互独立

Phase 5
├── 任务 16 → 任务 17
├── 任务 17 → 任务 18
└── 任务 18 → 任务 19
```

## 源码改造文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `comfy/execution.py` | 改造 | 集成 Fuse Box、Fallback、Retry |
| `comfy/model_management.py` | 改造 | 集成资源管理器 |
| `comfy/server.py` | 改造 | 集成可观测性埋点 |
| `comfy/nodes.py` | 改造 | 集成类型合约 |
| `comfy/harness/__init__.py` | 新增 | Harness 启用控制 |
| `comfy/harness/config.py` | 新增 | 配置管理 |
| `comfy/harness/execution/fuse_box.py` | 新增 | Fuse Box 模式 |
| `comfy/harness/execution/fallback.py` | 新增 | Fallback 机制 |
| `comfy/harness/execution/retry.py` | 新增 | Retry with Backoff |
| `comfy/harness/types/contracts.py` | 新增 | 元数据合约 |
| `comfy/harness/types/compiler.py` | 新增 | 图编译器 |
| `comfy/harness/types/registry.py` | 新增 | 类型注册表 |
| `comfy/harness/types/validators.py` | 新增 | 输入校验器 |
| `comfy/harness/observability/tracer.py` | 新增 | Tracing 层 |
| `comfy/harness/observability/recorder.py` | 新增 | 黑匣子记录器 |
| `comfy/harness/observability/telemetry.py` | 新增 | OpenTelemetry 埋点 |
| `comfy/harness/observability/dashboard.py` | 新增 | 监控看板 |
| `comfy/harness/resource/estimator.py` | 新增 | 资源预估 |
| `comfy/harness/resource/scheduler.py` | 新增 | 动态调度器 |
| `comfy/harness/resource/adaptive_precision.py` | 新增 | 精度自适应 |
| `comfy/harness/resource/memory_pool.py` | 新增 | 显存池管理 |
| `comfy/harness/evolution/versioning.py` | 新增 | 版本管理 |
| `comfy/harness/evolution/canary.py` | 新增 | 金丝雀部署 |
| `comfy/harness/evolution/referee.py` | 新增 | AI 裁判 |
| `comfy/harness/evolution/optimizer.py` | 新增 | 闭环优化器 |