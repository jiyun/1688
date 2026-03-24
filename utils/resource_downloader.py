#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资源下载器模块 - 基于DuckDB
从数据库读取资源URL，支持断点续传和失败重试
"""

import os
import sys
import subprocess
from typing import List, Dict, Optional, Callable
from datetime import datetime

try:
    from utils.database import Database, HAS_DUCKDB
except ImportError:
    HAS_DUCKDB = False


def get_aria2c_path() -> Optional[str]:
    """获取aria2c路径"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    
    aria2c_path = os.path.join(project_dir, 'tools', 'aria2c.exe')
    if os.path.exists(aria2c_path):
        return aria2c_path
    
    return None


class ResourceDownloader:
    """基于数据库的资源下载器"""
    
    def __init__(self, db: Database = None, output_base_dir: str = None):
        if not HAS_DUCKDB:
            raise ImportError("DuckDB未安装")
        
        self.db = db or Database()
        self.output_base_dir = output_base_dir or os.getcwd()
        self.aria2c_path = get_aria2c_path()
    
    def get_pending_resources(self, product_id: str = None, resource_type: str = None, 
                               limit: int = None) -> List[Dict]:
        """获取待下载资源"""
        return self.db.get_pending_resources(product_id, resource_type, limit)
    
    def get_download_stats(self, product_id: str = None) -> Dict:
        """获取下载统计"""
        return self.db.get_download_stats(product_id)
    
    def download_with_aria2c(self, resources: List[Dict], output_dir: str,
                              progress_callback: Callable = None) -> bool:
        """使用aria2c下载资源 - 直接传递URL，不生成down.txt"""
        if not self.aria2c_path:
            print("aria2c未找到")
            return False
        
        if not resources:
            return True
        
        os.makedirs(output_dir, exist_ok=True)
        
        # 直接构建 aria2c 命令参数
        cmd = [
            self.aria2c_path,
            '--console-log-level=warn',
            '-d', output_dir,
            '-x', '16',
            '-s', '16',
            '-k', '1M',
            '--max-tries=3',
            '--retry-wait=2',
            '--timeout=60',
            '--continue=true',
            '--auto-file-renaming=false'
        ]
        
        # 直接添加 URL 和输出文件名
        for r in resources:
            url = r['resource_url']
            filename = r.get('output_filename') or r.get('resource_name', 'file')
            cmd.extend(['-o', filename, url])
        
        startupinfo = None
        creationflags = 0
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            creationflags = subprocess.CREATE_NO_WINDOW
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                startupinfo=startupinfo,
                creationflags=creationflags
            )
            
            if result.returncode == 0:
                for r in resources:
                    filename = r.get('output_filename') or r.get('resource_name', 'file')
                    filepath = os.path.join(output_dir, filename)
                    if os.path.exists(filepath):
                        file_size = os.path.getsize(filepath)
                        self.db.mark_resource_downloaded(r['id'], file_size)
                
                return True
            else:
                print(f"aria2c返回码: {result.returncode}")
                print(f"aria2c stderr: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("aria2c下载超时")
            return False
        except Exception as e:
            print(f"下载失败: {e}")
            return False
    
    def download_product_resources(self, product_id: str, output_dir: str = None,
                                     resource_type: str = None,
                                     progress_callback: Callable = None) -> Dict:
        """下载指定商品的资源"""
        if output_dir is None:
            product = self.db.get_product(product_id)
            if product and product.get('output_path'):
                output_dir = product['output_path']
            else:
                output_dir = os.path.join(self.output_base_dir, product_id)
        
        resources = self.get_pending_resources(product_id, resource_type)
        
        if not resources:
            return {'success': True, 'message': '没有待下载的资源', 'count': 0}
        
        success = self.download_with_aria2c(resources, output_dir, progress_callback)
        
        return {
            'success': success,
            'message': '下载完成' if success else '下载失败',
            'count': len(resources)
        }
    
    def download_all_pending(self, progress_callback: Callable = None) -> Dict:
        """下载所有待下载资源"""
        stats = self.get_download_stats()
        pending_count = stats.get('pending', 0)
        
        if pending_count == 0:
            return {'success': True, 'message': '没有待下载的资源', 'total': 0}
        
        products = self.db.query('''
            SELECT DISTINCT product_id FROM resources 
            WHERE downloaded = FALSE
            ORDER BY created_at ASC
        ''')
        
        total_downloaded = 0
        failed_products = []
        
        for p in products:
            product_id = p['product_id']
            result = self.download_product_resources(product_id, progress_callback=progress_callback)
            
            if result['success']:
                total_downloaded += result['count']
            else:
                failed_products.append(product_id)
        
        return {
            'success': len(failed_products) == 0,
            'message': f'下载完成: {total_downloaded}个文件',
            'total': total_downloaded,
            'failed': failed_products
        }
    
    def retry_failed(self, progress_callback: Callable = None) -> Dict:
        """重试失败的下载"""
        return self.download_all_pending(progress_callback)
    
    def get_product_download_status(self, product_id: str) -> Dict:
        """获取商品下载状态"""
        stats = self.get_download_stats(product_id)
        resources = self.db.get_resources_by_type(product_id)
        
        return {
            'stats': stats,
            'resources': resources
        }
    
    def clean_small_files(self, min_size: int = 1024):
        """清理小文件"""
        cleaned = 0
        for f in os.listdir(self.output_base_dir):
            filepath = os.path.join(self.output_base_dir, f)
            if os.path.isfile(filepath) and os.path.getsize(filepath) < min_size:
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webp')):
                    os.remove(filepath)
                    cleaned += 1
        return cleaned


if __name__ == "__main__":
    if not HAS_DUCKDB:
        print("DuckDB未安装，请运行: pip install duckdb")
        sys.exit(1)
    
    db = Database()
    downloader = ResourceDownloader(db)
    
    stats = downloader.get_download_stats()
    print(f"下载统计: {stats}")
    
    if stats.get('pending', 0) > 0:
        print("开始下载待处理资源...")
        result = downloader.download_all_pending()
        print(f"下载结果: {result}")
    else:
        print("没有待下载的资源")
