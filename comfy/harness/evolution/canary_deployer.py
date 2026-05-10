"""
金丝雀部署管理器 - 工作流新版本的灰度发布与自动回滚
"""

import time
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class CanaryConfig:
    workflow_id: str
    new_version_id: str
    traffic_percent: float = 10.0
    max_traffic_percent: float = 100.0
    increment_percent: float = 10.0
    increment_interval: float = 60.0
    health_check_interval: float = 30.0
    failure_threshold: float = 5.0
    max_duration: float = 3600.0
    enabled: bool = False

@dataclass
class CanaryStatus:
    config: CanaryConfig
    start_time: float
    current_traffic: float = 0.0
    requests_served: int = 0
    requests_failed: int = 0
    is_running: bool = False
    status: str = "pending"
    last_health_check: float = 0.0
    
    @property
    def failure_rate(self) -> float:
        if self.requests_served == 0:
            return 0.0
        return (self.requests_failed / self.requests_served) * 100
    
    @property
    def duration(self) -> float:
        return time.time() - self.start_time

class CanaryDeployer:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._canaries: Dict[str, CanaryStatus] = {}
            cls._instance._running = False
            cls._instance._thread = None
            cls._instance._callbacks = []
            cls._instance._enabled = False
        return cls._instance
    
    def enable(self):
        self._enabled = True
    
    def disable(self):
        self._enabled = False
        self.stop_all_canaries()
    
    def is_enabled(self) -> bool:
        return self._enabled
    
    def start_canary(self, config: CanaryConfig) -> bool:
        if not self._enabled:
            return False
        
        if config.workflow_id in self._canaries:
            return False
        
        status = CanaryStatus(
            config=config,
            start_time=time.time(),
            current_traffic=0.0,
            status="starting"
        )
        self._canaries[config.workflow_id] = status
        
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._thread.start()
        
        self._notify_callbacks("canary_started", status)
        return True
    
    def stop_canary(self, workflow_id: str):
        if workflow_id not in self._canaries:
            return
        
        status = self._canaries[workflow_id]
        status.is_running = False
        status.status = "stopped"
        self._notify_callbacks("canary_stopped", status)
        
        del self._canaries[workflow_id]
        
        if not self._canaries:
            self._running = False
    
    def stop_all_canaries(self):
        for workflow_id in list(self._canaries.keys()):
            self.stop_canary(workflow_id)
    
    def promote_canary(self, workflow_id: str) -> bool:
        if workflow_id not in self._canaries:
            return False
        
        status = self._canaries[workflow_id]
        status.current_traffic = 100.0
        status.status = "promoted"
        
        self._notify_callbacks("canary_promoted", status)
        self.stop_canary(workflow_id)
        return True
    
    def rollback_canary(self, workflow_id: str) -> bool:
        if workflow_id not in self._canaries:
            return False
        
        status = self._canaries[workflow_id]
        status.current_traffic = 0.0
        status.status = "rolled_back"
        
        self._notify_callbacks("canary_rolled_back", status)
        self.stop_canary(workflow_id)
        return True
    
    def record_request(self, workflow_id: str, success: bool = True):
        if workflow_id not in self._canaries:
            return
        
        status = self._canaries[workflow_id]
        status.requests_served += 1
        if not success:
            status.requests_failed += 1
    
    def get_canary_status(self, workflow_id: str) -> Optional[CanaryStatus]:
        return self._canaries.get(workflow_id)
    
    def get_all_canaries(self) -> List[CanaryStatus]:
        return list(self._canaries.values())
    
    def _monitor_loop(self):
        while self._running:
            for workflow_id in list(self._canaries.keys()):
                self._check_canary(workflow_id)
            time.sleep(1.0)
    
    def _check_canary(self, workflow_id: str):
        if workflow_id not in self._canaries:
            return
        
        status = self._canaries[workflow_id]
        now = time.time()
        
        if status.status == "starting":
            status.current_traffic = status.config.traffic_percent
            status.is_running = True
            status.status = "running"
            status.last_health_check = now
            return
        
        if not status.is_running:
            return
        
        if status.duration >= status.config.max_duration:
            self.promote_canary(workflow_id)
            return
        
        if now - status.last_health_check >= status.config.health_check_interval:
            status.last_health_check = now
            
            if status.failure_rate >= status.config.failure_threshold:
                self.rollback_canary(workflow_id)
                return
        
        if now - status.start_time >= status.config.increment_interval:
            if status.current_traffic < status.config.max_traffic_percent:
                new_traffic = min(
                    status.current_traffic + status.config.increment_percent,
                    status.config.max_traffic_percent
                )
                status.current_traffic = new_traffic
                self._notify_callbacks("traffic_increased", status)
    
    def add_callback(self, callback):
        if callback not in self._callbacks:
            self._callbacks.append(callback)
    
    def remove_callback(self, callback):
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_callbacks(self, event: str, data):
        for callback in self._callbacks:
            try:
                callback(event, data)
            except Exception:
                pass

canary_deployer = CanaryDeployer()