#!/usr/bin/env python3
"""
ComfyUI Harness 启动脚本

完全解耦，不修改任何 ComfyUI 原有文件
通过 monkey-patch 动态注入 Harness 功能
"""

import os
import sys
import asyncio
import logging
import importlib.util

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

os.environ.setdefault("COMFYUI_HARNESS", "true")


def register_harness_routes_dynamically():
    """动态注册 Harness 路由到服务器"""
    try:
        from comfy.harness.evolution.api_integration import register_harness_routes
        return register_harness_routes
    except ImportError as e:
        logger.warning(f"[Harness] Failed to import API integration: {e}")
        return None


def patch_prompt_server():
    """Monkey-patch PromptServer 以动态注册 Harness 路由"""
    import server
    
    original_init = server.PromptServer.__init__
    
    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        
        register_func = register_harness_routes_dynamically()
        if register_func and hasattr(self, 'app'):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(_register_routes_async(self.app))
                else:
                    loop.run_until_complete(_register_routes_async(self.app))
            except Exception as e:
                logger.warning(f"[Harness] Failed to register routes: {e}")
    
    async def _register_routes_async(app):
        try:
            from comfy.harness.evolution.api_integration import HarnessAPI
            api = HarnessAPI(app)
            
            routes = {
                "/harness": {"method": "GET", "handler": api.handle_dashboard},
                "/api/harness/status": {"method": "GET", "handler": api.handle_status},
                "/api/harness/metrics": {"method": "GET", "handler": api.handle_metrics},
                "/api/harness/traces": {"method": "GET", "handler": api.handle_traces},
                "/api/harness/version/list": {"method": "GET", "handler": api.handle_version_list},
                "/api/harness/canary/start": {"method": "POST", "handler": api.handle_canary_start},
                "/api/harness/canary/stop": {"method": "POST", "handler": api.handle_canary_stop},
                "/api/harness/referee/judge": {"method": "POST", "handler": api.handle_referee_judge},
                "/api/harness/optimizer/step": {"method": "POST", "handler": api.handle_optimizer_step},
                "/api/harness/enable": {"method": "POST", "handler": api.handle_enable},
                "/api/harness/disable": {"method": "POST", "handler": api.handle_disable},
            }
            
            from aiohttp import web
            for path, route_info in routes.items():
                method = route_info["method"]
                handler_func = route_info["handler"]
                
                async def make_handler(func=handler_func):
                    async def handler(request):
                        try:
                            result = await func(request)
                            if isinstance(result, web.Response):
                                return result
                            return web.json_response(result)
                        except Exception as e:
                            logger.error(f"[Harness] Handler error: {e}")
                            return web.json_response({"status": "error", "message": str(e)}, status=500)
                    return handler
                
                app.router.add_route(method, path, make_handler())
                logger.info(f"[Harness] Registered route: {method} {path}")
            
            logger.info("[Harness] All routes registered successfully")
        except Exception as e:
            logger.warning(f"[Harness] Failed to register routes: {e}")
    
    server.PromptServer.__init__ = patched_init
    logger.info("[Harness] PromptServer patched successfully")


def main():
    """主入口"""
    logger.info("[Harness] Starting ComfyUI with Harness extensions...")
    
    patch_prompt_server()
    
    sys.argv = [sys.argv[0]] + sys.argv[1:]
    
    if __name__ == "__main__":
        from main import main as comfyui_main
        comfyui_main()


if __name__ == "__main__":
    main()
