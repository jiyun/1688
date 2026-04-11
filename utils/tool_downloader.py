# 工具下载器 - 自动下载所需工具和检查Python扩展
import os
import sys
import urllib.request
import zipfile
import shutil
import subprocess
from pathlib import Path

TOOLS_CONFIG = {
    'aria2c': {
        'windows': {
            'urls': [
                ('https://github.com/aria2/aria2/releases/download/release-1.37.0/aria2-1.37.0-win-64bit-build1.zip', 'zip', None),
            ],
            'fallback_urls': [
                'https://github.com/uup-dump/containment-zone/raw/master/aria2c.exe',
                'https://ghproxy.com/https://github.com/aria2/aria2/releases/download/release-1.37.0/aria2-1.37.0-win-64bit-build1.zip',
            ],
            'filename': 'aria2c.exe'
        }
    }
}

REQUIRED_PACKAGES = {
    'PIL': 'Pillow',
    'bs4': 'beautifulsoup4',
    'lxml': 'lxml',
    'pandas': 'pandas',
    'duckdb': 'duckdb',
    'customtkinter': 'customtkinter',
    'selenium': 'selenium',
    'webdriver_manager': 'webdriver-manager',
    'psutil': 'psutil',
    'pyperclip': 'pyperclip',
    'packaging': 'packaging',
    'requests': 'requests',
}

OPTIONAL_PACKAGES = {
    'tkinterweb': 'tkinterweb',
    'markdown': 'markdown',
    'cv2': 'opencv-python',
    'moviepy': 'moviepy',
}

def get_tools_dir():
    """获取工具目录"""
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, 'tools')

def download_file(url, dest_path, show_progress=True):
    """下载文件"""
    try:
        if show_progress:
            print(f"正在下载: {os.path.basename(dest_path)}")
            print(f"  URL: {url}")
        
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        downloaded = 0
        chunk_size = 8192
        
        with urllib.request.urlopen(req, timeout=60) as response:
            total_size = int(response.headers.get('Content-Length', 0))
            
            with open(dest_path, 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if show_progress and total_size > 0:
                        percent = min(100, downloaded * 100 / total_size)
                        bar_length = 40
                        filled = int(bar_length * percent / 100)
                        bar = '█' * filled + '-' * (bar_length - filled)
                        print(f'\r  [{bar}] {percent:.1f}%', end='', flush=True)
        
        if show_progress:
            print()
        return True
    except Exception as e:
        print(f"\n下载失败: {e}")
        if os.path.exists(dest_path):
            os.remove(dest_path)
        return False

def find_aria2c_in_zip(zip_path):
    """在ZIP文件中查找aria2c.exe"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for name in zf.namelist():
                if name.endswith('aria2c.exe'):
                    return name
    except Exception as e:
        print(f"读取ZIP文件失败: {e}")
    return None

def extract_from_zip(zip_path, extract_file, dest_path):
    """从ZIP文件中提取单个文件"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            with zf.open(extract_file) as src:
                with open(dest_path, 'wb') as dst:
                    shutil.copyfileobj(src, dst)
        return True
    except Exception as e:
        print(f"解压失败: {e}")
        return False

def check_tool_exists(tool_name):
    """检查工具是否存在"""
    tools_dir = get_tools_dir()
    config = TOOLS_CONFIG.get(tool_name, {})
    platform_config = config.get('windows', {})
    filename = platform_config.get('filename', f'{tool_name}.exe')
    tool_path = os.path.join(tools_dir, filename)
    return os.path.exists(tool_path), tool_path

def download_tool(tool_name, use_fallback=True):
    """下载指定工具"""
    config = TOOLS_CONFIG.get(tool_name)
    if not config:
        print(f"未知工具: {tool_name}")
        return None
    
    tools_dir = get_tools_dir()
    os.makedirs(tools_dir, exist_ok=True)
    
    platform_config = config.get('windows', {})
    if not platform_config:
        print(f"不支持当前平台")
        return None
    
    filename = platform_config.get('filename', f'{tool_name}.exe')
    dest_path = os.path.join(tools_dir, filename)
    
    if os.path.exists(dest_path):
        print(f"{tool_name} 已存在: {dest_path}")
        return dest_path
    
    urls = platform_config.get('urls', [])
    
    for url, url_type, extract_path in urls:
        if url_type == 'direct':
            if download_file(url, dest_path):
                print(f"下载完成: {dest_path}")
                return dest_path
        elif url_type == 'zip':
            zip_path = os.path.join(tools_dir, f'{tool_name}.zip')
            if download_file(url, zip_path):
                extract_file = find_aria2c_in_zip(zip_path)
                if extract_file:
                    if extract_from_zip(zip_path, extract_file, dest_path):
                        os.remove(zip_path)
                        print(f"下载完成: {dest_path}")
                        return dest_path
                    else:
                        os.remove(zip_path)
                else:
                    print("ZIP文件中未找到aria2c.exe")
                    os.remove(zip_path)
    
    if use_fallback:
        fallback_urls = platform_config.get('fallback_urls', [])
        for url in fallback_urls:
            print(f"尝试备用下载源...")
            if url.endswith('.zip'):
                zip_path = os.path.join(tools_dir, f'{tool_name}.zip')
                if download_file(url, zip_path):
                    extract_file = find_aria2c_in_zip(zip_path)
                    if extract_file:
                        if extract_from_zip(zip_path, extract_file, dest_path):
                            os.remove(zip_path)
                            print(f"下载完成: {dest_path}")
                            return dest_path
                        else:
                            os.remove(zip_path)
                    else:
                        os.remove(zip_path)
            else:
                if download_file(url, dest_path):
                    print(f"下载完成: {dest_path}")
                    return dest_path
    
    return None

def ensure_aria2c():
    """确保 aria2c 可用"""
    exists, path = check_tool_exists('aria2c')
    if exists:
        return path
    
    print("aria2c 不存在，正在自动下载...")
    return download_tool('aria2c')

def get_aria2c_path():
    """获取 aria2c 路径"""
    exists, path = check_tool_exists('aria2c')
    if exists:
        return path
    
    tools_dir = get_tools_dir()
    possible_paths = [
        os.path.join(tools_dir, 'aria2c.exe'),
        os.path.join(os.path.dirname(tools_dir), 'aria2c.exe'),
        'aria2c.exe',
        'aria2c'
    ]
    
    for p in possible_paths:
        if os.path.exists(p):
            return p
    
    return None

def check_package_installed(package_name):
    """检查Python包是否已安装"""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

def install_package(package_name):
    """安装Python包"""
    try:
        print(f"正在安装 {package_name}...")
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', package_name],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            print(f"{package_name} 安装成功")
            return True
        else:
            print(f"{package_name} 安装失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"安装 {package_name} 时出错: {e}")
        return False

def check_and_install_packages():
    """检查并安装所需的Python包"""
    print("\n=== 检查Python依赖 ===")
    results = {}
    
    for import_name, package_name in REQUIRED_PACKAGES.items():
        if check_package_installed(import_name):
            print(f"  {package_name}: 已安装")
            results[package_name] = True
        else:
            print(f"  {package_name}: 未安装，正在安装...")
            success = install_package(package_name)
            results[package_name] = success
    
    return results

def check_optional_packages():
    """检查可选Python包"""
    print("\n=== 检查可选依赖 ===")
    results = {}
    
    for import_name, package_name in OPTIONAL_PACKAGES.items():
        if check_package_installed(import_name):
            print(f"  {package_name}: 已安装")
            results[package_name] = True
        else:
            print(f"  {package_name}: 未安装 (可选)")
            results[package_name] = False
    
    return results

def install_optional_package(package_name):
    """安装可选Python包"""
    for import_name, pkg_name in OPTIONAL_PACKAGES.items():
        if pkg_name == package_name:
            return install_package(package_name)
    return False

def check_all_dependencies():
    """检查所有依赖（工具和Python包）"""
    print("=== 检查项目依赖 ===")
    
    tool_results = {}
    for tool_name in TOOLS_CONFIG:
        exists, path = check_tool_exists(tool_name)
        if exists:
            print(f"  {tool_name}: 已存在 ({path})")
            tool_results[tool_name] = True
        else:
            print(f"  {tool_name}: 不存在")
            tool_results[tool_name] = False
    
    package_results = check_and_install_packages()
    optional_results = check_optional_packages()
    
    missing_tools = [k for k, v in tool_results.items() if not v]
    missing_packages = [k for k, v in package_results.items() if not v]
    
    if missing_tools or missing_packages:
        print("\n=== 缺少的依赖 ===")
        if missing_tools:
            print(f"工具: {', '.join(missing_tools)}")
        if missing_packages:
            print(f"Python包: {', '.join(missing_packages)}")
        return False
    
    print("\n所有依赖已就绪")
    return True

def ensure_all_dependencies():
    """确保所有依赖可用，缺失则自动下载/安装"""
    missing_tools = []
    missing_packages = []
    
    for tool_name in TOOLS_CONFIG:
        exists, path = check_tool_exists(tool_name)
        if not exists:
            missing_tools.append(tool_name)
    
    for import_name, package_name in REQUIRED_PACKAGES.items():
        if not check_package_installed(import_name):
            missing_packages.append(package_name)
    
    if not missing_tools and not missing_packages:
        return
    
    print("=== 检查并安装依赖 ===")
    
    for tool_name in missing_tools:
        print(f"\n{tool_name} 不存在，正在下载...")
        path = download_tool(tool_name)
        if path:
            print(f"{tool_name} 下载完成: {path}")
        else:
            print(f"{tool_name} 下载失败")
    
    if missing_packages:
        print("\n=== 检查Python依赖 ===")
        for package_name in missing_packages:
            print(f"  {package_name}: 未安装，正在安装...")
            install_package(package_name)
    
    print("\n=== 依赖检查完成 ===")

def download_all_tools():
    """下载所有工具"""
    print("=== 检查并下载所需工具 ===")
    results = {}
    for tool_name in TOOLS_CONFIG:
        print(f"\n检查 {tool_name}...")
        path = download_tool(tool_name)
        results[tool_name] = path is not None
    return results

if __name__ == '__main__':
    ensure_all_dependencies()


class Downloader:
    """下载管理器"""
    
    def __init__(self, config, keep_avif=False, webp_support=False):
        self.config = config
        self.keep_avif = keep_avif
        self.webp_support = webp_support
    
    def _clean_duplicate_extension(self, url):
        """清理URL中的重复扩展名，如.jpg_b.jpg -> .jpg"""
        media_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif', '.bmp', '.mp4', '.avi', '.mov']

        for ext in media_extensions:
            ext_positions = []
            pos = url.lower().find(ext)
            while pos != -1:
                ext_positions.append((pos, pos + len(ext)))
                pos = url.lower().find(ext, pos + len(ext))

            if len(ext_positions) >= 2:
                last_pos, last_end = ext_positions[-1]
                second_last_pos, second_last_end = ext_positions[-2]

                if second_last_end < last_pos:
                    url = url[:second_last_end] + url[last_end:]

        return url

    def _clean_url(self, url):
        """清理URL，删除扩展名后的查询参数和重复扩展名
        
        JD平台：保留AVIF格式（如果keep_avif=True）
        阿里平台：保留WebP格式（如果webp_support=True）
        """
        url = self._clean_duplicate_extension(url)
        
        # JD平台AVIF处理
        if not self.keep_avif and url.endswith('.avif'):
            url = url[:-5]
        
        # 阿里平台WebP处理
        # 如果启用了WebP支持且URL以_.webp结尾
        if self.webp_support and url.endswith('_.webp'):
            pass  # 保留WebP格式
        elif url.endswith('_.webp'):
            url = url[:-6]  # 移除WebP后缀
        
        if '?' in url:
            base_url = url.split('?')[0]
            return base_url
        return url
    
    def generate_download_list(self, resources):
        """生成下载列表"""
        from os.path import splitext
        download_list = []
        
        for idx, (url, name) in enumerate(resources.get('main_images', [])):
            clean_url = self._clean_url(url)
            ext = splitext(clean_url)[1]
            if not ext:
                ext = '.jpg'
            output_name = f"{self.config['FILE_NAMING']['main_image_prefix']}{name}{ext}"
            download_list.append(f"{clean_url}\n out={output_name}")
        
        for idx, (url, name) in enumerate(resources.get('color_card_images', [])):
            clean_url = self._clean_url(url)
            ext = splitext(clean_url)[1]
            if not ext:
                ext = '.jpg'
            output_name = f"color_{name}{ext}"
            download_list.append(f"{clean_url}\n out={output_name}")
        
        for idx, url in enumerate(resources.get('detail_images', [])):
            clean_url = self._clean_url(url)
            ext = splitext(clean_url)[1]
            if not ext:
                ext = '.jpg'
            output_name = f"{self.config['FILE_NAMING']['detail_image_prefix']}{idx+1}{ext}"
            download_list.append(f"{clean_url}\n out={output_name}")
        
        for idx, url in enumerate(resources.get('videos', [])):
            clean_url = self._clean_url(url)
            ext = splitext(clean_url)[1]
            if not ext:
                ext = '.mp4'
            output_name = f"{self.config['FILE_NAMING']['video_prefix']}{idx+1}{ext}"
            download_list.append(f"{clean_url}\n out={output_name}")
        
        download_list = self._remove_duplicates(download_list)
        
        return download_list
    
    def _remove_duplicates(self, download_list):
        """去重下载列表"""
        unique_uris = {}
        for item in download_list:
            if '\n out=' in item:
                uri, out = item.split('\n out=')
                clean_uri = self._clean_url(uri)
                if clean_uri not in unique_uris:
                    unique_uris[clean_uri] = out
        new_list = [f"{uri}\n out={out}" for uri, out in unique_uris.items()]
        return new_list
    
    def clean_small_files(self, directory='.'):
        """清理小文件"""
        deleted_files = []
        min_size = self.config['DOWNLOAD_CONF']['min_file_size']
        
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path):
                # 支持更多图片格式：JPG, PNG, GIF, WebP, AVIF, 视频格式
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif', '.mp4', '.avi', '.mov')):
                    file_size = os.path.getsize(file_path)
                    if file_size < min_size:
                        os.remove(file_path)
                        deleted_files.append(file_path)
        
        return deleted_files
