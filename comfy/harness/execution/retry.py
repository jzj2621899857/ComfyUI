"""
Retry with Backoff - 自动重试机制

针对显存不足等瞬态错误，自动有限重试，并动态缩小批次大小
"""

import asyncio
import logging
import time
from typing import Any, Callable, Optional, Tuple
import torch

from ..config import RetryConfig

logger = logging.getLogger(__name__)


class RetryHandler:
    """
    重试处理器
    
    管理节点执行的重试逻辑，包括：
    - 指数退避
    - 批次大小动态调整
    - 显存不足错误识别
    """
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self._retry_stats = {
            "total_retries": 0,
            "successful_retries": 0,
            "failed_retries": 0,
        }
    
    def is_retryable_error(self, error: Exception) -> bool:
        """
        判断是否为可重试的错误
        
        Args:
            error: 发生的异常
        
        Returns:
            bool: 是否可重试
        """
        error_msg = str(error).lower()
        
        for pattern in self.config.retryable_errors:
            if pattern.lower() in error_msg:
                return True
        
        return False
    
    def calculate_backoff(self, attempt: int) -> float:
        """
        计算退避时间
        
        Args:
            attempt: 当前尝试次数（从0开始）
        
        Returns:
            float: 退避时间（秒）
        """
        return (self.config.backoff_factor ** attempt)
    
    def adjust_batch_size(self, current_batch_size: int, attempt: int) -> int:
        """
        调整批次大小
        
        Args:
            current_batch_size: 当前批次大小
            attempt: 当前尝试次数
        
        Returns:
            int: 调整后的批次大小
        """
        reduction = self.config.batch_size_reduction ** attempt
        new_size = max(1, int(current_batch_size * reduction))
        return new_size
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Tuple[Any, Any, Any]:
        """
        带重试的执行
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            tuple: (output_data, output_ui, has_subgraph)
        """
        if not self.config.enabled:
            return await func(*args, **kwargs)
        
        last_error = None
        
        for attempt in range(self.config.max_attempts):
            try:
                # 尝试执行
                result = await func(*args, **kwargs)
                
                # 如果之前有重试，记录成功
                if attempt > 0:
                    self._retry_stats["successful_retries"] += 1
                    logger.info(f"[Retry] 第 {attempt} 次重试成功")
                
                return result
                
            except Exception as e:
                last_error = e
                
                # 检查是否为可重试的错误
                if not self.is_retryable_error(e):
                    # 不可重试的错误，直接抛出
                    raise
                
                # 记录重试
                self._retry_stats["total_retries"] += 1
                
                # 检查是否还有重试次数
                if attempt >= self.config.max_attempts - 1:
                    logger.error(f"[Retry] 已达到最大重试次数 ({self.config.max_attempts})，放弃")
                    self._retry_stats["failed_retries"] += 1
                    raise
                
                # 计算退避时间
                backoff_time = self.calculate_backoff(attempt)
                
                logger.warning(
                    f"[Retry] 执行失败（尝试 {attempt + 1}/{self.config.max_attempts}）: {e}\n"
                    f"等待 {backoff_time:.1f} 秒后重试..."
                )
                
                # 尝试清理显存
                self._try_free_memory()
                
                # 等待退避时间
                await asyncio.sleep(backoff_time)
        
        # 所有重试都失败了
        if last_error:
            raise last_error
        
        raise RuntimeError("重试逻辑异常：未执行任何尝试")
    
    def _try_free_memory(self):
        """尝试释放显存"""
        try:
            if torch.cuda.is_available():
                # 清理 CUDA 缓存
                torch.cuda.empty_cache()
                
                # 记录清理后的显存状态
                allocated = torch.cuda.memory_allocated() / 1024**3  # GB
                reserved = torch.cuda.memory_reserved() / 1024**3  # GB
                
                logger.info(
                    f"[Retry] 显存清理完成 - "
                    f"已分配: {allocated:.2f}GB, "
                    f"已预留: {reserved:.2f}GB"
                )
        except Exception as e:
            logger.warning(f"[Retry] 显存清理失败: {e}")
    
    def get_stats(self) -> dict:
        """获取重试统计信息"""
        return self._retry_stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self._retry_stats = {
            "total_retries": 0,
            "successful_retries": 0,
            "failed_retries": 0,
        }


class BatchSizeReducer:
    """
    批次大小缩减器
    
    用于在重试时动态调整批次大小
    """
    
    def __init__(self, reduction_factor: float = 0.5):
        self.reduction_factor = reduction_factor
        self._original_batch_sizes = {}
    
    def reduce(self, key: str, current_size: int) -> int:
        """
        缩减批次大小
        
        Args:
            key: 标识符
            current_size: 当前批次大小
        
        Returns:
            int: 缩减后的批次大小
        """
        # 保存原始大小
        if key not in self._original_batch_sizes:
            self._original_batch_sizes[key] = current_size
        
        # 计算新大小
        new_size = max(1, int(current_size * self.reduction_factor))
        
        return new_size
    
    def restore(self, key: str) -> Optional[int]:
        """
        恢复原始批次大小
        
        Args:
            key: 标识符
        
        Returns:
            int: 原始批次大小，如果不存在则返回 None
        """
        return self._original_batch_sizes.pop(key, None)
    
    def get_original(self, key: str) -> Optional[int]:
        """获取原始批次大小（不移除）"""
        return self._original_batch_sizes.get(key)


def retry_with_backoff(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    retryable_errors: Tuple[str, ...] = None
):
    """
    重试装饰器
    
    Usage:
        @retry_with_backoff(max_attempts=3)
        async def my_function():
            ...
    """
    if retryable_errors is None:
        retryable_errors = (
            "CUDA out of memory",
            "out of memory",
            "Allocation on device",
        )
    
    def decorator(func: Callable) -> Callable:
        handler = RetryHandler(RetryConfig(
            enabled=True,
            max_attempts=max_attempts,
            backoff_factor=backoff_factor,
            retryable_errors=retryable_errors
        ))
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await handler.execute_with_retry(func, *args, **kwargs)
        
        return wrapper
    return decorator


# 导入 functools 用于装饰器
import functools