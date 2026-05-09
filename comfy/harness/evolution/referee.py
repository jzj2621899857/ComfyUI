"""
AI 裁判评分器

自动对比新旧版本输出质量，给出评分
"""

import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class QualityScore:
    """质量评分"""
    overall: float = 0.0  # 总分 0-100
    fidelity: float = 0.0  # 保真度
    consistency: float = 0.0  # 一致性
    performance: float = 0.0  # 性能
    stability: float = 0.0  # 稳定性
    details: Dict[str, Any] = field(default_factory=dict)
    
    def get_average(self) -> float:
        """获取平均分"""
        scores = [self.fidelity, self.consistency, self.performance, self.stability]
        return sum(scores) / len(scores)


@dataclass
class ComparisonResult:
    """对比结果"""
    baseline_score: QualityScore
    candidate_score: QualityScore
    improvement: float = 0.0  # 改进幅度
    recommendation: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


class AIReferee:
    """
    AI 裁判评分器
    
    自动对比新旧版本输出质量
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._enabled = False
            cls._instance._history: List[ComparisonResult] = []
            cls._instance._threshold = 0.05  # 5% 改进阈值
        return cls._instance
    
    def enable(self, threshold: float = 0.05):
        """启用裁判"""
        self._enabled = True
        self._threshold = threshold
    
    def disable(self):
        """禁用裁判"""
        self._enabled = False
    
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self._enabled
    
    def compare_outputs(self, baseline: Any, candidate: Any, metrics: Optional[Dict] = None) -> ComparisonResult:
        """
        对比两个输出
        
        Args:
            baseline: 基线版本输出
            candidate: 候选版本输出
            metrics: 额外指标
        
        Returns:
            对比结果
        """
        if not self._enabled:
            return ComparisonResult(
                baseline_score=QualityScore(),
                candidate_score=QualityScore(),
                recommendation="裁判未启用"
            )
        
        # 计算基线分数
        baseline_score = self._calculate_score(baseline, metrics)
        
        # 计算候选分数
        candidate_score = self._calculate_score(candidate, metrics)
        
        # 计算改进幅度
        improvement = self._calculate_improvement(baseline_score, candidate_score)
        
        # 生成建议
        recommendation = self._generate_recommendation(improvement, baseline_score, candidate_score)
        
        result = ComparisonResult(
            baseline_score=baseline_score,
            candidate_score=candidate_score,
            improvement=improvement,
            recommendation=recommendation,
            details={
                "timestamp": time.time(),
                "threshold": self._threshold
            }
        )
        
        self._history.append(result)
        
        return result
    
    def _calculate_score(self, output: Any, metrics: Optional[Dict]) -> QualityScore:
        """计算质量分数"""
        score = QualityScore()
        
        # 如果有外部指标，使用外部指标
        if metrics:
            score.fidelity = metrics.get("fidelity", 0.0) * 100
            score.consistency = metrics.get("consistency", 0.0) * 100
            score.performance = metrics.get("performance", 0.0) * 100
            score.stability = metrics.get("stability", 0.0) * 100
        else:
            # 否则基于输出特征计算
            score = self._analyze_output(output)
        
        # 计算总分
        score.overall = score.get_average()
        
        return score
    
    def _analyze_output(self, output: Any) -> QualityScore:
        """分析输出特征"""
        score = QualityScore()
        
        try:
            import torch
            if isinstance(output, torch.Tensor):
                # 分析 Tensor 质量
                score.fidelity = self._analyze_tensor_fidelity(output)
                score.consistency = self._analyze_tensor_consistency(output)
                score.stability = self._analyze_tensor_stability(output)
        except ImportError:
            pass
        
        # 默认中等分数
        if score.fidelity == 0:
            score.fidelity = 70.0
        if score.consistency == 0:
            score.consistency = 70.0
        if score.stability == 0:
            score.stability = 70.0
        
        # 性能分数基于输出大小
        score.performance = self._estimate_performance_score(output)
        
        return score
    
    def _analyze_tensor_fidelity(self, tensor: Any) -> float:
        """分析 Tensor 保真度"""
        try:
            import torch
            
            # 检查数值范围
            min_val = tensor.min().item()
            max_val = tensor.max().item()
            
            # 图像通常应在 [0, 1] 或 [-1, 1] 范围内
            if 0 <= min_val and max_val <= 1:
                return 95.0
            elif -1 <= min_val and max_val <= 1:
                return 90.0
            else:
                # 数值范围异常
                return max(0, 100 - abs(max_val) * 10)
        except:
            return 70.0
    
    def _analyze_tensor_consistency(self, tensor: Any) -> float:
        """分析 Tensor 一致性"""
        try:
            import torch
            
            # 检查是否有 NaN 或 Inf
            has_nan = torch.isnan(tensor).any().item()
            has_inf = torch.isinf(tensor).any().item()
            
            if has_nan or has_inf:
                return 0.0
            
            # 检查数值分布
            std = tensor.std().item()
            if std < 1e-6:
                # 数值过于一致（可能是错误）
                return 50.0
            
            return 95.0
        except:
            return 70.0
    
    def _analyze_tensor_stability(self, tensor: Any) -> float:
        """分析 Tensor 稳定性"""
        try:
            import torch
            
            # 检查梯度（如果有）
            if tensor.requires_grad and tensor.grad is not None:
                grad_norm = tensor.grad.norm().item()
                if grad_norm > 1000:
                    return 50.0  # 梯度爆炸
            
            return 90.0
        except:
            return 70.0
    
    def _estimate_performance_score(self, output: Any) -> float:
        """估计性能分数"""
        try:
            import torch
            if isinstance(output, torch.Tensor):
                # 基于输出大小估计
                size_mb = output.numel() * 4 / (1024 * 1024)  # float32
                if size_mb < 10:
                    return 95.0
                elif size_mb < 100:
                    return 85.0
                elif size_mb < 500:
                    return 75.0
                else:
                    return 60.0
        except:
            pass
        
        return 70.0
    
    def _calculate_improvement(self, baseline: QualityScore, candidate: QualityScore) -> float:
        """计算改进幅度"""
        baseline_avg = baseline.get_average()
        candidate_avg = candidate.get_average()
        
        if baseline_avg == 0:
            return 0.0
        
        return (candidate_avg - baseline_avg) / baseline_avg
    
    def _generate_recommendation(self, improvement: float, baseline: QualityScore, candidate: QualityScore) -> str:
        """生成建议"""
        if improvement > self._threshold:
            return f"推荐升级: 质量提升 {improvement*100:.1f}%"
        elif improvement > 0:
            return f"轻微改进: 质量提升 {improvement*100:.1f}%，但未达到阈值"
        elif improvement > -self._threshold:
            return f"质量持平: 变化 {improvement*100:.1f}%"
        else:
            return f"不推荐: 质量下降 {abs(improvement)*100:.1f}%"
    
    def should_promote(self, result: ComparisonResult) -> bool:
        """是否应该推广"""
        return result.improvement > self._threshold
    
    def get_history(self, limit: int = 10) -> List[ComparisonResult]:
        """获取历史记录"""
        return self._history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self._history:
            return {"enabled": self._enabled, "comparisons": 0}
        
        improvements = [r.improvement for r in self._history]
        promotions = sum(1 for r in self._history if self.should_promote(r))
        
        return {
            "enabled": self._enabled,
            "comparisons": len(self._history),
            "promotions": promotions,
            "average_improvement": sum(improvements) / len(improvements),
            "max_improvement": max(improvements),
            "min_improvement": min(improvements)
        }


# 全局裁判实例
referee = AIReferee()
