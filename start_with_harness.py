#!/usr/bin/env python3
"""
ComfyUI Harness 启动脚本

完全解耦，不修改任何 ComfyUI 原有文件
通过 subprocess 启动并注入 Harness 功能
"""

import os
import sys
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

os.environ.setdefault("COMFYUI_HARNESS", "true")

logger.info("[Harness] Starting ComfyUI with Harness extensions...")

def patch_server_after_start():
    """在服务器启动后尝试动态注册路由"""
    try:
        import time
        import requests
        import asyncio
        
        max_retries = 30
        for i in range(max_retries):
            try:
                response = requests.get("http://localhost:8188", timeout=2)
                if response.status_code in (200, 404):
                    logger.info("[Harness] Server is up, registering routes...")
                    
                    from comfy.harness.evolution.api_integration import HarnessAPI
                    from aiohttp import web
                    import server
                    
                    app = server.prompt_server.app
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
                    
                    logger.info("[Harness] All routes registered successfully!")
                    return
                    
            except Exception:
                pass
            
            time.sleep(1)
            if i % 5 == 0:
                logger.info(f"[Harness] Waiting for server to start... ({i+1}/{max_retries})")
        
        logger.warning("[Harness] Server did not start in time, routes not registered")
        
    except Exception as e:
        logger.warning(f"[Harness] Failed to register routes: {e}")


def main():
    """主入口 - 使用 subprocess 启动 ComfyUI"""
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    
    cmd = [sys.executable, script_path] + sys.argv[1:]
    
    logger.info(f"[Harness] Running: {' '.join(cmd)}")
    
    try:
        process = subprocess.Popen(cmd)
        
        patch_server_after_start()
        
        process.wait()
    except KeyboardInterrupt:
        logger.info("[Harness] Shutting down...")
        process.terminate()
        process.wait()


if __name__ == "__main__":
    main()
