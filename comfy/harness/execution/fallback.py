"""
Fallback 机制 - 非关键节点失败处理

当非关键节点失败时自动旁路，保障管线完整执行
"""

import logging
from typing import Any, Dict, Optional, Tuple
from enum import Enum

from ..config import FallbackConfig

logger = logging.getLogger(__name__)


class FallbackAction(Enum):
    """Fallback 处理动作"""
    BYPASS = "bypass"  # 旁路：输入直通输出
    ABORT = "abort"    # 中止：抛出异常
    RETRY = "retry"    # 重试：重新执行


class FallbackContext:
    """
    Fallback 上下文
    
    记录 fallback 决策的相关信息
    """
    
    def __init__(
        self,
        node_id: str,
        class_type: str,
        error: Exception,
        action: FallbackAction,
        inputs: Dict[str, Any],
        outputs: Optional[Dict[str, Any]] = None
    ):
        self.node_id = node_id
        self.class_type = class_type
        self.error = error
        self.action = action
        self.inputs = inputs
        self.outputs = outputs
        self.timestamp = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "node_id": self.node_id,
            "class_type": self.class_type,
            "error_type": type(self.error).__name__,
            "error_message": str(self.error),
            "action": self.action.value,
            "timestamp": self.timestamp,
        }


class FallbackHandler:
    """
    Fallback 处理器
    
    管理节点失败时的 fallback 决策
    """
    
    # 默认非关键节点类型列表（这些节点失败时可以旁路）
    _DEFAULT_NON_CRITICAL_NODE_TYPES = {
        "PreviewImage",
        "SaveImage",
        "SaveVideo",
        "LoadImage",  # 某些情况下可以返回占位图
        "ImageScale",
        "ImageUpscaleWithModel",
        "FaceDetailer",  # 美颜节点
        "ImageColorTransfer",  # 颜色迁移
        "ImageBlur",
        "ImageSharpen",
        "MaskEdgeDetailer",
    }
    
    def __init__(self, config: FallbackConfig):
        self.config = config
        self._fallback_history = []
        self._max_history = 1000
        # 使用实例级别的集合，避免测试间相互影响
        self.NON_CRITICAL_NODE_TYPES = set(self._DEFAULT_NON_CRITICAL_NODE_TYPES)
    
    def should_fallback(
        self, 
        error: Exception, 
        args: tuple, 
        kwargs: dict
    ) -> bool:
        """
        判断是否应该执行 fallback
        
        Args:
            error: 发生的异常
            args: 函数参数
            kwargs: 函数关键字参数
        
        Returns:
            bool: 是否应该 fallback
        """
        if not self.config.enabled:
            return False
        
        # 提取节点信息
        node_id = self._extract_node_id(args, kwargs)
        class_type = self._extract_class_type(args, kwargs)
        
        # 检查是否为可 fallback 的错误
        if not self._is_retryable_error(error):
            return False
        
        # 检查节点是否为非关键节点
        if class_type in self.NON_CRITICAL_NODE_TYPES:
            logger.warning(
                f"[Fallback] 节点 {node_id} ({class_type}) 执行失败，但启用 fallback: {error}"
            )
            return True
        
        # 检查节点是否标记为 optional
        if self._is_optional_node(args, kwargs):
            logger.warning(
                f"[Fallback] 节点 {node_id} ({class_type}) 标记为 optional，启用 fallback: {error}"
            )
            return True
        
        return False
    
    def handle_fallback(
        self,
        error: Exception,
        args: tuple,
        kwargs: dict
    ) -> Tuple[Any, Any, Any]:
        """
        处理 fallback
        
        Args:
            error: 发生的异常
            args: 函数参数
            kwargs: 函数关键字参数
        
        Returns:
            tuple: (output_data, output_ui, has_subgraph) - 旁路结果
        """
        node_id = self._extract_node_id(args, kwargs)
        class_type = self._extract_class_type(args, kwargs)
        
        # 创建 fallback 上下文
        context = FallbackContext(
            node_id=node_id,
            class_type=class_type,
            error=error,
            action=FallbackAction.BYPASS,
            inputs=self._extract_inputs(args, kwargs)
        )
        
        # 记录 fallback 事件
        self._record_fallback(context)
        
        if self.config.log_fallback:
            logger.info(
                f"[Fallback] 节点 {node_id} ({class_type}) 已旁路，"
                f"输入将直通输出"
            )
        
        # 返回旁路结果（输入直通输出）
        # 对于旁路操作，我们返回空输出，让后续节点继续执行
        return [], {}, False
    
    def _extract_node_id(self, args: tuple, kwargs: dict) -> Optional[str]:
        """提取节点 ID"""
        # args 格式: (server, dynprompt, caches, current_item, extra_data, ...)
        # current_item 通常就是 unique_id
        if len(args) >= 4:
            return str(args[3])  # current_item
        return kwargs.get("unique_id", "unknown")
    
    def _extract_class_type(self, args: tuple, kwargs: dict) -> Optional[str]:
        """提取节点类型"""
        # 需要从 dynprompt 获取
        return kwargs.get("class_type", "unknown")
    
    def _extract_inputs(self, args: tuple, kwargs: dict) -> Dict[str, Any]:
        """提取输入数据"""
        # args 格式: (server, dynprompt, caches, current_item, extra_data, ...)
        # inputs 在 dynprompt 中
        return kwargs.get("inputs", {})
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """
        判断是否为可重试的错误
        
        通常是资源相关或瞬态错误
        """
        error_msg = str(error).lower()
        
        # 可重试的错误类型
        retryable_patterns = [
            "cuda out of memory",
            "out of memory",
            "allocation",
            "timeout",
            "connection",
            "network",
        ]
        
        for pattern in retryable_patterns:
            if pattern in error_msg:
                return True
        
        return False
    
    def _is_optional_node(self, args: tuple, kwargs: dict) -> bool:
        """检查节点是否标记为 optional"""
        # 检查节点定义中的 optional 标记
        return kwargs.get("optional", False)
    
    def _record_fallback(self, context: FallbackContext):
        """记录 fallback 事件"""
        import datetime
        context.timestamp = datetime.datetime.now().isoformat()
        
        self._fallback_history.append(context)
        
        # 保持历史记录数量限制
        if len(self._fallback_history) > self._max_history:
            self._fallback_history = self._fallback_history[-self._max_history:]
    
    def get_fallback_stats(self) -> Dict[str, Any]:
        """获取 fallback 统计信息"""
        total = len(self._fallback_history)
        
        # 按节点类型统计
        by_node_type = {}
        for ctx in self._fallback_history:
            node_type = ctx.class_type
            by_node_type[node_type] = by_node_type.get(node_type, 0) + 1
        
        # 按错误类型统计
        by_error_type = {}
        for ctx in self._fallback_history:
            error_type = type(ctx.error).__name__
            by_error_type[error_type] = by_error_type.get(error_type, 0) + 1
        
        return {
            "total_fallbacks": total,
            "by_node_type": by_node_type,
            "by_error_type": by_error_type,
            "recent_fallbacks": [ctx.to_dict() for ctx in self._fallback_history[-10:]]
        }
    
    def set_node_as_optional(self, node_type: str, optional: bool = True):
        """
        设置节点类型为可选（可选节点失败时启用 fallback）
        
        Args:
            node_type: 节点类型名称
            optional: 是否为可选
        """
        if optional:
            if node_type not in self.NON_CRITICAL_NODE_TYPES:
                self.NON_CRITICAL_NODE_TYPES.add(node_type)
                logger.info(f"[Fallback] 将节点类型 '{node_type}' 添加到可选列表")
        else:
            if node_type in self.NON_CRITICAL_NODE_TYPES:
                self.NON_CRITICAL_NODE_TYPES.remove(node_type)
                logger.info(f"[Fallback] 将节点类型 '{node_type}' 从可选列表移除")
    
    def register_critical_node(self, node_type: str):
        """
        注册关键节点类型（这些节点失败时不会启用 fallback）
        
        Args:
            node_type: 节点类型名称
        """
        if node_type in self.NON_CRITICAL_NODE_TYPES:
            self.NON_CRITICAL_NODE_TYPES.remove(node_type)
            logger.info(f"[Fallback] 节点类型 '{node_type}' 已注册为关键节点")


def create_optional_node_decorator(handler: FallbackHandler):
    """
    创建可选节点装饰器
    
    用于标记节点为可选，失败时启用 fallback
    
    Usage:
        @create_optional_node_decorator(fallback_handler)
        class MyOptionalNode:
            ...
    """
    def decorator(cls):
        cls.OPTIONAL_NODE = True
        return cls
    return decorator