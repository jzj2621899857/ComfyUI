"""
精度自适应控制器

根据质量反馈自动选择 fp16/bf16/fp32
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class PrecisionMode(Enum):
    """精度模式"""
    FP32 = "float32"
    FP16 = "float16"
    BF16 = "bfloat16"


@dataclass
class QualityMetrics:
    """质量指标"""
    psnr: float = 0.0  # 峰值信噪比
    ssim: float = 0.0  # 结构相似性
    lpips: float = 0.0  # 感知距离
    user_rating: float = 0.0  # 用户评分
    
    def get_average(self) -> float:
        """获取平均质量分数"""
        scores = [self.psnr, self.ssim, 1.0 - self.lpips, self.user_rating]
        valid_scores = [s for s in scores if s > 0]
        return sum(valid_scores) / len(valid_scores) if valid_scores else 0.0


@dataclass
class PrecisionProfile:
    """精度配置档案"""
    mode: PrecisionMode
    quality_threshold: float = 0.8
    memory_target: float = 0.7
    speed_target: float = 1.0
    
    def get_torch_dtype(self):
        """获取 PyTorch 数据类型"""
        try:
            import torch
            dtype_map = {
                PrecisionMode.FP32: torch.float32,
                PrecisionMode.FP16: torch.float16,
                PrecisionMode.BF16: torch.bfloat16,
            }
            return dtype_map.get(self.mode, torch.float32)
        except ImportError:
            return None


class AdaptivePrecisionController:
    """
    精度自适应控制器
    
    根据质量反馈自动选择最佳精度模式
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._enabled = False
            cls._instance._current_mode = PrecisionMode.FP16
            cls._instance._quality_history: List[QualityMetrics] = []
            cls._instance._mode_history: List[Dict] = []
            cls._instance._quality_threshold = 0.8
            cls._instance._adaptation_rate = 0.1
        return cls._instance
    
    def enable(self, initial_mode: PrecisionMode = PrecisionMode.FP16):
        """启用控制器"""
        self._enabled = True
        self._current_mode = initial_mode
    
    def disable(self):
        """禁用控制器"""
        self._enabled = False
    
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self._enabled
    
    def get_current_mode(self) -> PrecisionMode:
        """获取当前精度模式"""
        return self._current_mode
    
    def record_quality(self, metrics: QualityMetrics):
        """记录质量反馈"""
        if not self._enabled:
            return
        
        self._quality_history.append(metrics)
        
        # 保留最近 100 条记录
        if len(self._quality_history) > 100:
            self._quality_history = self._quality_history[-100:]
        
        # 自适应调整
        self._adapt_precision()
    
    def _adapt_precision(self):
        """自适应调整精度"""
        if len(self._quality_history) < 5:
            return
        
        # 计算最近的质量平均值
        recent_quality = sum(m.get_average() for m in self._quality_history[-5:]) / 5
        
        # 根据质量调整精度
        if recent_quality < self._quality_threshold * 0.9:
            # 质量过低，提升精度
            if self._current_mode == PrecisionMode.FP16:
                self._current_mode = PrecisionMode.FP32
            elif self._current_mode == PrecisionMode.BF16:
                self._current_mode = PrecisionMode.FP32
        elif recent_quality > self._quality_threshold * 1.1:
            # 质量过剩，降低精度以提升速度
            if self._current_mode == PrecisionMode.FP32:
                # 检查是否支持 BF16
                if self._is_bf16_supported():
                    self._current_mode = PrecisionMode.BF16
                else:
                    self._current_mode = PrecisionMode.FP16
        
        # 记录模式变更
        self._mode_history.append({
            "mode": self._current_mode.value,
            "quality": recent_quality,
            "timestamp": time.time()
        })
    
    def _is_bf16_supported(self) -> bool:
        """检查是否支持 BF16"""
        try:
            import torch
            return torch.cuda.is_available() and torch.cuda.is_bf16_supported()
        except ImportError:
            return False
    
    def get_recommended_precision(self, node_type: str) -> PrecisionMode:
        """获取推荐的精度模式"""
        if not self._enabled:
            return PrecisionMode.FP32
        
        # 某些节点类型需要更高精度
        high_precision_nodes = ["CheckpointLoader", "SaveImage"]
        if node_type in high_precision_nodes:
            return PrecisionMode.FP32
        
        return self._current_mode
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        avg_quality = 0.0
        if self._quality_history:
            avg_quality = sum(m.get_average() for m in self._quality_history) / len(self._quality_history)
        
        return {
            "enabled": self._enabled,
            "current_mode": self._current_mode.value,
            "quality_threshold": self._quality_threshold,
            "average_quality": avg_quality,
            "quality_samples": len(self._quality_history),
            "mode_changes": len(self._mode_history)
        }
    
    def reset(self):
        """重置控制器"""
        self._current_mode = PrecisionMode.FP16
        self._quality_history.clear()
        self._mode_history.clear()


# 导入 time 模块
import time

# 全局控制器实例
precision_controller = AdaptivePrecisionController()
