"""
Harness 配置管理

集中管理所有 Harness 相关的配置项
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FuseBoxConfig:
    """Fuse Box 配置"""
    enabled: bool = True
    strict_mode: bool = False  # True=严格校验，False=警告模式
    max_shape_diff: float = 0.1  # shape 差异容忍度（10%）
    check_value_range: bool = True  # 是否检查数值范围


@dataclass
class FallbackConfig:
    """Fallback 配置"""
    enabled: bool = True
    default_behavior: str = "bypass"  # bypass/abort/retry
    log_fallback: bool = True  # 是否记录 fallback 事件


@dataclass
class RetryConfig:
    """Retry 配置"""
    enabled: bool = True
    max_attempts: int = 3
    backoff_factor: float = 2.0
    batch_size_reduction: float = 0.5  # 每次重试批次大小缩减比例
    retryable_errors: tuple = field(default_factory=lambda: (
        "CUDA out of memory",
        "out of memory",
        "Allocation on device",
    ))


@dataclass
class ExecutionConfig:
    """执行引擎配置"""
    fuse_box: FuseBoxConfig = field(default_factory=FuseBoxConfig)
    fallback: FallbackConfig = field(default_factory=FallbackConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)


@dataclass
class TypesConfig:
    """类型系统配置"""
    enabled: bool = True
    strict_mode: bool = False  # 编译期类型检查严格程度
    allow_any_type: bool = True  # 是否允许 * 通配类型


@dataclass
class ObservabilityConfig:
    """可观测性配置"""
    enabled: bool = True
    tracing_enabled: bool = True
    recorder_enabled: bool = True
    telemetry_format: str = "opentelemetry"
    trace_tensor_stats: bool = True  # 是否记录 tensor 统计特征
    trace_execution_time: bool = True  # 是否记录执行耗时
    trace_memory_peak: bool = True  # 是否记录显存峰值


@dataclass
class ResourceConfig:
    """资源管理配置"""
    enabled: bool = True
    estimation_enabled: bool = True
    adaptive_precision: bool = True
    memory_threshold: float = 0.9  # 显存使用阈值
    enable_offloading: bool = True  # 是否启用模型 offloading


@dataclass
class EvolutionConfig:
    """自进化系统配置"""
    enabled: bool = False
    versioning_enabled: bool = True
    canary_enabled: bool = True
    auto_promote_threshold: float = 0.95  # 自动提升阈值
    min_samples_for_promotion: int = 100  # 自动提升所需最小样本数


@dataclass
class HarnessConfig:
    """Harness 总配置"""
    enabled: bool = False
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    types: TypesConfig = field(default_factory=TypesConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    resource: ResourceConfig = field(default_factory=ResourceConfig)
    evolution: EvolutionConfig = field(default_factory=EvolutionConfig)
    
    @classmethod
    def from_env(cls) -> "HarnessConfig":
        """从环境变量加载配置"""
        config = cls()
        
        # 总开关
        config.enabled = os.environ.get("COMFYUI_HARNESS", "false").lower() == "true"
        
        # Execution 配置
        config.execution.fuse_box.enabled = os.environ.get(
            "COMFYUI_HARNESS_FUSE_BOX", "true"
        ).lower() == "true"
        config.execution.fuse_box.strict_mode = os.environ.get(
            "COMFYUI_HARNESS_FUSE_BOX_STRICT", "false"
        ).lower() == "true"
        
        config.execution.fallback.enabled = os.environ.get(
            "COMFYUI_HARNESS_FALLBACK", "true"
        ).lower() == "true"
        
        config.execution.retry.enabled = os.environ.get(
            "COMFYUI_HARNESS_RETRY", "true"
        ).lower() == "true"
        config.execution.retry.max_attempts = int(os.environ.get(
            "COMFYUI_HARNESS_RETRY_MAX", "3"
        ))
        
        # Types 配置
        config.types.enabled = os.environ.get(
            "COMFYUI_HARNESS_TYPES", "true"
        ).lower() == "true"
        config.types.strict_mode = os.environ.get(
            "COMFYUI_HARNESS_STRICT_TYPES", "false"
        ).lower() == "true"
        
        # Observability 配置
        config.observability.enabled = os.environ.get(
            "COMFYUI_HARNESS_OBSERVABILITY", "true"
        ).lower() == "true"
        
        # Resource 配置
        config.resource.enabled = os.environ.get(
            "COMFYUI_HARNESS_RESOURCE", "true"
        ).lower() == "true"
        config.resource.adaptive_precision = os.environ.get(
            "COMFYUI_HARNESS_ADAPTIVE_PRECISION", "true"
        ).lower() == "true"
        
        # Evolution 配置
        config.evolution.enabled = os.environ.get(
            "COMFYUI_HARNESS_EVOLUTION", "false"
        ).lower() == "true"
        
        return config


# 全局配置实例
_config: Optional[HarnessConfig] = None


def get_config() -> HarnessConfig:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = HarnessConfig.from_env()
    return _config


def reload_config() -> HarnessConfig:
    """重新加载配置"""
    global _config
    _config = HarnessConfig.from_env()
    return _config