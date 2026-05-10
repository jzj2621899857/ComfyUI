"""
图编译器

在工作流加载阶段进行静态类型检查，提前拦截不兼容连接
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from .contracts import NodeContract, PortContract, validate_connection, ConnectionValidationResult
from .registry import registry

logger = logging.getLogger(__name__)


class GraphCompiler:
    """
    图编译器
    
    在工作流加载阶段进行静态类型检查和优化
    """
    
    def __init__(self, strict_mode: bool = False):
        """
        初始化编译器
        
        Args:
            strict_mode: 是否启用严格模式（严格模式下类型不匹配会报错）
        """
        self.strict_mode = strict_mode
        self._errors = []
        self._warnings = []
    
    def compile(self, workflow: Dict) -> Tuple[bool, List[str], List[str]]:
        """
        编译工作流
        
        Args:
            workflow: 工作流字典
        
        Returns:
            tuple: (是否成功, 错误列表, 警告列表)
        """
        self._errors = []
        self._warnings = []
        
        # 1. 验证节点类型
        self._validate_node_types(workflow)
        
        # 2. 验证节点连接
        self._validate_connections(workflow)
        
        # 3. 验证输入完整性
        self._validate_input_completeness(workflow)
        
        # 4. 类型推断和优化
        self._type_inference(workflow)
        
        return len(self._errors) == 0, self._errors.copy(), self._warnings.copy()
    
    def _validate_node_types(self, workflow: Dict):
        """验证所有节点类型是否已知"""
        nodes = workflow.get("nodes", {})
        
        for node_id, node_data in nodes.items():
            node_type = node_data.get("type")
            
            if not node_type:
                self._errors.append(f"节点 {node_id} 缺少类型定义")
                continue
            
            if not registry.has_contract(node_type):
                if self.strict_mode:
                    self._errors.append(f"未知节点类型: {node_type}")
                else:
                    self._warnings.append(f"节点类型 {node_type} 没有合约定义")
    
    def _validate_connections(self, workflow: Dict):
        """验证所有节点连接"""
        nodes = workflow.get("nodes", {})
        connections = workflow.get("connections", [])
        
        for conn in connections:
            source_node_id = conn.get("source_node")
            source_port = conn.get("source_port")
            target_node_id = conn.get("target_node")
            target_port = conn.get("target_port")
            
            # 检查连接完整性
            if None in [source_node_id, source_port, target_node_id, target_port]:
                self._errors.append(f"不完整的连接: {conn}")
                continue
            
            # 获取节点数据
            source_node = nodes.get(str(source_node_id))
            target_node = nodes.get(str(target_node_id))
            
            if not source_node or not target_node:
                continue
            
            source_type = source_node.get("type")
            target_type = target_node.get("type")
            
            # 获取合约
            source_contract = registry.get_contract(source_type)
            target_contract = registry.get_contract(target_type)
            
            if not source_contract or not target_contract:
                # 如果没有合约，跳过类型检查
                continue
            
            # 查找端口合约
            source_port_contract = self._find_port_contract(source_contract.outputs, source_port)
            target_port_contract = self._find_port_contract(target_contract.inputs, target_port)
            
            if source_port_contract and target_port_contract:
                # 验证连接
                result = validate_connection(source_port_contract, target_port_contract)
                
                if not result.is_valid:
                    for error in result.errors:
                        self._errors.append(
                            f"连接错误 [{source_type}.{source_port} -> {target_type}.{target_port}]: {error}"
                        )
                
                for warning in result.warnings:
                    self._warnings.append(
                        f"连接警告 [{source_type}.{source_port} -> {target_type}.{target_port}]: {warning}"
                    )
            else:
                # 端口不存在
                if not source_port_contract:
                    self._warnings.append(
                        f"源端口不存在: {source_type}.{source_port}"
                    )
                if not target_port_contract:
                    self._warnings.append(
                        f"目标端口不存在: {target_type}.{target_port}"
                    )
    
    def _validate_input_completeness(self, workflow: Dict):
        """验证输入完整性"""
        nodes = workflow.get("nodes", {})
        connections = workflow.get("connections", [])
        
        # 构建输入连接映射
        input_connections = {}  # (node_id, port) -> True
        for conn in connections:
            key = (str(conn.get("target_node")), conn.get("target_port"))
            input_connections[key] = True
        
        for node_id, node_data in nodes.items():
            node_type = node_data.get("type")
            contract = registry.get_contract(node_type)
            
            if not contract:
                continue
            
            # 检查必填输入
            for inp in contract.inputs:
                if not inp.optional:
                    key = (node_id, inp.name)
                    if key not in input_connections:
                        # 检查是否有默认值
                        node_inputs = node_data.get("inputs", {})
                        if inp.name not in node_inputs:
                            self._errors.append(
                                f"节点 {node_id} ({node_type}) 缺少必填输入: {inp.name}"
                            )
    
    def _type_inference(self, workflow: Dict):
        """类型推断和优化（预留接口）"""
        # 这里可以实现更复杂的类型推断逻辑
        # 例如：根据连接推断节点类型，或者优化节点顺序
        pass
    
    def _find_port_contract(self, ports: List[PortContract], port_name: str) -> Optional[PortContract]:
        """
        在端口列表中查找指定名称的端口合约
        
        Args:
            ports: 端口合约列表
            port_name: 端口名称
        
        Returns:
            PortContract: 端口合约，如果不存在返回 None
        """
        for port in ports:
            if port.name == port_name:
                return port
        return None
    
    def get_errors(self) -> List[str]:
        """获取错误列表"""
        return self._errors.copy()
    
    def get_warnings(self) -> List[str]:
        """获取警告列表"""
        return self._warnings.copy()
    
    def reset(self):
        """重置编译器状态"""
        self._errors = []
        self._warnings = []


def compile_workflow(workflow: Dict, strict_mode: bool = False) -> Dict:
    """
    编译工作流的便捷函数
    
    Args:
        workflow: 工作流字典
        strict_mode: 是否启用严格模式
    
    Returns:
        Dict: 编译结果，包含 success, errors, warnings
    """
    compiler = GraphCompiler(strict_mode=strict_mode)
    success, errors, warnings = compiler.compile(workflow)
    
    return {
        "success": success,
        "errors": errors,
        "warnings": warnings,
        "compiled_workflow": workflow if success else None,
    }


def validate_workflow_before_execution(workflow: Dict) -> Tuple[bool, List[str]]:
    """
    在执行前验证工作流
    
    Args:
        workflow: 工作流字典
    
    Returns:
        tuple: (是否通过, 错误信息列表)
    """
    # 首先检查是否启用类型检查
    from ..config import get_config
    config = get_config()
    
    if not config.types.enabled:
        return True, []
    
    result = compile_workflow(workflow, strict_mode=config.types.strict_mode)
    
    if not result["success"]:
        logger.error(f"工作流验证失败: {result['errors']}")
    
    return result["success"], result["errors"]


# 示例工作流验证
def example_validation():
    """示例：验证工作流"""
    # 注册标准合约
    from .registry import register_standard_contracts
    register_standard_contracts()
    
    # 示例工作流
    workflow = {
        "nodes": {
            "1": {"type": "CLIPTextEncode", "inputs": {"text": "beautiful landscape"}},
            "2": {"type": "KSampler", "inputs": {"seed": 42, "steps": 20}},
            "3": {"type": "VAEDecode"},
        },
        "connections": [
            {"source_node": 1, "source_port": "conditioning", "target_node": 2, "target_port": "positive"},
            {"source_node": 2, "source_port": "latent", "target_node": 3, "target_port": "latent"},
        ]
    }
    
    # 编译工作流
    result = compile_workflow(workflow)
    
    print("编译结果:", result["success"])
    if result["errors"]:
        print("错误:")
        for error in result["errors"]:
            print(f"  - {error}")
    if result["warnings"]:
        print("警告:")
        for warning in result["warnings"]:
            print(f"  - {warning}")
    
    return result