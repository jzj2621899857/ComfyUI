"""
自进化系统模块
提供工作流版本化管理和金丝雀部署能力
"""

from .workflow_version import WorkflowVersionManager, version_manager, WorkflowVersion
from .canary_deployer import CanaryDeployer, canary_deployer, CanaryConfig, CanaryStatus
from .referee import AIReferee, referee, QualityScore, ComparisonResult
from .optimizer import ClosedLoopOptimizer, WorkflowOptimizer, optimizer, workflow_optimizer, HyperParameter, OptimizationConfig
from .api_integration import HarnessAPI, api, register_harness_routes

__all__ = [
    "WorkflowVersionManager",
    "version_manager",
    "WorkflowVersion",
    "CanaryDeployer",
    "canary_deployer",
    "CanaryConfig",
    "CanaryStatus",
    "AIReferee",
    "referee",
    "QualityScore",
    "ComparisonResult",
    "ClosedLoopOptimizer",
    "WorkflowOptimizer",
    "optimizer",
    "workflow_optimizer",
    "HyperParameter",
    "OptimizationConfig",
    "HarnessAPI",
    "api",
    "register_harness_routes",
]
