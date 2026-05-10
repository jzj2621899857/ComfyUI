"""
动态调度器

根据资源预估动态调整执行顺序和并行度
"""

import heapq
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum


class Priority(Enum):
    """任务优先级"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class Task:
    """执行任务"""
    task_id: str
    node_id: str
    node_type: str
    priority: Priority = Priority.NORMAL
    estimated_memory_mb: float = 0.0
    estimated_time_ms: float = 0.0
    dependencies: Set[str] = field(default_factory=set)
    status: str = "pending"  # pending, running, completed, failed
    
    def __lt__(self, other: "Task") -> bool:
        """用于优先级队列比较"""
        return self.priority.value < other.priority.value


@dataclass
class ResourceSnapshot:
    """资源快照"""
    available_memory_mb: float
    available_compute: float
    active_tasks: int
    timestamp: float


class DynamicScheduler:
    """
    动态调度器
    
    根据资源预估动态调整执行顺序和并行度
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._enabled = False
            cls._instance._task_queue: List[Task] = []
            cls._instance._running_tasks: Dict[str, Task] = {}
            cls._instance._completed_tasks: Dict[str, Task] = {}
            cls._instance._max_parallel = 4
            cls._instance._memory_threshold = 0.8  # 80% 内存使用率阈值
        return cls._instance
    
    def enable(self, max_parallel: int = 4):
        """启用调度器"""
        self._enabled = True
        self._max_parallel = max_parallel
    
    def disable(self):
        """禁用调度器"""
        self._enabled = False
    
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self._enabled
    
    def submit_task(self, task: Task) -> bool:
        """提交任务"""
        if not self._enabled:
            return False
        
        heapq.heappush(self._task_queue, task)
        return True
    
    def get_next_task(self, available_memory_mb: float) -> Optional[Task]:
        """获取下一个可执行的任务"""
        if not self._enabled:
            return None
        
        # 检查并行度限制
        if len(self._running_tasks) >= self._max_parallel:
            return None
        
        # 查找满足依赖和资源条件的任务
        temp_queue = []
        selected_task = None
        
        while self._task_queue:
            task = heapq.heappop(self._task_queue)
            
            # 检查依赖是否完成
            if not self._check_dependencies(task):
                temp_queue.append(task)
                continue
            
            # 检查资源是否足够
            if task.estimated_memory_mb > available_memory_mb:
                temp_queue.append(task)
                continue
            
            selected_task = task
            break
        
        # 将未选中的任务放回队列
        for task in temp_queue:
            heapq.heappush(self._task_queue, task)
        
        if selected_task:
            selected_task.status = "running"
            self._running_tasks[selected_task.task_id] = selected_task
        
        return selected_task
    
    def _check_dependencies(self, task: Task) -> bool:
        """检查任务依赖是否完成"""
        for dep in task.dependencies:
            if dep not in self._completed_tasks:
                return False
        return True
    
    def complete_task(self, task_id: str, success: bool = True):
        """标记任务完成"""
        if task_id in self._running_tasks:
            task = self._running_tasks.pop(task_id)
            task.status = "completed" if success else "failed"
            self._completed_tasks[task_id] = task
    
    def get_scheduling_plan(self, workflow: Dict[str, Any]) -> List[List[str]]:
        """
        生成调度计划
        
        Returns:
            分层调度计划，每层包含可并行执行的节点 ID
        """
        if not self._enabled:
            return []
        
        nodes = workflow.get("nodes", {})
        connections = workflow.get("connections", [])
        
        # 构建依赖图
        dependencies: Dict[str, Set[str]] = {node_id: set() for node_id in nodes}
        
        for conn in connections:
            target = conn.get("target_node")
            source = conn.get("source_node")
            if target and source:
                target_id = str(target)
                source_id = str(source)
                if target_id in dependencies:
                    dependencies[target_id].add(source_id)
        
        # 拓扑排序分层
        plan = []
        remaining = set(nodes.keys())
        completed = set()
        
        while remaining:
            layer = []
            for node_id in list(remaining):
                deps = dependencies.get(node_id, set())
                if deps.issubset(completed):
                    layer.append(node_id)
            
            if not layer:
                # 存在循环依赖
                break
            
            plan.append(layer)
            completed.update(layer)
            remaining -= set(layer)
        
        return plan
    
    def optimize_order(self, tasks: List[Task]) -> List[Task]:
        """优化任务执行顺序"""
        if not self._enabled:
            return tasks
        
        # 按优先级和时间排序
        # 优先级高的先执行，同优先级下执行时间短的先执行
        sorted_tasks = sorted(
            tasks,
            key=lambda t: (t.priority.value, t.estimated_time_ms)
        )
        
        return sorted_tasks
    
    def get_stats(self) -> Dict[str, Any]:
        """获取调度统计"""
        return {
            "enabled": self._enabled,
            "pending_tasks": len(self._task_queue),
            "running_tasks": len(self._running_tasks),
            "completed_tasks": len(self._completed_tasks),
            "max_parallel": self._max_parallel,
            "memory_threshold": self._memory_threshold
        }
    
    def clear(self):
        """清空所有任务"""
        self._task_queue.clear()
        self._running_tasks.clear()
        self._completed_tasks.clear()


# 全局调度器实例
scheduler = DynamicScheduler()
