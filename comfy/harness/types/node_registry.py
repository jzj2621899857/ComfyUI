"""
节点类型合约注册器

自动将 ComfyUI 节点注册到类型注册表
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Type
from functools import wraps

from .contracts import NodeContract, PortContract
from .registry import registry

logger = logging.getLogger(__name__)


class NodeContractExtractor:
    """节点合约提取器"""
    
    @staticmethod
    def extract_from_class(node_class: Type) -> Optional[NodeContract]:
        """从节点类提取合约"""
        try:
            input_types = getattr(node_class, "INPUT_TYPES", None)
            if not input_types:
                return None
            
            return_types = getattr(node_class, "RETURN_TYPES", ())
            function_name = getattr(node_class, "FUNCTION", "__call__")
            category = getattr(node_class, "CATEGORY", "default")
            
            input_contracts = []
            output_contracts = []
            
            input_def = input_types() if callable(input_types) else input_types
            
            for port_name, port_info in input_def.get("required", {}).items():
                contract = NodeContractExtractor._extract_input_contract(port_name, port_info)
                if contract:
                    input_contracts.append(contract)
            
            for port_name, port_info in input_def.get("optional", {}).items():
                contract = NodeContractExtractor._extract_input_contract(port_name, port_info)
                if contract:
                    contract.optional = True
                    input_contracts.append(contract)
            
            for i, return_type in enumerate(return_types):
                output_contract = PortContract(
                    name=f"output_{i}",
                    dtype=NodeContractExtractor._normalize_dtype(return_type),
                    optional=False
                )
                output_contracts.append(output_contract)
            
            node_contract = NodeContract(
                node_type=node_class.__name__,
                inputs=input_contracts,
                outputs=output_contracts,
                metadata={
                    "category": category,
                    "function": function_name
                }
            )
            
            return node_contract
        except Exception as e:
            logger.debug(f"提取节点合约失败: {e}")
            return None
    
    @staticmethod
    def _extract_input_contract(port_name: str, port_info: Tuple) -> Optional[PortContract]:
        """提取输入端口合约"""
        try:
            if len(port_info) < 2:
                return None
            
            dtype = port_info[0]
            options = port_info[1] if len(port_info) > 1 else {}
            
            contract = PortContract(
                name=port_name,
                dtype=NodeContractExtractor._normalize_dtype(dtype),
                optional=options.get("optional", False)
            )
            
            if "default" in options:
                contract.default = options["default"]
            
            if "min" in options:
                contract.value_range = (options["min"], options.get("max", options["min"]))
            
            if "tooltip" in options:
                contract.description = options["tooltip"]
            
            return contract
        except Exception:
            return None
    
    @staticmethod
    def _normalize_dtype(dtype: Any) -> str:
        """标准化数据类型"""
        if isinstance(dtype, str):
            return dtype
        
        dtype_map = {
            "IMAGE": "torch.Tensor",
            "MASK": "torch.Tensor",
            "LATENT": "Latent",
            "MODEL": "Model",
            "CLIP": "CLIP",
            "VAE": "VAE",
            "CONDITIONING": "Conditioning",
            "CONDITIONING": "Conditioning",
            "STRING": "str",
            "INT": "int",
            "FLOAT": "float",
            "BOOLEAN": "bool",
        }
        
        return dtype_map.get(dtype, str(dtype))


class HarnessNodeMixin:
    """Harness 节点混入类"""
    
    @classmethod
    def get_harness_contract(cls) -> Optional[NodeContract]:
        """获取 Harness 合约"""
        contract_attr = getattr(cls, "_harness_contract", None)
        if contract_attr:
            return contract_attr
        
        return NodeContractExtractor.extract_from_class(cls)
    
    @classmethod
    def register_harness_contract(cls, contract: NodeContract):
        """注册 Harness 合约"""
        cls._harness_contract = contract
        registry.register_contract(contract)


def with_harness_contract(contract: NodeContract):
    """节点合约装饰器"""
    def decorator(cls):
        cls._harness_contract = contract
        registry.register_contract(contract)
        return cls
    return decorator


def auto_register_nodes(node_classes: Dict[str, Type]) -> int:
    """
    自动注册节点到 Harness 类型系统
    
    Args:
        node_classes: NODE_CLASS_MAPPINGS 字典
    
    Returns:
        注册的节点数量
    """
    registered = 0
    
    for node_type, node_class in node_classes.items():
        try:
            contract = NodeContractExtractor.extract_from_class(node_class)
            if contract:
                registry.register_contract(contract)
                node_class._harness_contract = contract
                registered += 1
                logger.debug(f"注册节点合约: {node_type}")
        except Exception as e:
            logger.debug(f"注册节点 {node_type} 失败: {e}")
    
    logger.info(f"自动注册了 {registered} 个节点合约")
    return registered


def register_standard_comfyui_contracts():
    """注册 ComfyUI 标准节点合约"""
    standard_contracts = [
        NodeContract(
            node_type="CheckpointLoaderSimple",
            inputs=[
                PortContract(name="ckpt_name", dtype="str"),
            ],
            outputs=[
                PortContract(name="model", dtype="MODEL"),
                PortContract(name="clip", dtype="CLIP"),
                PortContract(name="vae", dtype="VAE"),
            ],
            metadata={"category": "loaders"}
        ),
        NodeContract(
            node_type="CLIPTextEncode",
            inputs=[
                PortContract(name="text", dtype="str"),
                PortContract(name="clip", dtype="CLIP"),
            ],
            outputs=[
                PortContract(name="conditioning", dtype="CONDITIONING"),
            ],
            metadata={"category": "conditioning"}
        ),
        NodeContract(
            node_type="KSampler",
            inputs=[
                PortContract(name="model", dtype="MODEL"),
                PortContract(name="seed", dtype="int"),
                PortContract(name="steps", dtype="int"),
                PortContract(name="cfg", dtype="float"),
                PortContract(name="sampler_name", dtype="str"),
                PortContract(name="scheduler", dtype="str"),
                PortContract(name="positive", dtype="CONDITIONING"),
                PortContract(name="negative", dtype="CONDITIONING"),
                PortContract(name="latent_image", dtype="LATENT"),
                PortContract(name="denoise", dtype="float", value_range=(0.0, 1.0)),
            ],
            outputs=[
                PortContract(name="latent", dtype="LATENT"),
            ],
            metadata={"category": "sampling"}
        ),
        NodeContract(
            node_type="VAEDecode",
            inputs=[
                PortContract(name="samples", dtype="LATENT"),
                PortContract(name="vae", dtype="VAE"),
            ],
            outputs=[
                PortContract(name="decoded", dtype="IMAGE"),
            ],
            metadata={"category": "latent"}
        ),
        NodeContract(
            node_type="VAEEncode",
            inputs=[
                PortContract(name="pixels", dtype="IMAGE"),
                PortContract(name="vae", dtype="VAE"),
            ],
            outputs=[
                PortContract(name="latent", dtype="LATENT"),
            ],
            metadata={"category": "latent"}
        ),
        NodeContract(
            node_type="EmptyLatentImage",
            inputs=[
                PortContract(name="width", dtype="int", value_range=(64, 8192)),
                PortContract(name="height", dtype="int", value_range=(64, 8192)),
                PortContract(name="batch_size", dtype="int", value_range=(1, 64)),
            ],
            outputs=[
                PortContract(name="latent", dtype="LATENT"),
            ],
            metadata={"category": "latent"}
        ),
        NodeContract(
            node_type="LoadImage",
            inputs=[
                PortContract(name="image", dtype="str"),
            ],
            outputs=[
                PortContract(name="image", dtype="IMAGE"),
                PortContract(name="mask", dtype="MASK"),
            ],
            metadata={"category": "image"}
        ),
        NodeContract(
            node_type="SaveImage",
            inputs=[
                PortContract(name="images", dtype="IMAGE"),
                PortContract(name="filename_prefix", dtype="str"),
            ],
            outputs=[],
            metadata={"category": "image", "output_node": True}
        ),
    ]
    
    for contract in standard_contracts:
        registry.register_contract(contract)
    
    logger.info(f"注册了 {len(standard_contracts)} 个标准节点合约")
    return len(standard_contracts)


def validate_node_inputs(node_type: str, inputs: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    验证节点输入
    
    Args:
        node_type: 节点类型
        inputs: 输入参数
    
    Returns:
        (是否通过, 错误信息列表)
    """
    contract = registry.get_contract(node_type)
    if not contract:
        logger.warning(f"未找到节点合约: {node_type}")
        return True, []
    
    return contract.validate_inputs(inputs)


def validate_connection(source_type: str, source_port: str, target_type: str, target_port: str) -> Tuple[bool, str]:
    """
    验证连接兼容性
    
    Args:
        source_type: 源节点类型
        source_port: 源端口名
        target_type: 目标节点类型
        target_port: 目标端口名
    
    Returns:
        (是否兼容, 错误信息)
    """
    result = registry.validate_connection(source_type, source_port, target_type, target_port)
    return result.is_valid, "; ".join(result.errors) if result.errors else ""


def get_node_contract(node_type: str) -> Optional[NodeContract]:
    """获取节点合约"""
    return registry.get_contract(node_type)


def list_registered_nodes() -> List[str]:
    """列出所有已注册的节点"""
    return list(registry._contracts.keys())
