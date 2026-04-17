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
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from utils.database import Database, HAS_DUCKDB
except ImportError:
    HAS_DUCKDB = False

from utils.exceptions import DownloadError, DatabaseError


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
            raise DatabaseError("DuckDB未安装")
        
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
                              progress_callback: Callable = None,
                              force: bool = False) -> bool:
        """使用aria2c下载资源 - 逐个下载
        
        Args:
            resources: 资源列表
            output_dir: 输出目录
            progress_callback: 进度回调
            force: 是否强制重新下载（忽略已存在的文件）
        """
        if not self.aria2c_path:
            print("aria2c未找到")
            return False
        
        if not resources:
            return True
        
        os.makedirs(output_dir, exist_ok=True)
        
        success_count = 0
        failed_count = 0
        
        for r in resources:
            url = r['resource_url']
            filename = r.get('output_filename') or r.get('resource_name', 'file')
            filepath = os.path.join(output_dir, filename)
            
            if not force and os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                if file_size > 0:
                    self.db.mark_resource_downloaded(r['id'], file_size)
                    success_count += 1
                    continue
            
            if force and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except:
                    pass
            
            self.db.mark_resource_pending(r['id'])
            
            cmd = [
                self.aria2c_path,
                '--console-log-level=warn',
                '-d', output_dir,
                '-o', filename,
                '-x', '16',
                '-s', '16',
                '-k', '1M',
                '--max-tries=3',
                '--retry-wait=2',
                '--timeout=60',
                '--continue=true',
                '--auto-file-renaming=false',
                url
            ]
            
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
                    timeout=120,
                    startupinfo=startupinfo,
                    creationflags=creationflags
                )
                
                if result.returncode == 0 and os.path.exists(filepath):
                    file_size = os.path.getsize(filepath)
                    self.db.mark_resource_downloaded(r['id'], file_size)
                    success_count += 1
                else:
                    print(f"下载失败: {filename}, returncode={result.returncode}")
                    failed_count += 1
                    
            except subprocess.TimeoutExpired:
                print(f"下载超时: {filename}")
                failed_count += 1
            except Exception as e:
                print(f"下载异常: {filename} - {e}")
                failed_count += 1
        
        print(f"下载完成: 成功 {success_count}, 失败 {failed_count}")
        return failed_count == 0
    
    def download_with_requests(self, resources: List[Dict], output_dir: str,
                                progress_callback: Callable = None,
                                force: bool = False) -> bool:
        if not HAS_REQUESTS:
            print("requests库未安装")
            return False
        
        if not resources:
            return True
        
        os.makedirs(output_dir, exist_ok=True)
        
        success_count = 0
        failed_count = 0
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://detail.1688.com/',
        }
        
        for r in resources:
            url = r['resource_url']
            filename = r.get('output_filename') or r.get('resource_name', 'file')
            filepath = os.path.join(output_dir, filename)
            
            if not force and os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                if file_size > 0:
                    self.db.mark_resource_downloaded(r['id'], file_size)
                    success_count += 1
                    continue
            
            if force and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except:
                    pass
            
            self.db.mark_resource_pending(r['id'])
            
            try:
                resp = requests.get(url, headers=headers, timeout=60, stream=True)
                resp.raise_for_status()
                
                with open(filepath, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                file_size = os.path.getsize(filepath)
                self.db.mark_resource_downloaded(r['id'], file_size)
                success_count += 1
                
            except Exception as e:
                print(f"下载失败: {filename} - {e}")
                failed_count += 1
        
        print(f"下载完成: 成功 {success_count}, 失败 {failed_count}")
        return failed_count == 0
    
    def download_product_resources(self, product_id: str, output_dir: str = None,
                                     resource_type: str = None,
                                     progress_callback: Callable = None,
                                     force: bool = False) -> Dict:
        """下载指定商品的资源
        
        Args:
            product_id: 商品ID
            output_dir: 输出目录
            resource_type: 资源类型过滤
            progress_callback: 进度回调
            force: 是否强制重新下载（忽略已存在的文件）
        """
        product = self.db.get_product(product_id)
        platform = product.get('platform', '1688') if product else '1688'
        
        if output_dir is None:
            if product and product.get('output_path'):
                output_dir = product['output_path']
            else:
                output_dir = os.path.join(self.output_base_dir, product_id)
        
        if force:
            resources = self.db.get_all_resources(product_id, resource_type)
        else:
            resources = self.get_pending_resources(product_id, resource_type)
        
        if not resources:
            self._create_url_shortcut(product_id, platform, output_dir)
            return {'success': True, 'message': '没有待下载的资源', 'count': 0}
        
        if self.aria2c_path:
            success = self.download_with_aria2c(resources, output_dir, progress_callback, force=force)
        else:
            print("aria2c未找到，使用requests下载")
            success = self.download_with_requests(resources, output_dir, progress_callback, force=force)
        
        if success:
            self._create_url_shortcut(product_id, platform, output_dir)
        
        return {
            'success': success,
            'message': '下载完成' if success else '下载失败',
            'count': len(resources)
        }
    
    def _create_url_shortcut(self, product_id: str, platform: str, output_dir: str) -> None:
        """创建URL快捷方式文件"""
        try:
            if platform == '京东':
                url = f"https://item.jd.com/{product_id}.html"
            else:
                url = f"https://detail.1688.com/offer/{product_id}.html"
            
            url_file = os.path.join(output_dir, '#URL.url')
            
            if os.path.exists(url_file):
                return
            
            os.makedirs(output_dir, exist_ok=True)
            
            content = f"""[DEFAULT]
BASEURL={url}
[InternetShortcut]
URL={url}
IconIndex=41
IconFile=C:\\WINDOWS\\system32\\shell32.dll
"""
            
            with open(url_file, 'w', encoding='utf-8') as f:
                f.write(content)
                
        except Exception as e:
            print(f"创建URL快捷方式失败: {e}")
    
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
    
    def clean_small_files(self, min_size: int = 1024) -> int:
        """清理小文件"""
        cleaned = 0
        for f in os.listdir(self.output_base_dir):
            filepath = os.path.join(self.output_base_dir, f)
            if os.path.isfile(filepath) and os.path.getsize(filepath) < min_size:
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif', '.mp4')):
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
