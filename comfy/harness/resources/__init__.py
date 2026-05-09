"""
自适应资源管理模块
提供显存监控和动态批处理大小调整能力
"""

from .memory_monitor import MemoryMonitor, memory_monitor, MemoryStats
from .resource_manager import ResourceManager, resource_manager, ResourceSettings

__all__ = [
    "MemoryMonitor",
    "memory_monitor",
    "MemoryStats",
    "ResourceManager",
    "resource_manager",
    "ResourceSettings",
]