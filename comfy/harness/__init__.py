"""
ComfyUI Harness - 源码级 Harness Engineering 实现

将"Harness Engineering"原则（可控、可观测、可自愈、可进化）编译进 ComfyUI 的源码基因，
使其自身成为内在质量更高、更健壮的生成式 AI 引擎。

使用方法:
    设置环境变量 COMFYUI_HARNESS=true 启用 Harness 模式
    默认关闭，保持原有行为
"""

import os
import logging

logger = logging.getLogger(__name__)

# Harness 启用开关
HARNESS_ENABLED = os.environ.get("COMFYUI_HARNESS", "false").lower() == "true"

# 各模块启用开关（可单独控制）
HARNESS_CONFIG = {
    "execution": {
        "fuse_box": os.environ.get("COMFYUI_HARNESS_FUSE_BOX", "true").lower() == "true",
        "fallback": os.environ.get("COMFYUI_HARNESS_FALLBACK", "true").lower() == "true",
        "retry": os.environ.get("COMFYUI_HARNESS_RETRY", "true").lower() == "true",
    },
    "types": {
        "enabled": os.environ.get("COMFYUI_HARNESS_TYPES", "true").lower() == "true",
        "strict_mode": os.environ.get("COMFYUI_HARNESS_STRICT_TYPES", "false").lower() == "true",
    },
    "observability": {
        "enabled": os.environ.get("COMFYUI_HARNESS_OBSERVABILITY", "true").lower() == "true",
        "tracing": os.environ.get("COMFYUI_HARNESS_TRACING", "true").lower() == "true",
        "recorder": os.environ.get("COMFYUI_HARNESS_RECORDER", "true").lower() == "true",
    },
    "resource": {
        "enabled": os.environ.get("COMFYUI_HARNESS_RESOURCE", "true").lower() == "true",
        "adaptive_precision": os.environ.get("COMFYUI_HARNESS_ADAPTIVE_PRECISION", "true").lower() == "true",
    },
    "evolution": {
        "enabled": os.environ.get("COMFYUI_HARNESS_EVOLUTION", "false").lower() == "true",
    }
}


def setup_harness():
    """
    初始化 Harness 系统
    
    在 ComfyUI 启动时调用，根据配置注入 Harness 能力
    """
    if not HARNESS_ENABLED:
        logger.info("[Harness] 已禁用，使用原有行为")
        return
    
    logger.info("[Harness] 正在初始化...")
    
    try:
        # 1. 初始化执行引擎增强（Fuse Box, Fallback, Retry）
        if any(HARNESS_CONFIG["execution"].values()):
            from .execution import patch_execution
            patch_execution()
            logger.info("[Harness] 执行引擎增强已启用")
        
        # 2. 初始化类型系统增强
        if HARNESS_CONFIG["types"]["enabled"]:
            from .types import patch_types
            patch_types()
            logger.info("[Harness] 类型系统增强已启用")
        
        # 3. 初始化可观测性增强
        if HARNESS_CONFIG["observability"]["enabled"]:
            from .observability import patch_observability
            patch_observability()
            logger.info("[Harness] 可观测性增强已启用")
        
        # 4. 初始化资源管理增强
        if HARNESS_CONFIG["resource"]["enabled"]:
            from .resource import patch_resource
            patch_resource()
            logger.info("[Harness] 资源管理增强已启用")
        
        # 5. 初始化自进化系统
        if HARNESS_CONFIG["evolution"]["enabled"]:
            from .evolution import patch_evolution
            patch_evolution()
            logger.info("[Harness] 自进化系统已启用")
        
        logger.info("[Harness] 初始化完成")
        
    except Exception as e:
        logger.error(f"[Harness] 初始化失败: {e}")
        logger.warning("[Harness] 回退到原有行为")


def is_enabled(module: str = None) -> bool:
    """
    检查 Harness 是否启用
    
    Args:
        module: 模块名称，如 "execution", "types" 等
               为 None 时检查整体启用状态
    
    Returns:
        bool: 是否启用
    """
    if not HARNESS_ENABLED:
        return False
    
    if module is None:
        return True
    
    return HARNESS_CONFIG.get(module, {}).get("enabled", False)


def fuse_box_enabled() -> bool:
    """检查 Fuse Box 是否启用"""
    return HARNESS_CONFIG["execution"]["fuse_box"]


def fallback_enabled() -> bool:
    """检查 Fallback 是否启用"""
    return HARNESS_CONFIG["execution"]["fallback"]


def retry_enabled() -> bool:
    """检查 Retry 是否启用"""
    return HARNESS_CONFIG["execution"]["retry"]


def observability_enabled() -> bool:
    """检查可观测性是否启用"""
    return HARNESS_CONFIG["observability"]["enabled"]


def resource_management_enabled() -> bool:
    """检查资源管理是否启用"""
    return HARNESS_CONFIG["resource"]["enabled"]


def evolution_enabled() -> bool:
    """检查自进化系统是否启用"""
    return HARNESS_CONFIG["evolution"]["enabled"]


__all__ = [
    "HARNESS_ENABLED",
    "HARNESS_CONFIG",
    "setup_harness",
    "is_enabled",
    "fuse_box_enabled",
    "fallback_enabled",
    "retry_enabled",
    "observability_enabled",
    "resource_management_enabled",
    "evolution_enabled",
]