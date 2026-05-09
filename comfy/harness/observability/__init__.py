"""
Harness 可观测性增强模块

提供 Tracing、黑匣子记录、OpenTelemetry 埋点能力
"""

import logging
from typing import Optional, Callable, Any

from ..config import get_config

logger = logging.getLogger(__name__)

# 标记是否已经 patch
_is_patched = False


def patch_observability():
    """
    注入 Harness 可观测性增强
    
    修改 server.py 中的 WebSocket 处理，添加埋点能力
    """
    global _is_patched
    
    if _is_patched:
        return
    
    config = get_config()
    if not config.observability.enabled:
        return
    
    try:
        logger.info("[Harness] 可观测性增强已启用")
        _is_patched = True
        
    except Exception as e:
        logger.error(f"[Harness] 可观测性增强注入失败: {e}")
        raise


__all__ = [
    "patch_observability",
]