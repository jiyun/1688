#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
临时资源存储模块 - 共享内存版本
用于在处理队列执行期间临时存储资源链接，避免DuckDB多进程冲突
"""

from typing import Dict, List, Optional
from datetime import datetime

try:
    from utils.shared_cache import get_shared_cache, connect_shared_cache, init_shared_cache, HAS_SHARED_MEMORY
except ImportError:
    HAS_SHARED_MEMORY = False


def _get_cache():
    """获取缓存实例，如果不存在则尝试连接"""
    if not HAS_SHARED_MEMORY:
        return None
    
    cache = get_shared_cache()
    if cache and cache.shm:
        return cache
    
    # 尝试连接已存在的共享内存
    if connect_shared_cache():
        cache = get_shared_cache()
        if cache and cache.shm:
            return cache
    
    # 如果连接失败，返回 None
    return None


def save_resources_temp(product_id: str, main_images: List, color_images: List, 
                        detail_images: List, videos: List) -> bool:
    """临时保存资源链接"""
    try:
        data = {
            'product_id': product_id,
            'main_images': main_images,
            'color_images': color_images,
            'detail_images': detail_images,
            'videos': videos,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        cache = _get_cache()
        if cache:
            key = f'resources_{product_id}'
            return cache.write(key, data)
        
        return True
    except Exception as e:
        print(f"临时保存资源失败: {e}")
        return False


def save_prices_temp(product_id: str, prices: Dict) -> bool:
    """临时保存价格信息"""
    try:
        data = {
            'product_id': product_id,
            'prices': prices,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        print(f"[DEBUG] save_prices_temp: product_id={product_id}, sku_prices={len(prices.get('sku_prices', []))}, consign_prices={len(prices.get('consign_prices', []))}")
        
        cache = _get_cache()
        if cache:
            key = f'prices_{product_id}'
            result = cache.write(key, data)
            print(f"[DEBUG] save_prices_temp: 写入共享内存结果={result}")
            return result
        
        print("[DEBUG] save_prices_temp: 共享内存不可用")
        return True
    except Exception as e:
        print(f"临时保存价格失败: {e}")
        return False


def save_resource_counts_temp(product_id: str, main_images: int, color_images: int,
                               detail_images: int, videos: int, output_path: str = None,
                               platform: str = 'alibaba') -> bool:
    """临时保存资源计数"""
    try:
        data = {
            'product_id': product_id,
            'resource_counts': [main_images, color_images, detail_images, videos],
            'output_path': output_path,
            'platform': platform,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        cache = _get_cache()
        if cache:
            key = f'counts_{product_id}'
            return cache.write(key, data)
        
        return True
    except Exception as e:
        print(f"临时保存资源计数失败: {e}")
        return False


def get_pending_resources() -> List[Dict]:
    """获取待导入的资源数据"""
    cache = _get_cache()
    if not cache:
        return []
    
    result = []
    all_data = cache.read_all()
    for key, data in all_data.items():
        if key.startswith('resources_'):
            result.append(data)
    
    return result


def get_pending_prices() -> List[Dict]:
    """获取待导入的价格数据"""
    cache = _get_cache()
    if not cache:
        print("[DEBUG] get_pending_prices: 共享内存不可用")
        return []
    
    result = []
    all_data = cache.read_all()
    print(f"[DEBUG] get_pending_prices: 读取到 {len(all_data)} 条数据: {list(all_data.keys())}")
    
    # 调试：检查是否有 prices_ 开头的 key
    for key in all_data.keys():
        print(f"[DEBUG] get_pending_prices: 检查 key: {key}, startswith('prices_')={key.startswith('prices_')}")
    
    for key, data in all_data.items():
        if key.startswith('prices_'):
            print(f"[DEBUG] get_pending_prices: 发现价格数据 {key}")
            result.append(data)
    
    print(f"[DEBUG] get_pending_prices: 返回 {len(result)} 条价格数据")
    return result


def get_pending_counts() -> List[Dict]:
    """获取待导入的资源计数数据"""
    cache = _get_cache()
    if not cache:
        return []
    
    result = []
    all_data = cache.read_all()
    for key, data in all_data.items():
        if key.startswith('counts_'):
            result.append(data)
    
    return result


def clear_pending_data():
    """清空共享内存缓存"""
    cache = _get_cache()
    if cache:
        cache.clear()


def has_pending_data() -> bool:
    """检查是否有待导入的数据"""
    cache = _get_cache()
    if not cache:
        return False
    
    all_data = cache.read_all()
    for key in all_data.keys():
        if key.startswith(('resources_', 'prices_', 'counts_')):
            return True
    return False


def get_cache_stats() -> Dict:
    """获取缓存统计"""
    cache = _get_cache()
    if not cache:
        return {'resources': 0, 'prices': 0, 'counts': 0}
    
    all_data = cache.read_all()
    return {
        'resources': sum(1 for k in all_data if k.startswith('resources_')),
        'prices': sum(1 for k in all_data if k.startswith('prices_')),
        'counts': sum(1 for k in all_data if k.startswith('counts_'))
    }
