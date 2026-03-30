#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混合采集器 - 结合 Playwright 和 SingleFile 功能
1. 使用 Playwright + 1688-extension 处理登录和反爬虫
2. 使用 CDP 获取完整页面内容（类似 SingleFile）
"""

import subprocess
import sys
import os
import time
import re
import json
import base64
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

class HybridCollector:
    """混合采集器 - 结合扩展登录和完整页面保存"""
    
    def __init__(self, output_dir: str = 'products', headless: bool = False):
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_dir)
        self.output_dir = output_dir
        self.headless = headless
        self.browser = None
        self.context = None
        self.playwright = None
        
        os.makedirs(output_dir, exist_ok=True)
    
    def start_browser(self, load_extension: bool = True):
        """启动浏览器，加载 1688-extension"""
        if not HAS_PLAYWRIGHT:
            raise ImportError("请安装 playwright: pip install playwright && playwright install chromium")
        
        self.playwright = sync_playwright().start()
        
        args = ['--start-maximized']
        extensions = []
        
        if load_extension:
            extension_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'tools', '1688-extension'
            )
            if os.path.exists(extension_dir):
                manifest_path = os.path.join(extension_dir, 'manifest.json')
                if os.path.exists(manifest_path):
                    extensions.append(extension_dir)
                    print(f"找到扩展: 1688-extension")
        
        if extensions:
            ext_paths = ','.join(extensions)
            args.extend([
                f'--disable-extensions-except={ext_paths}',
                f'--load-extension={ext_paths}',
            ])
            print(f"加载扩展: {len(extensions)} 个")
        
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir='./browser_data_new',
            headless=self.headless,
            args=args
        )
        self.browser = self.context
        print("浏览器启动成功")
    
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
    
    def login_interactive(self):
        """交互式登录"""
        print("\n" + "=" * 50)
        print("登录模式")
        print("=" * 50)
        print("请在浏览器中完成登录：")
        print("1. 登录 1688 账号")
        print("2. 登录成功后按 Enter 键继续...")
        print("=" * 50)
        
        pages = self.context.pages
        if pages:
            page = pages[0]
        else:
            page = self.context.new_page()
        
        try:
            print("正在打开 1688 首页...")
            page.goto('https://www.1688.com', wait_until='domcontentloaded', timeout=15000)
            print("页面加载完成")
        except Exception as e:
            print(f"页面加载失败: {e}")
        
        input("\n登录完成后按 Enter 键继续...")
    
    def save_page_full(self, url: str, wait_time: int = 10) -> Optional[str]:
        """保存完整页面 - 使用 CDP 获取完整内容
        
        此方法使用 Chrome DevTools Protocol 获取页面完整内容，
        类似于 SingleFile 的功能，但需要手动处理资源。
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
            for i in range(5):
                page.evaluate(f'window.scrollTo(0, document.body.scrollHeight * {(i+1)/5})')
                time.sleep(1)
            page.evaluate('window.scrollTo(0, 0)')
            time.sleep(2)
            
            # 使用 CDP 获取完整页面内容
            print("正在获取完整页面内容...")
            
            # 方法1: 获取渲染后的 HTML
            html_content = page.content()
            
            # 方法2: 使用 CDP 捕获截图（可选）
            # cdp = page.context.new_cdp_session(page)
            # result = cdp.send('Page.captureScreenshot', {'format': 'png'})
            # screenshot = base64.b64decode(result['data'])
            
            # 注释说明资源来源
            html_content = html_content.replace(
                '<head>',
                '<head>\n<!-- 页面由 HybridCollector 保存 -->\n<!-- 资源URL为原始URL，需要网络访问 -->'
            )
            
            content_len = len(html_content)
            if content_len < 1000:
                print(f"警告: 页面内容过短 ({content_len} 字节)")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            page.close()
            
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                print(f"页面保存成功: {output_file} ({file_size} 字节)")
                return output_file
            else:
                print("文件保存失败")
                return None
            
        except Exception as e:
            print(f"保存页面失败: {e}")
            return None
    
    def save_page_with_cookies(self, url: str, wait_time: int = 10) -> Optional[str]:
        """保存页面 - 先获取 cookies，然后用于后续请求
        
        流程：
        1. 使用 Playwright + 扩展打开页面（处理登录）
        2. 获取 cookies
        3. 关闭页面
        4. 使用 cookies 重新请求并保存
        """
        product_id = get_product_id_from_url(url)
        if not product_id:
            print(f"无法从URL提取商品ID: {url}")
            return None
        
        output_file = os.path.join(self.output_dir, f'{product_id}.html')
        
        try:
            # 步骤1: 使用扩展打开页面
            page = self.context.new_page()
            print(f"正在访问（带扩展）: {url}")
            page.goto(url, wait_until='domcontentloaded', timeout=60000)
            
            print(f"等待页面加载 ({wait_time}秒)...")
            time.sleep(wait_time)
            
            # 滚动加载懒加载内容
            print("滚动页面加载懒加载内容...")
            for i in range(5):
                page.evaluate(f'window.scrollTo(0, document.body.scrollHeight * {(i+1)/5})')
                time.sleep(1)
            page.evaluate('window.scrollTo(0, 0)')
            time.sleep(2)
            
            # 获取页面内容
            print("正在获取页面内容...")
            html_content = page.content()
            
            # 获取 cookies（可用于后续请求）
            cookies = self.context.cookies()
            cookies_file = os.path.join(self.output_dir, f'{product_id}_cookies.json')
            with open(cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2)
            print(f"Cookies 已保存: {cookies_file}")
            
            # 保存 HTML
            html_content = html_content.replace(
                '<head>',
                f'<head>\n<!-- 页面由 HybridCollector 保存 -->\n<!-- 商品ID: {product_id} -->\n<!-- 资源URL为原始URL -->'
            )
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            page.close()
            
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                print(f"页面保存成功: {output_file} ({file_size} 字节)")
                return output_file
            else:
                print("文件保存失败")
                return None
            
        except Exception as e:
            print(f"保存页面失败: {e}")
            return None
    
    def interactive_collect(self, url: str) -> Optional[str]:
        """交互式采集 - 打开页面让用户操作，然后保存"""
        print("\n" + "=" * 50)
        print("交互采集模式")
        print("=" * 50)
        print("请在浏览器中完成操作：")
        print("1. 确认页面加载完成")
        print("2. 如需登录请先登录")
        print("3. 完成后按 Enter 键保存页面...")
        print("=" * 50)
        
        product_id = get_product_id_from_url(url)
        
        page = self.context.new_page()
        print(f"正在打开: {url}")
        page.goto(url, wait_until='domcontentloaded', timeout=60000)
        print("页面加载完成")
        
        if product_id:
            print(f"商品ID: {product_id}")
        
        input("\n按 Enter 键保存页面...")
        
        # 滚动加载
        print("正在加载懒加载内容...")
        for i in range(5):
            page.evaluate(f'window.scrollTo(0, document.body.scrollHeight * {(i+1)/5})')
            time.sleep(0.5)
        page.evaluate('window.scrollTo(0, 0)')
        time.sleep(1)
        
        # 保存
        if product_id:
            output_file = os.path.join(self.output_dir, f'{product_id}.html')
        else:
            output_file = os.path.join(self.output_dir, f'page_{int(time.time())}.html')
        
        html_content = page.content()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        page.close()
        
        file_size = os.path.getsize(output_file)
        print(f"页面保存成功: {output_file} ({file_size} 字节)")
        return output_file

def main():
    print("混合采集器 - 结合 Playwright 和 SingleFile 功能")
    print("")
    
    if not HAS_PLAYWRIGHT:
        print("错误: 请安装 playwright")
        print("pip install playwright && playwright install chromium")
        return
    
    import argparse
    parser = argparse.ArgumentParser(description='混合采集器')
    parser.add_argument('url', nargs='?', help='目标URL')
    parser.add_argument('--login', action='store_true', help='先登录')
    parser.add_argument('--interactive', '-i', action='store_true', help='交互模式')
    parser.add_argument('--headless', action='store_true', help='无头模式')
    parser.add_argument('--output', '-o', default='products', help='输出目录')
    
    args = parser.parse_args()
    
    collector = HybridCollector(output_dir=args.output, headless=args.headless)
    
    try:
        collector.start_browser(load_extension=True)
        
        if args.login or args.interactive:
            collector.login_interactive()
        
        if args.url:
            if args.interactive:
                collector.interactive_collect(args.url)
            else:
                collector.save_page_with_cookies(args.url)
        else:
            print("请提供目标URL")
            print("用法: python hybrid_collector.py <url> [--login] [--interactive]")
    
    finally:
        collector.close_browser()

if __name__ == '__main__':
    main()
