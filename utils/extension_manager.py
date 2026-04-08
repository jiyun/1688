#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扩展管理模块 - 管理浏览器驱动
"""

import os
import json
import subprocess
import shutil
import zipfile
import re
from typing import Optional, Tuple, List
from pathlib import Path


def find_chrome_executable():
    """查找 Chrome 浏览器可执行文件"""
    chrome_paths = [
        os.path.join(os.environ.get('PROGRAMFILES', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
        os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
    ]
    
    for path in chrome_paths:
        if os.path.exists(path):
            return path
    return None


def find_edge_executable():
    """查找 Edge 浏览器可执行文件"""
    edge_paths = [
        os.path.join(os.environ.get('PROGRAMFILES', ''), 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
        os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
    ]
    
    for path in edge_paths:
        if os.path.exists(path):
            return path
    return None


class ExtensionManager:
    """扩展管理器"""
    
    def __init__(self, project_dir: str = None):
        if project_dir is None:
            project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.project_dir = project_dir
        self.tools_dir = os.path.join(project_dir, 'tools')
        self.extensions_dir = os.path.join(project_dir, 'utils', 'extensions')
        self.chromedriver_dir = os.path.join(self.tools_dir, 'chromedriver-win64')
    
    def check_chromedriver(self) -> bool:
        """检查 ChromeDriver 是否存在"""
        exe_path = os.path.join(self.chromedriver_dir, 'chromedriver.exe')
        return os.path.exists(exe_path)
    
    def check_browser(self) -> bool:
        """检查浏览器是否安装"""
        return find_chrome_executable() is not None or find_edge_executable() is not None
    
    def get_status(self) -> dict:
        """获取所有组件状态"""
        return {
            'chromedriver': self.check_chromedriver(),
            'chrome': find_chrome_executable() is not None,
            'edge': find_edge_executable() is not None
        }


def check_dependencies() -> Tuple[bool, str]:
    """检查依赖状态（便捷函数）"""
    manager = ExtensionManager()
    status = manager.get_status()
    
    missing = []
    if not status['chromedriver']:
        missing.append("ChromeDriver")
    if not status['chrome'] and not status['edge']:
        missing.append("浏览器 (Chrome 或 Edge)")
    
    if missing:
        return False, f"缺少: {', '.join(missing)}"
    return True, "所有依赖已就绪"


if __name__ == "__main__":
    manager = ExtensionManager()
    
    print("检查依赖状态...")
    status = manager.get_status()
    for name, installed in status.items():
        print(f"  {name}: {'已安装' if installed else '未安装'}")
    
    if not all(status.values()):
        print("\n缺少依赖，请确保已安装 Chrome 或 Edge 浏览器")
    else:
        print("\n所有依赖已就绪")
