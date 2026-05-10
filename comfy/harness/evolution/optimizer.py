"""
闭环优化器

根据评分反馈自动调整超参数
"""

import random
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class HyperParameter:
    """超参数"""
    name: str
    current_value: float
    min_value: float
    max_value: float
    step_size: float
    history: List[Tuple[float, float]] = field(default_factory=list)  # (value, score)
    
    def suggest_new_value(self, direction: int = 0) -> float:
        """建议新值"""
        if direction == 0:
            # 随机探索
            new_value = random.uniform(self.min_value, self.max_value)
        else:
            # 梯度方向调整
            adjustment = self.step_size * direction
            new_value = self.current_value + adjustment
        
        # 限制在范围内
        return max(self.min_value, min(self.max_value, new_value))
    
    def record_result(self, value: float, score: float):
        """记录结果"""
        self.history.append((value, score))
        # 保留最近 20 条记录
        if len(self.history) > 20:
            self.history = self.history[-20:]
    
    def get_best_value(self) -> float:
        """获取历史最佳值"""
        if not self.history:
            return self.current_value
        return max(self.history, key=lambda x: x[1])[0]


@dataclass
class OptimizationConfig:
    """优化配置"""
    learning_rate: float = 0.1
    exploration_rate: float = 0.2
    patience: int = 5
    min_improvement: float = 0.01


class ClosedLoopOptimizer:
    """
    闭环优化器
    
    根据评分反馈自动调整超参数
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._enabled = False
            cls._instance._parameters: Dict[str, HyperParameter] = {}
            cls._instance._config = OptimizationConfig()
            cls._instance._iteration = 0
            cls._instance._best_score = 0.0
            cls._instance._no_improvement_count = 0
        return cls._instance
    
    def enable(self, config: Optional[OptimizationConfig] = None):
        """启用优化器"""
        self._enabled = True
        if config:
            self._config = config
    
    def disable(self):
        """禁用优化器"""
        self._enabled = False
    
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self._enabled
    
    def register_parameter(self, name: str, current_value: float, min_value: float, max_value: float, step_size: float):
        """注册超参数"""
        self._parameters[name] = HyperParameter(
            name=name,
            current_value=current_value,
            min_value=min_value,
            max_value=max_value,
            step_size=step_size
        )
    
    def suggest_parameters(self) -> Dict[str, float]:
        """建议新的超参数值"""
        if not self._enabled:
            return {name: param.current_value for name, param in self._parameters.items()}
        
        suggestions = {}
        
        for name, param in self._parameters.items():
            # 决定是否探索
            if random.random() < self._config.exploration_rate:
                # 随机探索
                suggestions[name] = param.suggest_new_value(0)
            else:
                # 利用历史最佳
                if param.history:
                    # 找出改进方向
                    direction = self._calculate_gradient(param)
                    suggestions[name] = param.suggest_new_value(direction)
                else:
                    suggestions[name] = param.current_value
        
        return suggestions
    
    def _calculate_gradient(self, param: HyperParameter) -> int:
        """计算梯度方向"""
        if len(param.history) < 2:
            return 0
        
        # 简单梯度：最近两次的变化趋势
        recent = param.history[-2:]
        value_diff = recent[1][0] - recent[0][0]
        score_diff = recent[1][1] - recent[0][1]
        
        if abs(value_diff) < 1e-6:
            return 0
        
        gradient = score_diff / value_diff
        
        if gradient > 0:
            return 1 if value_diff > 0 else -1
        else:
            return -1 if value_diff > 0 else 1
    
    def update(self, parameters: Dict[str, float], score: float):
        """更新优化器状态"""
        if not self._enabled:
            return
        
        self._iteration += 1
        
        # 记录结果
        for name, value in parameters.items():
            if name in self._parameters:
                self._parameters[name].record_result(value, score)
        
        # 检查是否有改进
        if score > self._best_score + self._config.min_improvement:
            self._best_score = score
            self._no_improvement_count = 0
            
            # 更新当前值
            for name, value in parameters.items():
                if name in self._parameters:
                    self._parameters[name].current_value = value
        else:
            self._no_improvement_count += 1
    
    def should_stop(self) -> bool:
        """是否应该停止优化"""
        if not self._enabled:
            return True
        
        return self._no_improvement_count >= self._config.patience
    
    def get_best_parameters(self) -> Dict[str, float]:
        """获取最佳超参数"""
        return {
            name: param.get_best_value()
            for name, param in self._parameters.items()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "enabled": self._enabled,
            "iteration": self._iteration,
            "best_score": self._best_score,
            "no_improvement_count": self._no_improvement_count,
            "parameters": {
                name: {
                    "current": param.current_value,
                    "best": param.get_best_value(),
                    "history_count": len(param.history)
                }
                for name, param in self._parameters.items()
            }
        }
    
    def reset(self):
        """重置优化器"""
        self._iteration = 0
        self._best_score = 0.0
        self._no_improvement_count = 0
        for param in self._parameters.values():
            param.history.clear()


class WorkflowOptimizer:
    """工作流优化器"""
    
    def __init__(self):
        self._optimizer = ClosedLoopOptimizer()
        self._target_metrics = ["quality", "speed", "memory"]
        self._weights = {"quality": 0.5, "speed": 0.3, "memory": 0.2}
    
    def enable(self):
        """启用"""
        self._optimizer.enable()
    
    def disable(self):
        """禁用"""
        self._optimizer.disable()
    
    def optimize_workflow(self, workflow: Dict[str, Any], feedback: Dict[str, float]) -> Dict[str, Any]:
        """
        优化工作流
        
        Args:
            workflow: 当前工作流
            feedback: 反馈指标 {metric: score}
        
        Returns:
            优化后的工作流
        """
        if not self._optimizer.is_enabled():
            return workflow
        
        # 计算综合得分
        composite_score = self._calculate_composite_score(feedback)
        
        # 更新优化器
        current_params = self._extract_parameters(workflow)
        self._optimizer.update(current_params, composite_score)
        
        # 获取新的参数建议
        new_params = self._optimizer.suggest_parameters()
        
        # 应用新参数
        optimized_workflow = self._apply_parameters(workflow, new_params)
        
        return optimized_workflow
    
    def _calculate_composite_score(self, feedback: Dict[str, float]) -> float:
        """计算综合得分"""
        score = 0.0
        total_weight = 0.0
        
        for metric, weight in self._weights.items():
            if metric in feedback:
                score += feedback[metric] * weight
                total_weight += weight
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def _extract_parameters(self, workflow: Dict[str, Any]) -> Dict[str, float]:
        """从工作流中提取参数"""
        params = {}
        nodes = workflow.get("nodes", {})
        
        for node_id, node_data in nodes.items():
            inputs = node_data.get("inputs", {})
            for key, value in inputs.items():
                if isinstance(value, (int, float)):
                    param_name = f"{node_id}.{key}"
                    params[param_name] = float(value)
        
        return params
    
    def _apply_parameters(self, workflow: Dict[str, Any], params: Dict[str, float]) -> Dict[str, Any]:
        """应用参数到工作流"""
        import copy
        optimized = copy.deepcopy(workflow)
        nodes = optimized.get("nodes", {})
        
        for param_name, value in params.items():
            if "." in param_name:
                node_id, key = param_name.split(".", 1)
                if node_id in nodes:
                    if "inputs" not in nodes[node_id]:
                        nodes[node_id]["inputs"] = {}
                    nodes[node_id]["inputs"][key] = value
        
        return optimized


# 全局优化器实例
optimizer = ClosedLoopOptimizer()
workflow_optimizer = WorkflowOptimizer()
