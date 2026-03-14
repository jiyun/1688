#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
版本检测和升级管理模块
"""

import json
import os
import sys
import hashlib
import tempfile
import zipfile
import shutil
from datetime import datetime
from typing import Dict, Optional, Tuple
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

try:
    from config import UPDATE_CONF
except ImportError:
    UPDATE_CONF = {
        'check_on_startup': True,
        'check_interval': 86400,
        'timeout': 10,
        'github_api': 'https://api.github.com/repos/jiyun/1688',
        'github_raw': 'https://raw.githubusercontent.com/jiyun/1688',
        'gitee_api': 'https://gitee.com/api/v5/repos/jiyunui/1688',
        'gitee_raw': 'https://gitee.com/jiyunui/1688/raw',
        'version_file': 'version.json',
        'changelog_file': 'CHANGELOG.md',
        'download_dir': 'updates',
    }

try:
    from utils.version import __version__, VERSION_INFO
except ImportError:
    __version__ = "0.0.0"
    VERSION_INFO = {}


class VersionInfo:
    """版本信息类"""
    
    def __init__(self, version: str, release_date: str = None, 
                 download_urls: Dict = None, changelog: str = None,
                 mandatory: bool = False, breaking_changes: bool = False):
        self.version = version
        self.release_date = release_date
        self.download_urls = download_urls or {}
        self.changelog = changelog
        self.mandatory = mandatory
        self.breaking_changes = breaking_changes
    
    def __str__(self):
        return f"v{self.version} ({self.release_date})"
    
    @staticmethod
    def parse_version(version_str: str) -> Tuple[int, ...]:
        """解析版本号为元组"""
        try:
            return tuple(map(int, version_str.split('.')))
        except:
            return (0, 0, 0)
    
    def is_newer_than(self, other_version: str) -> bool:
        """检查是否比指定版本新"""
        return self.parse_version(self.version) > self.parse_version(other_version)


class UpdateChecker:
    """版本检测器"""
    
    def __init__(self, use_mirror: bool = False):
        self.use_mirror = use_mirror
        self.timeout = UPDATE_CONF.get('timeout', 10)
        self.last_check_file = os.path.join(tempfile.gettempdir(), '1688_updater_last_check')
    
    def _get_api_url(self) -> str:
        """获取API URL"""
        if self.use_mirror:
            return UPDATE_CONF['gitee_api']
        return UPDATE_CONF['github_api']
    
    def _get_raw_url(self) -> str:
        """获取Raw文件URL"""
        if self.use_mirror:
            return UPDATE_CONF['gitee_raw']
        return UPDATE_CONF['github_raw']
    
    def _fetch_url(self, url: str) -> Optional[str]:
        """获取URL内容"""
        try:
            request = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urlopen(request, timeout=self.timeout) as response:
                return response.read().decode('utf-8')
        except (URLError, HTTPError, Exception) as e:
            print(f"获取URL失败: {url}, 错误: {e}")
            return None
    
    def _fetch_json(self, url: str) -> Optional[Dict]:
        """获取JSON数据"""
        content = self._fetch_url(url)
        if content:
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return None
        return None
    
    def should_check(self) -> bool:
        """检查是否应该进行版本检测"""
        if not os.path.exists(self.last_check_file):
            return True
        
        try:
            with open(self.last_check_file, 'r') as f:
                last_check = float(f.read().strip())
            interval = UPDATE_CONF.get('check_interval', 86400)
            return (datetime.now().timestamp() - last_check) > interval
        except:
            return True
    
    def _save_last_check(self):
        """保存最后检测时间"""
        try:
            with open(self.last_check_file, 'w') as f:
                f.write(str(datetime.now().timestamp()))
        except:
            pass
    
    def check_update(self, force: bool = False) -> Optional[VersionInfo]:
        """检查更新
        
        Args:
            force: 是否强制检查（忽略间隔）
            
        Returns:
            VersionInfo: 如果有新版本返回版本信息，否则返回None
        """
        if not force and not self.should_check():
            return None
        
        self._save_last_check()
        
        version_url = f"{self._get_raw_url()}/main/version.json"
        data = self._fetch_json(version_url)
        
        if not data:
            if not self.use_mirror:
                self.use_mirror = True
                return self.check_update(force=True)
            return None
        
        version_info = VersionInfo(
            version=data.get('version', '0.0.0'),
            release_date=data.get('release_date'),
            download_urls=data.get('download_url', {}),
            changelog=data.get('changelog'),
            mandatory=data.get('mandatory', False),
            breaking_changes=data.get('breaking_changes', False)
        )
        
        if version_info.is_newer_than(__version__):
            return version_info
        
        return None
    
    def get_changelog(self) -> Optional[str]:
        """获取更新日志"""
        changelog_url = f"{self._get_raw_url()}/main/CHANGELOG.md"
        content = self._fetch_url(changelog_url)
        return content


class UpdateDownloader:
    """更新下载器"""
    
    def __init__(self, use_mirror: bool = False):
        self.use_mirror = use_mirror
        self.timeout = UPDATE_CONF.get('timeout', 10)
        self.download_dir = UPDATE_CONF.get('download_dir', 'updates')
    
    def _get_download_url(self, version_info: VersionInfo) -> Optional[str]:
        """获取下载URL"""
        urls = version_info.download_urls
        if self.use_mirror:
            return urls.get('gitee') or urls.get('github')
        return urls.get('github') or urls.get('gitee')
    
    def download_update(self, version_info: VersionInfo, 
                        progress_callback=None) -> Optional[str]:
        """下载更新包
        
        Args:
            version_info: 版本信息
            progress_callback: 进度回调函数 callback(downloaded, total)
            
        Returns:
            str: 下载文件路径，失败返回None
        """
        url = self._get_download_url(version_info)
        if not url:
            return None
        
        os.makedirs(self.download_dir, exist_ok=True)
        filename = f"v{version_info.version}.zip"
        filepath = os.path.join(self.download_dir, filename)
        
        try:
            request = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urlopen(request, timeout=self.timeout) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                chunk_size = 8192
                
                with open(filepath, 'wb') as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)
            
            return filepath
        except Exception as e:
            print(f"下载更新失败: {e}")
            if os.path.exists(filepath):
                os.remove(filepath)
            return None
    
    def verify_checksum(self, filepath: str, expected_sha256: str) -> bool:
        """验证文件校验和"""
        if not expected_sha256 or not os.path.exists(filepath):
            return False
        
        sha256_hash = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest() == expected_sha256
    
    def extract_update(self, filepath: str, target_dir: str = None) -> bool:
        """解压更新包"""
        if not os.path.exists(filepath):
            return False
        
        if target_dir is None:
            target_dir = os.path.dirname(filepath)
        
        try:
            with zipfile.ZipFile(filepath, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
            return True
        except Exception as e:
            print(f"解压更新失败: {e}")
            return False


def check_for_updates(silent: bool = True) -> Optional[VersionInfo]:
    """检查更新的便捷函数
    
    Args:
        silent: 是否静默模式（不打印信息）
        
    Returns:
        VersionInfo: 如果有新版本返回版本信息
    """
    checker = UpdateChecker()
    
    version_info = checker.check_update()
    if not version_info:
        if not silent:
            checker.use_mirror = True
            version_info = checker.check_update(force=True)
        else:
            return None
    
    return version_info


if __name__ == "__main__":
    print(f"当前版本: {__version__}")
    
    print("\n检查更新中...")
    version_info = check_for_updates(silent=False)
    
    if version_info:
        print(f"\n发现新版本: {version_info}")
        print(f"发布日期: {version_info.release_date}")
        print(f"强制更新: {'是' if version_info.mandatory else '否'}")
        print(f"重大变更: {'是' if version_info.breaking_changes else '否'}")
    else:
        print("\n当前已是最新版本")
