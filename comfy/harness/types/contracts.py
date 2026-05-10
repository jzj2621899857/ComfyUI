"""
类型合约定义

为节点输入/输出端口定义元数据合约，实现类型安全
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union


@dataclass
class PortContract:
    """
    端口合约
    
    定义单个输入/输出端口的元数据合约
    """
    name: str
    dtype: Optional[str] = None  # 数据类型: float32, float16, int32, etc.
    shape: Optional[Tuple] = None  # 形状约束: (1, 3, -1, -1) 表示批大小1, 通道3, 高度和宽度任意
    value_range: Optional[Tuple[float, float]] = None  # 数值范围约束
    color_space: Optional[str] = None  # 色彩空间: RGB, RGBA, L, LAB, etc.
    precision: Optional[str] = None  # 精度: fp32, fp16, bfp16, etc.
    optional: bool = False  # 是否可选
    description: Optional[str] = None  # 描述
    
    def validate(self, value: Any) -> Tuple[bool, str]:
        """
        验证值是否符合合约
        
        Args:
            value: 待验证的值
        
        Returns:
            tuple: (是否有效, 错误信息)
        """
        if value is None:
            return self.optional, "值为 None，但端口不是可选的"
        
        # 类型检查
        if self.dtype is not None:
            if not self._check_dtype(value):
                return False, f"类型不匹配: 期望 {self.dtype}, 实际 {type(value)}"
        
        # 形状检查（仅对 tensor/array）
        if self.shape is not None and hasattr(value, 'shape'):
            if not self._check_shape(value.shape):
                return False, f"形状不匹配: 期望 {self.shape}, 实际 {value.shape}"
        
        # 数值范围检查
        if self.value_range is not None:
            if not self._check_value_range(value):
                return False, f"数值超出范围: 期望 {self.value_range}"
        
        return True, ""
    
    def _check_dtype(self, value: Any) -> bool:
        """检查数据类型"""
        # 先尝试 Python 类型检查
        python_type_map = {
            "int": int,
            "float": float,
            "str": str,
            "bool": bool,
            "list": list,
            "dict": dict,
        }
        expected = python_type_map.get(self.dtype)
        if expected is not None:
            return isinstance(value, expected)
        
        # 尝试 torch tensor 类型检查（如果 torch 可用）
        try:
            import torch
            
            if isinstance(value, torch.Tensor):
                torch_dtype_map = {
                    "float32": torch.float32,
                    "float16": torch.float16,
                    "bfloat16": torch.bfloat16,
                    "int32": torch.int32,
                    "int64": torch.int64,
                    "uint8": torch.uint8,
                    "bool": torch.bool,
                }
                expected_torch = torch_dtype_map.get(self.dtype)
                if expected_torch is not None:
                    return value.dtype == expected_torch
        except ImportError:
            # torch 不可用，跳过 tensor 类型检查
            pass
        
        return True
    
    def _check_shape(self, actual_shape: Tuple) -> bool:
        """检查形状"""
        if len(actual_shape) != len(self.shape):
            return False
        
        for actual, expected in zip(actual_shape, self.shape):
            if expected == -1:  # -1 表示任意大小
                continue
            if isinstance(expected, tuple):
                # 范围检查 (min, max)
                min_val, max_val = expected
                if actual < min_val or actual > max_val:
                    return False
            else:
                if actual != expected:
                    return False
        
        return True
    
    def _check_value_range(self, value: Any) -> bool:
        """检查数值范围"""
        min_val, max_val = self.value_range
        
        # 先检查基本 Python 类型
        if isinstance(value, (int, float)):
            return min_val <= value <= max_val
        
        # 尝试 numpy 数组检查（如果 numpy 可用）
        try:
            import numpy as np
            if isinstance(value, np.ndarray):
                return np.all(value >= min_val) and np.all(value <= max_val)
        except ImportError:
            pass
        
        # 尝试 torch tensor 检查（如果 torch 可用）
        try:
            import torch
            if isinstance(value, torch.Tensor):
                return (value >= min_val).all() and (value <= max_val).all()
        except ImportError:
            pass
        
        return True
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "name": self.name,
            "dtype": self.dtype,
            "shape": self.shape,
            "value_range": self.value_range,
            "color_space": self.color_space,
            "precision": self.precision,
            "optional": self.optional,
            "description": self.description,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "PortContract":
        """从字典创建"""
        return cls(**data)


@dataclass
class NodeContract:
    """
    节点合约
    
    定义节点的完整类型合约
    """
    node_type: str  # 节点类型名称
    inputs: List[PortContract] = field(default_factory=list)
    outputs: List[PortContract] = field(default_factory=list)
    version: str = "1.0.0"  # 合约版本
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证所有输入
        
        Args:
            inputs: 输入字典
        
        Returns:
            tuple: (是否有效, 错误信息列表)
        """
        errors = []
        
        for input_contract in self.inputs:
            value = inputs.get(input_contract.name)
            valid, msg = input_contract.validate(value)
            if not valid:
                errors.append(f"输入 '{input_contract.name}': {msg}")
        
        return len(errors) == 0, errors
    
    def validate_outputs(self, outputs: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证所有输出
        
        Args:
            outputs: 输出字典
        
        Returns:
            tuple: (是否有效, 错误信息列表)
        """
        errors = []
        
        for output_contract in self.outputs:
            value = outputs.get(output_contract.name)
            valid, msg = output_contract.validate(value)
            if not valid:
                errors.append(f"输出 '{output_contract.name}': {msg}")
        
        return len(errors) == 0, errors
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "node_type": self.node_type,
            "inputs": [inp.to_dict() for inp in self.inputs],
            "outputs": [out.to_dict() for out in self.outputs],
            "version": self.version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "NodeContract":
        """从字典创建"""
        inputs = [PortContract.from_dict(inp) for inp in data.get("inputs", [])]
        outputs = [PortContract.from_dict(out) for out in data.get("outputs", [])]
        return cls(
            node_type=data["node_type"],
            inputs=inputs,
            outputs=outputs,
            version=data.get("version", "1.0.0")
        )
    
    def save(self, filepath: str):
        """保存合约到文件"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> "NodeContract":
        """从文件加载合约"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)


@dataclass
class ConnectionValidationResult:
    """
    连接验证结果
    """
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def __bool__(self):
        return self.is_valid


def validate_connection(
    source_contract: PortContract,
    target_contract: PortContract
) -> ConnectionValidationResult:
    """
    验证两个端口之间的连接是否有效
    
    Args:
        source_contract: 源端口合约
        target_contract: 目标端口合约
    
    Returns:
        ConnectionValidationResult: 验证结果
    """
    errors = []
    warnings = []
    
    # 类型兼容性检查
    if source_contract.dtype and target_contract.dtype:
        if source_contract.dtype != target_contract.dtype:
            # 允许向上转换（如 fp16 -> fp32）
            conversion_matrix = {
                ("float16", "float32"): True,
                ("bfloat16", "float32"): True,
                ("uint8", "float32"): True,
                ("int32", "float32"): True,
            }
            key = (source_contract.dtype, target_contract.dtype)
            if key not in conversion_matrix:
                warnings.append(
                    f"类型不匹配: 源 {source_contract.dtype} -> 目标 {target_contract.dtype}"
                )
    
    # 形状兼容性检查
    if source_contract.shape and target_contract.shape:
        source_shape = source_contract.shape
        target_shape = target_contract.shape
        
        if len(source_shape) != len(target_shape):
            errors.append(f"维度数量不匹配: {len(source_shape)}D -> {len(target_shape)}D")
        else:
            for i, (s, t) in enumerate(zip(source_shape, target_shape)):
                # 跳过通配符
                if s == -1 or t == -1:
                    continue
                
                # 检查范围兼容性
                if isinstance(s, tuple) and isinstance(t, tuple):
                    # 两个都是范围，检查是否有重叠
                    s_min, s_max = s
                    t_min, t_max = t
                    if s_max < t_min or t_max < s_min:
                        errors.append(
                            f"第 {i} 维范围不兼容: [{s_min},{s_max}] -> [{t_min},{t_max}]"
                        )
                elif isinstance(s, tuple) or isinstance(t, tuple):
                    # 一个是范围，一个是具体值
                    if isinstance(s, tuple):
                        s_min, s_max = s
                        if not (s_min <= t <= s_max):
                            errors.append(
                                f"第 {i} 维不兼容: {t} 不在范围 [{s_min},{s_max}] 内"
                            )
                    else:
                        t_min, t_max = t
                        if not (t_min <= s <= t_max):
                            errors.append(
                                f"第 {i} 维不兼容: {s} 不在范围 [{t_min},{t_max}] 内"
                            )
                else:
                    # 两个都是具体值，必须相等
                    if s != t:
                        errors.append(
                            f"第 {i} 维不兼容: {s} != {t}"
                        )
    
    # 色彩空间检查
    if source_contract.color_space and target_contract.color_space:
        if source_contract.color_space != target_contract.color_space:
            warnings.append(
                f"色彩空间不匹配: {source_contract.color_space} -> {target_contract.color_space}"
            )
    
    return ConnectionValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


# 预定义的标准类型合约
STANDARD_CONTRACTS = {
    "IMAGE_RGB": PortContract(
        name="image",
        dtype="float32",
        shape=(1, 3, (256, 4096), (256, 4096)),
        value_range=(0.0, 1.0),
        color_space="RGB",
        precision="fp32",
        description="RGB 图像 tensor"
    ),
    "IMAGE_RGBA": PortContract(
        name="image",
        dtype="float32",
        shape=(1, 4, (256, 4096), (256, 4096)),
        value_range=(0.0, 1.0),
        color_space="RGBA",
        precision="fp32",
        description="RGBA 图像 tensor"
    ),
    "LATENT": PortContract(
        name="latent",
        dtype="float32",
        shape=(1, 4, (64, 1024), (64, 1024)),
        description="Latent 表示 tensor"
    ),
    "MASK": PortContract(
        name="mask",
        dtype="float32",
        shape=(1, 1, (256, 4096), (256, 4096)),
        value_range=(0.0, 1.0),
        description="遮罩 tensor"
    ),
    "PROMPT": PortContract(
        name="prompt",
        dtype="str",
        description="文本提示词"
    ),
    "SEED": PortContract(
        name="seed",
        dtype="int",
        value_range=(0, 2**32 - 1),
        description="随机种子"
    ),
    "STEPS": PortContract(
        name="steps",
        dtype="int",
        value_range=(1, 200),
        description="采样步数"
    ),
    "CFG": PortContract(
        name="cfg",
        dtype="float",
        value_range=(1.0, 30.0),
        description="分类器自由引导系数"
    ),
    "SCALE": PortContract(
        name="scale",
        dtype="float",
        value_range=(0.1, 10.0),
        description="缩放因子"
    ),
}


def create_contract_decorator(
    inputs: Optional[List[PortContract]] = None,
    outputs: Optional[List[PortContract]] = None
):
    """
    创建合约装饰器
    
    Usage:
        @create_contract_decorator(
            inputs=[
                PortContract(name="image", dtype="float32", shape=(1, 3, -1, -1)),
                PortContract(name="strength", dtype="float", value_range=(0.0, 1.0)),
            ],
            outputs=[
                PortContract(name="image", dtype="float32"),
            ]
        )
        class MyNode:
            ...
    """
    def decorator(cls):
        cls.CONTRACT = NodeContract(
            node_type=cls.__name__,
            inputs=inputs or [],
            outputs=outputs or []
        )
        return cls
    return decorator