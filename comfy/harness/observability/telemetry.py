"""
OpenTelemetry 埋点

支持分布式追踪和性能指标收集
"""

import time
import functools
from typing import Any, Dict, List, Optional, Callable
from contextlib import contextmanager


class Span:
    """追踪跨度"""
    
    def __init__(self, name: str, parent: Optional["Span"] = None, attributes: Optional[Dict] = None):
        self.name = name
        self.parent = parent
        self.attributes = attributes or {}
        self.start_time = time.time()
        self.end_time = 0.0
        self.status = "ok"
        self.events = []
    
    def set_attribute(self, key: str, value: Any):
        """设置属性"""
        self.attributes[key] = value
    
    def add_event(self, name: str, attributes: Optional[Dict] = None):
        """添加事件"""
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {}
        })
    
    def set_status(self, status: str, description: str = ""):
        """设置状态"""
        self.status = status
        if description:
            self.attributes["status_description"] = description
    
    def end(self):
        """结束跨度"""
        self.end_time = time.time()
    
    @property
    def duration_ms(self) -> float:
        """持续时间（毫秒）"""
        if self.end_time == 0:
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000


class Tracer:
    """追踪器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._enabled = False
            cls._instance._current_span = None
            cls._instance._spans = []
        return cls._instance
    
    def enable(self):
        """启用追踪"""
        self._enabled = True
    
    def disable(self):
        """禁用追踪"""
        self._enabled = False
    
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self._enabled
    
    def start_span(self, name: str, attributes: Optional[Dict] = None) -> Span:
        """开始新的跨度"""
        span = Span(name, parent=self._current_span, attributes=attributes)
        self._current_span = span
        self._spans.append(span)
        return span
    
    def end_span(self, span: Span):
        """结束跨度"""
        span.end()
        if span.parent:
            self._current_span = span.parent
        else:
            self._current_span = None
    
    @contextmanager
    def span(self, name: str, attributes: Optional[Dict] = None):
        """上下文管理器形式的跨度"""
        span = self.start_span(name, attributes)
        try:
            yield span
        except Exception as e:
            span.set_status("error", str(e))
            raise
        finally:
            self.end_span(span)
    
    def get_spans(self) -> List[Span]:
        """获取所有跨度"""
        return self._spans
    
    def clear_spans(self):
        """清空跨度"""
        self._spans.clear()


class Metric:
    """指标"""
    
    def __init__(self, name: str, description: str = "", unit: str = ""):
        self.name = name
        self.description = description
        self.unit = unit
        self.values = []
    
    def record(self, value: float, attributes: Optional[Dict] = None):
        """记录值"""
        self.values.append({
            "value": value,
            "timestamp": time.time(),
            "attributes": attributes or {}
        })
    
    def get_average(self) -> float:
        """获取平均值"""
        if not self.values:
            return 0.0
        return sum(v["value"] for v in self.values) / len(self.values)
    
    def get_latest(self) -> Optional[float]:
        """获取最新值"""
        if not self.values:
            return None
        return self.values[-1]["value"]


class MetricsCollector:
    """指标收集器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._enabled = False
            cls._instance._metrics: Dict[str, Metric] = {}
        return cls._instance
    
    def enable(self):
        """启用收集"""
        self._enabled = True
    
    def disable(self):
        """禁用收集"""
        self._enabled = False
    
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self._enabled
    
    def create_metric(self, name: str, description: str = "", unit: str = "") -> Metric:
        """创建指标"""
        metric = Metric(name, description, unit)
        self._metrics[name] = metric
        return metric
    
    def record(self, name: str, value: float, attributes: Optional[Dict] = None):
        """记录指标值"""
        if not self._enabled:
            return
        
        if name not in self._metrics:
            self._metrics[name] = Metric(name)
        
        self._metrics[name].record(value, attributes)
    
    def get_metric(self, name: str) -> Optional[Metric]:
        """获取指标"""
        return self._metrics.get(name)
    
    def get_all_metrics(self) -> Dict[str, Metric]:
        """获取所有指标"""
        return dict(self._metrics)
    
    def export_metrics(self) -> Dict[str, Any]:
        """导出指标"""
        return {
            name: {
                "name": metric.name,
                "description": metric.description,
                "unit": metric.unit,
                "average": metric.get_average(),
                "latest": metric.get_latest(),
                "count": len(metric.values)
            }
            for name, metric in self._metrics.items()
        }


class Telemetry:
    """
    OpenTelemetry 埋点管理器
    
    提供分布式追踪和性能指标收集功能
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tracer = Tracer()
            cls._instance._metrics = MetricsCollector()
            cls._instance._enabled = False
        return cls._instance
    
    def enable(self):
        """启用埋点"""
        self._enabled = True
        self._tracer.enable()
        self._metrics.enable()
    
    def disable(self):
        """禁用埋点"""
        self._enabled = False
        self._tracer.disable()
        self._metrics.disable()
    
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self._enabled
    
    @property
    def tracer(self) -> Tracer:
        """获取追踪器"""
        return self._tracer
    
    @property
    def metrics(self) -> MetricsCollector:
        """获取指标收集器"""
        return self._metrics
    
    def trace_method(self, name: Optional[str] = None):
        """方法追踪装饰器"""
        def decorator(func: Callable) -> Callable:
            span_name = name or func.__name__
            
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not self._enabled:
                    return func(*args, **kwargs)
                
                with self._tracer.span(span_name, {
                    "function": func.__name__,
                    "module": func.__module__
                }) as span:
                    try:
                        result = func(*args, **kwargs)
                        span.set_attribute("status", "success")
                        return result
                    except Exception as e:
                        span.set_status("error", str(e))
                        raise
            
            return wrapper
        return decorator
    
    def record_execution_time(self, name: str):
        """记录执行时间装饰器"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not self._enabled:
                    return func(*args, **kwargs)
                
                start = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start
                    self._metrics.record(f"{name}_duration", duration * 1000)
            
            return wrapper
        return decorator
    
    def record_counter(self, name: str, value: float = 1.0):
        """记录计数器"""
        if self._enabled:
            self._metrics.record(name, value)
    
    def record_gauge(self, name: str, value: float):
        """记录仪表值"""
        if self._enabled:
            self._metrics.record(name, value)
    
    def get_telemetry_data(self) -> Dict[str, Any]:
        """获取所有埋点数据"""
        return {
            "enabled": self._enabled,
            "metrics": self._metrics.export_metrics(),
            "spans": [
                {
                    "name": span.name,
                    "duration_ms": span.duration_ms,
                    "status": span.status,
                    "attributes": span.attributes,
                    "events": span.events
                }
                for span in self._tracer.get_spans()
            ]
        }


# 全局埋点实例
telemetry = Telemetry()
