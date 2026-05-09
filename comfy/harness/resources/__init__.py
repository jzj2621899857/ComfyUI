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
from .hooks import (
    ResourceManagementHooks,
    hooks as resource_hooks,
    install_hooks as install_resource_hooks,
    uninstall_hooks as uninstall_resource_hooks,
    get_hooks as get_resource_hooks,
    estimate_node_resources,
    estimate_workflow_resources,
    check_memory_available,
    force_cleanup
)

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
    "ResourceManagementHooks",
    "resource_hooks",
    "install_resource_hooks",
    "uninstall_resource_hooks",
    "get_resource_hooks",
    "estimate_node_resources",
    "estimate_workflow_resources",
    "check_memory_available",
    "force_cleanup",
]
