"""
Retry 机制单元测试
"""

import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

from .retry import RetryHandler, BatchSizeReducer, retry_with_backoff


class TestRetryHandler(unittest.TestCase):
    
    def setUp(self):
        """初始化测试环境"""
        from ..config import RetryConfig
        config = RetryConfig(
            enabled=True,
            max_attempts=3,
            backoff_factor=2.0,
            batch_size_reduction=0.5
        )
        self.handler = RetryHandler(config)
    
    def test_is_retryable_error(self):
        """测试可重试错误识别"""
        retryable_errors = [
            RuntimeError("CUDA out of memory"),
            RuntimeError("Out of memory"),
            RuntimeError("Allocation on device"),
        ]
        
        non_retryable_errors = [
            ValueError("Invalid parameter"),
            TypeError("Wrong type"),
            RuntimeError("Something went wrong"),
        ]
        
        for error in retryable_errors:
            self.assertTrue(self.handler.is_retryable_error(error))
        
        for error in non_retryable_errors:
            self.assertFalse(self.handler.is_retryable_error(error))
    
    def test_calculate_backoff(self):
        """测试退避时间计算"""
        # 指数退避: backoff_factor^attempt
        self.assertEqual(self.handler.calculate_backoff(0), 1.0)   # 2^0 = 1
        self.assertEqual(self.handler.calculate_backoff(1), 2.0)   # 2^1 = 2
        self.assertEqual(self.handler.calculate_backoff(2), 4.0)   # 2^2 = 4
        self.assertEqual(self.handler.calculate_backoff(3), 8.0)   # 2^3 = 8
    
    def test_adjust_batch_size(self):
        """测试批次大小调整"""
        # 每次重试缩减 50%
        self.assertEqual(self.handler.adjust_batch_size(32, 0), 32)  # 32 * 0.5^0 = 32
        self.assertEqual(self.handler.adjust_batch_size(32, 1), 16)  # 32 * 0.5^1 = 16
        self.assertEqual(self.handler.adjust_batch_size(32, 2), 8)   # 32 * 0.5^2 = 8
        self.assertEqual(self.handler.adjust_batch_size(32, 3), 4)   # 32 * 0.5^3 = 4
    
    def test_adjust_batch_size_min(self):
        """测试批次大小不小于 1"""
        self.assertEqual(self.handler.adjust_batch_size(1, 10), 1)  # 最小为 1
    
    def test_retry_stats(self):
        """测试重试统计"""
        stats = self.handler.get_stats()
        self.assertEqual(stats["total_retries"], 0)
        self.assertEqual(stats["successful_retries"], 0)
        self.assertEqual(stats["failed_retries"], 0)


class TestBatchSizeReducer(unittest.TestCase):
    
    def setUp(self):
        """初始化测试环境"""
        self.reducer = BatchSizeReducer(reduction_factor=0.5)
    
    def test_reduce(self):
        """测试缩减批次大小"""
        self.assertEqual(self.reducer.reduce("key1", 32), 16)
        self.assertEqual(self.reducer.reduce("key1", 16), 8)
    
    def test_restore(self):
        """测试恢复原始批次大小"""
        self.reducer.reduce("key1", 32)
        self.assertEqual(self.reducer.restore("key1"), 32)
    
    def test_get_original(self):
        """测试获取原始批次大小"""
        self.reducer.reduce("key1", 32)
        self.assertEqual(self.reducer.get_original("key1"), 32)
    
    def test_restore_nonexistent(self):
        """测试恢复不存在的键"""
        self.assertIsNone(self.reducer.restore("nonexistent"))


class TestRetryWithBackoffDecorator(unittest.TestCase):
    
    def test_decorator_retries_on_error(self):
        """测试装饰器在错误时重试"""
        call_count = 0
        
        @retry_with_backoff(max_attempts=3)
        async def failing_function():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("CUDA out of memory")
        
        # 应该重试 3 次然后失败
        with self.assertRaises(RuntimeError):
            asyncio.run(failing_function())
        
        self.assertEqual(call_count, 3)
    
    def test_decorator_succeeds_after_retry(self):
        """测试装饰器在重试后成功"""
        call_count = 0
        
        @retry_with_backoff(max_attempts=3)
        async def eventually_succeeding_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("CUDA out of memory")
            return "success"
        
        result = asyncio.run(eventually_succeeding_function())
        
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)


if __name__ == "__main__":
    unittest.main()


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Running Retry Handler Tests")
    print("=" * 60)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRetryHandler)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestBatchSizeReducer))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestRetryWithBackoffDecorator))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 60)
    print(f"测试结果: {result.testsRun} 个测试，"
          f"失败: {len(result.failures)}，错误: {len(result.errors)}")
    print("=" * 60)
    
    return result.wasSuccessful()