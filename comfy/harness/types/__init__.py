"""
类型安全与合约化模块
提供强类型接口和静态类型检查能力
"""

from .contracts import PortContract, NodeContract, ConnectionValidationResult
from .registry import TypeRegistry, registry
from .compiler import GraphCompiler, compile_workflow
from .validators import (
    TypeValidator, ValueValidator, TensorValidator, InputValidator,
    input_validator
)
from .node_registry import (
    NodeContractExtractor,
    HarnessNodeMixin,
    auto_register_nodes,
    register_standard_comfyui_contracts,
    validate_node_inputs,
    validate_connection,
    get_node_contract,
    list_registered_nodes,
    with_harness_contract
)

__all__ = [
    "PortContract",
    "NodeContract",
    "ConnectionValidationResult",
    "TypeRegistry",
    "registry",
    "GraphCompiler",
    "compile_workflow",
    "TypeValidator",
    "ValueValidator",
    "TensorValidator",
    "InputValidator",
    "input_validator",
    "NodeContractExtractor",
    "HarnessNodeMixin",
    "auto_register_nodes",
    "register_standard_comfyui_contracts",
    "validate_node_inputs",
    "validate_connection",
    "get_node_contract",
    "list_registered_nodes",
    "with_harness_contract",
]
