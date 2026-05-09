"""
可观测性埋点钩子

提供在 ComfyUI 执行流程中集成埋点的接口
"""

import logging
import time
from typing import Any, Dict, List, Optional, Callable
from functools import wraps

from .tracer import tracer
from .profiler import profiler
from .logger import logger
from .recorder import recorder
from .telemetry import telemetry

logger = logging.getLogger(__name__)


class ObservabilityHooks:
    """可观测性埋点钩子管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._enabled = False
            cls._instance._hooks: Dict[str, List[Callable]] = {
                "workflow_start": [],
                "workflow_end": [],
                "node_start": [],
                "node_end": [],
                "error": [],
                "memory_warning": [],
                "performance_warning": [],
            }
        return cls._instance
    
    def enable(self):
        """启用埋点钩子"""
        self._enabled = True
        tracer.enable()
        profiler.enable()
        logger.enable()
        recorder.enable()
        telemetry.enable()
    
    def disable(self):
        """禁用埋点钩子"""
        self._enabled = False
        tracer.disable()
        profiler.disable()
        logger.disable()
        recorder.disable()
        telemetry.disable()
    
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self._enabled
    
    def register_hook(self, event: str, callback: Callable):
        """注册钩子回调"""
        if event in self._hooks:
            self._hooks[event].append(callback)
    
    def unregister_hook(self, event: str, callback: Callable):
        """取消注册钩子回调"""
        if event in self._hooks:
            if callback in self._hooks[event]:
                self._hooks[event].remove(callback)
    
    def _trigger_hook(self, event: str, *args, **kwargs):
        """触发钩子"""
        if not self._enabled:
            return
        
        for callback in self._hooks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.warning(f"钩子执行失败: {e}")
    
    def on_workflow_start(self, workflow_id: str, prompt: Dict, extra_data: Optional[Dict] = None):
        """工作流开始"""
        if not self._enabled:
            return
        
        metadata = {
            "prompt_keys": list(prompt.keys()) if prompt else [],
            "extra_data": extra_data or {}
        }
        
        tracer.start_workflow_trace(workflow_id, metadata)
        profiler.start_workflow(workflow_id)
        recorder.start_recording(workflow_id, metadata.get("name", ""))
        logger.log_workflow_start(workflow_id, node_count=len(prompt) if prompt else 0)
        telemetry.record_counter("workflow_start")
        
        self._trigger_hook("workflow_start", workflow_id, prompt)
    
    def on_workflow_end(self, workflow_id: str, status: str, outputs: Optional[Dict] = None):
        """工作流结束"""
        if not self._enabled:
            return
        
        perf = profiler.end_workflow(workflow_id)
        duration = perf.duration if perf else 0.0
        
        tracer.end_workflow_trace(workflow_id, status)
        recorder.end_recording(status)
        logger.log_workflow_end(
            workflow_id, status, duration,
            completed_nodes=perf.completed_nodes if perf else 0,
            failed_nodes=perf.failed_nodes if perf else 0
        )
        telemetry.record_counter("workflow_end")
        telemetry.record_gauge("workflow_duration_ms", duration * 1000)
        
        self._trigger_hook("workflow_end", workflow_id, status, outputs)
    
    def on_node_start(self, workflow_id: str, node_id: str, node_type: str, inputs: Dict):
        """节点开始执行"""
        if not self._enabled:
            return
        
        tracer.start_node_trace(workflow_id, node_id, node_type, inputs)
        profiler.start_node(workflow_id, node_id)
        recorder.start_node_execution(node_id, node_type, inputs)
        logger.log_node_execution(node_id, node_type, "running")
        
        self._trigger_hook("node_start", workflow_id, node_id, node_type, inputs)
    
    def on_node_end(self, workflow_id: str, node_id: str, node_type: str, outputs: Dict, error: Optional[str] = None):
        """节点执行结束"""
        if not self._enabled:
            return
        
        status = "failed" if error else "completed"
        
        profiler.end_node(workflow_id, node_id, node_type, success=(error is None))
        tracer.end_node_trace(workflow_id, node_id, outputs, error)
        recorder.end_node_execution(node_id, outputs, error)
        logger.log_node_execution(node_id, node_type, status, error=error)
        
        if error:
            telemetry.record_counter("node_error")
            self._trigger_hook("error", workflow_id, node_id, node_type, error)
        
        self._trigger_hook("node_end", workflow_id, node_id, node_type, outputs, error)
    
    def on_memory_warning(self, workflow_id: str, memory_used_mb: float, threshold_mb: float):
        """内存警告"""
        if not self._enabled:
            return
        
        logger.warning(f"内存使用警告: {memory_used_mb:.2f}MB / {threshold_mb:.2f}MB")
        telemetry.record_counter("memory_warning")
        self._trigger_hook("memory_warning", workflow_id, memory_used_mb, threshold_mb)
    
    def on_performance_warning(self, workflow_id: str, node_id: str, duration_ms: float, threshold_ms: float):
        """性能警告"""
        if not self._enabled:
            return
        
        logger.warning(f"节点性能警告: {node_id} 执行时间 {duration_ms:.2f}ms 超过阈值 {threshold_ms:.2f}ms")
        telemetry.record_counter("performance_warning")
        self._trigger_hook("performance_warning", workflow_id, node_id, duration_ms, threshold_ms)


class NodeExecutionContext:
    """节点执行上下文管理器"""
    
    def __init__(self, workflow_id: str, node_id: str, node_type: str, inputs: Dict):
        self.workflow_id = workflow_id
        self.node_id = node_id
        self.node_type = node_type
        self.inputs = inputs
        self.start_time = 0.0
        self.outputs = None
        self.error = None
    
    def __enter__(self):
        self.start_time = time.time()
        hooks.on_node_start(self.workflow_id, self.node_id, self.node_type, self.inputs)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.error = str(exc_val)
        
        hooks.on_node_end(self.workflow_id, self.node_id, self.node_type, self.outputs or {}, self.error)
        return False


def trace_node_execution(workflow_id_attr: str = "workflow_id", node_id_attr: str = "node_id", node_type_attr: str = "node_type"):
    """节点执行追踪装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            workflow_id = kwargs.get(workflow_id_attr, "default")
            node_id = kwargs.get(node_id_attr, "default")
            node_type = kwargs.get(node_type_attr, func.__name__)
            inputs = kwargs
            
            with NodeExecutionContext(workflow_id, node_id, node_type, inputs):
                try:
                    result = func(*args, **kwargs)
                    wrapper.outputs = result
                    return result
                except Exception as e:
                    wrapper.error = str(e)
                    raise
        
        return wrapper
    return decorator


hooks = ObservabilityHooks()


def install_hooks():
    """安装全局钩子"""
    hooks.enable()
    logger.info("可观测性埋点钩子已启用")


def uninstall_hooks():
    """卸载全局钩子"""
    hooks.disable()
    logger.info("可观测性埋点钩子已禁用")


def get_hooks() -> ObservabilityHooks:
    """获取全局钩子实例"""
    return hooks


def export_telemetry_data() -> Dict[str, Any]:
    """导出所有遥测数据"""
    return telemetry.get_telemetry_data()


def get_workflow_trace(workflow_id: str):
    """获取工作流追踪数据"""
    return tracer.get_trace(workflow_id)


def get_workflow_performance(workflow_id: str) -> str:
    """获取工作流性能摘要"""
    return profiler.get_workflow_summary(workflow_id)


def analyze_failure(record_id: str) -> Dict[str, Any]:
    """分析失败原因"""
    return recorder.analyze_failure(record_id)
