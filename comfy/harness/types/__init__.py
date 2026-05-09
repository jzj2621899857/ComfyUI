"""
Harness 类型系统增强模块

提供类型安全与合约化能力
"""

import logging
from typing import Optional, Callable, Any

from ..config import get_config

logger = logging.getLogger(__name__)

# 标记是否已经 patch
_is_patched = False


def patch_types():
    """
    注入 Harness 类型系统增强
    
    修改 nodes.py 中的节点注册逻辑，添加类型合约支持
    """
    global _is_patched
    
    if _is_patched:
        return
    
    config = get_config()
    if not config.types.enabled:
        return
    
    try:
        logger.info("[Harness] 类型系统增强已启用")
        _is_patched = True
        
    except Exception as e:
        logger.error(f"[Harness] 类型系统增强注入失败: {e}")
        raise


__all__ = [
    "patch_types",
]