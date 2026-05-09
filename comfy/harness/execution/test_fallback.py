"""
Fallback 机制单元测试
"""

import unittest
from unittest.mock import patch, MagicMock

from .fallback import FallbackHandler, FallbackAction, FallbackContext


class TestFallbackHandler(unittest.TestCase):
    
    def setUp(self):
        """初始化测试环境"""
        from ..config import FallbackConfig
        config = FallbackConfig(enabled=True, default_behavior="bypass")
        self.handler = FallbackHandler(config)
    
    def test_should_fallback_non_critical_node(self):
        """测试非关键节点失败时应该 fallback"""
        # 模拟 CUDA OOM 错误
        error = RuntimeError("CUDA out of memory")
        
        # 非关键节点类型
        kwargs = {"class_type": "PreviewImage", "inputs": {}}
        
        result = self.handler.should_fallback(error, (), kwargs)
        self.assertTrue(result)
    
    def test_should_not_fallback_critical_node(self):
        """测试关键节点失败时不应该 fallback"""
        error = RuntimeError("CUDA out of memory")
        
        # 关键节点类型
        kwargs = {"class_type": "KSampler", "inputs": {}}
        
        result = self.handler.should_fallback(error, (), kwargs)
        self.assertFalse(result)
    
    def test_should_not_fallback_non_retryable_error(self):
        """测试非重试错误不应该 fallback"""
        error = ValueError("Invalid parameter")
        
        kwargs = {"class_type": "PreviewImage", "inputs": {}}
        
        result = self.handler.should_fallback(error, (), kwargs)
        self.assertFalse(result)
    
    def test_should_fallback_optional_node(self):
        """测试标记为 optional 的节点应该 fallback"""
        error = RuntimeError("CUDA out of memory")
        
        kwargs = {"class_type": "CustomNode", "inputs": {}, "optional": True}
        
        result = self.handler.should_fallback(error, (), kwargs)
        self.assertTrue(result)
    
    def test_handle_fallback(self):
        """测试 fallback 处理"""
        error = RuntimeError("CUDA out of memory")
        kwargs = {
            "unique_id": "node_0",
            "class_type": "PreviewImage",
            "inputs": {"image": "test_input"}
        }
        
        result = self.handler.handle_fallback(error, (), kwargs)
        
        # 应该返回空输出
        self.assertEqual(result, ([], {}, False))
    
    def test_fallback_stats(self):
        """测试 fallback 统计"""
        # 初始状态
        stats = self.handler.get_fallback_stats()
        self.assertEqual(stats["total_fallbacks"], 0)
        
        # 模拟几次 fallback
        error = RuntimeError("CUDA out of memory")
        kwargs = {"class_type": "PreviewImage", "inputs": {}}
        
        for i in range(3):
            self.handler.handle_fallback(error, (), kwargs)
        
        stats = self.handler.get_fallback_stats()
        self.assertEqual(stats["total_fallbacks"], 3)
        self.assertIn("PreviewImage", stats["by_node_type"])
    
    def test_register_critical_node(self):
        """测试注册关键节点"""
        # PreviewImage 原本是非关键节点
        self.assertIn("PreviewImage", self.handler.NON_CRITICAL_NODE_TYPES)
        
        # 注册为关键节点
        self.handler.register_critical_node("PreviewImage")
        
        # 不再是非关键节点
        self.assertNotIn("PreviewImage", self.handler.NON_CRITICAL_NODE_TYPES)
    
    def test_set_node_as_optional(self):
        """测试设置节点为可选"""
        # 自定义节点默认不是非关键节点
        self.assertNotIn("MyCustomNode", self.handler.NON_CRITICAL_NODE_TYPES)
        
        # 设置为可选
        self.handler.set_node_as_optional("MyCustomNode", optional=True)
        
        # 现在应该是非关键节点
        self.assertIn("MyCustomNode", self.handler.NON_CRITICAL_NODE_TYPES)


if __name__ == "__main__":
    unittest.main()


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Running Fallback Handler Tests")
    print("=" * 60)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFallbackHandler)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 60)
    print(f"测试结果: {result.testsRun} 个测试，"
          f"失败: {len(result.failures)}，错误: {len(result.errors)}")
    print("=" * 60)
    
    return result.wasSuccessful()