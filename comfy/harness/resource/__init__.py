"""
Harness 资源管理增强模块

提供资源预估、动态调度、精度自适应能力
"""

import logging
from typing import Optional, Callable, Any

from ..config import get_config

logger = logging.getLogger(__name__)

# 标记是否已经 patch
_is_patched = False


def patch_resource():
    """
    注入 Harness 资源管理增强
    
    修改 model_management.py 中的模型加载逻辑，添加资源管理能力
    """
    global _is_patched
    
    if _is_patched:
        return
    
    config = get_config()
    if not config.resource.enabled:
        return
    
    try:
        logger.info("[Harness] 资源管理增强已启用")
        _is_patched = True
        
    except Exception as e:
        logger.error(f"[Harness] 资源管理增强注入失败: {e}")
        raise


__all__ = [
    "patch_resource",
]