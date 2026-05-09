"""
Fuse Box 模式 - 输入校验层

为每个节点注入输入校验层，在异常前切断执行，防止单节点崩溃导致全局失败
"""

import logging
import torch
import numpy as np
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass

from ..config import FuseBoxConfig

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """校验结果"""
    is_valid: bool
    error_message: Optional[str] = None
    warning_messages: List[str] = None
    
    def __post_init__(self):
        if self.warning_messages is None:
            self.warning_messages = []


class FuseBoxValidator:
    """
    Fuse Box 校验器
    
    在节点执行前对输入进行多维度校验：
    1. 类型校验（tensor dtype, shape）
    2. 数值范围校验（value range）
    3. 设备一致性校验
    """
    
    def __init__(self, config: FuseBoxConfig):
        self.config = config
        self._validation_stats = {
            "total_validations": 0,
            "failed_validations": 0,
            "warnings": 0,
        }
    
    def validate_inputs(
        self, 
        node_id: str, 
        class_type: str, 
        inputs: Dict[str, Any],
        input_specs: Optional[Dict] = None
    ) -> ValidationResult:
        """
        校验节点输入
        
        Args:
            node_id: 节点 ID
            class_type: 节点类型
            inputs: 输入数据字典
            input_specs: 输入规格定义（可选）
        
        Returns:
            ValidationResult: 校验结果
        """
        if not self.config.enabled:
            return ValidationResult(is_valid=True)
        
        self._validation_stats["total_validations"] += 1
        
        warnings = []
        
        for input_name, input_value in inputs.items():
            # 1. 类型校验
            type_result = self._validate_type(input_name, input_value)
            if not type_result.is_valid:
                self._validation_stats["failed_validations"] += 1
                return type_result
            warnings.extend(type_result.warning_messages)
            
            # 2. Tensor 专项校验
            if isinstance(input_value, torch.Tensor):
                tensor_result = self._validate_tensor(input_name, input_value, input_specs)
                if not tensor_result.is_valid:
                    self._validation_stats["failed_validations"] += 1
                    return tensor_result
                warnings.extend(tensor_result.warning_messages)
            
            # 3. 数值范围校验
            if self.config.check_value_range:
                range_result = self._validate_value_range(input_name, input_value)
                if not range_result.is_valid:
                    self._validation_stats["failed_validations"] += 1
                    return range_result
                warnings.extend(range_result.warning_messages)
        
        self._validation_stats["warnings"] += len(warnings)
        
        return ValidationResult(
            is_valid=True,
            warning_messages=warnings
        )
    
    def _validate_type(self, input_name: str, input_value: Any) -> ValidationResult:
        """校验类型"""
        # 检查是否为 None
        if input_value is None:
            return ValidationResult(
                is_valid=False,
                error_message=f"输入 '{input_name}' 为 None"
            )
        
        # 检查是否为支持的类型
        supported_types = (
            torch.Tensor, np.ndarray, int, float, str, bool,
            list, tuple, dict
        )
        
        if not isinstance(input_value, supported_types):
            return ValidationResult(
                is_valid=False,
                error_message=f"输入 '{input_name}' 类型不支持: {type(input_value)}"
            )
        
        return ValidationResult(is_valid=True)
    
    def _validate_tensor(
        self, 
        input_name: str, 
        tensor: torch.Tensor,
        input_specs: Optional[Dict] = None
    ) -> ValidationResult:
        """校验 Tensor"""
        warnings = []
        
        # 1. 检查是否为有效 tensor
        if not torch.is_tensor(tensor):
            return ValidationResult(
                is_valid=False,
                error_message=f"输入 '{input_name}' 不是有效的 Tensor"
            )
        
        # 2. 检查是否包含 NaN 或 Inf
        if torch.isnan(tensor).any():
            if self.config.strict_mode:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"输入 '{input_name}' 包含 NaN 值"
                )
            else:
                warnings.append(f"输入 '{input_name}' 包含 NaN 值")
        
        if torch.isinf(tensor).any():
            if self.config.strict_mode:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"输入 '{input_name}' 包含 Inf 值"
                )
            else:
                warnings.append(f"输入 '{input_name}' 包含 Inf 值")
        
        # 3. 检查 dtype
        supported_dtypes = [
            torch.float32, torch.float16, torch.bfloat16,
            torch.int32, torch.int64, torch.uint8, torch.bool
        ]
        
        if tensor.dtype not in supported_dtypes:
            warnings.append(
                f"输入 '{input_name}' 使用非标准 dtype: {tensor.dtype}"
            )
        
        # 4. 检查 shape（如果提供了规格）
        if input_specs and input_name in input_specs:
            spec = input_specs[input_name]
            expected_shape = spec.get("shape")
            if expected_shape:
                shape_valid, shape_msg = self._validate_shape(
                    input_name, tensor.shape, expected_shape
                )
                if not shape_valid:
                    return ValidationResult(is_valid=False, error_message=shape_msg)
        
        return ValidationResult(is_valid=True, warning_messages=warnings)
    
    def _validate_shape(
        self, 
        input_name: str, 
        actual_shape: torch.Size, 
        expected_shape: Tuple
    ) -> Tuple[bool, Optional[str]]:
        """
        校验 shape
        
        支持部分匹配（-1 表示任意维度）
        """
        actual_dims = len(actual_shape)
        expected_dims = len(expected_shape)
        
        if actual_dims != expected_dims:
            return False, (
                f"输入 '{input_name}' 维度不匹配: "
                f"期望 {expected_dims}D, 实际 {actual_dims}D"
            )
        
        # 检查每个维度
        for i, (actual, expected) in enumerate(zip(actual_shape, expected_shape)):
            if expected == -1:  # -1 表示任意大小
                continue
            
            if isinstance(expected, (list, tuple)):
                # 期望尺寸范围 [min, max]
                min_size, max_size = expected
                if actual < min_size or actual > max_size:
                    return False, (
                        f"输入 '{input_name}' 第 {i} 维大小 {actual} "
                        f"超出范围 [{min_size}, {max_size}]"
                    )
            else:
                # 精确匹配
                diff_ratio = abs(actual - expected) / max(expected, 1)
                if diff_ratio > self.config.max_shape_diff:
                    return False, (
                        f"输入 '{input_name}' 第 {i} 维大小 {actual} "
                        f"与期望 {expected} 差异过大 ({diff_ratio:.1%})"
                    )
        
        return True, None
    
    def _validate_value_range(self, input_name: str, input_value: Any) -> ValidationResult:
        """校验数值范围"""
        warnings = []
        
        if isinstance(input_value, torch.Tensor):
            # 检查数值范围（针对图像类数据）
            if input_value.dtype in [torch.float32, torch.float16, torch.bfloat16]:
                min_val = input_value.min().item()
                max_val = input_value.max().item()
                
                # 图像数据通常应该在 [0, 1] 或 [-1, 1] 范围内
                if min_val < -10 or max_val > 10:
                    warnings.append(
                        f"输入 '{input_name}' 数值范围异常: [{min_val:.2f}, {max_val:.2f}]"
                    )
        
        elif isinstance(input_value, (int, float)):
            # 检查数值是否异常
            if isinstance(input_value, float):
                if np.isnan(input_value):
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"输入 '{input_name}' 为 NaN"
                    )
                if np.isinf(input_value):
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"输入 '{input_name}' 为 Inf"
                    )
        
        return ValidationResult(is_valid=True, warning_messages=warnings)
    
    def get_stats(self) -> Dict[str, int]:
        """获取校验统计信息"""
        return self._validation_stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self._validation_stats = {
            "total_validations": 0,
            "failed_validations": 0,
            "warnings": 0,
        }


class InputContract:
    """
    输入合约定义
    
    用于定义节点输入的元数据合约
    """
    
    def __init__(
        self,
        name: str,
        dtype: Optional[str] = None,
        shape: Optional[Tuple] = None,
        value_range: Optional[Tuple[float, float]] = None,
        device: Optional[str] = None,
        optional: bool = False,
        description: Optional[str] = None
    ):
        self.name = name
        self.dtype = dtype
        self.shape = shape
        self.value_range = value_range
        self.device = device
        self.optional = optional
        self.description = description
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "name": self.name,
            "dtype": self.dtype,
            "shape": self.shape,
            "value_range": self.value_range,
            "device": self.device,
            "optional": self.optional,
            "description": self.description,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "InputContract":
        """从字典创建"""
        return cls(**data)


def create_fuse_box_wrapper(validator: FuseBoxValidator):
    """
    创建 Fuse Box 包装器
    
    用于包装节点执行函数，在执行前进行输入校验
    """
    def wrapper(func):
        @functools.wraps(func)
        async def async_wrapped(*args, **kwargs):
            # 提取节点信息
            node_id = kwargs.get("unique_id", "unknown")
            class_type = kwargs.get("class_type", "unknown")
            inputs = kwargs.get("inputs", {})
            
            # 执行校验
            result = validator.validate_inputs(node_id, class_type, inputs)
            
            if not result.is_valid:
                logger.error(f"[FuseBox] 节点 {node_id} ({class_type}) 输入校验失败: {result.error_message}")
                raise ValueError(result.error_message)
            
            # 记录警告
            for warning in result.warning_messages:
                logger.warning(f"[FuseBox] 节点 {node_id} ({class_type}): {warning}")
            
            # 执行原函数
            return await func(*args, **kwargs)
        
        return async_wrapped
    return wrapper