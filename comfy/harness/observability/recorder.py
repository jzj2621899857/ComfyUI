"""
黑匣子记录器

生成可回放的执行轨迹，用于异常回溯和效果归因
"""

import json
import time
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class TensorSnapshot:
    """Tensor 快照"""
    shape: List[int]
    dtype: str
    device: str
    min_val: float
    max_val: float
    mean_val: float
    std_val: float
    has_nan: bool
    has_inf: bool
    
    @classmethod
    def from_tensor(cls, tensor: Any) -> "TensorSnapshot":
        """从 tensor 创建快照"""
        try:
            import torch
            if isinstance(tensor, torch.Tensor):
                return cls(
                    shape=list(tensor.shape),
                    dtype=str(tensor.dtype),
                    device=str(tensor.device),
                    min_val=tensor.min().item(),
                    max_val=tensor.max().item(),
                    mean_val=tensor.mean().item(),
                    std_val=tensor.std().item(),
                    has_nan=torch.isnan(tensor).any().item(),
                    has_inf=torch.isinf(tensor).any().item()
                )
        except ImportError:
            pass
        
        try:
            import numpy as np
            if isinstance(tensor, np.ndarray):
                return cls(
                    shape=list(tensor.shape),
                    dtype=str(tensor.dtype),
                    device="cpu",
                    min_val=float(tensor.min()),
                    max_val=float(tensor.max()),
                    mean_val=float(tensor.mean()),
                    std_val=float(tensor.std()),
                    has_nan=np.isnan(tensor).any(),
                    has_inf=np.isinf(tensor).any()
                )
        except ImportError:
            pass
        
        return None


@dataclass
class NodeExecutionRecord:
    """节点执行记录"""
    node_id: str
    node_type: str
    start_time: float
    end_time: float
    duration_ms: float
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    input_snapshots: Dict[str, Optional[TensorSnapshot]] = field(default_factory=dict)
    output_snapshots: Dict[str, Optional[TensorSnapshot]] = field(default_factory=dict)
    memory_peak_mb: float = 0.0
    error: Optional[str] = None
    status: str = "pending"


@dataclass
class WorkflowExecutionRecord:
    """工作流执行记录"""
    record_id: str
    workflow_id: str
    workflow_name: str
    start_time: float
    end_time: float
    duration_ms: float
    node_records: List[NodeExecutionRecord] = field(default_factory=list)
    total_nodes: int = 0
    completed_nodes: int = 0
    failed_nodes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "running"


class ExecutionRecorder:
    """
    执行记录器（黑匣子）
    
    记录完整的执行轨迹，支持：
    - 异常回溯
    - 效果归因
    - 执行回放
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._enabled = False
            cls._instance._storage_path = None
            cls._instance._current_record = None
            cls._instance._records_history = []
            cls._instance._max_history = 100
        return cls._instance
    
    def enable(self, storage_path: Optional[str] = None):
        """启用记录器"""
        self._enabled = True
        if storage_path:
            self._storage_path = storage_path
            os.makedirs(storage_path, exist_ok=True)
    
    def disable(self):
        """禁用记录器"""
        self._enabled = False
    
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self._enabled
    
    def start_recording(self, workflow_id: str, workflow_name: str = "", metadata: Optional[Dict] = None) -> str:
        """开始记录工作流执行"""
        if not self._enabled:
            return ""
        
        record_id = f"{workflow_id}_{int(time.time() * 1000)}"
        
        self._current_record = WorkflowExecutionRecord(
            record_id=record_id,
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            start_time=time.time(),
            end_time=0.0,
            duration_ms=0.0,
            metadata=metadata or {}
        )
        
        return record_id
    
    def start_node_execution(self, node_id: str, node_type: str, inputs: Dict[str, Any]):
        """开始记录节点执行"""
        if not self._enabled or not self._current_record:
            return
        
        # 创建输入快照
        input_snapshots = {}
        for name, value in inputs.items():
            snapshot = self._create_snapshot(value)
            if snapshot:
                input_snapshots[name] = snapshot
        
        node_record = NodeExecutionRecord(
            node_id=node_id,
            node_type=node_type,
            start_time=time.time(),
            end_time=0.0,
            duration_ms=0.0,
            inputs=self._serialize_values(inputs),
            input_snapshots=input_snapshots,
            memory_peak_mb=self._get_memory_usage()
        )
        
        self._current_record.node_records.append(node_record)
    
    def end_node_execution(self, node_id: str, outputs: Dict[str, Any], error: Optional[str] = None):
        """结束节点执行记录"""
        if not self._enabled or not self._current_record:
            return
        
        # 找到对应的节点记录
        for record in reversed(self._current_record.node_records):
            if record.node_id == node_id and record.status == "pending":
                record.end_time = time.time()
                record.duration_ms = (record.end_time - record.start_time) * 1000
                record.outputs = self._serialize_values(outputs)
                record.error = error
                record.status = "failed" if error else "completed"
                
                # 创建输出快照
                for name, value in outputs.items():
                    snapshot = self._create_snapshot(value)
                    if snapshot:
                        record.output_snapshots[name] = snapshot
                
                # 更新内存峰值
                record.memory_peak_mb = max(record.memory_peak_mb, self._get_memory_usage())
                
                # 更新工作流统计
                self._current_record.total_nodes += 1
                if error:
                    self._current_record.failed_nodes += 1
                else:
                    self._current_record.completed_nodes += 1
                
                break
    
    def end_recording(self, status: str = "completed"):
        """结束记录"""
        if not self._enabled or not self._current_record:
            return
        
        self._current_record.end_time = time.time()
        self._current_record.duration_ms = (self._current_record.end_time - self._current_record.start_time) * 1000
        self._current_record.status = status
        
        # 保存到历史
        self._records_history.append(self._current_record)
        
        # 限制历史记录数量
        if len(self._records_history) > self._max_history:
            self._records_history = self._records_history[-self._max_history:]
        
        # 保存到文件
        if self._storage_path:
            self._save_record(self._current_record)
        
        self._current_record = None
    
    def _create_snapshot(self, value: Any) -> Optional[TensorSnapshot]:
        """创建值快照"""
        return TensorSnapshot.from_tensor(value)
    
    def _serialize_values(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """序列化值"""
        serialized = {}
        for name, value in values.items():
            serialized[name] = self._serialize_value(value)
        return serialized
    
    def _serialize_value(self, value: Any) -> Any:
        """序列化单个值"""
        if value is None:
            return None
        
        # Tensor 快照
        snapshot = TensorSnapshot.from_tensor(value)
        if snapshot:
            return {
                "__type__": "tensor_snapshot",
                **asdict(snapshot)
            }
        
        # 基本类型
        if isinstance(value, (int, float, str, bool)):
            return value
        
        # 列表
        if isinstance(value, list):
            return [self._serialize_value(v) for v in value]
        
        # 字典
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        
        # 其他类型转为字符串
        return str(value)
    
    def _get_memory_usage(self) -> float:
        """获取当前内存使用（MB）"""
        try:
            import torch
            if torch.cuda.is_available():
                return torch.cuda.memory_allocated() / 1024 / 1024
        except ImportError:
            pass
        
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            pass
        
        return 0.0
    
    def _save_record(self, record: WorkflowExecutionRecord):
        """保存记录到文件"""
        if not self._storage_path:
            return
        
        filepath = os.path.join(self._storage_path, f"{record.record_id}.json")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self._record_to_dict(record), f, indent=2, ensure_ascii=False)
    
    def _record_to_dict(self, record: WorkflowExecutionRecord) -> Dict:
        """将记录转为字典"""
        return {
            "record_id": record.record_id,
            "workflow_id": record.workflow_id,
            "workflow_name": record.workflow_name,
            "start_time": record.start_time,
            "end_time": record.end_time,
            "duration_ms": record.duration_ms,
            "total_nodes": record.total_nodes,
            "completed_nodes": record.completed_nodes,
            "failed_nodes": record.failed_nodes,
            "status": record.status,
            "metadata": record.metadata,
            "node_records": [
                {
                    "node_id": nr.node_id,
                    "node_type": nr.node_type,
                    "start_time": nr.start_time,
                    "end_time": nr.end_time,
                    "duration_ms": nr.duration_ms,
                    "inputs": nr.inputs,
                    "outputs": nr.outputs,
                    "input_snapshots": {k: asdict(v) if v else None for k, v in nr.input_snapshots.items()},
                    "output_snapshots": {k: asdict(v) if v else None for k, v in nr.output_snapshots.items()},
                    "memory_peak_mb": nr.memory_peak_mb,
                    "error": nr.error,
                    "status": nr.status
                }
                for nr in record.node_records
            ]
        }
    
    def get_record(self, record_id: str) -> Optional[WorkflowExecutionRecord]:
        """获取记录"""
        for record in self._records_history:
            if record.record_id == record_id:
                return record
        
        # 尝试从文件加载
        if self._storage_path:
            filepath = os.path.join(self._storage_path, f"{record_id}.json")
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return self._dict_to_record(data)
        
        return None
    
    def _dict_to_record(self, data: Dict) -> WorkflowExecutionRecord:
        """从字典创建记录"""
        node_records = []
        for nr_data in data.get("node_records", []):
            node_record = NodeExecutionRecord(
                node_id=nr_data["node_id"],
                node_type=nr_data["node_type"],
                start_time=nr_data["start_time"],
                end_time=nr_data["end_time"],
                duration_ms=nr_data["duration_ms"],
                inputs=nr_data.get("inputs", {}),
                outputs=nr_data.get("outputs", {}),
                memory_peak_mb=nr_data.get("memory_peak_mb", 0.0),
                error=nr_data.get("error"),
                status=nr_data.get("status", "completed")
            )
            node_records.append(node_record)
        
        return WorkflowExecutionRecord(
            record_id=data["record_id"],
            workflow_id=data["workflow_id"],
            workflow_name=data.get("workflow_name", ""),
            start_time=data["start_time"],
            end_time=data["end_time"],
            duration_ms=data["duration_ms"],
            node_records=node_records,
            total_nodes=data.get("total_nodes", 0),
            completed_nodes=data.get("completed_nodes", 0),
            failed_nodes=data.get("failed_nodes", 0),
            metadata=data.get("metadata", {}),
            status=data.get("status", "completed")
        )
    
    def get_recent_records(self, limit: int = 10) -> List[WorkflowExecutionRecord]:
        """获取最近的记录"""
        return self._records_history[-limit:]
    
    def analyze_failure(self, record_id: str) -> Dict[str, Any]:
        """分析失败原因"""
        record = self.get_record(record_id)
        if not record:
            return {"error": "记录不存在"}
        
        analysis = {
            "record_id": record_id,
            "workflow_id": record.workflow_id,
            "status": record.status,
            "total_nodes": record.total_nodes,
            "failed_nodes": record.failed_nodes,
            "failure_points": [],
            "recommendations": []
        }
        
        for node_record in record.node_records:
            if node_record.status == "failed":
                failure_point = {
                    "node_id": node_record.node_id,
                    "node_type": node_record.node_type,
                    "error": node_record.error,
                    "memory_peak_mb": node_record.memory_peak_mb,
                    "duration_ms": node_record.duration_ms
                }
                analysis["failure_points"].append(failure_point)
                
                # 生成建议
                if node_record.memory_peak_mb > 8000:  # 超过 8GB
                    analysis["recommendations"].append(
                        f"节点 {node_record.node_id} 内存使用过高，建议降低批次大小"
                    )
                
                if "out of memory" in str(node_record.error).lower():
                    analysis["recommendations"].append(
                        "显存不足错误，建议启用自动重试机制或降低分辨率"
                    )
        
        return analysis
    
    def clear_history(self):
        """清空历史记录"""
        self._records_history.clear()


# 全局记录器实例
recorder = ExecutionRecorder()
