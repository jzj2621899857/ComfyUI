# ComfyUI Harness 源码改造规格说明

## 一、核心思想：源码级 Harness Engineering

**不是**在 ComfyUI 外面套一个调度壳，**而是**重构其内部执行模型，构建一套内置的"线束系统"，像高性能引擎的电气线束一样，安全连接各个节点，精确控制输入/输出/状态，隔离故障，实时监控，并让工作流具备自进化能力。

**改造核心目标**：
- 将"Harness Engineering"原则（可控、可观测、可自愈、可进化）编译进 ComfyUI 的源码基因
- 使引擎本身成为内在质量更高、更健壮的生成式 AI 引擎
- 让工作流具备闭环自进化能力，"生成更高质量"

---

## 二、五大核心改造方向

### 2.1 节点执行引擎的"带保险丝"重构

| 改造点 | 现状 | 改造方案 | 实现位置 |
|--------|------|----------|----------|
| Fuse Box 模式 | `execution.py` 递归执行，单节点崩溃导致全局失败 | 为每个节点注入输入校验层（类型、shape、value range），异常前切断执行 | `comfy/harness/execution/fuse_box.py` |
| Fallback 机制 | 无 | 非关键节点失败时自动旁路（如美颜节点失败则直出原图） | `comfy/harness/execution/fallback.py` |
| Retry with Backoff | 无 | 针对显存不足等瞬态错误，自动有限重试，动态缩小批次大小 | `comfy/harness/execution/retry.py` |

### 2.2 工作流"类型安全与合约化"

| 改造点 | 现状 | 改造方案 | 实现位置 |
|--------|------|----------|----------|
| 强类型接口 | 节点连接靠松散字符串匹配 | 在 `NODE_CLASS_MAPPINGS` 中引入强类型接口，每个输入/输出附上**元数据合约**（尺寸范围、色彩空间、数值精度等） | `comfy/harness/types/contracts.py` |
| 静态类型检查 | 错误只能在运行时暴露 | 增加"图编译阶段"的静态类型检查，提前拦截不兼容连接 | `comfy/harness/types/compiler.py` |
| 类型注册表 | 无 | 建立统一的类型注册表，支持自定义类型扩展 | `comfy/harness/types/registry.py` |

### 2.3 内建可观测性与"黑匣子"记录

| 改造点 | 现状 | 改造方案 | 实现位置 |
|--------|------|----------|----------|
| Tracing 层 | 日志粗糙，调试困难 | 在节点执行管线中嵌入 Tracing 层，自动记录每个节点的输入/输出 tensor 统计特征、执行耗时、显存峰值 | `comfy/harness/observability/tracer.py` |
| 执行轨迹 | 无 | 生成可回放的执行轨迹，用于异常回溯和效果归因 | `comfy/harness/observability/recorder.py` |
| OpenTelemetry | 无 | 借鉴 OpenTelemetry 轻量级埋点思想植入 `execution.py` | `comfy/harness/observability/telemetry.py` |

### 2.4 自适应资源管理器（Harness 式调度）

| 改造点 | 现状 | 改造方案 | 实现位置 |
|--------|------|----------|----------|
| 资源预估 | 显存管理被动依赖 PyTorch 分配器 | 执行前基于节点类型和输入尺寸估算显存与计算时间 | `comfy/harness/resource/estimator.py` |
| 动态调度 | 无 | 运行时动态选择 CUDA Stream、Model Offloading、Latent 切片策略 | `comfy/harness/resource/scheduler.py` |
| 精度自适应 | 无 | 高负载自动降低精度（fp32→fp16），轻负载全速运行 | `comfy/harness/resource/adaptive_precision.py` |

### 2.5 工作流版本化与"金丝雀部署"自进化

| 改造点 | 现状 | 改造方案 | 实现位置 |
|--------|------|----------|----------|
| 版本管理 | 工作流 JSON 是静态快照 | 前端/API 层支持工作流版本管理（`v1-stable`, `v2-canary`） | `comfy/harness/evolution/versioning.py` |
| 金丝雀部署 | 无 | 内置 Harness 引擎将同一批输入同时推送到稳定版与灰度版 | `comfy/harness/evolution/canary.py` |
| AI 裁判评分 | 无 | 用 AI 裁判自动评分，质量持续超过阈值后自动提升为稳定版 | `comfy/harness/evolution/referee.py` |
| 闭环进化 | 无 | 形成"生成更高质量"的闭环自进化能力 | `comfy/harness/evolution/optimizer.py` |

---

## 三、源码目录结构改造

```
ComfyUI/
├── comfy/
│   ├── __init__.py
│   ├── api/                    # [保留] 原有 API
│   ├── execution.py            # [改造] 集成 Harness 执行引擎
│   ├── model_management.py     # [改造] 集成资源管理器
│   ├── server.py               # [改造] 集成可观测性埋点
│   ├── nodes.py                # [改造] 集成类型合约
│   │
│   └── harness/               # [新增] Harness 核心模块
│       ├── __init__.py         # Harness 启用控制
│       ├── config.py           # 配置管理
│       │
│       ├── execution/          # [新增] 执行引擎改造
│       │   ├── __init__.py
│       │   ├── fuse_box.py     # Fuse Box 模式
│       │   ├── fallback.py     # Fallback 机制
│       │   ├── retry.py        # Retry with Backoff
│       │   └── executor.py     # 增强执行器
│       │
│       ├── types/              # [新增] 类型安全与合约
│       │   ├── __init__.py
│       │   ├── contracts.py    # 元数据合约定义
│       │   ├── compiler.py     # 图编译阶段类型检查
│       │   ├── registry.py     # 类型注册表
│       │   └── validators.py   # 输入校验器
│       │
│       ├── observability/      # [新增] 可观测性
│       │   ├── __init__.py
│       │   ├── tracer.py       # Tracing 层
│       │   ├── recorder.py     # 黑匣子记录器
│       │   ├── telemetry.py    # OpenTelemetry 埋点
│       │   └── dashboard.py    # 监控看板
│       │
│       ├── resource/           # [新增] 资源管理
│       │   ├── __init__.py
│       │   ├── estimator.py    # 资源需求预估
│       │   ├── scheduler.py    # 动态调度器
│       │   ├── adaptive_precision.py  # 精度自适应
│       │   └── memory_pool.py  # 显存池管理
│       │
│       └── evolution/          # [新增] 自进化系统
│           ├── __init__.py
│           ├── versioning.py   # 工作流版本管理
│           ├── canary.py       # 金丝雀部署
│           ├── referee.py      # AI 裁判评分
│           └── optimizer.py    # 闭环优化器
```

---

## 四、功能需求（源码级别）

### 4.1 节点执行引擎改造

#### 场景：Fuse Box 输入校验
- **当** 节点执行前
- **且** 输入数据不符合合约要求（类型、shape、value range）
- **那么** 在校验层切断执行，返回明确的错误信息
- **实现位置**：`comfy/harness/execution/fuse_box.py`

#### 场景：Fallback 自动旁路
- **当** 非关键节点执行失败时
- **且** 该节点标记为 `optional=True`
- **那么** 自动旁路该节点，将输入直通到输出
- **实现位置**：`comfy/harness/execution/fallback.py`

#### 场景：Retry with Backoff
- **当** 节点执行因显存不足失败时
- **那么** 自动重试，每次重试动态缩小批次大小
- **且** 重试次数不超过配置上限
- **实现位置**：`comfy/harness/execution/retry.py`

### 4.2 类型安全与合约化

#### 场景：元数据合约定义
- **当** 节点注册时
- **那么** 每个输入/输出端口附上元数据合约
- **包含**：尺寸范围、色彩空间、数值精度、数据类型等
- **实现位置**：`comfy/harness/types/contracts.py`

#### 场景：图编译阶段类型检查
- **当** 工作流加载时
- **那么** 执行静态类型检查，验证所有连接兼容性
- **且** 发现不兼容连接时提前报错，阻止执行
- **实现位置**：`comfy/harness/types/compiler.py`

### 4.3 内建可观测性

#### 场景：Tracing 层自动记录
- **当** 节点执行时
- **那么** 自动记录：
  - 输入 tensor 统计特征（均值、方差、极值）
  - 执行耗时、显存峰值
  - 输出 tensor 统计特征
- **实现位置**：`comfy/harness/observability/tracer.py`

#### 场景：黑匣子记录
- **当** 任务执行完成（无论成功/失败）
- **那么** 生成可回放的执行轨迹
- **用于**：异常回溯和效果归因
- **实现位置**：`comfy/harness/observability/recorder.py`

### 4.4 自适应资源管理

#### 场景：资源需求预估
- **当** 工作流执行前
- **那么** 基于节点类型和输入尺寸估算显存与计算时间
- **实现位置**：`comfy/harness/resource/estimator.py`

#### 场景：动态调度
- **当** 节点执行时
- **那么** 根据资源预估动态选择：
  - CUDA Stream 分配
  - Model Offloading 策略
  - Latent 切片策略
- **实现位置**：`comfy/harness/resource/scheduler.py`

#### 场景：精度自适应
- **当** 系统负载高时
- **那么** 自动降低精度（fp32→fp16）
- **当** 系统负载低时
- **那么** 全精度运行
- **实现位置**：`comfy/harness/resource/adaptive_precision.py`

### 4.5 工作流版本化与自进化

#### 场景：工作流版本管理
- **当** 用户保存工作流时
- **那么** 支持版本标记（`v1-stable`, `v2-canary`）
- **实现位置**：`comfy/harness/evolution/versioning.py`

#### 场景：金丝雀部署
- **当** 执行生成任务时
- **且** 存在灰度版本工作流
- **那么** 将同一批输入同时推送到稳定版与灰度版
- **实现位置**：`comfy/harness/evolution/canary.py`

#### 场景：AI 裁判评分
- **当** 金丝雀部署产生输出时
- **那么** 用 AI 裁判自动评分
- **且** 质量持续超过阈值后自动提升为稳定版
- **实现位置**：`comfy/harness/evolution/referee.py`

#### 场景：闭环优化
- **当** 收集到足够反馈数据时
- **那么** 自动优化工作流参数
- **形成**："生成更高质量"的闭环自进化能力
- **实现位置**：`comfy/harness/evolution/optimizer.py`

---

## 五、技术选型

| 组件 | 技术方案 | 代码位置 |
|------|---------|---------|
| 执行引擎 | 改造 `comfy/execution.py` | `comfy/harness/execution/` |
| 类型系统 | Python Type Hints + 自定义合约 | `comfy/harness/types/` |
| 可观测性 | OpenTelemetry 规范 | `comfy/harness/observability/` |
| 资源管理 | PyTorch CUDA API + 自定义调度器 | `comfy/harness/resource/` |
| 版本管理 | Git-like 工作流版本系统 | `comfy/harness/evolution/` |

---

## 六、源码改造架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Harness 线束系统 (新增)                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │  execution/ │ │   types/    │ │observability│ │  resource/  ││
│  │  带保险丝   │ │ 类型安全    │ │  黑匣子     │ │ 自适应调度  ││
│  │  执行引擎   │ │ 合约化      │ │  可观测     │ │ 资源管理    ││
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘│
│         │               │               │               │       │
│  ┌──────▼───────────────▼───────────────▼───────────────▼──────┐│
│  │                    evolution/                               ││
│  │              金丝雀部署 + 自进化系统                          ││
│  └─────────────────────────────────────────────────────────────┘│
└───────────────────────────┬─────────────────────────────────────┘
                            │ 注入
┌───────────────────────────▼─────────────────────────────────────┐
│                   ComfyUI 核心 (改造)                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │ execution.py│ │model_manag..│ │  server.py  │ │  nodes.py   ││
│  │ [改造]      │ │   [改造]    │ │   [改造]    │ │   [改造]    ││
│  │ 集成保险丝  │ │ 集成资源管理 │ │ 集成埋点    │ │ 集成合约    ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## 七、改造优先级

### Phase 1: 执行引擎可靠性（可控、可自愈）
- [ ] 改造 `comfy/execution.py` - 集成 Fuse Box 模式
- [ ] 新增 `comfy/harness/execution/fuse_box.py`
- [ ] 新增 `comfy/harness/execution/fallback.py`
- [ ] 新增 `comfy/harness/execution/retry.py`

### Phase 2: 类型安全与合约化（可控）
- [ ] 改造 `comfy/nodes.py` - 集成类型合约
- [ ] 新增 `comfy/harness/types/contracts.py`
- [ ] 新增 `comfy/harness/types/compiler.py`
- [ ] 新增 `comfy/harness/types/registry.py`

### Phase 3: 可观测性（可观测）
- [ ] 改造 `comfy/server.py` - 集成可观测性埋点
- [ ] 新增 `comfy/harness/observability/tracer.py`
- [ ] 新增 `comfy/harness/observability/recorder.py`
- [ ] 新增 `comfy/harness/observability/telemetry.py`

### Phase 4: 资源管理（可控、可自愈）
- [ ] 改造 `comfy/model_management.py` - 集成资源管理器
- [ ] 新增 `comfy/harness/resource/estimator.py`
- [ ] 新增 `comfy/harness/resource/scheduler.py`
- [ ] 新增 `comfy/harness/resource/adaptive_precision.py`

### Phase 5: 自进化系统（可进化）
- [ ] 新增 `comfy/harness/evolution/versioning.py`
- [ ] 新增 `comfy/harness/evolution/canary.py`
- [ ] 新增 `comfy/harness/evolution/referee.py`
- [ ] 新增 `comfy/harness/evolution/optimizer.py`

---

## 八、向后兼容性

**重要原则**：所有改造必须保持向后兼容

- 原有的 API 端点必须继续工作
- 原有启动方式必须保持不变
- 原有的自定义节点必须继续可用
- 新增的 Harness 能力作为可选项存在

### 兼容性实现策略

```python
# comfy/harness/__init__.py
HARNESS_ENABLED = os.environ.get("COMFYUI_HARNESS", "false").lower() == "true"

def setup_harness():
    if not HARNESS_ENABLED:
        return  # 原有行为
    
    # Harness 增强逻辑
    from .execution import patch_execution
    from .types import patch_nodes
    from .observability import patch_server
    
    patch_execution()
    patch_nodes()
    patch_server()
```

---

## 九、配置项（config_options.yaml）

```yaml
harness:
  enabled: false  # 默认关闭，保持原有行为
  
execution:
  fuse_box:
    enabled: true
    strict_mode: false  # true=严格校验，false=警告模式
  fallback:
    enabled: true
    default_behavior: "bypass"  # bypass/abort/retry
  retry:
    enabled: true
    max_attempts: 3
    backoff_factor: 2
    
types:
  strict_mode: false  # 编译期类型检查严格程度
  
observability:
  tracing_enabled: true
  recorder_enabled: true
  telemetry_format: "opentelemetry"
  
resource:
  estimation_enabled: true
  adaptive_precision: true
  memory_threshold: 0.9  # 显存使用阈值
  
evolution:
  versioning_enabled: false
  canary_enabled: false
  auto_promote_threshold: 0.95  # 自动提升阈值
```

---

## 十、改造后的核心收益

- **可靠性跃升**：非关键节点失败不影响全局，自动重试/降解保障管线完整
- **输出一致性**：强类型合约杜绝"颜色空间错乱"等隐蔽错误
- **质量自进化**：金丝雀部署 + 自动反馈让工作流越用越好
- **调试效率**：全链路可观测，可快速定位"画面偏色从哪个节点开始"
- **极致资源利用**：自适应调度降低显存溢出，同级硬件跑更复杂任务

---

## 十一、硬件配置影响

- 改造后，**入门级 GPU (12 GB)** 可运行更复杂工作流（资源预估降低溢出风险）
- **专业级 (24 GB+)** 可并行 A/B 实验，成为"生成更高质量"的必要算力基础
