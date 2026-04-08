#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扩展管理模块 - 管理 SingleFile 扩展和 Companion
"""

import os
import json
import subprocess
import shutil
import zipfile
import re
from typing import Optional, Tuple, List
from pathlib import Path


class ExtensionManager:
    """扩展管理器"""
    
    SINGLEFILE_REPO = "https://github.com/gildas-lormeau/SingleFile-MV3/archive/refs/heads/main.zip"
    COMPANION_REPO = "https://github.com/gildas-lormeau/single-file-companion-lite/raw/main/install/chromium-win.zip"
    
    def __init__(self, project_dir: str = None):
        if project_dir is None:
            project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.project_dir = project_dir
        self.tools_dir = os.path.join(project_dir, 'tools')
        self.extensions_dir = os.path.join(project_dir, 'utils', 'extensions')
        
        self.singlefile_dir = os.path.join(self.tools_dir, 'SingleFile-MV3-main')
        self.companion_dir = os.path.join(self.tools_dir, 'companion')
        self.chromedriver_dir = os.path.join(self.tools_dir, 'chromedriver-win64')
    
    def check_singlefile(self) -> bool:
        """检查 SingleFile 扩展是否存在"""
        manifest_path = os.path.join(self.singlefile_dir, 'manifest.json')
        lib_dir = os.path.join(self.singlefile_dir, 'lib')
        
        if not os.path.exists(manifest_path):
            return False
        
        if not os.path.exists(lib_dir) or not os.listdir(lib_dir):
            return False
        
        return True
    
    def check_companion(self) -> bool:
        """检查 Companion 是否存在"""
        exe_path = os.path.join(self.companion_dir, 'singlefile_companion_lite.exe')
        json_path = os.path.join(self.companion_dir, 'singlefile_companion.json')
        return os.path.exists(exe_path) and os.path.exists(json_path)
    
    def check_chromedriver(self) -> bool:
        """检查 ChromeDriver 是否存在"""
        exe_path = os.path.join(self.chromedriver_dir, 'chromedriver.exe')
        return os.path.exists(exe_path)
    
    def check_companion_registry(self) -> bool:
        """检查 Companion 注册表是否已安装"""
        try:
            result = subprocess.run(
                ['reg', 'query', 'HKEY_CURRENT_USER\\Software\\Google\\Chrome\\NativeMessagingHosts\\singlefile_companion'],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def download_file(self, url: str, output_path: str, progress_callback=None) -> bool:
        """下载文件"""
        try:
            import requests
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)
            
            return True
        except Exception as e:
            print(f"下载失败: {e}")
            return False
    
    def download_singlefile(self, progress_callback=None) -> bool:
        """下载 SingleFile 扩展"""
        if self.check_singlefile():
            return True
        
        print("正在下载 SingleFile 扩展...")
        
        zip_path = os.path.join(self.tools_dir, 'SingleFile-MV3.zip')
        
        if not self.download_file(self.SINGLEFILE_REPO, zip_path, progress_callback):
            return False
        
        print("正在解压...")
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(self.tools_dir)
            os.remove(zip_path)
        except Exception as e:
            print(f"解压失败: {e}")
            return False
        
        print("正在构建扩展...")
        if not self.build_singlefile():
            print("构建失败，但扩展可能仍可用")
        
        self.apply_singlefile_patch()
        
        return self.check_singlefile()
    
    def build_singlefile(self) -> bool:
        """构建 SingleFile 扩展"""
        try:
            npm_path = shutil.which('npm')
            if not npm_path:
                print("npm 未找到，跳过构建")
                return False
            
            result = subprocess.run(
                [npm_path, 'install'],
                cwd=self.singlefile_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                print(f"npm install 失败: {result.stderr}")
                return False
            
            result = subprocess.run(
                [npm_path, 'run', 'build'],
                cwd=self.singlefile_dir,
                capture_output=True,
                text=True,
                timeout=120,
                shell=True
            )
            
            if result.returncode != 0:
                print(f"npm build 失败: {result.stderr}")
                return False
            
            return True
        except Exception as e:
            print(f"构建失败: {e}")
            return False
    
    def apply_singlefile_patch(self):
        """应用 SingleFile 配置补丁"""
        config_path = os.path.join(self.singlefile_dir, 'src', 'core', 'bg', 'config.js')
        patch_path = os.path.join(self.extensions_dir, 'singlefile-config-patch.js')
        
        if not os.path.exists(config_path):
            return False
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original = '''async function getProfile(profileName) {
\tconst profileKey = PROFILE_NAME_PREFIX + profileName;
\tconst data = await configStorage.get([profileKey]);
\treturn data[profileKey];
}'''
            
            patched = '''async function getProfile(profileName) {
\tconst profileKey = PROFILE_NAME_PREFIX + profileName;
\tconst data = await configStorage.get([profileKey]);
\tconst profile = data[profileKey];
\tif (profile) {
\t\tprofile.saveOriginalURLs = true;
\t}
\treturn profile;
}'''
            
            if original in content:
                content = content.replace(original, patched)
                with open(config_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print("已应用 saveOriginalURLs 补丁")
                return True
            else:
                print("补丁可能已应用或代码结构已变化")
                return True
                
        except Exception as e:
            print(f"应用补丁失败: {e}")
            return False
    
    def download_companion(self, progress_callback=None) -> bool:
        """下载 Companion"""
        if self.check_companion():
            return True
        
        print("正在下载 Companion...")
        
        os.makedirs(self.companion_dir, exist_ok=True)
        zip_path = os.path.join(self.tools_dir, 'companion.zip')
        
        if not self.download_file(self.COMPANION_REPO, zip_path, progress_callback):
            return False
        
        print("正在解压...")
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(self.companion_dir)
            os.remove(zip_path)
        except Exception as e:
            print(f"解压失败: {e}")
            return False
        
        self.update_companion_config()
        
        return self.check_companion()
    
    def update_companion_config(self, extension_id: str = None):
        """更新 Companion 配置"""
        json_path = os.path.join(self.companion_dir, 'singlefile_companion.json')
        options_path = os.path.join(self.companion_dir, 'options.json')
        
        exe_path = os.path.join(self.companion_dir, 'singlefile_companion_lite.exe')
        
        allowed_origins = [
            "chrome-extension://mpiodijhokgodhhofbcjdecpffjipkle/",
            "chrome-extension://efnbkdcfmcmnhlkaijjjmhjjgladedno/",
        ]
        
        if extension_id:
            allowed_origins.insert(0, f"chrome-extension://{extension_id}/")
        
        companion_config = {
            "name": "singlefile_companion",
            "description": "SingleFile Companion Lite",
            "path": exe_path.replace('\\', '\\\\'),
            "type": "stdio",
            "allowed_origins": allowed_origins
        }
        
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(companion_config, f, indent=4)
            
            save_path = os.path.join(self.project_dir, 'utils', 'products').replace('\\', '\\\\')
            options_config = {
                "savePath": save_path + '\\\\'
            }
            with open(options_path, 'w', encoding='utf-8') as f:
                json.dump(options_config, f, indent=4)
            
            print("Companion 配置已更新")
            return True
        except Exception as e:
            print(f"更新配置失败: {e}")
            return False
    
    def install_companion_registry(self) -> bool:
        """安装 Companion 注册表"""
        json_path = os.path.join(self.companion_dir, 'singlefile_companion.json')
        
        if not os.path.exists(json_path):
            print("Companion 配置文件不存在")
            return False
        
        try:
            result = subprocess.run(
                ['reg', 'add', 'HKEY_CURRENT_USER\\Software\\Google\\Chrome\\NativeMessagingHosts\\singlefile_companion',
                 '/ve', '/t', 'REG_SZ', '/d', json_path, '/f'],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if result.returncode == 0:
                print("Companion 注册表已安装")
                return True
            else:
                print(f"注册表安装失败: {result.stderr}")
                return False
        except Exception as e:
            print(f"注册表安装失败: {e}")
            return False
    
    def uninstall_companion_registry(self) -> bool:
        """卸载 Companion 注册表"""
        try:
            result = subprocess.run(
                ['reg', 'delete', 'HKEY_CURRENT_USER\\Software\\Google\\Chrome\\NativeMessagingHosts\\singlefile_companion', '/f'],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def get_extension_id(self) -> Optional[str]:
        """获取 SingleFile 扩展 ID（需要启动浏览器）"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service as ChromeService
            
            user_data_dir = os.path.join(self.tools_dir, 'browser_temp_profile')
            if os.path.exists(user_data_dir):
                shutil.rmtree(user_data_dir)
            os.makedirs(user_data_dir, exist_ok=True)
            
            options = Options()
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument(f'--user-data-dir={user_data_dir}')
            options.add_argument(f'--load-extension={self.singlefile_dir}')
            
            chromedriver_path = os.path.join(self.chromedriver_dir, 'chromedriver.exe')
            
            if os.path.exists(chromedriver_path):
                service = ChromeService(executable_path=chromedriver_path)
                driver = webdriver.Chrome(options=options, service=service)
            else:
                driver = webdriver.Chrome(options=options)
            
            try:
                driver.get('chrome://extensions/')
                import time
                time.sleep(2)
                
                items = driver.find_elements('tag name', 'extensions-item')
                for item in items:
                    ext_id = item.get_attribute('id')
                    ext_name = item.get_attribute('name')
                    if 'SingleFile' in ext_name:
                        return ext_id
            finally:
                driver.quit()
                if os.path.exists(user_data_dir):
                    shutil.rmtree(user_data_dir)
            
            return None
        except Exception as e:
            print(f"获取扩展 ID 失败: {e}")
            return None
    
    def setup_all(self, progress_callback=None) -> Tuple[bool, str]:
        """设置所有依赖"""
        messages = []
        
        if not self.check_singlefile():
            if self.download_singlefile(progress_callback):
                messages.append("SingleFile 扩展已安装")
            else:
                return False, "SingleFile 扩展安装失败"
        else:
            messages.append("SingleFile 扩展已存在")
        
        if not self.check_companion():
            if self.download_companion(progress_callback):
                messages.append("Companion 已安装")
            else:
                return False, "Companion 安装失败"
        else:
            messages.append("Companion 已存在")
        
        if not self.check_companion_registry():
            if self.install_companion_registry():
                messages.append("Companion 注册表已安装")
            else:
                return False, "Companion 注册表安装失败"
        else:
            messages.append("Companion 注册表已存在")
        
        return True, "\n".join(messages)
    
    def get_status(self) -> dict:
        """获取所有组件状态"""
        return {
            'singlefile': self.check_singlefile(),
            'companion': self.check_companion(),
            'chromedriver': self.check_chromedriver(),
            'companion_registry': self.check_companion_registry()
        }


def check_dependencies() -> Tuple[bool, str]:
    """检查依赖状态（便捷函数）"""
    manager = ExtensionManager()
    status = manager.get_status()
    
    missing = []
    if not status['singlefile']:
        missing.append("SingleFile 扩展")
    if not status['companion']:
        missing.append("Companion")
    if not status['chromedriver']:
        missing.append("ChromeDriver")
    if not status['companion_registry']:
        missing.append("Companion 注册表")
    
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
        print("\n开始安装缺失的依赖...")
        success, message = manager.setup_all()
        print(f"\n结果: {message}")
    else:
        print("\n所有依赖已就绪")
