"""
性能分析器 - 节点执行耗时统计与热点识别
"""

import time
import statistics
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

@dataclass
class NodePerformance:
    node_type: str
    total_executions: int = 0
    total_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    durations: List[float] = field(default_factory=list)
    
    @property
    def avg_duration(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return self.total_duration / self.total_executions
    
    @property
    def std_dev(self) -> float:
        if len(self.durations) < 2:
            return 0.0
        return statistics.stdev(self.durations)
    
    @property
    def p95(self) -> float:
        if not self.durations:
            return 0.0
        sorted_durations = sorted(self.durations)
        index = int(len(sorted_durations) * 0.95)
        return sorted_durations[min(index, len(sorted_durations) - 1)]
    
    @property
    def p99(self) -> float:
        if not self.durations:
            return 0.0
        sorted_durations = sorted(self.durations)
        index = int(len(sorted_durations) * 0.99)
        return sorted_durations[min(index, len(sorted_durations) - 1)]

@dataclass
class WorkflowPerformance:
    workflow_id: str
    total_nodes: int = 0
    completed_nodes: int = 0
    failed_nodes: int = 0
    total_duration: float = 0.0
    node_performance: Dict[str, NodePerformance] = field(default_factory=dict)
    
    def record_node_execution(self, node_type: str, duration: float, success: bool = True):
        if node_type not in self.node_performance:
            self.node_performance[node_type] = NodePerformance(node_type=node_type)
        
        perf = self.node_performance[node_type]
        perf.total_executions += 1
        perf.total_duration += duration
        perf.durations.append(duration)
        perf.min_duration = min(perf.min_duration, duration)
        perf.max_duration = max(perf.max_duration, duration)
        
        if success:
            self.completed_nodes += 1
        else:
            self.failed_nodes += 1

class PerformanceProfiler:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._enabled = False
            cls._instance._workflow_perf = {}
            cls._global_perf: Dict[str, NodePerformance] = {}
            cls._workflow_start_times: Dict[str, float] = {}
            cls._node_start_times: Dict[str, float] = {}
        return cls._instance
    
    def enable(self):
        self._enabled = True
    
    def disable(self):
        self._enabled = False
    
    def is_enabled(self) -> bool:
        return self._enabled
    
    def start_workflow(self, workflow_id: str):
        if not self._enabled:
            return
        
        self._workflow_start_times[workflow_id] = time.time()
        self._workflow_perf[workflow_id] = WorkflowPerformance(workflow_id=workflow_id)
    
    def start_node(self, workflow_id: str, node_id: str):
        if not self._enabled:
            return
        
        key = f"{workflow_id}:{node_id}"
        self._node_start_times[key] = time.time()
    
    def end_node(self, workflow_id: str, node_id: str, node_type: str, success: bool = True):
        if not self._enabled:
            return
        
        key = f"{workflow_id}:{node_id}"
        if key not in self._node_start_times:
            return
        
        duration = time.time() - self._node_start_times[key]
        del self._node_start_times[key]
        
        if workflow_id in self._workflow_perf:
            self._workflow_perf[workflow_id].total_nodes += 1
            self._workflow_perf[workflow_id].record_node_execution(node_type, duration, success)
        
        if node_type not in self._global_perf:
            self._global_perf[node_type] = NodePerformance(node_type=node_type)
        self._global_perf[node_type].total_executions += 1
        self._global_perf[node_type].total_duration += duration
        self._global_perf[node_type].durations.append(duration)
        self._global_perf[node_type].min_duration = min(self._global_perf[node_type].min_duration, duration)
        self._global_perf[node_type].max_duration = max(self._global_perf[node_type].max_duration, duration)
    
    def end_workflow(self, workflow_id: str) -> Optional[WorkflowPerformance]:
        if not self._enabled:
            return None
        
        if workflow_id not in self._workflow_start_times:
            return None
        
        if workflow_id in self._workflow_perf:
            self._workflow_perf[workflow_id].total_duration = time.time() - self._workflow_start_times[workflow_id]
            result = self._workflow_perf[workflow_id]
            del self._workflow_perf[workflow_id]
            del self._workflow_start_times[workflow_id]
            return result
        
        return None
    
    def get_global_stats(self) -> Dict[str, NodePerformance]:
        return dict(self._global_perf)
    
    def get_slowest_nodes(self, limit: int = 10) -> List[NodePerformance]:
        sorted_nodes = sorted(
            self._global_perf.values(),
            key=lambda x: x.avg_duration,
            reverse=True
        )
        return sorted_nodes[:limit]
    
    def get_hotspots(self, threshold_ms: float = 1000) -> List[NodePerformance]:
        return [
            perf for perf in self._global_perf.values()
            if perf.avg_duration * 1000 > threshold_ms
        ]
    
    def get_workflow_summary(self, workflow_id: str) -> Optional[str]:
        if workflow_id not in self._workflow_perf:
            return None
        
        perf = self._workflow_perf[workflow_id]
        lines = [
            f"Workflow: {workflow_id}",
            f"Total Nodes: {perf.total_nodes}",
            f"Completed: {perf.completed_nodes}",
            f"Failed: {perf.failed_nodes}",
            f"Total Duration: {perf.total_duration:.2f}s",
            "",
            "Node Performance:"
        ]
        
        for node_type, node_perf in sorted(
            perf.node_performance.items(),
            key=lambda x: x[1].total_duration,
            reverse=True
        ):
            lines.append(
                f"  {node_type}: {node_perf.total_executions}x, "
                f"avg={node_perf.avg_duration:.2f}s, "
                f"min={node_perf.min_duration:.2f}s, "
                f"max={node_perf.max_duration:.2f}s"
            )
        
        return "\n".join(lines)
    
    def reset_global_stats(self):
        self._global_perf.clear()

profiler = PerformanceProfiler()