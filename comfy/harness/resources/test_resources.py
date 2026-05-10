"""
资源管理模块单元测试
"""

import unittest

from .memory_monitor import memory_monitor, MemoryMonitor, MemoryStats
from .resource_manager import resource_manager, ResourceManager, ResourceSettings


class TestMemoryMonitor(unittest.TestCase):
    
    def setUp(self):
        memory_monitor.enable()
    
    def tearDown(self):
        memory_monitor.disable()
    
    def test_memory_monitor_enabled(self):
        """测试内存监控器启用"""
        self.assertTrue(memory_monitor.is_enabled())
    
    def test_memory_monitor_stats(self):
        """测试内存统计"""
        stats = memory_monitor.get_stats()
        self.assertIsInstance(stats, MemoryStats)
        self.assertIsInstance(stats.used, int)
        self.assertIsInstance(stats.free, int)
        self.assertIsInstance(stats.total, int)
    
    def test_memory_monitor_percent(self):
        """测试内存使用率计算"""
        stats = memory_monitor.get_stats()
        percent = stats.usage_percent
        self.assertIsInstance(percent, float)
        self.assertTrue(0 <= percent <= 100)
    
    def test_memory_monitor_low_memory(self):
        """测试低内存检测"""
        result = memory_monitor.is_low_memory(0.9)
        self.assertIsInstance(result, bool)


class TestResourceManager(unittest.TestCase):
    
    def setUp(self):
        resource_manager.enable()
    
    def tearDown(self):
        resource_manager.disable()
    
    def test_resource_manager_enabled(self):
        """测试资源管理器启用"""
        self.assertTrue(resource_manager.is_enabled())
    
    def test_batch_size_adjustment(self):
        """测试批处理大小调整"""
        settings = ResourceSettings(
            max_batch_size=16,
            min_batch_size=1,
            current_batch_size=4,
            auto_adjust=True
        )
        resource_manager.set_settings(settings)
        
        self.assertEqual(resource_manager.get_batch_size(), 4)
        
        resource_manager.increase_batch_size()
        self.assertEqual(resource_manager.get_batch_size(), 8)
        
        resource_manager.increase_batch_size()
        self.assertEqual(resource_manager.get_batch_size(), 16)
        
        resource_manager.decrease_batch_size()
        self.assertEqual(resource_manager.get_batch_size(), 8)
    
    def test_batch_size_limits(self):
        """测试批处理大小限制"""
        settings = ResourceSettings(
            max_batch_size=8,
            min_batch_size=2,
            current_batch_size=8,
            auto_adjust=True
        )
        resource_manager.set_settings(settings)
        
        resource_manager.increase_batch_size()
        self.assertEqual(resource_manager.get_batch_size(), 8)
        
        resource_manager.decrease_batch_size()
        self.assertEqual(resource_manager.get_batch_size(), 4)
        
        resource_manager.decrease_batch_size()
        self.assertEqual(resource_manager.get_batch_size(), 2)
        
        resource_manager.decrease_batch_size()
        self.assertEqual(resource_manager.get_batch_size(), 2)
    
    def test_suggest_batch_size(self):
        """测试建议批处理大小"""
        settings = ResourceSettings(
            max_batch_size=16,
            min_batch_size=1,
            current_batch_size=4,
            auto_adjust=False
        )
        resource_manager.set_settings(settings)
        
        suggestion = resource_manager.suggest_batch_size(0)
        self.assertEqual(suggestion, 4)
    
    def test_force_gc(self):
        """测试强制垃圾回收"""
        resource_manager.force_garbage_collection()
        self.assertTrue(True)
    
    def test_memory_status(self):
        """测试内存状态获取"""
        status = resource_manager.get_memory_status()
        self.assertIn("batch_size", status)
        self.assertIn("max_batch_size", status)
        self.assertIn("auto_adjust", status)
        self.assertIn("used", status)
        self.assertIn("free", status)
        self.assertIn("total", status)


if __name__ == "__main__":
    unittest.main()