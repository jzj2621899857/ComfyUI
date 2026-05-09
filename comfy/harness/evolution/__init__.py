"""
自进化系统模块
提供工作流版本化管理和金丝雀部署能力
"""

from .workflow_version import WorkflowVersionManager, version_manager, WorkflowVersion
from .canary_deployer import CanaryDeployer, canary_deployer, CanaryConfig, CanaryStatus

__all__ = [
    "WorkflowVersionManager",
    "version_manager",
    "WorkflowVersion",
    "CanaryDeployer",
    "canary_deployer",
    "CanaryConfig",
    "CanaryStatus",
]