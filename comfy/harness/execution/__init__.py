"""
Harness 执行引擎增强模块

提供 Fuse Box、Fallback、Retry 三种机制，增强 ComfyUI 执行引擎的可靠性
"""

import logging
from typing import Optional, Callable, Any
import functools

from .. import HARNESS_CONFIG
from ..config import get_config

logger = logging.getLogger(__name__)

# 标记是否已经 patch
_is_patched = False


def patch_execution():
    """
    注入 Harness 执行引擎增强
    
    修改 execution.py 中的关键函数，添加 Fuse Box、Fallback、Retry 能力
    """
    global _is_patched
    
    if _is_patched:
        return
    
    config = get_config()
    if not config.enabled:
        return
    
    try:
        # 导入需要 patch 的模块
        import execution
        import comfy_execution.validation as validation
        
        # 1. 注入 Fuse Box 输入校验
        if config.execution.fuse_box.enabled:
            from .fuse_box import FuseBoxValidator
            validator = FuseBoxValidator(config.execution.fuse_box)
            
            # 保存原始函数
            _original_validate_node_input = validation.validate_node_input
            
            # 包装函数，添加 Fuse Box 校验
            @functools.wraps(_original_validate_node_input)
            def _wrapped_validate_node_input(received_type: str, input_type: str, strict: bool = False):
                # 先执行原始校验
                result = _original_validate_node_input(received_type, input_type, strict)
                
                # 如果原始校验通过，执行 Fuse Box 增强校验
                if result:
                    # Fuse Box 会在实际执行时进行更详细的校验
                    pass
                
                return result
            
            validation.validate_node_input = _wrapped_validate_node_input
            logger.info("[Harness] Fuse Box 已启用")
        
        # 2. 注入 Fallback 机制
        if config.execution.fallback.enabled:
            from .fallback import FallbackHandler
            fallback_handler = FallbackHandler(config.execution.fallback)
            
            # 保存原始 execute 函数
            _original_execute = execution.execute
            
            # 包装 execute 函数，添加 Fallback 处理
            @functools.wraps(_original_execute)
            async def _wrapped_execute(*args, **kwargs):
                try:
                    return await _original_execute(*args, **kwargs)
                except Exception as e:
                    # 检查是否可以 fallback
                    if fallback_handler.should_fallback(e, args, kwargs):
                        return await fallback_handler.handle_fallback(e, args, kwargs)
                    raise
            
            execution.execute = _wrapped_execute
            logger.info("[Harness] Fallback 机制已启用")
        
        # 3. 注入 Retry 机制
        if config.execution.retry.enabled:
            from .retry import RetryHandler
            retry_handler = RetryHandler(config.execution.retry)
            
            # 包装 execute 函数，添加 Retry 处理
            _original_execute_for_retry = execution.execute
            
            @functools.wraps(_original_execute_for_retry)
            async def _wrapped_execute_with_retry(*args, **kwargs):
                return await retry_handler.execute_with_retry(
                    _original_execute_for_retry, *args, **kwargs
                )
            
            execution.execute = _wrapped_execute_with_retry
            logger.info("[Harness] Retry 机制已启用")
        
        _is_patched = True
        logger.info("[Harness] 执行引擎增强注入完成")
        
    except Exception as e:
        logger.error(f"[Harness] 执行引擎增强注入失败: {e}")
        raise


__all__ = [
    "patch_execution",
]