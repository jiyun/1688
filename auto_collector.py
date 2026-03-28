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
        self.output_dir = output_dir
        self.headless = headless
        self.browser = None
        self.context = None
        self.playwright = None
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def start_browser(self, extension_paths: List[str] = None):
        """启动浏览器，支持加载多个扩展"""
        if not HAS_PLAYWRIGHT:
            raise ImportError("请安装 playwright: pip install playwright && playwright install chromium")
        
        self.playwright = sync_playwright().start()
        
        args = []
        if extension_paths:
            valid_extensions = [p for p in extension_paths if os.path.exists(p)]
            if valid_extensions:
                ext_paths = ','.join(valid_extensions)
                args.extend([
                    f'--disable-extensions-except={ext_paths}',
                    f'--load-extension={ext_paths}',
                ])
                print(f"加载扩展: {len(valid_extensions)} 个")
        
        args.append('--start-maximized')
        
        extension_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'tools', '1688-extension'
        )
        
        extensions = []
        if os.path.exists(extension_dir):
            extensions.append(extension_dir)
        
        if extensions:
            ext_paths = ','.join(extensions)
            args.extend([
                f'--disable-extensions-except={ext_paths}',
                f'--load-extension={ext_paths}',
            ])
            print(f"加载扩展: {len(extensions)} 个")
            for ext in extensions:
                print(f"  - {os.path.basename(ext)}")
        
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir='./browser_data',
            headless=self.headless,
            args=args if args else None
        )
        
        self.browser = self.context
        print("浏览器启动成功")
    
    def close_browser(self):
        """关闭浏览器"""
        if self.context:
            self.context.close()
        if self.playwright:
            self.playwright.stop()
        print("浏览器已关闭")
    
    def interactive_mode(self):
        """交互模式：等待用户登录和安装插件"""
        print("\n" + "=" * 50)
        print("交互模式")
        print("=" * 50)
        print("请在浏览器中完成以下操作：")
        print("1. 登录 1688 账号")
        print("2. 安装需要的浏览器插件")
        print("3. 完成后按 Enter 键继续采集...")
        print("=" * 50)
        
        page = self.context.new_page()
        page.goto('https://www.1688.com')
        
        input("\n按 Enter 键继续...")
        page.close()
    
    def save_page(self, url: str, wait_time: int = 5) -> Optional[str]:
        """保存页面"""
        product_id = get_product_id_from_url(url)
        if not product_id:
            print(f"无法从URL提取商品ID: {url}")
            return None
        
        output_file = os.path.join(self.output_dir, f'{product_id}.html')
        
        try:
            page = self.context.new_page()
            print(f"正在访问: {url}")
            page.goto(url, wait_until='networkidle', timeout=60000)
            
            print(f"等待页面加载 ({wait_time}秒)...")
            time.sleep(wait_time)
            
            print("正在保存页面...")
            html_content = page.content()
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            page.close()
            print(f"页面保存成功: {output_file}")
            return output_file
            
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
            collector.interactive_mode()
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
