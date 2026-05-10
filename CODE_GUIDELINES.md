# ComfyUI Harness 代码规范

## 一、核心原则

### 1.1 完全解耦原则（强制）
- **严禁直接修改** ComfyUI 原有文件（如 `server.py`、`main.py`、`execution.py` 等）
- 所有功能必须通过 **钩子（hooks）**、**装饰器（decorators）** 或 **动态注入** 实现
- 冲突优先策略：以 ComfyUI 官方代码为准，Harness 代码作为可选扩展

### 1.2 向后兼容性（强制）
- Harness 功能必须默认为 **关闭状态**
- 启用后不应影响原有工作流的正常执行
- 支持 `COMFYUI_HARNESS=false` 完全禁用

### 1.3 渐进式增强（推荐）
- 功能设计遵循渐进式增强原则
- 核心功能可用作独立模块
- 支持按需启用/禁用单个子模块

---

## 二、代码结构规范

### 2.1 目录结构
```
comfy/
└── harness/              # Harness 主目录（新增，不影响原有结构）
    ├── __init__.py       # 入口模块，初始化配置
    ├── config.py         # 配置管理
    ├── README.md         # 模块说明
    ├── execution/        # 执行引擎增强
    ├── types/            # 类型系统
    ├── observability/    # 可观测性
    ├── resources/        # 资源管理
    └── evolution/        # 自进化系统
```

### 2.2 文件命名
- 使用小写字母和下划线（snake_case）
- 测试文件以 `test_` 开头
- API 路由文件以 `api_` 开头

---

## 三、扩展方式规范

### 3.1 路由注册
- 使用 **动态注入** 方式注册 API 路由
- 通过 `start_with_harness.py` 启动脚本统一管理
- 不修改 `server.py`

```python
# 推荐：动态注入
def patch_server(server_instance):
    """通过 monkey-patch 动态注册路由"""
    if hasattr(server_instance, 'app'):
        register_harness_routes(server_instance.app)
```

### 3.2 功能扩展
- 使用 ComfyUI 现有的钩子系统
- 通过装饰器包装原有函数
- 支持运行时动态启用/禁用

### 3.3 配置管理
- 通过环境变量配置
- 支持 `.env` 文件
- 配置项必须有合理默认值

---

## 四、冲突处理规范

### 4.1 同步官方更新
使用 `sync-harness.sh` 脚本：
- 自动拉取官方更新
- 冲突时以 Harness 代码为主
- 记录冲突日志供人工审查

### 4.2 冲突解决优先级
1. **API 兼容层**：保持对外接口不变
2. **功能降级**：核心功能不可用时优雅降级
3. **日志告警**：记录但不中断执行

---

## 五、部署规范

### 5.1 启动方式
**推荐方式**（完全解耦）：
```bash
python start_with_harness.py
```

**传统方式**（禁用 Harness）：
```bash
python main.py
```

### 5.2 环境变量
```bash
# 全局开关
COMFYUI_HARNESS=true

# 模块开关
HARNESS_FUSE_BOX=true
HARNESS_FALLBACK=true
HARNESS_RETRY=true
HARNESS_OBSERVABILITY=true
HARNESS_RESOURCE=true
HARNESS_EVOLUTION=false
```

---

## 六、测试规范

### 6.1 单元测试
- 每个模块必须有对应的测试文件
- 测试文件位于模块目录内（`test_*.py`）
- 支持独立运行测试

### 6.2 集成测试
- 测试不应修改原有功能
- 支持测试隔离模式
- 测试结果不影响生产环境

---

## 七、文档规范

### 7.1 代码注释
- 使用 Google 风格注释
- 关键函数必须有文档字符串
- 复杂逻辑应有注释说明

### 7.2 API 文档
- 使用 OpenAPI/Swagger 格式
- 提供完整的 API 说明
- 示例代码

---

## 八、强制检查清单

在提交代码前必须检查：

- [ ] 是否修改了 ComfyUI 原有文件？（禁止）
- [ ] 是否有完整的单元测试？
- [ ] 是否支持默认关闭？
- [ ] 是否有向后兼容性？
- [ ] 是否符合代码风格规范？
- [ ] 是否有足够的文档？

---

## 九、违规处理

- 首次违规：警告并要求修复
- 重复违规：暂停合并权限
- 严重违规：移除相关代码

---

**版本**: v1.0  
**生效日期**: 2024-01-01  
**适用范围**: ComfyUI Harness 所有代码