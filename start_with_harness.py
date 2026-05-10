#!/usr/bin/env python3
"""
ComfyUI Harness 启动脚本

完全解耦，不修改任何 ComfyUI 原有文件
"""

import os
import sys
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def setup_harness():
    """设置 Harness 环境变量"""
    os.environ.setdefault("COMFYUI_HARNESS", "true")
    logger.info("[Harness] Environment configured")


def register_harness_routes_dynamically():
    """动态注册 Harness 路由到服务器"""
    try:
        from comfy.harness.evolution.api_integration import register_harness_routes
        return register_harness_routes
    except ImportError as e:
        logger.warning(f"[Harness] Failed to import API integration: {e}")
        return None


async def patch_server(server_instance):
    """动态 patch 服务器实例，注册 Harness 路由"""
    register_func = register_harness_routes_dynamically()
    if register_func and hasattr(server_instance, 'app'):
        try:
            register_func(server_instance.app)
            logger.info("[Harness] Routes registered dynamically")
        except Exception as e:
            logger.warning(f"[Harness] Failed to register routes: {e}")


def main():
    """主入口"""
    setup_harness()
    
    # 添加 comfy 模块路径
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # 导入 ComfyUI 主模块
    from main import main as comfy_main
    
    # 在启动前注入路由注册
    import server
    
    original_init = server.PromptServer.__init__
    
    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        # 异步注册路由
        asyncio.create_task(patch_server(self))
    
    server.PromptServer.__init__ = patched_init
    
    # 启动 ComfyUI
    comfy_main()


if __name__ == "__main__":
    main()