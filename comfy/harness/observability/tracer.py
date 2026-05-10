"""
执行追踪器 - 记录每个节点的输入输出快照
"""

import time
import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class NodeTrace:
    node_id: str
    node_type: str
    start_time: float
    end_time: float = 0.0
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    status: str = "pending"
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

@dataclass
class WorkflowTrace:
    workflow_id: str
    start_time: float
    end_time: float = 0.0
    nodes: List[NodeTrace] = field(default_factory=list)
    status: str = "running"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

class ExecutionTracer:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._active_traces = {}
            cls._instance._trace_history = []
            cls._instance._enabled = False
        return cls._instance
    
    def enable(self):
        self._enabled = True
    
    def disable(self):
        self._enabled = False
    
    def is_enabled(self) -> bool:
        return self._enabled
    
    def start_workflow_trace(self, workflow_id: str, metadata: Optional[Dict] = None) -> str:
        if not self._enabled:
            return workflow_id
        
        trace = WorkflowTrace(
            workflow_id=workflow_id,
            start_time=time.time(),
            metadata=metadata or {}
        )
        self._active_traces[workflow_id] = trace
        return workflow_id
    
    def start_node_trace(self, workflow_id: str, node_id: str, node_type: str, inputs: Dict[str, Any]):
        if not self._enabled or workflow_id not in self._active_traces:
            return
        
        trace = self._active_traces[workflow_id]
        node_trace = NodeTrace(
            node_id=str(node_id),
            node_type=node_type,
            start_time=time.time(),
            inputs=self._serialize_inputs(inputs)
        )
        trace.nodes.append(node_trace)
    
    def end_node_trace(self, workflow_id: str, node_id: str, outputs: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        if not self._enabled or workflow_id not in self._active_traces:
            return
        
        trace = self._active_traces[workflow_id]
        for node_trace in trace.nodes:
            if node_trace.node_id == str(node_id) and node_trace.status == "pending":
                node_trace.end_time = time.time()
                node_trace.outputs = self._serialize_outputs(outputs or {})
                node_trace.error = error
                node_trace.status = "failed" if error else "completed"
                break
    
    def end_workflow_trace(self, workflow_id: str, status: str = "completed"):
        if not self._enabled or workflow_id not in self._active_traces:
            return
        
        trace = self._active_traces[workflow_id]
        trace.end_time = time.time()
        trace.status = status
        
        self._trace_history.append(trace)
        del self._active_traces[workflow_id]
    
    def _serialize_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        for key, value in inputs.items():
            result[key] = self._serialize_value(value)
        return result
    
    def _serialize_outputs(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        for key, value in outputs.items():
            result[key] = self._serialize_value(value)
        return result
    
    def _serialize_value(self, value: Any) -> Any:
        if value is None:
            return None
        
        try:
            import torch
            if isinstance(value, torch.Tensor):
                return {
                    "__type__": "torch.Tensor",
                    "shape": list(value.shape),
                    "dtype": str(value.dtype),
                    "device": str(value.device),
                    "requires_grad": value.requires_grad
                }
        except ImportError:
            pass
        
        try:
            import numpy as np
            if isinstance(value, np.ndarray):
                return {
                    "__type__": "numpy.ndarray",
                    "shape": list(value.shape),
                    "dtype": str(value.dtype)
                }
        except ImportError:
            pass
        
        if isinstance(value, (int, float, str, bool)):
            return value
        
        if isinstance(value, (list, tuple)):
            return [self._serialize_value(v) for v in value]
        
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        
        return str(value)
    
    def get_trace(self, workflow_id: str) -> Optional[WorkflowTrace]:
        if workflow_id in self._active_traces:
            return self._active_traces[workflow_id]
        
        for trace in self._trace_history:
            if trace.workflow_id == workflow_id:
                return trace
        
        return None
    
    def get_recent_traces(self, limit: int = 10) -> List[WorkflowTrace]:
        return self._trace_history[-limit:]
    
    def export_trace(self, workflow_id: str, filepath: str) -> bool:
        trace = self.get_trace(workflow_id)
        if not trace:
            return False
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    "workflow_id": trace.workflow_id,
                    "start_time": trace.start_time,
                    "end_time": trace.end_time,
                    "duration": trace.duration,
                    "status": trace.status,
                    "metadata": trace.metadata,
                    "nodes": [
                        {
                            "node_id": n.node_id,
                            "node_type": n.node_type,
                            "start_time": n.start_time,
                            "end_time": n.end_time,
                            "duration": n.duration,
                            "inputs": n.inputs,
                            "outputs": n.outputs,
                            "error": n.error,
                            "status": n.status
                        } for n in trace.nodes
                    ]
                }, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False
    
    def clear_history(self):
        self._trace_history.clear()

tracer = ExecutionTracer()