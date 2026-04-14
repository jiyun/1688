#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cookie 管理模块 - 检测平台登录状态和 Cookie 有效期
"""

import os
import json
import time
import sqlite3
import shutil
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LoginStatus:
    """登录状态数据类"""
    platform: str
    is_logged_in: bool
    username: Optional[str] = None
    cookie_count: int = 0
    expires_at: Optional[datetime] = None
    last_checked: Optional[datetime] = None
    
    @property
    def expires_in_seconds(self) -> Optional[int]:
        """返回距离过期的秒数"""
        if self.expires_at is None:
            return None
        delta = self.expires_at - datetime.now()
        return max(0, int(delta.total_seconds()))
    
    @property
    def expires_in_text(self) -> str:
        """返回人类可读的剩余时间"""
        seconds = self.expires_in_seconds
        if seconds is None:
            return "未知"
        if seconds == 0:
            return "已过期"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        
        if hours > 24:
            days = hours // 24
            return f"{days}天"
        elif hours > 0:
            return f"{hours}小时{minutes}分钟"
        else:
            return f"{minutes}分钟"


class CookieManager:
    """Cookie 管理器"""
    
    PLATFORM_CONFIG = {
        '1688': {
            'domains': ['.1688.com', '1688.com', '.alibaba.com', '.alibaba-inc.com'],
            'key_cookies': ['_m_h5_tk', 'ctoken', 'isg', 'sg', 't', 'unb', 'uc1', 'uc3', 'uc4'],
            'login_check_url': 'https://www.1688.com',
            'chrome_profile': 'Default',
            'edge_profile': 'Default',
        },
        'jd': {
            'domains': ['.jd.com', 'jd.com', '.jd.hk'],
            'key_cookies': ['pt_key', 'pt_pin', 'pt_token'],
            'login_check_url': 'https://www.jd.com',
            'chrome_profile': 'Default',
            'edge_profile': 'Default',
        }
    }
    
    def __init__(self):
        self._cache: Dict[str, LoginStatus] = {}
        self._cache_time: Dict[str, float] = {}
        self._cache_ttl = 60
        
    def _get_project_browser_data_path(self) -> list:
        """获取项目目录下的浏览器数据路径"""
        paths = []
        try:
            project_dir = os.path.dirname(os.path.dirname(__file__))
            browser_data_dir = os.path.join(project_dir, 'tools', 'browser_data')
            
            if os.path.exists(browser_data_dir):
                for profile in ['Default', 'Profile 1', 'Profile 2']:
                    profile_dir = os.path.join(browser_data_dir, profile)
                    if os.path.exists(profile_dir):
                        cookies_path = os.path.join(profile_dir, 'Network', 'Cookies')
                        if os.path.exists(cookies_path):
                            paths.append(('project_browser', cookies_path))
                        cookies_path_old = os.path.join(profile_dir, 'Cookies')
                        if os.path.exists(cookies_path_old):
                            paths.append(('project_browser', cookies_path_old))
        except Exception:
            pass
        
        return paths
    
    def _get_chrome_cookie_paths(self) -> list:
        """获取 Chrome Cookie 文件路径"""
        paths = []
        local_app_data = os.environ.get('LOCALAPPDATA', '')
        
        chrome_base = os.path.join(local_app_data, 'Google', 'Chrome', 'User Data')
        for profile in ['Default', 'Profile 1', 'Profile 2']:
            profile_dir = os.path.join(chrome_base, profile)
            if os.path.exists(profile_dir):
                cookies_path = os.path.join(profile_dir, 'Network', 'Cookies')
                if os.path.exists(cookies_path):
                    paths.append(('chrome', cookies_path))
                cookies_path_old = os.path.join(profile_dir, 'Cookies')
                if os.path.exists(cookies_path_old):
                    paths.append(('chrome', cookies_path_old))
        
        return paths
    
    def _get_edge_cookie_paths(self) -> list:
        """获取 Edge Cookie 文件路径"""
        paths = []
        local_app_data = os.environ.get('LOCALAPPDATA', '')
        
        edge_base = os.path.join(local_app_data, 'Microsoft', 'Edge', 'User Data')
        for profile in ['Default', 'Profile 1', 'Profile 2']:
            profile_dir = os.path.join(edge_base, profile)
            if os.path.exists(profile_dir):
                cookies_path = os.path.join(profile_dir, 'Network', 'Cookies')
                if os.path.exists(cookies_path):
                    paths.append(('edge', cookies_path))
                cookies_path_old = os.path.join(profile_dir, 'Cookies')
                if os.path.exists(cookies_path_old):
                    paths.append(('edge', cookies_path_old))
        
        return paths
    
    def _get_cookie_db_paths(self) -> list:
        """获取所有浏览器 Cookie 数据库路径"""
        return self._get_project_browser_data_path() + self._get_chrome_cookie_paths() + self._get_edge_cookie_paths()
    
    def _copy_cookie_db(self, db_path: str) -> Optional[str]:
        """复制 Cookie 数据库到临时文件（避免锁定问题）"""
        try:
            temp_dir = os.path.join(os.environ.get('TEMP', '.'), 'cookie_manager')
            os.makedirs(temp_dir, exist_ok=True)
            
            temp_db = os.path.join(temp_dir, f'cookies_{int(time.time() * 1000)}.db')
            shutil.copy2(db_path, temp_db)
            
            return temp_db
        except Exception:
            return None
    
    def _query_cookies_from_db(self, db_path: str, domains: list) -> list:
        """从数据库查询指定域名的 Cookie"""
        cookies = []
        temp_db = self._copy_cookie_db(db_path)
        
        if not temp_db:
            return cookies
        
        try:
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            
            for domain in domains:
                try:
                    cursor.execute(
                        "SELECT name, value, expires_utc, host_key FROM cookies WHERE host_key LIKE ?",
                        (f'%{domain}%',)
                    )
                    
                    for row in cursor.fetchall():
                        name, value, expires_utc, host_key = row
                        cookies.append({
                            'name': name,
                            'value': value,
                            'expires_utc': expires_utc,
                            'domain': host_key
                        })
                except sqlite3.Error:
                    pass
            
            conn.close()
            
        except Exception:
            pass
        finally:
            try:
                os.remove(temp_db)
            except:
                pass
        
        return cookies
    
    def _chrome_time_to_datetime(self, chrome_time: int) -> Optional[datetime]:
        """将 Chrome 时间戳转换为 datetime
        
        Chrome 时间戳格式：
        - 旧格式：从 1601-01-01 开始的微秒数
        - 新格式：从 1601-01-01 开始的 100 纳秒数
        """
        if chrome_time is None or chrome_time == 0:
            return None
        
        try:
            if chrome_time == 86400000000000:
                return None
            
            if chrome_time > 10000000000000000:
                microseconds = chrome_time // 10
            else:
                microseconds = chrome_time
            
            if microseconds > 10**17:
                return None
            
            chrome_epoch = datetime(1601, 1, 1)
            delta = timedelta(microseconds=microseconds)
            result = chrome_epoch + delta
            
            if result.year < 2020 or result.year > 2100:
                return None
            
            return result
        except:
            return None
    
    def check_login_status(self, platform: str, force: bool = False) -> LoginStatus:
        """检查平台登录状态"""
        now = time.time()
        
        if not force and platform in self._cache:
            if now - self._cache_time.get(platform, 0) < self._cache_ttl:
                return self._cache[platform]
        
        config = self.PLATFORM_CONFIG.get(platform)
        if not config:
            return LoginStatus(platform=platform, is_logged_in=False)
        
        domains = config['domains']
        key_cookies = config['key_cookies']
        
        all_cookies = []
        db_paths = self._get_cookie_db_paths()
        
        for browser_type, db_path in db_paths:
            cookies = self._query_cookies_from_db(db_path, domains)
            all_cookies.extend(cookies)
        
        if not all_cookies:
            status = LoginStatus(
                platform=platform,
                is_logged_in=False,
                cookie_count=0,
                last_checked=datetime.now()
            )
            self._cache[platform] = status
            self._cache_time[platform] = now
            return status
        
        found_key_cookies = set()
        earliest_expiry: Optional[datetime] = None
        username = None
        
        for cookie in all_cookies:
            name = cookie.get('name', '')
            
            if name in key_cookies:
                found_key_cookies.add(name)
                
                if platform == '1688':
                    if name == 'unb' and cookie.get('value'):
                        username = cookie.get('value')
                elif platform == 'jd':
                    if name == 'pt_pin' and cookie.get('value'):
                        try:
                            import base64
                            username = base64.b64decode(cookie.get('value', '')).decode('utf-8', errors='ignore')
                        except:
                            username = cookie.get('value')
            
            expires_at = self._chrome_time_to_datetime(cookie.get('expires_utc'))
            if expires_at:
                if earliest_expiry is None or expires_at < earliest_expiry:
                    earliest_expiry = expires_at
        
        is_logged_in = len(found_key_cookies) >= 2
        
        if earliest_expiry and earliest_expiry < datetime.now():
            is_logged_in = False
        
        status = LoginStatus(
            platform=platform,
            is_logged_in=is_logged_in,
            username=username,
            cookie_count=len(all_cookies),
            expires_at=earliest_expiry,
            last_checked=datetime.now()
        )
        
        self._cache[platform] = status
        self._cache_time[platform] = now
        
        return status
    
    def get_all_platform_status(self, force: bool = False) -> Dict[str, LoginStatus]:
        """获取所有平台的登录状态"""
        result = {}
        for platform in self.PLATFORM_CONFIG.keys():
            result[platform] = self.check_login_status(platform, force)
        return result
    
    def check_login_from_driver(self, platform: str, driver) -> LoginStatus:
        """从 Selenium driver 检查登录状态"""
        config = self.PLATFORM_CONFIG.get(platform)
        if not config:
            return LoginStatus(platform=platform, is_logged_in=False)
        
        key_cookies = config['key_cookies']
        
        try:
            selenium_cookies = driver.get_cookies()
        except Exception:
            return LoginStatus(platform=platform, is_logged_in=False)
        
        found_key_cookies = set()
        username = None
        
        for cookie in selenium_cookies:
            name = cookie.get('name', '')
            
            if name in key_cookies:
                found_key_cookies.add(name)
                
                if platform == '1688':
                    if name == 'unb' and cookie.get('value'):
                        username = cookie.get('value')
                elif platform == 'jd':
                    if name == 'pt_pin' and cookie.get('value'):
                        try:
                            import base64
                            username = base64.b64decode(cookie.get('value', '')).decode('utf-8', errors='ignore')
                        except:
                            username = cookie.get('value')
        
        is_logged_in = len(found_key_cookies) >= 2
        
        status = LoginStatus(
            platform=platform,
            is_logged_in=is_logged_in,
            username=username,
            cookie_count=len(selenium_cookies),
            expires_at=None,
            last_checked=datetime.now()
        )
        
        self._cache[platform] = status
        self._cache_time[platform] = time.time()
        
        return status
    
    def clear_cache(self):
        """清除缓存"""
        self._cache.clear()
        self._cache_time.clear()


_cookie_manager: Optional[CookieManager] = None


def get_cookie_manager() -> CookieManager:
    """获取全局 Cookie 管理器实例"""
    global _cookie_manager
    if _cookie_manager is None:
        _cookie_manager = CookieManager()
    return _cookie_manager


def check_platform_login(platform: str, force: bool = False) -> LoginStatus:
    """检查指定平台的登录状态"""
    return get_cookie_manager().check_login_status(platform, force)


def get_login_status_icon(is_logged_in: bool) -> str:
    """获取登录状态图标（SVG 字符串）"""
    if is_logged_in:
        return '''<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#4CAF50" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>'''
    else:
        return '''<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f44336" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>'''


def get_login_status_color(is_logged_in: bool) -> str:
    """获取登录状态颜色"""
    return "#4CAF50" if is_logged_in else "#f44336"
