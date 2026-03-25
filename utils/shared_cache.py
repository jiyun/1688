#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
共享内存缓存模块
用于跨进程共享数据，避免硬盘I/O
"""

import json
import struct
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    from multiprocessing import shared_memory
    HAS_SHARED_MEMORY = True
except ImportError:
    HAS_SHARED_MEMORY = False
    print("警告: shared_memory 需要 Python 3.8+")


SHM_NAME = '1688_cache'
SHM_SIZE = 10 * 1024 * 1024  # 10MB


class SharedCache:
    """命名共享内存缓存"""
    
    def __init__(self, name: str = SHM_NAME, size: int = SHM_SIZE):
        self.name = name
        self.size = size
        self.shm = None
        self._is_creator = False
    
    def create(self) -> bool:
        """创建共享内存（主进程调用）"""
        if not HAS_SHARED_MEMORY:
            return False
        
        try:
            self.shm = shared_memory.SharedMemory(
                name=self.name,
                create=True,
                size=self.size
            )
            self._is_creator = True
            self._clear()
            return True
        except FileExistsError:
            return self.connect()
        except Exception as e:
            print(f"创建共享内存失败: {e}")
            return False
    
    def connect(self) -> bool:
        """连接共享内存（子进程调用）"""
        if not HAS_SHARED_MEMORY:
            return False
        
        try:
            self.shm = shared_memory.SharedMemory(name=self.name)
            return True
        except Exception as e:
            print(f"连接共享内存失败: {e}")
            return False
    
    def _clear(self):
        """清空共享内存"""
        if self.shm:
            self.shm.buf[:] = b'\x00' * self.size
    
    def _write_block(self, offset: int, key: str, data: bytes) -> int:
        """写入数据块"""
        key_bytes = key.encode('utf-8')
        key_len = len(key_bytes)
        data_len = len(data)
        
        header = struct.pack('>II', key_len, data_len)
        self.shm.buf[offset:offset+8] = header
        self.shm.buf[offset+8:offset+8+key_len] = key_bytes
        self.shm.buf[offset+8+key_len:offset+8+key_len+data_len] = data
        
        return offset + 8 + key_len + data_len
    
    def _read_block(self, offset: int) -> tuple:
        """读取数据块"""
        header = bytes(self.shm.buf[offset:offset+8])
        if header == b'\x00' * 8:
            return None, None, offset
        
        key_len, data_len = struct.unpack('>II', header)
        key = bytes(self.shm.buf[offset+8:offset+8+key_len]).decode('utf-8')
        data = bytes(self.shm.buf[offset+8+key_len:offset+8+key_len+data_len])
        
        return key, data, offset + 8 + key_len + data_len
    
    def write(self, key: str, data: Any) -> bool:
        """写入数据"""
        if not self.shm:
            return False
        
        try:
            json_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
            
            offset = 0
            while offset < self.size - 8:
                header = bytes(self.shm.buf[offset:offset+8])
                if header == b'\x00' * 8:
                    break
                
                existing_key, _, next_offset = self._read_block(offset)
                if existing_key == key:
                    self._remove_block(offset)
                    break
                offset = next_offset
            
            if offset + 8 + len(key) + len(json_bytes) > self.size:
                print("共享内存空间不足")
                return False
            
            self._write_block(offset, key, json_bytes)
            return True
        except Exception as e:
            print(f"写入共享内存失败: {e}")
            return False
    
    def _remove_block(self, offset: int):
        """移除数据块（标记为删除）"""
        header = bytes(self.shm.buf[offset:offset+8])
        if header == b'\x00' * 8:
            return
        
        key_len, data_len = struct.unpack('>II', header)
        block_size = 8 + key_len + data_len
        self.shm.buf[offset:offset+block_size] = b'\x00' * block_size
    
    def read(self, key: str) -> Optional[Any]:
        """读取数据"""
        if not self.shm:
            return None
        
        try:
            offset = 0
            while offset < self.size - 8:
                existing_key, data, next_offset = self._read_block(offset)
                if existing_key is None:
                    break
                if existing_key == key:
                    return json.loads(data.decode('utf-8'))
                offset = next_offset
            return None
        except Exception as e:
            print(f"读取共享内存失败: {e}")
            return None
    
    def read_all(self) -> Dict[str, Any]:
        """读取所有数据"""
        if not self.shm:
            return {}
        
        result = {}
        try:
            offset = 0
            while offset < self.size - 8:
                key, data, next_offset = self._read_block(offset)
                if key is None:
                    break
                if data:
                    result[key] = json.loads(data.decode('utf-8'))
                offset = next_offset
        except Exception as e:
            print(f"读取所有数据失败: {e}")
        
        return result
    
    def delete(self, key: str) -> bool:
        """删除数据"""
        if not self.shm:
            return False
        
        try:
            offset = 0
            while offset < self.size - 8:
                header = bytes(self.shm.buf[offset:offset+8])
                if header == b'\x00' * 8:
                    break
                
                existing_key, _, next_offset = self._read_block(offset)
                if existing_key == key:
                    self._remove_block(offset)
                    return True
                offset = next_offset
            return False
        except Exception as e:
            print(f"删除数据失败: {e}")
            return False
    
    def clear(self):
        """清空所有数据"""
        if self.shm:
            self._clear()
    
    def close(self):
        """关闭共享内存"""
        if self.shm:
            self.shm.close()
            self.shm = None
    
    def unlink(self):
        """删除共享内存"""
        if self.shm:
            self.shm.close()
            if self._is_creator:
                try:
                    self.shm.unlink()
                except:
                    pass
            self.shm = None


_cache: Optional[SharedCache] = None


def get_shared_cache() -> Optional[SharedCache]:
    """获取共享内存缓存实例"""
    global _cache
    if _cache is None and HAS_SHARED_MEMORY:
        _cache = SharedCache()
        # 尝试连接已存在的共享内存
        if not _cache.connect():
            # 如果连接失败，尝试创建新的共享内存
            _cache.create()
    elif _cache is not None and _cache.shm is None:
        # 缓存实例存在但未连接，尝试连接
        if not _cache.connect():
            _cache.create()
    return _cache


def init_shared_cache() -> bool:
    """初始化共享内存（主进程调用）"""
    global _cache
    if not HAS_SHARED_MEMORY:
        return False
    
    _cache = SharedCache()
    return _cache.create()


def connect_shared_cache() -> bool:
    """连接共享内存（子进程调用）"""
    global _cache
    if not HAS_SHARED_MEMORY:
        return False
    
    _cache = SharedCache()
    return _cache.connect()


def close_shared_cache():
    """关闭共享内存"""
    global _cache
    if _cache:
        _cache.close()
        _cache = None


def destroy_shared_cache():
    """销毁共享内存"""
    global _cache
    if _cache:
        _cache.unlink()
        _cache = None
