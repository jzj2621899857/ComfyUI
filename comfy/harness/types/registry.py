"""
类型注册表

统一管理节点类型合约，支持自定义类型扩展
"""

import logging
from typing import Any, Dict, List, Optional, Set, Type

from .contracts import NodeContract, PortContract

logger = logging.getLogger(__name__)


class TypeRegistry:
    """
    类型注册表
    
    维护节点类型合约的全局注册表
    """
    
    _instance = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._contracts = {}  # node_type -> NodeContract
            cls._instance._aliases = {}    # alias -> node_type
        return cls._instance
    
    def register_contract(self, contract: NodeContract):
        """
        注册节点合约
        
        Args:
            contract: 节点合约
        
        Returns:
            bool: 是否注册成功
        """
        if contract.node_type in self._contracts:
            logger.warning(f"合约 '{contract.node_type}' 已存在，将被覆盖")
        
        self._contracts[contract.node_type] = contract
        logger.info(f"已注册节点合约: {contract.node_type}")
        return True
    
    def register_contracts(self, contracts: List[NodeContract]):
        """
        批量注册节点合约
        
        Args:
            contracts: 合约列表
        
        Returns:
            int: 成功注册的数量
        """
        count = 0
        for contract in contracts:
            if self.register_contract(contract):
                count += 1
        return count
    
    def get_contract(self, node_type: str) -> Optional[NodeContract]:
        """
        获取节点合约
        
        Args:
            node_type: 节点类型名称
        
        Returns:
            NodeContract: 节点合约，如果不存在返回 None
        """
        # 先检查别名
        if node_type in self._aliases:
            node_type = self._aliases[node_type]
        
        return self._contracts.get(node_type)
    
    def has_contract(self, node_type: str) -> bool:
        """
        检查是否存在节点合约
        
        Args:
            node_type: 节点类型名称
        
        Returns:
            bool: 是否存在
        """
        return self.get_contract(node_type) is not None
    
    def remove_contract(self, node_type: str) -> bool:
        """
        移除节点合约
        
        Args:
            node_type: 节点类型名称
        
        Returns:
            bool: 是否移除成功
        """
        if node_type in self._contracts:
            del self._contracts[node_type]
            logger.info(f"已移除节点合约: {node_type}")
            return True
        return False
    
    def register_alias(self, alias: str, node_type: str):
        """
        注册节点类型别名
        
        Args:
            alias: 别名
            node_type: 实际节点类型
        
        Returns:
            bool: 是否注册成功
        """
        if alias in self._aliases:
            logger.warning(f"别名 '{alias}' 已存在，将被覆盖")
        
        self._aliases[alias] = node_type
        logger.info(f"已注册别名: {alias} -> {node_type}")
        return True
    
    def get_all_node_types(self) -> List[str]:
        """
        获取所有注册的节点类型
        
        Returns:
            List[str]: 节点类型列表
        """
        return list(self._contracts.keys())
    
    def get_contracts_by_category(self, category: str) -> List[NodeContract]:
        """
        按类别获取合约（预留接口）
        
        Args:
            category: 类别名称
        
        Returns:
            List[NodeContract]: 合约列表
        """
        # 这是预留接口，实际实现需要合约支持类别字段
        return list(self._contracts.values())
    
    def validate_workflow(self, workflow: Dict) -> List[str]:
        """
        验证工作流中的所有节点连接
        
        Args:
            workflow: 工作流字典
        
        Returns:
            List[str]: 错误信息列表
        """
        errors = []
        
        nodes = workflow.get("nodes", {})
        connections = workflow.get("connections", [])
        
        for conn in connections:
            source_node_id = conn.get("source_node")
            source_port = conn.get("source_port")
            target_node_id = conn.get("target_node")
            target_port = conn.get("target_port")
            
            # 获取节点合约
            source_node = nodes.get(str(source_node_id))
            target_node = nodes.get(str(target_node_id))
            
            if not source_node or not target_node:
                continue
            
            source_type = source_node.get("type")
            target_type = target_node.get("type")
            
            source_contract = self.get_contract(source_type)
            target_contract = self.get_contract(target_type)
            
            if not source_contract or not target_contract:
                continue
            
            # 查找端口合约
            source_port_contract = None
            for out in source_contract.outputs:
                if out.name == source_port:
                    source_port_contract = out
                    break
            
            target_port_contract = None
            for inp in target_contract.inputs:
                if inp.name == target_port:
                    target_port_contract = inp
                    break
            
            if source_port_contract and target_port_contract:
                # 验证连接
                from .contracts import validate_connection
                result = validate_connection(source_port_contract, target_port_contract)
                
                if not result.is_valid:
                    for error in result.errors:
                        errors.append(
                            f"连接错误 [{source_type}.{source_port} -> {target_type}.{target_port}]: {error}"
                        )
        
        return errors
    
    def get_stats(self) -> Dict[str, int]:
        """
        获取注册表统计信息
        
        Returns:
            Dict[str, int]: 统计信息
        """
        return {
            "total_contracts": len(self._contracts),
            "total_aliases": len(self._aliases),
        }
    
    def clear(self):
        """清空注册表"""
        self._contracts.clear()
        self._aliases.clear()
        logger.info("类型注册表已清空")


# 全局注册表实例
registry = TypeRegistry()


def register_node_contract(cls: Type):
    """
    节点合约注册装饰器
    
    Usage:
        @register_node_contract
        class MyNode:
            CONTRACT = NodeContract(...)
    """
    if hasattr(cls, 'CONTRACT') and isinstance(cls.CONTRACT, NodeContract):
        registry.register_contract(cls.CONTRACT)
    return cls


def register_standard_contracts():
    """
    注册预定义的标准合约
    
    为常用节点类型创建默认合约
    """
    from .contracts import STANDARD_CONTRACTS, PortContract, NodeContract
    
    # KSampler 节点
    ksampler_contract = NodeContract(
        node_type="KSampler",
        inputs=[
            PortContract(name="model", dtype="str", description="模型名称"),
            PortContract(name="seed", dtype="int", value_range=(0, 2**32 - 1)),
            PortContract(name="steps", dtype="int", value_range=(1, 200)),
            PortContract(name="cfg", dtype="float", value_range=(1.0, 30.0)),
            PortContract(name="sampler_name", dtype="str"),
            PortContract(name="scheduler", dtype="str"),
            PortContract(name="positive", description="正向提示词"),
            PortContract(name="negative", description="负向提示词"),
            PortContract(name="latent_image", dtype="float32", shape=(1, 4, -1, -1)),
        ],
        outputs=[
            PortContract(name="latent", dtype="float32", shape=(1, 4, -1, -1)),
        ]
    )
    registry.register_contract(ksampler_contract)
    
    # VAEEncode 节点
    vae_encode_contract = NodeContract(
        node_type="VAEEncode",
        inputs=[
            PortContract(name="pixels", dtype="float32", shape=(1, 3, -1, -1), color_space="RGB"),
            PortContract(name="vae", dtype="str"),
        ],
        outputs=[
            PortContract(name="latent", dtype="float32", shape=(1, 4, -1, -1)),
        ]
    )
    registry.register_contract(vae_encode_contract)
    
    # VAEDecode 节点
    vae_decode_contract = NodeContract(
        node_type="VAEDecode",
        inputs=[
            PortContract(name="latent", dtype="float32", shape=(1, 4, -1, -1)),
            PortContract(name="vae", dtype="str"),
        ],
        outputs=[
            PortContract(name="image", dtype="float32", shape=(1, 3, -1, -1), color_space="RGB"),
        ]
    )
    registry.register_contract(vae_decode_contract)
    
    # CLIPTextEncode 节点
    clip_encode_contract = NodeContract(
        node_type="CLIPTextEncode",
        inputs=[
            PortContract(name="text", dtype="str"),
            PortContract(name="clip", dtype="str"),
        ],
        outputs=[
            PortContract(name="conditioning", description="条件向量"),
        ]
    )
    registry.register_contract(clip_encode_contract)
    
    # LoadImage 节点
    load_image_contract = NodeContract(
        node_type="LoadImage",
        inputs=[
            PortContract(name="image", dtype="str", description="图像路径"),
        ],
        outputs=[
            PortContract(name="image", dtype="float32", shape=(1, 3, -1, -1), color_space="RGB"),
            PortContract(name="mask", dtype="float32", shape=(1, 1, -1, -1)),
        ]
    )
    registry.register_contract(load_image_contract)
    
    # SaveImage 节点
    save_image_contract = NodeContract(
        node_type="SaveImage",
        inputs=[
            PortContract(name="images", dtype="float32", shape=(1, 3, -1, -1), color_space="RGB"),
            PortContract(name="filename_prefix", dtype="str", optional=True),
        ],
        outputs=[]
    )
    registry.register_contract(save_image_contract)
    
    logger.info(f"已注册 {registry.get_stats()['total_contracts']} 个标准节点合约")