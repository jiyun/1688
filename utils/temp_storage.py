#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
临时资源存储模块 - 文件存储版本
用于在处理队列执行期间临时存储资源链接，避免DuckDB多进程冲突
"""

import os
import json
from typing import Dict, List, Optional
from datetime import datetime

TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'temp')
PENDING_RESOURCES_FILE = os.path.join(TEMP_DIR, 'pending_resources.json')
PENDING_PRICES_FILE = os.path.join(TEMP_DIR, 'pending_prices.json')
PENDING_COUNTS_FILE = os.path.join(TEMP_DIR, 'pending_counts.json')


def ensure_temp_dir():
    """确保临时目录存在"""
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)


def save_resources_temp(product_id: str, main_images: List, color_images: List, 
                        detail_images: List, videos: List) -> bool:
    """临时保存资源链接到JSON文件"""
    try:
        ensure_temp_dir()
        
        data = {
            'product_id': product_id,
            'main_images': main_images,
            'color_images': color_images,
            'detail_images': detail_images,
            'videos': videos,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if os.path.exists(PENDING_RESOURCES_FILE):
            with open(PENDING_RESOURCES_FILE, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
        else:
            all_data = []
        
        existing_ids = [d['product_id'] for d in all_data]
        if product_id in existing_ids:
            idx = existing_ids.index(product_id)
            all_data[idx] = data
        else:
            all_data.append(data)
        
        with open(PENDING_RESOURCES_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"临时保存资源失败: {e}")
        return False


def save_prices_temp(product_id: str, prices: Dict) -> bool:
    """临时保存价格信息到JSON文件"""
    try:
        ensure_temp_dir()
        
        data = {
            'product_id': product_id,
            'prices': prices,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if os.path.exists(PENDING_PRICES_FILE):
            with open(PENDING_PRICES_FILE, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
        else:
            all_data = []
        
        existing_ids = [d['product_id'] for d in all_data]
        if product_id in existing_ids:
            idx = existing_ids.index(product_id)
            all_data[idx] = data
        else:
            all_data.append(data)
        
        with open(PENDING_PRICES_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"临时保存价格失败: {e}")
        return False


def save_resource_counts_temp(product_id: str, main_images: int, color_images: int,
                               detail_images: int, videos: int, output_path: str = None,
                               platform: str = 'alibaba') -> bool:
    """临时保存资源计数到JSON文件"""
    try:
        ensure_temp_dir()
        
        data = {
            'product_id': product_id,
            'resource_counts': [main_images, color_images, detail_images, videos],
            'output_path': output_path,
            'platform': platform,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if os.path.exists(PENDING_COUNTS_FILE):
            with open(PENDING_COUNTS_FILE, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
        else:
            all_data = []
        
        existing_ids = [d['product_id'] for d in all_data]
        if product_id in existing_ids:
            idx = existing_ids.index(product_id)
            all_data[idx] = data
        else:
            all_data.append(data)
        
        with open(PENDING_COUNTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"临时保存资源计数失败: {e}")
        return False


def get_pending_resources() -> List[Dict]:
    """获取待导入的资源数据"""
    if os.path.exists(PENDING_RESOURCES_FILE):
        with open(PENDING_RESOURCES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def get_pending_prices() -> List[Dict]:
    """获取待导入的价格数据"""
    if os.path.exists(PENDING_PRICES_FILE):
        with open(PENDING_PRICES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def get_pending_counts() -> List[Dict]:
    """获取待导入的资源计数数据"""
    if os.path.exists(PENDING_COUNTS_FILE):
        with open(PENDING_COUNTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def clear_pending_data():
    """清空临时数据文件"""
    files = [PENDING_RESOURCES_FILE, PENDING_PRICES_FILE, PENDING_COUNTS_FILE]
    for f in files:
        if os.path.exists(f):
            os.remove(f)


def has_pending_data() -> bool:
    """检查是否有待导入的数据"""
    return (os.path.exists(PENDING_RESOURCES_FILE) or 
            os.path.exists(PENDING_PRICES_FILE) or
            os.path.exists(PENDING_COUNTS_FILE))


def get_cache_stats() -> Dict:
    """获取缓存统计"""
    return {
        'resources': len(get_pending_resources()),
        'prices': len(get_pending_prices()),
        'counts': len(get_pending_counts())
    }
