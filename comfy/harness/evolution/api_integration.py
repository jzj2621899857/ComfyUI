"""
Harness API 路由

提供 Harness 相关功能的 HTTP API
"""

import logging
from typing import Any, Dict, List, Optional
import json

logger = logging.getLogger(__name__)


class HarnessAPI:
    """Harness API 路由处理器"""
    
    def __init__(self, app=None):
        self.app = app
        self._routes = self._get_routes()
    
    def _get_routes(self) -> Dict[str, Dict]:
        """获取路由定义"""
        return {
            "/api/harness/status": {
                "method": "GET",
                "handler": self.handle_status,
                "description": "获取 Harness 系统状态"
            },
            "/api/harness/enable": {
                "method": "POST",
                "handler": self.handle_enable,
                "description": "启用 Harness 系统"
            },
            "/api/harness/disable": {
                "method": "POST",
                "handler": self.handle_disable,
                "description": "禁用 Harness 系统"
            },
            "/api/harness/config": {
                "method": "GET",
                "handler": self.handle_get_config,
                "method": "PUT",
                "handler": self.handle_update_config,
                "description": "获取/更新 Harness 配置"
            },
            "/api/harness/metrics": {
                "method": "GET",
                "handler": self.handle_metrics,
                "description": "获取性能指标"
            },
            "/api/harness/version/list": {
                "method": "GET",
                "handler": self.handle_list_versions,
                "description": "列出工作流版本"
            },
            "/api/harness/version/rollback": {
                "method": "POST",
                "handler": self.handle_rollback,
                "description": "回滚到指定版本"
            },
            "/api/harness/canary/start": {
                "method": "POST",
                "handler": self.handle_start_canary,
                "description": "启动金丝雀部署"
            },
            "/api/harness/canary/stop": {
                "method": "POST",
                "handler": self.handle_stop_canary,
                "description": "停止金丝雀部署"
            },
            "/api/harness/canary/status": {
                "method": "GET",
                "handler": self.handle_canary_status,
                "description": "获取金丝雀状态"
            },
        }
    
    async def handle_status(self, request) -> Dict[str, Any]:
        """获取 Harness 状态"""
        try:
            from .. import harness
            return {
                "status": "ok",
                "enabled": harness.is_enabled(),
                "components": {
                    "fuse_box": harness.fuse_box_enabled(),
                    "fallback": harness.fallback_enabled(),
                    "retry": harness.retry_enabled(),
                    "observability": harness.observability_enabled(),
                    "resource_management": harness.resource_management_enabled(),
                    "evolution": harness.evolution_enabled()
                }
            }
        except ImportError:
            return {"status": "error", "message": "Harness 模块不可用"}
    
    async def handle_enable(self, request) -> Dict[str, Any]:
        """启用 Harness"""
        try:
            data = await request.json() if request.can_read_body else {}
            from .. import harness
            
            components = data.get("components", ["all"])
            if "all" in components:
                harness.initialize_harness(enabled=True)
            else:
                for component in components:
                    harness.enable_component(component)
            
            return {"status": "ok", "enabled": True}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def handle_disable(self, request) -> Dict[str, Any]:
        """禁用 Harness"""
        try:
            from .. import harness
            harness.disable_harness()
            return {"status": "ok", "enabled": False}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def handle_get_config(self, request) -> Dict[str, Any]:
        """获取配置"""
        try:
            from ..harness.config import config
            return {
                "status": "ok",
                "config": config.to_dict()
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def handle_update_config(self, request) -> Dict[str, Any]:
        """更新配置"""
        try:
            data = await request.json()
            from ..harness.config import config
            
            for key, value in data.items():
                config.set(key, value)
            
            return {"status": "ok", "config": config.to_dict()}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def handle_metrics(self, request) -> Dict[str, Any]:
        """获取性能指标"""
        try:
            from ..harness.observability import profiler, telemetry
            
            return {
                "status": "ok",
                "metrics": profiler.get_slowest_nodes(10),
                "telemetry": telemetry.get_telemetry_data()
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def handle_list_versions(self, request) -> Dict[str, Any]:
        """列出版本"""
        try:
            workflow_id = request.query.get("workflow_id")
            if not workflow_id:
                return {"status": "error", "message": "workflow_id is required"}
            
            from ..harness.evolution import version_manager
            
            versions = version_manager.get_all_versions(workflow_id)
            return {
                "status": "ok",
                "versions": [
                    {
                        "version_id": v.version_id,
                        "timestamp": v.created_at,
                        "is_active": v.is_active,
                        "description": v.description
                    }
                    for v in versions
                ]
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def handle_rollback(self, request) -> Dict[str, Any]:
        """回滚版本"""
        try:
            data = await request.json()
            workflow_id = data.get("workflow_id")
            version_id = data.get("version_id")
            
            if not workflow_id or not version_id:
                return {"status": "error", "message": "workflow_id and version_id are required"}
            
            from ..harness.evolution import version_manager
            
            success = version_manager.rollback_to_version(workflow_id, version_id)
            
            if success:
                return {"status": "ok", "message": "回滚成功"}
            else:
                return {"status": "error", "message": "回滚失败"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def handle_start_canary(self, request) -> Dict[str, Any]:
        """启动金丝雀部署"""
        try:
            data = await request.json()
            from ..harness.evolution import canary_deployer, CanaryConfig
            
            config = CanaryConfig(
                workflow_id=data.get("workflow_id"),
                new_version_id=data.get("new_version_id"),
                traffic_percent=data.get("traffic_percent", 10.0),
                max_traffic_percent=data.get("max_traffic_percent", 100.0)
            )
            
            success = canary_deployer.start_canary(config)
            
            if success:
                return {"status": "ok", "message": "金丝雀部署已启动"}
            else:
                return {"status": "error", "message": "金丝雀部署启动失败"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def handle_stop_canary(self, request) -> Dict[str, Any]:
        """停止金丝雀部署"""
        try:
            data = await request.json()
            workflow_id = data.get("workflow_id")
            
            if not workflow_id:
                return {"status": "error", "message": "workflow_id is required"}
            
            from ..harness.evolution import canary_deployer
            
            canary_deployer.stop_canary(workflow_id)
            return {"status": "ok", "message": "金丝雀部署已停止"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def handle_canary_status(self, request) -> Dict[str, Any]:
        """获取金丝雀状态"""
        try:
            workflow_id = request.query.get("workflow_id")
            
            from ..harness.evolution import canary_deployer
            
            if workflow_id:
                status = canary_deployer.get_canary_status(workflow_id)
                if status:
                    return {
                        "status": "ok",
                        "canary": {
                            "workflow_id": status.config.workflow_id,
                            "current_traffic": status.current_traffic,
                            "requests_served": status.requests_served,
                            "requests_failed": status.requests_failed,
                            "failure_rate": status.failure_rate
                        }
                    }
                else:
                    return {"status": "ok", "canary": None}
            else:
                canaries = canary_deployer.get_all_canaries()
                return {
                    "status": "ok",
                    "canaries": [
                        {
                            "workflow_id": c.config.workflow_id,
                            "current_traffic": c.current_traffic
                        }
                        for c in canaries
                    ]
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_routes(self) -> Dict[str, Dict]:
        """获取所有路由"""
        return self._routes


def register_harness_routes(app):
    """注册 Harness 路由到 Web 应用"""
    try:
        api = HarnessAPI(app)
        
        for path, route_info in api.get_routes().items():
            async def make_handler(path=path, route_info=route_info):
                async def handler(request):
                    method = route_info.get("method", "GET")
                    handler_func = route_info.get("handler")
                    
                    if request.method != method:
                        return {"status": "error", "message": f"Method {method} required"}
                    
                    result = await handler_func(request)
                    return result
                
                return handler
            
            app.router.add_route("GET", path, make_handler())
            logger.info(f"注册 Harness 路由: {path}")
        
        logger.info("Harness API 路由注册完成")
    except Exception as e:
        logger.warning(f"注册 Harness 路由失败: {e}")


api = HarnessAPI()
