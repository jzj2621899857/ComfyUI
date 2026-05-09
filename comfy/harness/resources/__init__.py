"""
自适应资源管理模块
提供显存监控和动态批处理大小调整能力
"""

from .memory_monitor import MemoryMonitor, memory_monitor, MemoryStats
from .resource_manager import ResourceManager, resource_manager, ResourceSettings
from .estimator import ResourceEstimator, estimator, ResourceEstimate, NodeProfile
from .scheduler import DynamicScheduler, scheduler, Task, Priority, ResourceSnapshot
from .adaptive_precision import AdaptivePrecisionController, precision_controller, PrecisionMode, QualityMetrics, PrecisionProfile
from .memory_pool import MemoryPool, memory_pool, MemoryBlock

__all__ = [
    "MemoryMonitor",
    "memory_monitor",
    "MemoryStats",
    "ResourceManager",
    "resource_manager",
    "ResourceSettings",
    "ResourceEstimator",
    "estimator",
    "ResourceEstimate",
    "NodeProfile",
    "DynamicScheduler",
    "scheduler",
    "Task",
    "Priority",
    "ResourceSnapshot",
    "AdaptivePrecisionController",
    "precision_controller",
    "PrecisionMode",
    "QualityMetrics",
    "PrecisionProfile",
    "MemoryPool",
    "memory_pool",
    "MemoryBlock",
]