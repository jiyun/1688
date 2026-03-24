#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
临时资源存储模块 - 内存缓存版本
用于在处理队列执行期间临时存储资源链接，避免DuckDB多进程冲突
"""

from typing import Dict, List, Optional
from datetime import datetime

# 内存缓存
_memory_cache = {
    'resources': [],
    'prices': [],
    'counts': []
}


def save_resources_temp(product_id: str, main_images: List, color_images: List, 
                        detail_images: List, videos: List) -> bool:
    """临时保存资源链接到内存缓存"""
    try:
        data = {
            'product_id': product_id,
            'main_images': main_images,
            'color_images': color_images,
            'detail_images': detail_images,
            'videos': videos,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        existing_ids = [d['product_id'] for d in _memory_cache['resources']]
        if product_id in existing_ids:
            idx = existing_ids.index(product_id)
            _memory_cache['resources'][idx] = data
        else:
            _memory_cache['resources'].append(data)
        
        return True
    except Exception as e:
        print(f"临时保存资源失败: {e}")
        return False


def save_prices_temp(product_id: str, prices: Dict) -> bool:
    """临时保存价格信息到内存缓存"""
    try:
        data = {
            'product_id': product_id,
            'prices': prices,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        existing_ids = [d['product_id'] for d in _memory_cache['prices']]
        if product_id in existing_ids:
            idx = existing_ids.index(product_id)
            _memory_cache['prices'][idx] = data
        else:
            _memory_cache['prices'].append(data)
        
        return True
    except Exception as e:
        print(f"临时保存价格失败: {e}")
        return False


def save_resource_counts_temp(product_id: str, main_images: int, color_images: int,
                               detail_images: int, videos: int, output_path: str = None,
                               platform: str = 'alibaba') -> bool:
    """临时保存资源计数到内存缓存"""
    try:
        data = {
            'product_id': product_id,
            'resource_counts': [main_images, color_images, detail_images, videos],
            'output_path': output_path,
            'platform': platform,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        existing_ids = [d['product_id'] for d in _memory_cache['counts']]
        if product_id in existing_ids:
            idx = existing_ids.index(product_id)
            _memory_cache['counts'][idx] = data
        else:
            _memory_cache['counts'].append(data)
        
        return True
    except Exception as e:
        print(f"临时保存资源计数失败: {e}")
        return False


def get_pending_resources() -> List[Dict]:
    """获取待导入的资源数据"""
    return _memory_cache['resources'].copy()


def get_pending_prices() -> List[Dict]:
    """获取待导入的价格数据"""
    return _memory_cache['prices'].copy()


def get_pending_counts() -> List[Dict]:
    """获取待导入的资源计数数据"""
    return _memory_cache['counts'].copy()


def clear_pending_data():
    """清空内存缓存"""
    _memory_cache['resources'].clear()
    _memory_cache['prices'].clear()
    _memory_cache['counts'].clear()


def has_pending_data() -> bool:
    """检查是否有待导入的数据"""
    return (len(_memory_cache['resources']) > 0 or 
            len(_memory_cache['prices']) > 0 or
            len(_memory_cache['counts']) > 0)


def get_cache_stats() -> Dict:
    """获取缓存统计"""
    return {
        'resources': len(_memory_cache['resources']),
        'prices': len(_memory_cache['prices']),
        'counts': len(_memory_cache['counts'])
    }
