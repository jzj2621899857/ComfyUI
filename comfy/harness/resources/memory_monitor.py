"""
显存监控器 - 实时监控 GPU 显存使用情况
"""

import time
import threading
from typing import Dict, Optional, Any
from dataclasses import dataclass, field

@dataclass
class MemoryStats:
    used: int = 0
    free: int = 0
    total: int = 0
    peak: int = 0
    timestamp: float = 0.0
    
    @property
    def usage_percent(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.used / self.total) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "used": self.used,
            "free": self.free,
            "total": self.total,
            "peak": self.peak,
            "usage_percent": self.usage_percent,
            "timestamp": self.timestamp
        }

class MemoryMonitor:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._enabled = False
            cls._instance._running = False
            cls._instance._thread = None
            cls._instance._interval = 1.0
            cls._instance._stats = MemoryStats()
            cls._instance._peak_memory = 0
            cls._instance._callbacks = []
            cls._instance._torch_available = False
            cls._instance._nvidia_available = False
            cls._instance._init_backends()
        return cls._instance
    
    def _init_backends(self):
        try:
            import torch
            self._torch_available = True
            if torch.cuda.is_available():
                self._nvidia_available = True
        except ImportError:
            pass
    
    def enable(self):
        self._enabled = True
    
    def disable(self):
        self._enabled = False
    
    def is_enabled(self) -> bool:
        return self._enabled
    
    def set_interval(self, interval: float):
        self._interval = interval
    
    def _update_stats(self):
        if not self._torch_available or not self._nvidia_available:
            return
        
        import torch
        
        try:
            total = torch.cuda.get_device_properties(0).total_memory
            used = torch.cuda.memory_allocated(0)
            free = total - used
            
            self._peak_memory = max(self._peak_memory, used)
            
            self._stats = MemoryStats(
                used=used,
                free=free,
                total=total,
                peak=self._peak_memory,
                timestamp=time.time()
            )
            
            for callback in self._callbacks:
                callback(self._stats)
        except Exception:
            pass
    
    def start(self):
        if not self._enabled or self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()
    
    def _monitor_loop(self):
        while self._running:
            self._update_stats()
            time.sleep(self._interval)
    
    def get_stats(self) -> MemoryStats:
        if not self._enabled:
            return MemoryStats()
        
        if not self._running:
            self._update_stats()
        
        return self._stats
    
    def get_usage_percent(self) -> float:
        return self.get_stats().usage_percent
    
    def is_low_memory(self, threshold: float = 0.9) -> bool:
        return self.get_usage_percent() >= threshold * 100
    
    def add_callback(self, callback):
        if callback not in self._callbacks:
            self._callbacks.append(callback)
    
    def remove_callback(self, callback):
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def reset_peak(self):
        self._peak_memory = 0

memory_monitor = MemoryMonitor()