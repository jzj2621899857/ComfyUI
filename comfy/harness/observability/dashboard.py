"""
监控看板

提供实时性能监控和可视化数据
"""

import json
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class DashboardMetric:
    """看板指标"""
    name: str
    value: float
    unit: str = ""
    timestamp: float = 0.0
    threshold: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
    
    @property
    def is_alert(self) -> bool:
        """是否触发告警"""
        if self.threshold is None:
            return False
        return self.value >= self.threshold


@dataclass
class DashboardPanel:
    """看板面板"""
    title: str
    metrics: List[DashboardMetric] = field(default_factory=list)
    chart_type: str = "line"  # line, bar, gauge
    refresh_interval: float = 5.0
    
    def add_metric(self, metric: DashboardMetric):
        """添加指标"""
        self.metrics.append(metric)
        # 保留最近 100 个数据点
        if len(self.metrics) > 100:
            self.metrics = self.metrics[-100:]
    
    def get_latest(self) -> Optional[DashboardMetric]:
        """获取最新指标"""
        if not self.metrics:
            return None
        return self.metrics[-1]
    
    def get_average(self) -> float:
        """获取平均值"""
        if not self.metrics:
            return 0.0
        return sum(m.value for m in self.metrics) / len(self.metrics)


class MonitoringDashboard:
    """
    监控看板
    
    提供实时性能监控和可视化数据
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._enabled = False
            cls._instance._panels: Dict[str, DashboardPanel] = {}
            cls._instance._alerts: List[Dict] = []
            cls._instance._max_alerts = 100
        return cls._instance
    
    def enable(self):
        """启用看板"""
        self._enabled = True
    
    def disable(self):
        """禁用看板"""
        self._enabled = False
    
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self._enabled
    
    def create_panel(self, panel_id: str, title: str, chart_type: str = "line") -> DashboardPanel:
        """创建面板"""
        panel = DashboardPanel(title=title, chart_type=chart_type)
        self._panels[panel_id] = panel
        return panel
    
    def get_panel(self, panel_id: str) -> Optional[DashboardPanel]:
        """获取面板"""
        return self._panels.get(panel_id)
    
    def update_metric(self, panel_id: str, metric_name: str, value: float, unit: str = "", threshold: Optional[float] = None):
        """更新指标"""
        if not self._enabled:
            return
        
        if panel_id not in self._panels:
            return
        
        metric = DashboardMetric(
            name=metric_name,
            value=value,
            unit=unit,
            threshold=threshold
        )
        
        self._panels[panel_id].add_metric(metric)
        
        # 检查告警
        if metric.is_alert:
            self._add_alert(panel_id, metric)
    
    def _add_alert(self, panel_id: str, metric: DashboardMetric):
        """添加告警"""
        alert = {
            "panel_id": panel_id,
            "metric_name": metric.name,
            "value": metric.value,
            "threshold": metric.threshold,
            "timestamp": metric.timestamp,
            "message": f"{metric.name} 超过阈值: {metric.value:.2f} >= {metric.threshold:.2f}"
        }
        
        self._alerts.append(alert)
        
        # 限制告警数量
        if len(self._alerts) > self._max_alerts:
            self._alerts = self._alerts[-self._max_alerts:]
    
    def get_alerts(self, limit: int = 10) -> List[Dict]:
        """获取告警"""
        return self._alerts[-limit:]
    
    def clear_alerts(self):
        """清空告警"""
        self._alerts.clear()
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取看板数据"""
        return {
            "enabled": self._enabled,
            "timestamp": time.time(),
            "panels": {
                panel_id: {
                    "title": panel.title,
                    "chart_type": panel.chart_type,
                    "latest": {
                        "name": panel.get_latest().name if panel.get_latest() else None,
                        "value": panel.get_latest().value if panel.get_latest() else None,
                        "unit": panel.get_latest().unit if panel.get_latest() else None,
                    },
                    "average": panel.get_average(),
                    "data_points": len(panel.metrics)
                }
                for panel_id, panel in self._panels.items()
            },
            "alerts": self.get_alerts(5),
            "alert_count": len(self._alerts)
        }
    
    def export_html(self) -> str:
        """导出 HTML 看板"""
        data = self.get_dashboard_data()
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>ComfyUI Harness 监控看板</title>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: #333;
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .panel {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .panel-title {{
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
        }}
        .metric {{
            display: inline-block;
            margin: 10px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 4px;
            min-width: 150px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
        }}
        .metric-label {{
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }}
        .alert {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 4px;
            padding: 10px;
            margin: 5px 0;
        }}
        .alert-critical {{
            background: #f8d7da;
            border-color: #dc3545;
        }}
        .status {{
            display: inline-block;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }}
        .status-enabled {{
            background: #d4edda;
            color: #155724;
        }}
        .status-disabled {{
            background: #f8d7da;
            color: #721c24;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>ComfyUI Harness 监控看板</h1>
        <span class="status {'status-enabled' if data['enabled'] else 'status-disabled'}">
            {'运行中' if data['enabled'] else '已停止'}
        </span>
        <span style="margin-left: 20px; color: #ccc;">
            更新时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['timestamp']))}
        </span>
    </div>
"""
        
        # 面板
        for panel_id, panel_data in data['panels'].items():
            html += f"""
    <div class="panel">
        <div class="panel-title">{panel_data['title']}</div>
        <div class="metric">
            <div class="metric-value">{panel_data['latest']['value']:.2f if panel_data['latest']['value'] else 'N/A'}</div>
            <div class="metric-label">当前值 {panel_data['latest']['unit'] or ''}</div>
        </div>
        <div class="metric">
            <div class="metric-value">{panel_data['average']:.2f}</div>
            <div class="metric-label">平均值</div>
        </div>
        <div class="metric">
            <div class="metric-value">{panel_data['data_points']}</div>
            <div class="metric-label">数据点</div>
        </div>
    </div>
"""
        
        # 告警
        if data['alerts']:
            html += """
    <div class="panel">
        <div class="panel-title">最近告警</div>
"""
            for alert in data['alerts']:
                html += f"""
        <div class="alert {'alert-critical' if alert['value'] > alert['threshold'] * 1.5 else ''}">
            <strong>{alert['metric_name']}</strong>: {alert['message']}
            <br><small>{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert['timestamp']))}</small>
        </div>
"""
            html += "    </div>"
        
        html += """
</body>
</html>
"""
        
        return html
    
    def save_html(self, filepath: str):
        """保存 HTML 看板到文件"""
        html = self.export_html()
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)


# 全局看板实例
dashboard = MonitoringDashboard()
