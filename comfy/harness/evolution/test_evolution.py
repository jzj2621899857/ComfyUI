"""
自进化系统单元测试
"""

import unittest
import tempfile
import os

from .workflow_version import version_manager, WorkflowVersionManager, WorkflowVersion
from .canary_deployer import canary_deployer, CanaryDeployer, CanaryConfig, CanaryStatus


class TestWorkflowVersionManager(unittest.TestCase):
    
    def setUp(self):
        version_manager.enable()
    
    def tearDown(self):
        version_manager.disable()
    
    def test_save_version(self):
        """测试保存版本"""
        workflow_data = {"nodes": [], "connections": []}
        version_id = version_manager.save_version("test_workflow", workflow_data, "initial version")
        
        self.assertIsNotNone(version_id)
        self.assertTrue(len(version_id) > 0)
    
    def test_get_version(self):
        """测试获取版本"""
        workflow_data = {"nodes": [{"id": "1", "type": "TestNode"}]}
        version_id = version_manager.save_version("test_workflow2", workflow_data)
        
        version = version_manager.get_version("test_workflow2", version_id)
        self.assertIsNotNone(version)
        self.assertEqual(version.version_id, version_id)
    
    def test_get_all_versions(self):
        """测试获取所有版本"""
        workflow_data1 = {"version": 1}
        workflow_data2 = {"version": 2}
        
        version_manager.save_version("test_workflow3", workflow_data1, "v1")
        version_manager.save_version("test_workflow3", workflow_data2, "v2")
        
        versions = version_manager.get_all_versions("test_workflow3")
        self.assertEqual(len(versions), 2)
    
    def test_get_latest_version(self):
        """测试获取最新版本"""
        workflow_data1 = {"version": 1}
        workflow_data2 = {"version": 2}
        
        version_manager.save_version("test_workflow4", workflow_data1, "v1")
        version_manager.save_version("test_workflow4", workflow_data2, "v2")
        
        latest = version_manager.get_latest_version("test_workflow4")
        self.assertIsNotNone(latest)
        self.assertEqual(latest.description, "v2")
    
    def test_rollback_to_version(self):
        """测试回滚到版本"""
        workflow_data1 = {"version": 1}
        workflow_data2 = {"version": 2}
        
        v1_id = version_manager.save_version("test_workflow5", workflow_data1, "v1")
        v2_id = version_manager.save_version("test_workflow5", workflow_data2, "v2")
        
        result = version_manager.rollback_to_version("test_workflow5", v1_id)
        self.assertTrue(result)
        
        v1 = version_manager.get_version("test_workflow5", v1_id)
        v2 = version_manager.get_version("test_workflow5", v2_id)
        
        self.assertTrue(v1.is_active)
        self.assertFalse(v2.is_active)
    
    def test_delete_version(self):
        """测试删除版本"""
        workflow_data = {"nodes": []}
        version_id = version_manager.save_version("test_workflow6", workflow_data)
        
        result = version_manager.delete_version("test_workflow6", version_id)
        self.assertTrue(result)
        
        version = version_manager.get_version("test_workflow6", version_id)
        self.assertIsNone(version)


class TestCanaryDeployer(unittest.TestCase):
    
    def setUp(self):
        canary_deployer.enable()
    
    def tearDown(self):
        canary_deployer.disable()
    
    def test_start_canary(self):
        """测试启动金丝雀部署"""
        config = CanaryConfig(
            workflow_id="test_canary",
            new_version_id="v2",
            traffic_percent=10.0,
            increment_interval=0.1,
            health_check_interval=0.1,
            max_duration=1.0
        )
        
        result = canary_deployer.start_canary(config)
        self.assertTrue(result)
        
        status = canary_deployer.get_canary_status("test_canary")
        self.assertIsNotNone(status)
    
    def test_stop_canary(self):
        """测试停止金丝雀部署"""
        config = CanaryConfig(
            workflow_id="test_canary2",
            new_version_id="v2",
            traffic_percent=10.0,
            increment_interval=100.0,
            health_check_interval=100.0,
            max_duration=100.0
        )
        
        canary_deployer.start_canary(config)
        canary_deployer.stop_canary("test_canary2")
        
        status = canary_deployer.get_canary_status("test_canary2")
        self.assertIsNone(status)
    
    def test_promote_canary(self):
        """测试推广金丝雀部署"""
        config = CanaryConfig(
            workflow_id="test_canary3",
            new_version_id="v2",
            traffic_percent=10.0,
            increment_interval=100.0,
            health_check_interval=100.0,
            max_duration=100.0
        )
        
        canary_deployer.start_canary(config)
        result = canary_deployer.promote_canary("test_canary3")
        
        self.assertTrue(result)
        
        status = canary_deployer.get_canary_status("test_canary3")
        self.assertIsNone(status)
    
    def test_record_request(self):
        """测试记录请求"""
        config = CanaryConfig(
            workflow_id="test_canary4",
            new_version_id="v2",
            traffic_percent=10.0,
            increment_interval=100.0,
            health_check_interval=100.0,
            max_duration=100.0
        )
        
        canary_deployer.start_canary(config)
        
        canary_deployer.record_request("test_canary4", success=True)
        canary_deployer.record_request("test_canary4", success=True)
        canary_deployer.record_request("test_canary4", success=False)
        
        status = canary_deployer.get_canary_status("test_canary4")
        self.assertEqual(status.requests_served, 3)
        self.assertEqual(status.requests_failed, 1)
        
        canary_deployer.stop_canary("test_canary4")


if __name__ == "__main__":
    unittest.main()