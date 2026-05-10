"""
资源预估器

预估节点资源需求，支持显存/算力/时间的预计算
"""

import json
import os
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ResourceEstimate:
    """资源预估结果"""
    memory_mb: float = 0.0
    compute_flops: float = 0.0
    estimated_time_ms: float = 0.0
    confidence: float = 1.0  # 置信度 0-1
    
    def __add__(self, other: "ResourceEstimate") -> "ResourceEstimate":
        """合并两个预估"""
        return ResourceEstimate(
            memory_mb=self.memory_mb + other.memory_mb,
            compute_flops=self.compute_flops + other.compute_flops,
            estimated_time_ms=self.estimated_time_ms + other.estimated_time_ms,
            confidence=min(self.confidence, other.confidence)
        )


@dataclass
class NodeProfile:
    """节点性能画像"""
    node_type: str
    avg_memory_mb: float = 0.0
    avg_time_ms: float = 0.0
    sample_count: int = 0
    input_shapes: Dict[str, Any] = field(default_factory=dict)
    
    def update(self, memory_mb: float, time_ms: float):
        """更新画像"""
        total_samples = self.sample_count + 1
        self.avg_memory_mb = (self.avg_memory_mb * self.sample_count + memory_mb) / total_samples
        self.avg_time_ms = (self.avg_time_ms * self.sample_count + time_ms) / total_samples
        self.sample_count = total_samples


class ResourceEstimator:
    """
    资源预估器
    
    基于历史数据和模型特征预估资源需求
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._profiles: Dict[str, NodeProfile] = {}
            cls._instance._model_profiles: Dict[str, Dict] = {}
            cls._instance._storage_path = None
            cls._instance._enabled = False
        return cls._instance
    
    def enable(self, storage_path: Optional[str] = None):
        """启用预估器"""
        self._enabled = True
        if storage_path:
            self._storage_path = storage_path
            self._load_profiles()
    
    def disable(self):
        """禁用预估器"""
        self._enabled = False
    
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self._enabled
    
    def record_execution(self, node_type: str, memory_mb: float, time_ms: float, input_shapes: Optional[Dict] = None):
        """记录执行数据用于学习"""
        if not self._enabled:
            return
        
        if node_type not in self._profiles:
            self._profiles[node_type] = NodeProfile(node_type=node_type)
        
        profile = self._profiles[node_type]
        profile.update(memory_mb, time_ms)
        
        if input_shapes:
            profile.input_shapes = input_shapes
        
        # 保存到文件
        if self._storage_path:
            self._save_profiles()
    
    def estimate(self, node_type: str, input_shapes: Optional[Dict] = None) -> ResourceEstimate:
        """
        预估节点资源需求
        
        Args:
            node_type: 节点类型
            input_shapes: 输入形状信息
        
        Returns:
            资源预估结果
        """
        if not self._enabled:
            return ResourceEstimate(confidence=0.0)
        
        # 如果有历史数据，使用历史平均值
        if node_type in self._profiles:
            profile = self._profiles[node_type]
            return ResourceEstimate(
                memory_mb=profile.avg_memory_mb,
                estimated_time_ms=profile.avg_time_ms,
                confidence=min(1.0, profile.sample_count / 10)  # 样本越多置信度越高
            )
        
        # 否则使用启发式预估
        return self._heuristic_estimate(node_type, input_shapes)
    
    def _heuristic_estimate(self, node_type: str, input_shapes: Optional[Dict] = None) -> ResourceEstimate:
        """启发式预估"""
        # 基于节点类型的启发式规则
        heuristics = {
            "CheckpointLoader": ResourceEstimate(memory_mb=2000, estimated_time_ms=5000),
            "CLIPTextEncode": ResourceEstimate(memory_mb=500, estimated_time_ms=100),
            "KSampler": ResourceEstimate(memory_mb=4000, estimated_time_ms=5000),
            "VAEDecode": ResourceEstimate(memory_mb=1000, estimated_time_ms=500),
            "VAEEncode": ResourceEstimate(memory_mb=1000, estimated_time_ms=500),
            "EmptyLatentImage": ResourceEstimate(memory_mb=100, estimated_time_ms=10),
            "LoadImage": ResourceEstimate(memory_mb=500, estimated_time_ms=200),
            "SaveImage": ResourceEstimate(memory_mb=200, estimated_time_ms=100),
        }
        
        base_estimate = heuristics.get(node_type, ResourceEstimate(memory_mb=500, estimated_time_ms=100))
        base_estimate.confidence = 0.3  # 启发式预估置信度较低
        
        # 根据输入形状调整
        if input_shapes:
            base_estimate = self._adjust_by_shape(base_estimate, input_shapes)
        
        return base_estimate
    
    def _adjust_by_shape(self, estimate: ResourceEstimate, input_shapes: Dict) -> ResourceEstimate:
        """根据输入形状调整预估"""
        # 计算总元素数
        total_elements = 0
        for shape in input_shapes.values():
            if isinstance(shape, (list, tuple)):
                elements = 1
                for dim in shape:
                    if isinstance(dim, int) and dim > 0:
                        elements *= dim
                total_elements += elements
        
        # 根据元素数调整内存预估
        if total_elements > 0:
            # 假设每个元素 4 字节 (float32)
            memory_factor = total_elements * 4 / (1024 * 1024)  # MB
            estimate.memory_mb = max(estimate.memory_mb, memory_factor * 2)  # 考虑中间结果
        
        return estimate
    
    def estimate_workflow(self, workflow: Dict[str, Any]) -> ResourceEstimate:
        """预估整个工作流的资源需求"""
        if not self._enabled:
            return ResourceEstimate(confidence=0.0)
        
        total_estimate = ResourceEstimate()
        
        nodes = workflow.get("nodes", {})
        for node_id, node_data in nodes.items():
            node_type = node_data.get("type", "Unknown")
            inputs = node_data.get("inputs", {})
            
            node_estimate = self.estimate(node_type, inputs)
            total_estimate = total_estimate + node_estimate
        
        return total_estimate
    
    def _load_profiles(self):
        """加载性能画像"""
        if not self._storage_path:
            return
        
        filepath = os.path.join(self._storage_path, "resource_profiles.json")
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    for node_type, profile_data in data.items():
                        self._profiles[node_type] = NodeProfile(**profile_data)
            except Exception:
                pass
    
    def _save_profiles(self):
        """保存性能画像"""
        if not self._storage_path:
            return
        
        os.makedirs(self._storage_path, exist_ok=True)
        filepath = os.path.join(self._storage_path, "resource_profiles.json")
        
        data = {
            node_type: {
                "node_type": profile.node_type,
                "avg_memory_mb": profile.avg_memory_mb,
                "avg_time_ms": profile.avg_time_ms,
                "sample_count": profile.sample_count,
                "input_shapes": profile.input_shapes
            }
            for node_type, profile in self._profiles.items()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_profile(self, node_type: str) -> Optional[NodeProfile]:
        """获取节点画像"""
        return self._profiles.get(node_type)
    
    def get_all_profiles(self) -> Dict[str, NodeProfile]:
        """获取所有画像"""
        return dict(self._profiles)
    
    def can_fit_in_memory(self, node_type: str, available_memory_mb: float) -> Tuple[bool, float]:
        """检查是否可以放入内存"""
        estimate = self.estimate(node_type)
        required = estimate.memory_mb
        
        # 添加 20% 安全边距
        required_with_margin = required * 1.2
        
        return available_memory_mb >= required_with_margin, required_with_margin


# 全局预估器实例
estimator = ResourceEstimator()
