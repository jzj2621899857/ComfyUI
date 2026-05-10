"""
Harness 前端控制面板
"""

import json
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class DashboardMetric:
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
        if self.threshold is None:
            return False
        return self.value >= self.threshold


class MonitoringDashboard:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._enabled = False
            cls._instance._panels: Dict[str, Any] = {}
            cls._instance._alerts = []
        return cls._instance
    
    def enable(self):
        self._enabled = True
    
    def disable(self):
        self._enabled = False
    
    def is_enabled(self) -> bool:
        return self._enabled
    
    def update_metric(self, panel_id: str, metric_name: str, value: float, unit: str = "", threshold: float = None):
        if panel_id not in self._panels:
            self._panels[panel_id] = {
                "title": panel_id.replace("_", " ").title(),
                "metrics": [],
                "chart_type": "line"
            }
        
        metric = {
            "name": metric_name,
            "value": value,
            "unit": unit,
            "timestamp": time.time(),
            "threshold": threshold,
            "is_alert": threshold is not None and value >= threshold
        }
        
        self._panels[panel_id]["metrics"].append(metric)
        if len(self._panels[panel_id]["metrics"]) > 100:
            self._panels[panel_id]["metrics"] = self._panels[panel_id]["metrics"][-100:]
    
    def get_panel(self, panel_id: str) -> Optional[Dict]:
        return self._panels.get(panel_id)
    
    def get_all_panels(self) -> Dict:
        return self._panels
    
    def get_alerts(self) -> List[Dict]:
        alerts = []
        for panel_id, panel in self._panels.items():
            for metric in panel.get("metrics", []):
                if metric.get("is_alert"):
                    alerts.append({
                        "panel": panel.get("title", panel_id),
                        "metric": metric.get("name"),
                        "value": metric.get("value"),
                        "unit": metric.get("unit"),
                        "timestamp": metric.get("timestamp")
                    })
        return alerts[:100]


def generate_dashboard_html() -> str:
    """生成仪表盘 HTML"""
    dashboard = MonitoringDashboard()
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ComfyUI Harness Control Panel</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; color: #fff; }}
        .header {{ background: rgba(255,255,255,0.05); padding: 20px; border-bottom: 1px solid rgba(255,255,255,0.1); }}
        .header h1 {{ font-size: 24px; font-weight: 600; }}
        .header p {{ color: #888; margin-top: 5px; }}
        .container {{ padding: 20px; max-width: 1400px; margin: 0 auto; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .stat-card {{ background: rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; border: 1px solid rgba(255,255,255,0.1); }}
        .stat-card.success {{ border-color: #00ff88; }}
        .stat-card.warning {{ border-color: #ffaa00; }}
        .stat-card.danger {{ border-color: #ff4444; }}
        .stat-label {{ color: #888; font-size: 14px; }}
        .stat-value {{ font-size: 32px; font-weight: 700; margin: 10px 0; }}
        .stat-unit {{ color: #888; font-size: 14px; }}
        .panels-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }}
        .panel {{ background: rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; border: 1px solid rgba(255,255,255,0.1); }}
        .panel-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
        .panel-title {{ font-size: 16px; font-weight: 600; }}
        .panel-status {{ padding: 4px 12px; border-radius: 20px; font-size: 12px; }}
        .panel-status.online {{ background: rgba(0,255,136,0.2); color: #00ff88; }}
        .panel-status.offline {{ background: rgba(255,68,68,0.2); color: #ff4444; }}
        .metrics-list {{ max-height: 300px; overflow-y: auto; }}
        .metric-row {{ display: flex; justify-content: space-between; padding: 10px; background: rgba(255,255,255,0.03); border-radius: 8px; margin-bottom: 8px; }}
        .metric-name {{ color: #aaa; }}
        .metric-value {{ font-weight: 600; }}
        .alert {{ background: rgba(255,68,68,0.1); border-left: 3px solid #ff4444; padding: 10px; margin-bottom: 8px; }}
        .btn {{ padding: 10px 20px; border-radius: 8px; border: none; cursor: pointer; font-size: 14px; font-weight: 600; }}
        .btn-primary {{ background: linear-gradient(135deg, #00ff88, #00cc6a); color: #000; }}
        .btn-danger {{ background: linear-gradient(135deg, #ff4444, #cc3333); color: #fff; }}
        .btn-secondary {{ background: rgba(255,255,255,0.1); color: #fff; border: 1px solid rgba(255,255,255,0.2); }}
        .api-section {{ background: rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; margin-top: 20px; }}
        pre {{ background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; overflow-x: auto; font-size: 13px; }}
        .status-dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 8px; }}
        .status-dot.green {{ background: #00ff88; box-shadow: 0 0 10px #00ff88; }}
        .status-dot.red {{ background: #ff4444; }}
        .status-dot.yellow {{ background: #ffaa00; }}
        @keyframes pulse {{ 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }}
        .status-dot.green {{ animation: pulse 2s infinite; }}
    </style>
</head>
<body>
    <div class="header">
        <h1><span class="status-dot green"></span> ComfyUI Harness Control Panel</h1>
        <p>Execution Engine with Fuse Box Protection | Type Safety | Observability | Resource Management | Self-Evolution</p>
    </div>
    
    <div class="container">
        <div class="stats-grid" id="stats-grid">
            <div class="stat-card success">
                <div class="stat-label">Harness Status</div>
                <div class="stat-value" id="harness-status">Enabled</div>
                <div class="stat-unit">All modules active</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Active Modules</div>
                <div class="stat-value" id="active-modules">6</div>
                <div class="stat-unit">of 6 available</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">API Status</div>
                <div class="stat-value" id="api-status">Online</div>
                <div class="stat-unit">Ready for requests</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Alerts</div>
                <div class="stat-value" id="alert-count">0</div>
                <div class="stat-unit">No active alerts</div>
            </div>
        </div>

        <div class="panels-grid" id="panels-grid">
            <div class="panel">
                <div class="panel-header">
                    <span class="panel-title">Execution Engine</span>
                    <span class="panel-status online">Active</span>
                </div>
                <div class="metrics-list" id="execution-metrics">
                    <div class="metric-row">
                        <span class="metric-name">Fuse Box</span>
                        <span class="metric-value">✓ Enabled</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-name">Fallback</span>
                        <span class="metric-value">✓ Enabled</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-name">Retry</span>
                        <span class="metric-value">✓ Enabled</span>
                    </div>
                </div>
            </div>

            <div class="panel">
                <div class="panel-header">
                    <span class="panel-title">Type System</span>
                    <span class="panel-status online">Active</span>
                </div>
                <div class="metrics-list" id="types-metrics">
                    <div class="metric-row">
                        <span class="metric-name">Contract Validation</span>
                        <span class="metric-value">✓ Enabled</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-name">Static Checking</span>
                        <span class="metric-value">✓ Enabled</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-name">Registry</span>
                        <span class="metric-value">✓ Active</span>
                    </div>
                </div>
            </div>

            <div class="panel">
                <div class="panel-header">
                    <span class="panel-title">Observability</span>
                    <span class="panel-status online">Active</span>
                </div>
                <div class="metrics-list" id="observability-metrics">
                    <div class="metric-row">
                        <span class="metric-name">Tracing</span>
                        <span class="metric-value">✓ Enabled</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-name">Recorder</span>
                        <span class="metric-value">✓ Enabled</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-name">Telemetry</span>
                        <span class="metric-value">✓ Enabled</span>
                    </div>
                </div>
            </div>

            <div class="panel">
                <div class="panel-header">
                    <span class="panel-title">Resource Management</span>
                    <span class="panel-status online">Active</span>
                </div>
                <div class="metrics-list" id="resource-metrics">
                    <div class="metric-row">
                        <span class="metric-name">Estimator</span>
                        <span class="metric-value">✓ Enabled</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-name">Scheduler</span>
                        <span class="metric-value">✓ Enabled</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-name">Adaptive Precision</span>
                        <span class="metric-value">✓ Enabled</span>
                    </div>
                </div>
            </div>

            <div class="panel">
                <div class="panel-header">
                    <span class="panel-title">Self-Evolution</span>
                    <span class="panel-status offline">Disabled</span>
                </div>
                <div class="metrics-list" id="evolution-metrics">
                    <div class="metric-row">
                        <span class="metric-name">Versioning</span>
                        <span class="metric-value">✗ Disabled</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-name">Canary Deploy</span>
                        <span class="metric-value">✗ Disabled</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-name">AI Referee</span>
                        <span class="metric-value">✗ Disabled</span>
                    </div>
                </div>
            </div>

            <div class="panel">
                <div class="panel-header">
                    <span class="panel-title">Alerts</span>
                    <span class="panel-status" id="alerts-status">Normal</span>
                </div>
                <div class="metrics-list" id="alerts-list">
                    <div style="text-align: center; color: #666; padding: 20px;">No active alerts</div>
                </div>
            </div>
        </div>

        <div class="api-section">
            <h3 style="margin-bottom: 15px;">API Endpoints</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px;">
                <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px;">
                    <div style="font-weight: 600; margin-bottom: 5px;">Status</div>
                    <code style="color: #00ff88;">GET /api/harness/status</code>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px;">
                    <div style="font-weight: 600; margin-bottom: 5px;">Metrics</div>
                    <code style="color: #00ff88;">GET /api/harness/metrics</code>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px;">
                    <div style="font-weight: 600; margin-bottom: 5px;">Enable</div>
                    <code style="color: #ffaa00;">POST /api/harness/enable</code>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px;">
                    <div style="font-weight: 600; margin-bottom: 5px;">Canary Start</div>
                    <code style="color: #ffaa00;">POST /api/harness/canary/start</code>
                </div>
            </div>
        </div>
    </div>

    <script>
        async function fetchStatus() {
            try {
                const response = await fetch('/api/harness/status');
                const data = await response.json();
                updateDashboard(data);
            } catch (error) {
                document.getElementById('harness-status').textContent = 'Offline';
                document.querySelector('.stat-card.success').className = 'stat-card danger';
            }
        }

        function updateDashboard(data) {
            if (data.enabled) {
                document.getElementById('harness-status').textContent = 'Enabled';
            } else {
                document.getElementById('harness-status').textContent = 'Disabled';
                document.querySelector('.stat-card.success').className = 'stat-card warning';
            }
            
            const components = data.components || {};
            const activeCount = Object.values(components).filter(v => v).length;
            document.getElementById('active-modules').textContent = activeCount;
            
            if (components.fuse_box === false) {
                document.querySelector('#execution-metrics .metric-row:nth-child(1) .metric-value').textContent = '✗ Disabled';
            }
            if (components.fallback === false) {
                document.querySelector('#execution-metrics .metric-row:nth-child(2) .metric-value').textContent = '✗ Disabled';
            }
            if (components.retry === false) {
                document.querySelector('#execution-metrics .metric-row:nth-child(3) .metric-value').textContent = '✗ Disabled';
            }
            
            if (components.evolution) {
                document.querySelector('#evolution-metrics .panel-status').textContent = 'Active';
                document.querySelector('#evolution-metrics .panel-status').className = 'panel-status online';
                document.querySelectorAll('#evolution-metrics .metric-value').forEach(el => el.textContent = '✓ Enabled');
            }
        }

        async function fetchMetrics() {
            try {
                const response = await fetch('/api/harness/metrics');
                const data = await response.json();
                console.log('Metrics:', data);
            } catch (error) {
                console.error('Failed to fetch metrics:', error);
            }
        }

        setInterval(fetchStatus, 5000);
        fetchStatus();
        fetchMetrics();
    </script>
</body>
</html>"""
    
    return html


def export_html() -> str:
    """导出 HTML"""
    return generate_dashboard_html()


def save_html(filepath: str):
    """保存到文件"""
    html = generate_dashboard_html()
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)


dashboard = MonitoringDashboard()
