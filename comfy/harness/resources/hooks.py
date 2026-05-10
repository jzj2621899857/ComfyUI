"""
资源管理钩子

提供在模型加载流程中集成资源管理的接口
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Callable
from functools import wraps

from .memory_monitor import memory_monitor, MemoryStats
from .resource_manager import resource_manager, ResourceSettings
from .estimator import estimator, ResourceEstimate
from .scheduler import scheduler, Task, Priority
from .adaptive_precision import precision_controller, PrecisionMode
from .memory_pool import memory_pool

logger = logging.getLogger(__name__)


class ResourceManagementHooks:
    """资源管理钩子管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._enabled = False
            cls._instance._callbacks: Dict[str, List[Callable]] = {
                "before_load": [],
                "after_load": [],
                "memory_warning": [],
                "load_error": [],
            }
        return cls._instance
    
    def enable(self):
        """启用资源管理"""
        self._enabled = True
        memory_monitor.enable()
        resource_manager.enable()
        estimator.enable()
        scheduler.enable()
        precision_controller.enable()
        memory_pool.enable()
    
    def disable(self):
        """禁用资源管理"""
        self._enabled = False
        memory_monitor.disable()
        resource_manager.disable()
        estimator.disable()
        scheduler.disable()
        precision_controller.disable()
        memory_pool.disable()
    
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self._enabled
    
    def register_callback(self, event: str, callback: Callable):
        """注册回调"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def _trigger_callbacks(self, event: str, *args, **kwargs):
        """触发回调"""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.warning(f"资源管理回调执行失败: {e}")
    
    def before_model_load(self, model_type: str, model_path: str, size_hint: Optional[int] = None) -> bool:
        """模型加载前检查"""
        if not self._enabled:
            return True
        
        stats = memory_monitor.get_stats()
        
        if size_hint:
            required_mb = size_hint / (1024 * 1024)
            available_mb = stats.free
            
            if available_mb < required_mb * 1.2:
                logger.warning(
                    f"显存可能不足: 需要约 {required_mb:.0f}MB, "
                    f"可用 {available_mb:.0f}MB"
                )
                self._trigger_callbacks("memory_warning", model_type, required_mb, available_mb)
        
        self._trigger_callbacks("before_load", model_type, model_path)
        return True
    
    def after_model_load(self, model_type: str, model_path: str, success: bool = True, error: Optional[str] = None):
        """模型加载后处理"""
        if not self._enabled:
            return
        
        stats = memory_monitor.get_stats()
        
        if success:
            logger.info(
                f"模型加载成功: {model_type}, "
                f"显存使用 {stats.usage_percent:.1f}%"
            )
            estimator.record_execution(
                model_type,
                memory_mb=stats.used,
                time_ms=0
            )
        else:
            logger.error(f"模型加载失败: {model_type}, 错误: {error}")
            self._trigger_callbacks("load_error", model_type, error)
        
        self._trigger_callbacks("after_load", model_type, success)
    
    def estimate_workflow_resources(self, workflow: Dict[str, Any]) -> ResourceEstimate:
        """预估工作流资源需求"""
        if not self._enabled:
            return ResourceEstimate()
        
        return estimator.estimate_workflow(workflow)
    
    def check_workflow_fit(self, workflow: Dict[str, Any]) -> Tuple[bool, str]:
        """检查工作流是否可以执行"""
        estimate = self.estimate_workflow_resources(workflow)
        stats = memory_monitor.get_stats()
        
        available_mb = stats.free
        
        if estimate.memory_mb > available_mb * 0.8:
            return False, (
                f"资源不足: 预估需要 {estimate.memory_mb:.0f}MB, "
                f"可用 {available_mb:.0f}MB"
            )
        
        return True, "资源充足"
    
    def get_suggested_batch_size(self, estimated_memory_usage: float) -> int:
        """获取建议的批次大小"""
        if not self._enabled:
            return 1
        
        return resource_manager.suggest_batch_size(estimated_memory_usage)
    
    def on_out_of_memory(self, node_type: str, attempt: int, max_attempts: int) -> bool:
        """显存不足处理"""
        if not self._enabled:
            return False
        
        logger.warning(
            f"显存不足: {node_type}, "
            f"重试 {attempt}/{max_attempts}"
        )
        
        resource_manager.decrease_batch_size()
        resource_manager.force_garbage_collection()
        
        return attempt < max_attempts
    
    def get_current_precision(self) -> PrecisionMode:
        """获取当前精度模式"""
        return precision_controller.get_current_mode()
    
    def record_quality_feedback(self, quality_metrics: Dict[str, float]):
        """记录质量反馈用于精度自适应"""
        if not self._enabled:
            return
        
        try:
            from .adaptive_precision import QualityMetrics
            metrics = QualityMetrics(
                psnr=quality_metrics.get("psnr", 0),
                ssim=quality_metrics.get("ssim", 0),
                lpips=quality_metrics.get("lpips", 0),
                user_rating=quality_metrics.get("user_rating", 0)
            )
            precision_controller.record_quality(metrics)
        except Exception as e:
            logger.warning(f"记录质量反馈失败: {e}")
    
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有资源统计"""
        return {
            "memory": memory_monitor.get_stats().to_dict(),
            "resource_manager": {
                "batch_size": resource_manager.get_batch_size(),
                "max_batch_size": resource_manager.get_settings().max_batch_size
            },
            "estimator": {
                "profiles": len(estimator.get_all_profiles())
            },
            "precision": precision_controller.get_stats(),
            "memory_pool": memory_pool.get_stats()
        }


hooks = ResourceManagementHooks()


def install_hooks():
    """安装资源管理钩子"""
    hooks.enable()
    logger.info("资源管理钩子已启用")


def uninstall_hooks():
    """卸载资源管理钩子"""
    hooks.disable()
    logger.info("资源管理钩子已禁用")


def get_hooks() -> ResourceManagementHooks:
    """获取资源管理钩子实例"""
    return hooks


def estimate_node_resources(node_type: str, input_shapes: Optional[Dict] = None) -> ResourceEstimate:
    """预估节点资源需求"""
    return estimator.estimate(node_type, input_shapes)


def estimate_workflow_resources(workflow: Dict[str, Any]) -> ResourceEstimate:
    """预估工作流资源需求"""
    return estimator.estimate_workflow(workflow)


def check_memory_available(required_mb: float) -> bool:
    """检查是否有足够的可用显存"""
    stats = memory_monitor.get_stats()
    return stats.free >= required_mb * 1.2


def force_cleanup():
    """强制清理资源"""
    memory_pool.defragment()
    resource_manager.force_garbage_collection()
