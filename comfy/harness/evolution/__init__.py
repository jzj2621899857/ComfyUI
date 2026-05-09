"""
Harness 自进化系统模块

提供工作流版本管理、金丝雀部署、AI 裁判评分、闭环优化能力
"""

import logging
from typing import Optional, Callable, Any

from ..config import get_config

logger = logging.getLogger(__name__)

# 标记是否已经 patch
_is_patched = False


def patch_evolution():
    """
    注入 Harness 自进化系统
    
    添加工作流版本管理和自动优化能力
    """
    global _is_patched
    
    if _is_patched:
        return
    
    config = get_config()
    if not config.evolution.enabled:
        return
    
    try:
        logger.info("[Harness] 自进化系统已启用")
        _is_patched = True
        
    except Exception as e:
        logger.error(f"[Harness] 自进化系统注入失败: {e}")
        raise


__all__ = [
    "patch_evolution",
]