"""
结构化日志记录器 - 统一日志格式与输出管理
"""

import logging
import json
import sys
from typing import Any, Dict, Optional
from datetime import datetime

class StructuredLogger:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._logger = logging.getLogger("comfy-harness")
            cls._instance._logger.setLevel(logging.INFO)
            cls._instance._enabled = True
            cls._instance._init_handlers()
        return cls._instance
    
    def _init_handlers(self):
        if self._logger.handlers:
            return
        
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)
    
    def enable(self):
        self._enabled = True
    
    def disable(self):
        self._enabled = False
    
    def is_enabled(self) -> bool:
        return self._enabled
    
    def set_level(self, level: str):
        level_map = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL
        }
        self._logger.setLevel(level_map.get(level.lower(), logging.INFO))
    
    def log_node_execution(self, node_id: str, node_type: str, status: str, duration: float = 0.0, error: Optional[str] = None):
        if not self._enabled:
            return
        
        log_data = {
            "event": "node_execution",
            "node_id": node_id,
            "node_type": node_type,
            "status": status,
            "duration_ms": duration * 1000
        }
        
        if error:
            log_data["error"] = error
        
        self._logger.info(json.dumps(log_data))
    
    def log_workflow_start(self, workflow_id: str, node_count: int = 0):
        if not self._enabled:
            return
        
        log_data = {
            "event": "workflow_start",
            "workflow_id": workflow_id,
            "node_count": node_count,
            "timestamp": datetime.now().isoformat()
        }
        self._logger.info(json.dumps(log_data))
    
    def log_workflow_end(self, workflow_id: str, status: str, duration: float = 0.0, completed_nodes: int = 0, failed_nodes: int = 0):
        if not self._enabled:
            return
        
        log_data = {
            "event": "workflow_end",
            "workflow_id": workflow_id,
            "status": status,
            "duration_ms": duration * 1000,
            "completed_nodes": completed_nodes,
            "failed_nodes": failed_nodes,
            "timestamp": datetime.now().isoformat()
        }
        self._logger.info(json.dumps(log_data))
    
    def log_fallback(self, node_id: str, node_type: str, reason: str):
        if not self._enabled:
            return
        
        log_data = {
            "event": "fallback_triggered",
            "node_id": node_id,
            "node_type": node_type,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        self._logger.warning(json.dumps(log_data))
    
    def log_retry(self, node_id: str, node_type: str, attempt: int, max_attempts: int, error: str):
        if not self._enabled:
            return
        
        log_data = {
            "event": "retry_attempt",
            "node_id": node_id,
            "node_type": node_type,
            "attempt": attempt,
            "max_attempts": max_attempts,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        self._logger.warning(json.dumps(log_data))
    
    def log_validation_error(self, node_id: str, node_type: str, errors: list):
        if not self._enabled:
            return
        
        log_data = {
            "event": "validation_error",
            "node_id": node_id,
            "node_type": node_type,
            "errors": errors,
            "timestamp": datetime.now().isoformat()
        }
        self._logger.error(json.dumps(log_data))
    
    def log_memory_usage(self, usage: Dict[str, Any]):
        if not self._enabled:
            return
        
        log_data = {
            "event": "memory_usage",
            **usage,
            "timestamp": datetime.now().isoformat()
        }
        self._logger.debug(json.dumps(log_data))
    
    def debug(self, message: str, **kwargs):
        if not self._enabled:
            return
        if kwargs:
            message = f"{message} | {json.dumps(kwargs)}"
        self._logger.debug(message)
    
    def info(self, message: str, **kwargs):
        if not self._enabled:
            return
        if kwargs:
            message = f"{message} | {json.dumps(kwargs)}"
        self._logger.info(message)
    
    def warning(self, message: str, **kwargs):
        if not self._enabled:
            return
        if kwargs:
            message = f"{message} | {json.dumps(kwargs)}"
        self._logger.warning(message)
    
    def error(self, message: str, **kwargs):
        if not self._enabled:
            return
        if kwargs:
            message = f"{message} | {json.dumps(kwargs)}"
        self._logger.error(message)
    
    def critical(self, message: str, **kwargs):
        if not self._enabled:
            return
        if kwargs:
            message = f"{message} | {json.dumps(kwargs)}"
        self._logger.critical(message)

logger = StructuredLogger()