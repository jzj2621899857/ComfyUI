"""
资源管理器 - 动态调整批处理大小和资源分配
"""

import time
from typing import Dict, Optional, Any, Callable
from dataclasses import dataclass, field

from .memory_monitor import memory_monitor, MemoryStats

@dataclass
class ResourceSettings:
    max_batch_size: int = 8
    min_batch_size: int = 1
    current_batch_size: int = 4
    auto_adjust: bool = True
    memory_threshold: float = 0.85
    target_memory_usage: float = 0.70

class ResourceManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._settings = ResourceSettings()
            cls._instance._enabled = False
            cls._instance._last_adjust_time = 0
            cls._instance._adjust_interval = 5.0
            cls._instance._callbacks = []
            cls._instance._init_memory_callback()
        return cls._instance
    
    def _init_memory_callback(self):
        def on_memory_update(stats: MemoryStats):
            if not self._enabled or not self._settings.auto_adjust:
                return
            
            now = time.time()
            if now - self._last_adjust_time < self._adjust_interval:
                return
            
            self._last_adjust_time = now
            self._adjust_batch_size(stats)
        
        memory_monitor.add_callback(on_memory_update)
    
    def enable(self):
        self._enabled = True
        memory_monitor.enable()
    
    def disable(self):
        self._enabled = False
    
    def is_enabled(self) -> bool:
        return self._enabled
    
    def set_settings(self, settings: ResourceSettings):
        self._settings = settings
    
    def get_settings(self) -> ResourceSettings:
        return self._settings
    
    def _adjust_batch_size(self, stats: MemoryStats):
        usage = stats.usage_percent / 100
        
        if usage >= self._settings.memory_threshold:
            self.decrease_batch_size()
        elif usage < self._settings.target_memory_usage and self._settings.current_batch_size < self._settings.max_batch_size:
            self.increase_batch_size()
    
    def increase_batch_size(self):
        if self._settings.current_batch_size < self._settings.max_batch_size:
            new_size = min(self._settings.current_batch_size * 2, self._settings.max_batch_size)
            self._settings.current_batch_size = new_size
            self._notify_callbacks("batch_size_increased", new_size)
    
    def decrease_batch_size(self):
        if self._settings.current_batch_size > self._settings.min_batch_size:
            new_size = max(self._settings.current_batch_size // 2, self._settings.min_batch_size)
            self._settings.current_batch_size = new_size
            self._notify_callbacks("batch_size_decreased", new_size)
    
    def get_batch_size(self) -> int:
        return self._settings.current_batch_size
    
    def suggest_batch_size(self, estimated_memory_usage: float) -> int:
        if not self._enabled:
            return self._settings.current_batch_size
        
        stats = memory_monitor.get_stats()
        if stats.total == 0:
            return self._settings.current_batch_size
        
        available_memory = stats.total - stats.used
        estimated_per_batch = estimated_memory_usage / self._settings.current_batch_size
        
        if estimated_per_batch == 0:
            return self._settings.current_batch_size
        
        max_possible = int(available_memory * 0.8 / estimated_per_batch)
        
        return max(self._settings.min_batch_size, min(max_possible, self._settings.max_batch_size))
    
    def add_callback(self, callback):
        if callback not in self._callbacks:
            self._callbacks.append(callback)
    
    def remove_callback(self, callback):
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_callbacks(self, event: str, data: Any):
        for callback in self._callbacks:
            try:
                callback(event, data)
            except Exception:
                pass
    
    def force_garbage_collection(self):
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
        
        import gc
        gc.collect()
    
    def get_memory_status(self) -> Dict[str, Any]:
        stats = memory_monitor.get_stats()
        return {
            "batch_size": self._settings.current_batch_size,
            "max_batch_size": self._settings.max_batch_size,
            "auto_adjust": self._settings.auto_adjust,
            **stats.to_dict()
        }

resource_manager = ResourceManager()