#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路径智能匹配模块 - 解决跨机器操作时的路径一致性问题
"""

import os
import re
import threading
from typing import Dict, Optional, List, Tuple, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class PathMatchResult:
    """路径匹配结果"""
    original_path: str
    is_available: bool
    matched_path: Optional[str] = None
    match_confidence: float = 0.0
    match_type: str = "none"
    suggestions: List[str] = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []


class PathMatcher:
    """路径智能匹配器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._temp_paths: Dict[str, str] = {}
        self._path_cache: Dict[str, PathMatchResult] = {}
        self._cache_time: Dict[str, float] = {}
        self._cache_ttl = 300
    
    def validate_path(self, path: str) -> Tuple[bool, str]:
        """验证路径是否可用"""
        if not path:
            return False, "路径为空"
        
        try:
            if not os.path.exists(path):
                return False, "路径不存在"
            
            if not os.path.isdir(path):
                return False, "路径不是目录"
            
            if not os.access(path, os.R_OK):
                return False, "无读取权限"
            
            return True, "路径可用"
        except Exception as e:
            return False, f"路径验证失败: {str(e)}"
    
    def extract_product_id_from_path(self, path: str) -> Optional[str]:
        """从路径中提取商品ID"""
        if not path:
            return None
        
        path = path.replace('\\', '/')
        parts = path.split('/')
        
        for part in reversed(parts):
            if part and part not in ['upload', 'products', 'download', 'output']:
                if re.match(r'^\d{10,}$', part):
                    return part
                if re.match(r'^[A-Za-z0-9_-]{10,}$', part):
                    return part
        
        return None
    
    def find_product_directories(self, base_dir: str, product_id: str) -> List[str]:
        """在基础目录下查找商品目录"""
        matches = []
        
        if not os.path.exists(base_dir):
            return matches
        
        try:
            for item in os.listdir(base_dir):
                item_path = os.path.join(base_dir, item)
                if os.path.isdir(item_path):
                    if item == product_id:
                        matches.append(item_path)
                    elif product_id in item:
                        matches.append(item_path)
        except Exception:
            pass
        
        return matches
    
    def scan_project_directories(self, product_id: str, max_depth: int = 4) -> List[str]:
        """扫描项目目录结构查找商品目录
        
        优先级：
        1. products/采集/upload/{商品ID}
        2. products/upload/{商品ID}
        3. products/{商品ID}
        4. 其他位置匹配的目录
        """
        matches = []
        project_dir = os.path.dirname(os.path.dirname(__file__))
        
        priority_paths = [
            ('products', '采集', 'upload'),
            ('products', 'upload'),
            ('products', 'download'),
            ('products'),
            ('output'),
        ]
        
        for path_parts in priority_paths:
            base_dir = os.path.join(project_dir, *path_parts)
            if os.path.exists(base_dir):
                found = self.find_product_directories(base_dir, product_id)
                for f in found:
                    if f not in matches:
                        matches.append(f)
        
        def scan_recursive(base_path: str, current_depth: int, found_paths: List[str]):
            """递归扫描目录"""
            if current_depth > max_depth:
                return
            
            try:
                for item in os.listdir(base_path):
                    item_path = os.path.join(base_path, item)
                    if os.path.isdir(item_path):
                        if item == product_id:
                            if item_path not in found_paths:
                                found_paths.append(item_path)
                        elif product_id in item:
                            if item_path not in found_paths:
                                found_paths.append(item_path)
                        
                        skip_dirs = ['node_modules', '.git', '__pycache__', '.venv', 'venv', 
                                    'env', '.idea', '.vscode', 'build', 'dist', '.wdm_cache',
                                    'tools', 'extensions', 'cache', 'temp', 'tmp']
                        if item.lower() not in skip_dirs:
                            scan_recursive(item_path, current_depth + 1, found_paths)
            except (PermissionError, OSError):
                pass
        
        scan_recursive(project_dir, 1, matches)
        
        return matches
    
    def scan_common_directories(self, product_id: str) -> List[str]:
        """扫描常见目录查找商品目录"""
        return self.scan_project_directories(product_id)
    
    def calculate_path_similarity(self, path1: str, path2: str) -> float:
        """计算两个路径的相似度"""
        if not path1 or not path2:
            return 0.0
        
        path1 = path1.replace('\\', '/').lower()
        path2 = path2.replace('\\', '/').lower()
        
        parts1 = [p for p in path1.split('/') if p]
        parts2 = [p for p in path2.split('/') if p]
        
        if not parts1 or not parts2:
            return 0.0
        
        common_parts = 0
        for p1, p2 in zip(reversed(parts1), reversed(parts2)):
            if p1 == p2:
                common_parts += 1
            else:
                break
        
        max_len = max(len(parts1), len(parts2))
        if max_len == 0:
            return 0.0
        
        return common_parts / max_len
    
    def match_path(self, original_path: str, product_id: str = None) -> PathMatchResult:
        """智能匹配路径"""
        if original_path in self._path_cache:
            cache_time = self._cache_time.get(original_path, 0)
            import time
            if time.time() - cache_time < self._cache_ttl:
                cached = self._path_cache[original_path]
                if cached.is_available:
                    return cached
        
        is_available, message = self.validate_path(original_path)
        
        if is_available:
            result = PathMatchResult(
                original_path=original_path,
                is_available=True,
                matched_path=original_path,
                match_confidence=1.0,
                match_type="direct"
            )
            self._cache_result(original_path, result)
            return result
        
        if not product_id:
            product_id = self.extract_product_id_from_path(original_path)
        
        suggestions = []
        matched_path = None
        match_confidence = 0.0
        match_type = "none"
        
        if product_id:
            suggestions = self.scan_common_directories(product_id)
            
            if suggestions:
                best_match = None
                best_similarity = 0.0
                
                for suggestion in suggestions:
                    similarity = self.calculate_path_similarity(original_path, suggestion)
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = suggestion
                
                if best_match:
                    matched_path = best_match
                    match_confidence = best_similarity
                    match_type = "smart_match"
        
        result = PathMatchResult(
            original_path=original_path,
            is_available=False,
            matched_path=matched_path,
            match_confidence=match_confidence,
            match_type=match_type,
            suggestions=suggestions
        )
        
        if matched_path:
            self._cache_result(original_path, result)
        
        return result
    
    def _cache_result(self, original_path: str, result: PathMatchResult):
        """缓存匹配结果"""
        import time
        self._path_cache[original_path] = result
        self._cache_time[original_path] = time.time()
    
    def set_temp_path(self, product_id: str, temp_path: str):
        """设置临时路径映射"""
        if temp_path and os.path.exists(temp_path):
            self._temp_paths[product_id] = temp_path
    
    def get_temp_path(self, product_id: str) -> Optional[str]:
        """获取临时路径"""
        return self._temp_paths.get(product_id)
    
    def clear_temp_path(self, product_id: str = None):
        """清除临时路径"""
        if product_id:
            self._temp_paths.pop(product_id, None)
        else:
            self._temp_paths.clear()
    
    def clear_cache(self):
        """清除缓存"""
        self._path_cache.clear()
        self._cache_time.clear()
    
    def get_effective_path(self, product_id: str, original_path: str) -> Tuple[str, PathMatchResult]:
        """获取有效路径（优先使用临时路径）"""
        temp_path = self.get_temp_path(product_id)
        if temp_path:
            is_available, _ = self.validate_path(temp_path)
            if is_available:
                result = PathMatchResult(
                    original_path=original_path,
                    is_available=True,
                    matched_path=temp_path,
                    match_confidence=1.0,
                    match_type="temp"
                )
                return temp_path, result
        
        result = self.match_path(original_path, product_id)
        return result.matched_path or original_path, result


_path_matcher: Optional[PathMatcher] = None


def get_path_matcher() -> PathMatcher:
    """获取全局路径匹配器实例"""
    global _path_matcher
    if _path_matcher is None:
        _path_matcher = PathMatcher()
    return _path_matcher


def match_output_path(original_path: str, product_id: str = None) -> PathMatchResult:
    """匹配输出路径"""
    return get_path_matcher().match_path(original_path, product_id)


def get_effective_output_path(product_id: str, original_path: str) -> Tuple[str, PathMatchResult]:
    """获取有效输出路径"""
    return get_path_matcher().get_effective_path(product_id, original_path)


def set_temp_output_path(product_id: str, temp_path: str):
    """设置临时输出路径"""
    get_path_matcher().set_temp_path(product_id, temp_path)


def get_temp_output_path(product_id: str) -> Optional[str]:
    """获取临时输出路径"""
    return get_path_matcher().get_temp_path(product_id)


def clear_temp_output_path(product_id: str = None):
    """清除临时输出路径"""
    get_path_matcher().clear_temp_path(product_id)
