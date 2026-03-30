#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1688 商品信息自动采集脚本
使用 Playwright 控制浏览器，支持加载 1688 官方插件和 SingleFile 扩展
"""

import subprocess
import sys
import os
import time
import re
import shutil
import glob
from datetime import datetime
from typing import List, Optional

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

def get_product_id_from_url(url: str) -> Optional[str]:
    """从URL中提取商品ID"""
    match = re.search(r'offer/(\d+)\.html', url)
    if match:
        return match.group(1)
    return None

def find_extensions():
    """查找已安装的浏览器扩展"""
    extensions = []
    
    edge_extensions = os.path.join(
        os.environ.get('LOCALAPPDATA', ''),
        'Microsoft', 'Edge', 'User Data', 'Default', 'Extensions'
    )
    
    if os.path.exists(edge_extensions):
        for item in os.listdir(edge_extensions):
            item_path = os.path.join(edge_extensions, item)
            if os.path.isdir(item_path):
                versions = [v for v in os.listdir(item_path) if v[0].isdigit()]
                if versions:
                    latest_version = sorted(versions)[-1]
                    ext_path = os.path.join(item_path, latest_version)
                    manifest_path = os.path.join(ext_path, 'manifest.json')
                    if os.path.exists(manifest_path):
                        extensions.append(ext_path)
    
    return extensions

class AutoCollector:
    """自动采集器"""
    
    def __init__(self, output_dir: str = 'products', headless: bool = False):
        # 使用绝对路径
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_dir)
        self.output_dir = output_dir
        self.headless = headless
        self.browser = None
        self.context = None
        self.playwright = None
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"创建输出目录: {output_dir}")
    
    def start_browser(self, extension_paths: List[str] = None):
        """启动浏览器，支持加载多个扩展"""
        if not HAS_PLAYWRIGHT:
            raise ImportError("请安装 playwright: pip install playwright && playwright install chromium")
        
        self.playwright = sync_playwright().start()
        
        args = ['--start-maximized']
        
        # 收集所有扩展路径
        extensions = []
        
        # 1. 1688-extension
        extension_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'tools', '1688-extension'
        )
        if os.path.exists(extension_dir):
            manifest_path = os.path.join(extension_dir, 'manifest.json')
            if os.path.exists(manifest_path):
                extensions.append(extension_dir)
                print(f"找到扩展: 1688-extension")
        
        # 2. SingleFile扩展 (Manifest V3)
        singlefile_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'tools', 'SingleFile-crx'
        )
        if os.path.exists(singlefile_dir):
            manifest_path = os.path.join(singlefile_dir, 'manifest.json')
            if os.path.exists(manifest_path):
                extensions.append(singlefile_dir)
                print(f"找到扩展: SingleFile (Manifest V3)")
        
        # 3. 外部传入的扩展路径
        if extension_paths:
            for ext_path in extension_paths:
                if os.path.exists(ext_path) and ext_path not in extensions:
                    extensions.append(ext_path)
        
        if extensions:
            ext_paths = ','.join(extensions)
            args.extend([
                f'--disable-extensions-except={ext_paths}',
                f'--load-extension={ext_paths}',
            ])
            print(f"加载扩展: {len(extensions)} 个")
        
        downloads_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'products'
        )
        os.makedirs(downloads_dir, exist_ok=True)
        
        try:
            self.context = self.playwright.chromium.launch_persistent_context(
                user_data_dir='./browser_data_new',
                headless=self.headless,
                args=args,
                accept_downloads=True,
                downloads_path=downloads_dir
            )
            self.browser = self.context
            self.downloads_dir = downloads_dir
            print(f"浏览器启动成功，下载目录: {downloads_dir}")
            
            self._setup_singlefile_config()
        except Exception as e:
            print(f"浏览器启动失败: {e}")
            print("尝试不加载扩展启动...")
            # 不加载扩展重试
            args = [a for a in args if not a.startswith('--disable-extensions') and not a.startswith('--load-extension')]
            self.context = self.playwright.chromium.launch_persistent_context(
                user_data_dir='./browser_data_new',
                headless=self.headless,
                args=args
            )
            self.browser = self.context
            print("浏览器启动成功（无扩展）")
    
    def _setup_singlefile_config(self):
        """设置 SingleFile 配置
        
        通过 CDP (Chrome DevTools Protocol) 设置扩展存储
        SingleFile 配置键名: profile___Default_Settings__
        """
        try:
            pages = self.context.pages
            if not pages:
                page = self.context.new_page()
            else:
                page = pages[0]
            
            cdp = page.context.new_cdp_session(page)
            
            singlefile_config = {
                "saveOriginalURLs": True,
                "filenameTemplate": "{url-last-segment}.{filename-extension}",
                "filenameConflictAction": "uniquify",
                "compressHTML": True,
                "loadDeferredImages": True,
                "blockScripts": True,
                "blockVideos": True,
                "blockAudios": True
            }
            
            storage_data = {
                "profile___Default_Settings__": singlefile_config,
                "rules": [{"url": "file:", "profile": "__Default_Settings__", "autoSaveProfile": "__Disabled_Settings__"}]
            }
            
            try:
                cdp.send('DOMStorage.setDOMStorageItem', {
                    'storageId': {'securityOrigin': 'chrome-extension://mdiodlaeghegjfkbcjlhgjlnhfgfcbjj', 'isLocalStorage': True},
                    'key': 'profile___Default_Settings__',
                    'value': str(singlefile_config)
                })
                print("SingleFile 配置已通过 CDP 注入")
            except Exception as e:
                print(f"CDP 注入失败: {e}")
                print("SingleFile 配置需要手动设置：点击扩展图标 -> 齿轮图标")
                
        except Exception as e:
            print(f"设置 SingleFile 配置失败: {e}")
    
    def close_browser(self):
        """关闭浏览器"""
        try:
            if self.context:
                self.context.close()
        except Exception as e:
            print(f"关闭上下文时出错: {e}")
        
        try:
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            print(f"停止Playwright时出错: {e}")
        
        print("浏览器已关闭")
    
    def find_singlefile_downloads(self) -> List[str]:
        """查找 SingleFile 下载的文件
        
        SingleFile 默认保存到浏览器下载目录，
        文件名格式通常是: {url-last-segment}.html
        """
        download_dirs = [
            os.path.join(os.environ.get('USERPROFILE', ''), 'Downloads'),
            os.path.join(os.environ.get('USERPROFILE', ''), '下载'),
        ]
        
        found_files = []
        for download_dir in download_dirs:
            if os.path.exists(download_dir):
                # 查找最近的 HTML 文件
                html_files = glob.glob(os.path.join(download_dir, '*.html'))
                for f in html_files:
                    # 排除太旧的文件（超过1小时）
                    if time.time() - os.path.getmtime(f) < 3600:
                        found_files.append(f)
        
        return found_files
    
    def move_singlefile_download(self, product_id: str) -> Optional[str]:
        """将 SingleFile 下载的文件移动到输出目录
        
        Args:
            product_id: 商品ID，用于匹配文件名
        
        Returns:
            移动后的文件路径，如果未找到则返回 None
        """
        download_dirs = [
            os.path.join(os.environ.get('USERPROFILE', ''), 'Downloads'),
            os.path.join(os.environ.get('USERPROFILE', ''), '下载'),
        ]
        
        # 可能的文件名格式
        patterns = [
            f'{product_id}.html',
            f'{product_id}*.html',
        ]
        
        for download_dir in download_dirs:
            if not os.path.exists(download_dir):
                continue
                
            for pattern in patterns:
                matches = glob.glob(os.path.join(download_dir, pattern))
                for src_file in matches:
                    # 检查文件是否是最近创建的（5分钟内）
                    if time.time() - os.path.getmtime(src_file) < 300:
                        dst_file = os.path.join(self.output_dir, os.path.basename(src_file))
                        if src_file != dst_file:
                            shutil.move(src_file, dst_file)
                            print(f"已移动 SingleFile 下载: {dst_file}")
                            return dst_file
        
        return None
    
    def interactive_mode(self, target_url: str = None):
        """交互模式：等待用户登录和初始化扩展
        
        Args:
            target_url: 目标页面URL，如果提供则在登录后自动打开
        """
        print("\n" + "=" * 50)
        print("交互模式")
        print("=" * 50)
        print("请在浏览器中完成以下操作：")
        print("1. 登录 1688 账号")
        print("2. 使用 SingleFile 保存页面：")
        print("   - 点击浏览器右上角 SingleFile 图标")
        print("   - 或按快捷键 Ctrl+Shift+Y")
        print("3. 完成后按 Enter 键移动文件到 products 目录...")
        print("=" * 50)
        
        pages = self.context.pages
        if pages:
            page = pages[0]
        else:
            page = self.context.new_page()
        
        if target_url:
            try:
                print(f"正在打开目标页面: {target_url}")
                page.goto(target_url, wait_until='domcontentloaded', timeout=30000)
                print("目标页面加载完成")
                product_id = get_product_id_from_url(target_url)
                if product_id:
                    print(f"\n商品ID: {product_id}")
                print("\n提示: 点击 SingleFile 图标或按 Ctrl+Shift+Y 保存页面")
            except Exception as e:
                print(f"目标页面加载失败: {e}")
                print("请手动在浏览器中打开目标页面")
        else:
            try:
                print("正在打开 1688 首页...")
                page.goto('https://www.1688.com', wait_until='domcontentloaded', timeout=15000)
                print("页面加载完成")
            except Exception as e:
                print(f"页面加载失败: {e}")
                print("请手动在浏览器中打开 https://www.1688.com")
        
        input("\n按 Enter 键移动 SingleFile 下载的文件...")
        
        # 移动 SingleFile 下载的文件
        if target_url:
            product_id = get_product_id_from_url(target_url)
            if product_id:
                moved_file = self.move_singlefile_download(product_id)
                if moved_file:
                    print(f"文件已移动到: {moved_file}")
                else:
                    print("未找到 SingleFile 下载的文件")
                    print("请检查浏览器下载目录")
        else:
            # 列出所有最近的下载
            downloads = self.find_singlefile_downloads()
            if downloads:
                print(f"找到 {len(downloads)} 个最近的 HTML 文件:")
                for f in downloads:
                    print(f"  {f}")
    
    def save_page(self, url: str, wait_time: int = 5) -> Optional[str]:
        """保存页面 - 直接获取渲染后的HTML
        
        注意：此方法保存的是 Playwright 获取的渲染后HTML，
        不包含 SingleFile 的完整资源嵌入功能。
        如需完整保存，请使用 SingleFile 扩展手动操作。
        """
        product_id = get_product_id_from_url(url)
        if not product_id:
            print(f"无法从URL提取商品ID: {url}")
            return None
        
        output_file = os.path.join(self.output_dir, f'{product_id}.html')
        
        try:
            page = self.context.new_page()
            print(f"正在访问: {url}")
            page.goto(url, wait_until='domcontentloaded', timeout=60000)
            
            print(f"等待页面加载 ({wait_time}秒)...")
            time.sleep(wait_time)
            
            # 滚动页面加载懒加载图片
            print("滚动页面加载懒加载内容...")
            for i in range(3):
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(1)
            page.evaluate('window.scrollTo(0, 0)')
            
            print("正在保存页面...")
            html_content = page.content()
            
            content_len = len(html_content)
            if content_len < 1000:
                print(f"警告: 页面内容过短 ({content_len} 字节)")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            page.close()
            
            # 验证文件是否保存成功
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                print(f"页面保存成功: {output_file} ({file_size} 字节)")
                return output_file
            else:
                print(f"文件保存失败: 文件不存在")
                return None
            
        except Exception as e:
            print(f"保存页面失败: {e}")
            return None
    
    def collect_urls(self, urls: List[str], delay: int = 3):
        """批量采集URL"""
        success_count = 0
        fail_count = 0
        
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] 处理: {url}")
            result = self.save_page(url)
            if result:
                success_count += 1
            else:
                fail_count += 1
            
            if i < len(urls):
                print(f"等待 {delay} 秒...")
                time.sleep(delay)
        
        print(f"\n采集完成: 成功 {success_count}, 失败 {fail_count}")
        return success_count

def main():
    print("1688 商品信息自动采集工具")
    print("")
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python auto_collector.py <URL1> [URL2] ...")
        print("  python auto_collector.py --file urls.txt")
        print("  python auto_collector.py --interactive  # 交互模式，先登录再采集")
        print("")
        print("选项:")
        print("  --headless    无头模式运行（不显示浏览器窗口）")
        print("  --ext PATH    加载浏览器扩展路径（可多次使用）")
        print("  --delay N     请求间隔秒数（默认3秒）")
        print("  --auto-ext    自动查找并加载已安装的扩展")
        print("  --interactive 交互模式，先登录和安装插件")
        print("")
        print("示例:")
        print("  python auto_collector.py --interactive")
        print("  python auto_collector.py https://detail.1688.com/offer/123456789.html")
        print("  python auto_collector.py --file urls.txt --headless")
        sys.exit(1)
    
    urls = []
    headless = '--headless' in sys.argv
    extension_paths = []
    delay = 3
    auto_find_ext = '--auto-ext' in sys.argv
    interactive = '--interactive' in sys.argv
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--file' and i + 1 < len(sys.argv):
            with open(sys.argv[i + 1], 'r', encoding='utf-8') as f:
                urls.extend([line.strip() for line in f if line.strip()])
            i += 2
        elif arg == '--ext' and i + 1 < len(sys.argv):
            extension_paths.append(sys.argv[i + 1])
            i += 2
        elif arg == '--delay' and i + 1 < len(sys.argv):
            delay = int(sys.argv[i + 1])
            i += 2
        elif not arg.startswith('--'):
            urls.append(arg)
            i += 1
        else:
            i += 1
    
    if auto_find_ext:
        found_extensions = find_extensions()
        if found_extensions:
            extension_paths = found_extensions
            print(f"自动发现扩展: {len(found_extensions)} 个")
    
    if interactive:
        print("交互模式: 先登录和安装插件")
        headless = False
    elif urls:
        print(f"准备采集 {len(urls)} 个页面")
    else:
        print("错误: 未提供有效的URL")
        sys.exit(1)
    
    print(f"无头模式: {headless}")
    print(f"请求间隔: {delay}秒")
    if extension_paths:
        print(f"加载扩展: {len(extension_paths)} 个")
    
    collector = AutoCollector(output_dir='products', headless=headless)
    
    try:
        collector.start_browser(extension_paths=extension_paths if extension_paths else None)
        
        if interactive:
            # 交互模式：如果有URL，打开第一个URL让用户操作
            target_url = urls[0] if urls else None
            collector.interactive_mode(target_url=target_url)
            if urls:
                collector.collect_urls(urls, delay=delay)
            else:
                print("\n交互模式结束。下次可以直接提供 URL 进行采集。")
        else:
            collector.collect_urls(urls, delay=delay)
    finally:
        collector.close_browser()

if __name__ == '__main__':
    main()
