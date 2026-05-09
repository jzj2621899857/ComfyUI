"""
输入校验器集合

提供各种类型输入的校验功能
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import logging

logger = logging.getLogger(__name__)


class TypeValidator:
    """类型校验器"""
    
    @staticmethod
    def validate_tensor(value: Any, expected_shape: Optional[Tuple] = None) -> Tuple[bool, str]:
        """校验 Tensor 类型和形状"""
        try:
            import torch
            if not isinstance(value, torch.Tensor):
                return False, f"期望 torch.Tensor, 实际 {type(value)}"
            
            if expected_shape is not None:
                if len(value.shape) != len(expected_shape):
                    return False, f"维度不匹配: 期望 {len(expected_shape)} 维, 实际 {len(value.shape)} 维"
                
                for i, (actual, expected) in enumerate(zip(value.shape, expected_shape)):
                    if isinstance(expected, int) and expected != -1:
                        if actual != expected:
                            return False, f"第 {i} 维大小不匹配: 期望 {expected}, 实际 {actual}"
            
            return True, ""
        except ImportError:
            return True, "torch 不可用，跳过 tensor 校验"
    
    @staticmethod
    def validate_ndarray(value: Any, expected_shape: Optional[Tuple] = None) -> Tuple[bool, str]:
        """校验 NumPy 数组"""
        try:
            import numpy as np
            if not isinstance(value, np.ndarray):
                return False, f"期望 numpy.ndarray, 实际 {type(value)}"
            
            if expected_shape is not None:
                if value.shape != expected_shape:
                    return False, f"形状不匹配: 期望 {expected_shape}, 实际 {value.shape}"
            
            return True, ""
        except ImportError:
            return True, "numpy 不可用，跳过 ndarray 校验"
    
    @staticmethod
    def validate_int(value: Any, min_val: Optional[int] = None, max_val: Optional[int] = None) -> Tuple[bool, str]:
        """校验整数"""
        if not isinstance(value, int) or isinstance(value, bool):
            return False, f"期望 int, 实际 {type(value)}"
        
        if min_val is not None and value < min_val:
            return False, f"值 {value} 小于最小值 {min_val}"
        
        if max_val is not None and value > max_val:
            return False, f"值 {value} 大于最大值 {max_val}"
        
        return True, ""
    
    @staticmethod
    def validate_float(value: Any, min_val: Optional[float] = None, max_val: Optional[float] = None) -> Tuple[bool, str]:
        """校验浮点数"""
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return False, f"期望 float, 实际 {type(value)}"
        
        value = float(value)
        
        if min_val is not None and value < min_val:
            return False, f"值 {value} 小于最小值 {min_val}"
        
        if max_val is not None and value > max_val:
            return False, f"值 {value} 大于最大值 {max_val}"
        
        return True, ""
    
    @staticmethod
    def validate_string(value: Any, min_length: Optional[int] = None, max_length: Optional[int] = None) -> Tuple[bool, str]:
        """校验字符串"""
        if not isinstance(value, str):
            return False, f"期望 str, 实际 {type(value)}"
        
        if min_length is not None and len(value) < min_length:
            return False, f"长度 {len(value)} 小于最小长度 {min_length}"
        
        if max_length is not None and len(value) > max_length:
            return False, f"长度 {len(value)} 大于最大长度 {max_length}"
        
        return True, ""
    
    @staticmethod
    def validate_list(value: Any, min_length: Optional[int] = None, max_length: Optional[int] = None) -> Tuple[bool, str]:
        """校验列表"""
        if not isinstance(value, list):
            return False, f"期望 list, 实际 {type(value)}"
        
        if min_length is not None and len(value) < min_length:
            return False, f"长度 {len(value)} 小于最小长度 {min_length}"
        
        if max_length is not None and len(value) > max_length:
            return False, f"长度 {len(value)} 大于最大长度 {max_length}"
        
        return True, ""


class ValueValidator:
    """数值校验器"""
    
    @staticmethod
    def validate_range(value: Union[int, float], min_val: Optional[float] = None, max_val: Optional[float] = None) -> Tuple[bool, str]:
        """校验数值范围"""
        if min_val is not None and value < min_val:
            return False, f"值 {value} 小于最小值 {min_val}"
        
        if max_val is not None and value > max_val:
            return False, f"值 {value} 大于最大值 {max_val}"
        
        return True, ""
    
    @staticmethod
    def validate_enum(value: Any, allowed_values: List[Any]) -> Tuple[bool, str]:
        """校验枚举值"""
        if value not in allowed_values:
            return False, f"值 {value} 不在允许列表 {allowed_values} 中"
        
        return True, ""
    
    @staticmethod
    def validate_regex(value: str, pattern: str) -> Tuple[bool, str]:
        """校验正则表达式"""
        import re
        if not re.match(pattern, value):
            return False, f"值 '{value}' 不匹配模式 '{pattern}'"
        
        return True, ""


class TensorValidator:
    """Tensor 专用校验器"""
    
    @staticmethod
    def validate_dtype(tensor: Any, allowed_dtypes: List[str]) -> Tuple[bool, str]:
        """校验 Tensor 数据类型"""
        try:
            import torch
            if not isinstance(tensor, torch.Tensor):
                return False, "不是 torch.Tensor"
            
            dtype_str = str(tensor.dtype).replace('torch.', '')
            if dtype_str not in allowed_dtypes:
                return False, f"数据类型 {dtype_str} 不在允许列表 {allowed_dtypes} 中"
            
            return True, ""
        except ImportError:
            return True, "torch 不可用"
    
    @staticmethod
    def validate_device(tensor: Any, expected_device: str) -> Tuple[bool, str]:
        """校验 Tensor 设备"""
        try:
            import torch
            if not isinstance(tensor, torch.Tensor):
                return False, "不是 torch.Tensor"
            
            actual_device = str(tensor.device)
            if expected_device not in actual_device:
                return False, f"设备不匹配: 期望 {expected_device}, 实际 {actual_device}"
            
            return True, ""
        except ImportError:
            return True, "torch 不可用"
    
    @staticmethod
    def validate_value_range(tensor: Any, min_val: float, max_val: float) -> Tuple[bool, str]:
        """校验 Tensor 数值范围"""
        try:
            import torch
            if not isinstance(tensor, torch.Tensor):
                return False, "不是 torch.Tensor"
            
            actual_min = tensor.min().item()
            actual_max = tensor.max().item()
            
            if actual_min < min_val:
                return False, f"最小值 {actual_min} 小于允许的最小值 {min_val}"
            
            if actual_max > max_val:
                return False, f"最大值 {actual_max} 大于允许的最大值 {max_val}"
            
            return True, ""
        except ImportError:
            return True, "torch 不可用"
    
    @staticmethod
    def validate_no_nan(tensor: Any) -> Tuple[bool, str]:
        """校验 Tensor 不包含 NaN"""
        try:
            import torch
            if not isinstance(tensor, torch.Tensor):
                return False, "不是 torch.Tensor"
            
            if torch.isnan(tensor).any():
                return False, "Tensor 包含 NaN 值"
            
            return True, ""
        except ImportError:
            return True, "torch 不可用"
    
    @staticmethod
    def validate_no_inf(tensor: Any) -> Tuple[bool, str]:
        """校验 Tensor 不包含 Inf"""
        try:
            import torch
            if not isinstance(tensor, torch.Tensor):
                return False, "不是 torch.Tensor"
            
            if torch.isinf(tensor).any():
                return False, "Tensor 包含 Inf 值"
            
            return True, ""
        except ImportError:
            return True, "torch 不可用"


class InputValidator:
    """综合输入校验器"""
    
    def __init__(self):
        self.type_validator = TypeValidator()
        self.value_validator = ValueValidator()
        self.tensor_validator = TensorValidator()
    
    def validate(self, value: Any, spec: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        根据规格校验输入
        
        Args:
            value: 要校验的值
            spec: 校验规格，包含 type, shape, min, max 等
        
        Returns:
            (是否通过, 错误信息列表)
        """
        errors = []
        
        # 获取类型
        value_type = spec.get('type')
        
        if value_type == 'tensor':
            shape = spec.get('shape')
            valid, msg = self.type_validator.validate_tensor(value, shape)
            if not valid:
                errors.append(msg)
            else:
                # Tensor 额外校验
                dtype = spec.get('dtype')
                if dtype:
                    valid, msg = self.tensor_validator.validate_dtype(value, [dtype])
                    if not valid:
                        errors.append(msg)
                
                device = spec.get('device')
                if device:
                    valid, msg = self.tensor_validator.validate_device(value, device)
                    if not valid:
                        errors.append(msg)
                
                value_range = spec.get('value_range')
                if value_range:
                    min_val, max_val = value_range
                    valid, msg = self.tensor_validator.validate_value_range(value, min_val, max_val)
                    if not valid:
                        errors.append(msg)
                
                if spec.get('no_nan', False):
                    valid, msg = self.tensor_validator.validate_no_nan(value)
                    if not valid:
                        errors.append(msg)
                
                if spec.get('no_inf', False):
                    valid, msg = self.tensor_validator.validate_no_inf(value)
                    if not valid:
                        errors.append(msg)
        
        elif value_type == 'ndarray':
            shape = spec.get('shape')
            valid, msg = self.type_validator.validate_ndarray(value, shape)
            if not valid:
                errors.append(msg)
        
        elif value_type == 'int':
            min_val = spec.get('min')
            max_val = spec.get('max')
            valid, msg = self.type_validator.validate_int(value, min_val, max_val)
            if not valid:
                errors.append(msg)
        
        elif value_type == 'float':
            min_val = spec.get('min')
            max_val = spec.get('max')
            valid, msg = self.type_validator.validate_float(value, min_val, max_val)
            if not valid:
                errors.append(msg)
        
        elif value_type == 'string':
            min_length = spec.get('min_length')
            max_length = spec.get('max_length')
            valid, msg = self.type_validator.validate_string(value, min_length, max_length)
            if not valid:
                errors.append(msg)
            
            # 正则校验
            pattern = spec.get('pattern')
            if pattern and valid:
                valid, msg = self.value_validator.validate_regex(value, pattern)
                if not valid:
                    errors.append(msg)
            
            # 枚举校验
            enum = spec.get('enum')
            if enum and valid:
                valid, msg = self.value_validator.validate_enum(value, enum)
                if not valid:
                    errors.append(msg)
        
        elif value_type == 'list':
            min_length = spec.get('min_length')
            max_length = spec.get('max_length')
            valid, msg = self.type_validator.validate_list(value, min_length, max_length)
            if not valid:
                errors.append(msg)
        
        else:
            errors.append(f"未知的类型: {value_type}")
        
        return len(errors) == 0, errors


# 全局校验器实例
input_validator = InputValidator()
