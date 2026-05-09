"""
显存池管理

管理显存块复用，减少碎片
"""

import time
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field


@dataclass
class MemoryBlock:
    """内存块"""
    size: int  # 字节
    device: str
    data: Any = None  # 实际的 tensor 数据
    allocated_at: float = 0.0
    last_used: float = 0.0
    use_count: int = 0
    is_free: bool = True
    
    def __post_init__(self):
        if self.allocated_at == 0.0:
            self.allocated_at = time.time()
            self.last_used = self.allocated_at
    
    @property
    def age_seconds(self) -> float:
        """块年龄"""
        return time.time() - self.allocated_at
    
    @property
    def idle_seconds(self) -> float:
        """空闲时间"""
        return time.time() - self.last_used


class MemoryPool:
    """
    显存池管理器
    
    管理显存块复用，减少内存碎片
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._enabled = False
            cls._instance._pools: Dict[str, List[MemoryBlock]] = {}  # device -> blocks
            cls._instance._allocated_blocks: Dict[int, MemoryBlock] = {}  # id -> block
            cls._instance._max_pool_size_mb = 1024  # 最大池大小
            cls._instance._fragmentation_threshold = 0.3  # 碎片率阈值
            cls._instance._block_size_alignment = 512  # 块大小对齐
        return cls._instance
    
    def enable(self, max_pool_size_mb: int = 1024):
        """启用内存池"""
        self._enabled = True
        self._max_pool_size_mb = max_pool_size_mb
    
    def disable(self):
        """禁用内存池"""
        self._enabled = False
        self.clear()
    
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self._enabled
    
    def allocate(self, size: int, device: str = "cuda:0") -> Optional[Any]:
        """
        分配内存
        
        优先从池中获取，不足时创建新块
        """
        if not self._enabled:
            return self._allocate_raw(size, device)
        
        # 对齐大小
        size = self._align_size(size)
        
        # 查找合适的空闲块
        block = self._find_free_block(size, device)
        
        if block:
            # 复用现有块
            block.is_free = False
            block.last_used = time.time()
            block.use_count += 1
            self._allocated_blocks[id(block.data)] = block
            return block.data
        
        # 创建新块
        data = self._allocate_raw(size, device)
        if data is None:
            # 分配失败，尝试清理碎片
            self._defragment()
            data = self._allocate_raw(size, device)
        
        if data:
            block = MemoryBlock(
                size=size,
                device=device,
                data=data,
                is_free=False
            )
            block.use_count = 1
            
            if device not in self._pools:
                self._pools[device] = []
            self._pools[device].append(block)
            self._allocated_blocks[id(data)] = block
        
        return data
    
    def free(self, data: Any) -> bool:
        """
        释放内存
        
        将块标记为空闲，而非立即释放
        """
        if not self._enabled:
            return self._free_raw(data)
        
        block_id = id(data)
        if block_id not in self._allocated_blocks:
            return self._free_raw(data)
        
        block = self._allocated_blocks.pop(block_id)
        block.is_free = True
        block.last_used = time.time()
        
        # 检查是否需要清理
        self._maybe_cleanup()
        
        return True
    
    def _find_free_block(self, size: int, device: str) -> Optional[MemoryBlock]:
        """查找合适的空闲块"""
        if device not in self._pools:
            return None
        
        best_block = None
        best_size_diff = float('inf')
        
        for block in self._pools[device]:
            if not block.is_free:
                continue
            
            if block.size < size:
                continue
            
            size_diff = block.size - size
            if size_diff < best_size_diff:
                best_size_diff = size_diff
                best_block = block
        
        return best_block
    
    def _allocate_raw(self, size: int, device: str) -> Optional[Any]:
        """原始分配"""
        try:
            import torch
            if "cuda" in device and torch.cuda.is_available():
                return torch.empty(size // 4, dtype=torch.float32, device=device)
            else:
                return torch.empty(size // 4, dtype=torch.float32)
        except ImportError:
            return None
        except Exception:
            return None
    
    def _free_raw(self, data: Any) -> bool:
        """原始释放"""
        try:
            import torch
            if isinstance(data, torch.Tensor):
                del data
                return True
        except ImportError:
            pass
        return False
    
    def _align_size(self, size: int) -> int:
        """对齐大小"""
        alignment = self._block_size_alignment
        return ((size + alignment - 1) // alignment) * alignment
    
    def _defragment(self):
        """清理碎片"""
        for device, blocks in self._pools.items():
            # 释放长时间未使用的空闲块
            blocks_to_remove = []
            for block in blocks:
                if block.is_free and block.idle_seconds > 60:  # 空闲超过 60 秒
                    blocks_to_remove.append(block)
            
            for block in blocks_to_remove:
                self._free_raw(block.data)
                blocks.remove(block)
    
    def _maybe_cleanup(self):
        """可能需要清理"""
        total_size = self._get_total_pool_size()
        if total_size > self._max_pool_size_mb * 1024 * 1024:
            self._cleanup_oldest()
    
    def _cleanup_oldest(self):
        """清理最旧的块"""
        all_blocks = []
        for device, blocks in self._pools.items():
            for block in blocks:
                if block.is_free:
                    all_blocks.append((block.idle_seconds, block, device))
        
        # 按空闲时间排序
        all_blocks.sort(reverse=True)
        
        # 清理最旧的 20%
        to_remove = all_blocks[:len(all_blocks) // 5]
        for _, block, device in to_remove:
            self._free_raw(block.data)
            self._pools[device].remove(block)
    
    def _get_total_pool_size(self) -> int:
        """获取池总大小"""
        total = 0
        for blocks in self._pools.values():
            for block in blocks:
                total += block.size
        return total
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_blocks = 0
        free_blocks = 0
        total_size = 0
        free_size = 0
        
        for device, blocks in self._pools.items():
            total_blocks += len(blocks)
            for block in blocks:
                total_size += block.size
                if block.is_free:
                    free_blocks += 1
                    free_size += block.size
        
        fragmentation = 0.0
        if total_size > 0:
            fragmentation = free_size / total_size
        
        return {
            "enabled": self._enabled,
            "total_blocks": total_blocks,
            "free_blocks": free_blocks,
            "allocated_blocks": total_blocks - free_blocks,
            "total_size_mb": total_size / (1024 * 1024),
            "free_size_mb": free_size / (1024 * 1024),
            "fragmentation_ratio": fragmentation,
            "max_pool_size_mb": self._max_pool_size_mb
        }
    
    def clear(self):
        """清空内存池"""
        for device, blocks in self._pools.items():
            for block in blocks:
                self._free_raw(block.data)
        self._pools.clear()
        self._allocated_blocks.clear()


# 全局内存池实例
memory_pool = MemoryPool()
