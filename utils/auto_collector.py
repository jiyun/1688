#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1688 商品信息自动采集脚本
使用 Selenium 控制浏览器，支持加载 1688 官方插件和 SingleFile 扩展
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
from utils.extension_manager import find_chrome_executable, find_edge_executable

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.microsoft import EdgeChromiumDriverManager
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False

def setup_webdriver_cache():
    """设置 webdriver 缓存目录到项目目录"""
    cache_dir = os.path.abspath(os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        '.wdm_cache'
    ))
    os.makedirs(cache_dir, exist_ok=True)
    os.environ['WDM_LOCAL'] = cache_dir
    return cache_dir

def get_product_id_from_url(url: str) -> Optional[str]:
    """从URL中提取商品ID"""
    match = re.search(r'offer/(\d+)\.html', url)
    if match:
        return match.group(1)
    return None

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

class AutoCollector:
    """自动采集器 - Selenium 版本"""
    
    def __init__(self, output_dir: str = 'products', headless: bool = False, browser_type: str = 'chrome'):
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), output_dir)
        self.output_dir = output_dir
        self.headless = headless
        self.browser_type = browser_type
        self.driver = None
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"创建输出目录: {output_dir}")
    
    def start_browser(self, extension_paths: List[str] = None):
        """启动浏览器，支持加载多个扩展"""
        if not HAS_SELENIUM:
            raise ImportError("请安装 selenium: pip install selenium webdriver-manager")
        
        setup_webdriver_cache()
        
        extensions = []
        
        from utils.tool_downloader import ensure_1688_extension, get_1688_extension_path
        
        ext_path = get_1688_extension_path()
        if ext_path:
            extensions.append(ext_path)
            print(f"找到扩展: 1688-extension ({ext_path})")
        else:
            print("1688-extension 未找到，尝试自动下载...")
            ext_path = ensure_1688_extension()
            if ext_path:
                extensions.append(ext_path)
                print(f"已下载扩展: 1688-extension")
        
        singlefile_dir = os.path.abspath(os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'tools', 'SingleFile-MV3-main'
        ))
        if os.path.exists(singlefile_dir):
            manifest_path = os.path.join(singlefile_dir, 'manifest.json')
            if os.path.exists(manifest_path):
                extensions.append(singlefile_dir)
                print(f"找到扩展: SingleFile (Manifest V3)")
        
        if extension_paths:
            for ext_path in extension_paths:
                ext_path = os.path.abspath(ext_path)
                if os.path.exists(ext_path) and ext_path not in extensions:
                    extensions.append(ext_path)
        
        options = Options()
        
        if self.headless:
            options.add_argument('--headless=new')
        
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlledByAutomation')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--enable-extensions')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        download_dir = os.path.abspath(self.output_dir)
        os.makedirs(download_dir, exist_ok=True)
        prefs = {
            'download.default_directory': download_dir,
            'download.prompt_for_download': False,
            'download.directory_upgrade': True,
            'safebrowsing.enabled': False,
            'safebrowsing.disable_download_protection': True,
        }
        options.add_experimental_option('prefs', prefs)
        
        user_data_dir = os.path.abspath(os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'tools', 'browser_data'
        ))
        os.makedirs(user_data_dir, exist_ok=True)
        options.add_argument(f'--user-data-dir={user_data_dir}')
        
        if extensions:
            ext_paths = ','.join(extensions)
            options.add_argument(f'--load-extension={ext_paths}')
            print(f"加载扩展: {len(extensions)} 个")
            print(f"扩展路径: {ext_paths}")
        
        if self.browser_type == 'edge':
            print("使用 Edge 浏览器...")
            edge_path = find_edge_executable()
            if edge_path:
                print(f"找到 Edge: {edge_path}")
                options.binary_location = edge_path
            else:
                print("未找到 Edge 浏览器，请安装 Microsoft Edge")
                raise RuntimeError("Edge 浏览器未安装")
            
            try:
                from selenium.webdriver.edge.service import Service as EdgeService
                edgedriver_path = os.path.abspath(os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    'tools', 'msedgedriver.exe'
                ))
                if os.path.exists(edgedriver_path):
                    print(f"使用本地 msedgedriver: {edgedriver_path}")
                    self.driver = webdriver.Edge(options=options, service=EdgeService(executable_path=edgedriver_path))
                else:
                    self.driver = webdriver.Edge(options=options)
            except Exception as e:
                print(f"Edge WebDriver 初始化失败: {e}")
                print("提示: Edge 适配尚未完全完成，建议使用 Chrome 浏览器")
                raise
        else:
            chrome_path = find_chrome_executable()
            
            if chrome_path:
                print(f"使用 Chrome 浏览器: {chrome_path}")
                options.binary_location = chrome_path
            else:
                edge_path = find_edge_executable()
                if edge_path:
                    print(f"Chrome 未找到，尝试使用 Edge 浏览器: {edge_path}")
                    print("警告: Edge 适配尚未完全完成，建议安装 Chrome 浏览器")
                    options.binary_location = edge_path
                    try:
                        self.driver = webdriver.Edge(options=options)
                        self.driver.implicitly_wait(10)
                        print(f"浏览器启动成功，下载目录: {self.output_dir}")
                        return
                    except Exception as e:
                        print(f"Edge 启动失败: {e}")
                        raise RuntimeError("Chrome 和 Edge 浏览器均不可用，请安装 Chrome 浏览器")
                else:
                    print("使用 Chrome 浏览器...")
            
            chromedriver_path = os.path.abspath(os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'tools', 'chromedriver-win64', 'chromedriver.exe'
            ))
            if os.path.exists(chromedriver_path):
                print(f"使用本地 chromedriver: {chromedriver_path}")
                from selenium.webdriver.chrome.service import Service as ChromeService
                self.driver = webdriver.Chrome(
                    options=options,
                    service=ChromeService(executable_path=chromedriver_path)
                )
            else:
                self.driver = webdriver.Chrome(options=options)
        
        self.driver.implicitly_wait(10)
        print(f"浏览器启动成功，下载目录: {self.output_dir}")
        
        self.driver.get('chrome://extensions/')
        print("已打开扩展管理页面，请检查扩展是否正确加载")
        time.sleep(2)
    
    def close_browser(self):
        """关闭浏览器"""
        if self.driver:
            try:
                self.driver.quit()
                print("浏览器已关闭")
            except Exception as e:
                print(f"关闭浏览器时出错: {e}")
    
    def find_singlefile_downloads(self) -> List[str]:
        """查找 SingleFile 下载的文件"""
        download_dirs = [
            os.path.join(os.environ.get('USERPROFILE', ''), 'Downloads'),
            os.path.join(os.environ.get('USERPROFILE', ''), '下载'),
        ]
        
        found_files = []
        for download_dir in download_dirs:
            if os.path.exists(download_dir):
                html_files = glob.glob(os.path.join(download_dir, '*.html'))
                for f in html_files:
                    if time.time() - os.path.getmtime(f) < 3600:
                        found_files.append(f)
        
        return found_files
    
    def move_singlefile_download(self, product_id: str) -> Optional[str]:
        """将 SingleFile 下载的文件移动到输出目录"""
        download_dirs = [
            os.path.join(os.environ.get('USERPROFILE', ''), 'Downloads'),
            os.path.join(os.environ.get('USERPROFILE', ''), '下载'),
        ]
        
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
                    if time.time() - os.path.getmtime(src_file) < 300:
                        dst_file = os.path.join(self.output_dir, os.path.basename(src_file))
                        if src_file != dst_file:
                            shutil.move(src_file, dst_file)
                            print(f"已移动 SingleFile 下载: {dst_file}")
                            return dst_file
        
        return None
    
    def interactive_mode(self, target_url: str = None):
        """交互模式：等待用户登录和初始化扩展"""
        print("\n" + "=" * 50)
        print("交互模式")
        print("=" * 50)
        print("请在浏览器中完成以下操作：")
        print("1. 登录 1688 账号")
        print("2. 打开目标页面:")
        if target_url:
            print(f"   {target_url}")
        else:
            print("   https://www.1688.com")
        print("3. 使用 SingleFile 保存页面：")
        print("   - 点击浏览器右上角 SingleFile 图标")
        print("   - 或按快捷键 Ctrl+Shift+Y")
        print("4. 完成后按 Enter 键移动文件到 products 目录...")
        print("=" * 50)
        
        if target_url:
            try:
                print(f"正在打开目标页面: {target_url}")
                self.driver.get(target_url)
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
                self.driver.get('https://www.1688.com')
                print("页面加载完成")
            except Exception as e:
                print(f"页面加载失败: {e}")
                print("请手动在浏览器中打开 https://www.1688.com")
        
        input("\n按 Enter 键移动 SingleFile 下载的文件...")
        
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
            downloads = self.find_singlefile_downloads()
            if downloads:
                print(f"找到 {len(downloads)} 个最近的 HTML 文件:")
                for f in downloads:
                    print(f"  {f}")
    
    def save_page(self, url: str, wait_time: int = 5) -> Optional[str]:
        """保存页面 - 直接获取渲染后的HTML"""
        product_id = get_product_id_from_url(url)
        if not product_id:
            print(f"无法从URL提取商品ID: {url}")
            return None
        
        output_file = os.path.join(self.output_dir, f'{product_id}.html')
        
        try:
            print(f"正在访问: {url}")
            self.driver.get(url)
            
            WebDriverWait(self.driver, 60).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            print(f"等待页面加载 ({wait_time}秒)...")
            time.sleep(wait_time)
            
            print("滚动页面加载懒加载内容...")
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, 0);")
            
            print("正在保存页面...")
            html_content = self.driver.page_source
            
            content_len = len(html_content)
            if content_len < 1000:
                print(f"警告: 页面内容过短 ({content_len} 字节)")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
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
    
    def extract_page_data(self) -> Optional[dict]:
        """直接从页面提取 window.context 数据"""
        try:
            js_script = """
            if (typeof window.context !== 'undefined') {
                return JSON.stringify(window.context);
            }
            return null;
            """
            result = self.driver.execute_script(js_script)
            
            if result:
                import json
                try:
                    data = json.loads(result)
                    print("成功提取 window.context 数据")
                    return data
                except json.JSONDecodeError as e:
                    print(f"JSON 解析失败: {e}")
                    print(f"数据长度: {len(result)} 字符")
                    try:
                        import demjson3
                        data = demjson3.decode(result)
                        print("使用 demjson3 解析成功")
                        return data
                    except ImportError:
                        print("请安装 demjson3: pip install demjson3")
                        return None
                    except Exception as e2:
                        print(f"demjson3 解析也失败: {e2}")
                        return None
            else:
                print("页面中未找到 window.context 数据")
                print("尝试查找其他数据源...")
                
                js_script2 = """
                if (typeof window.__INITIAL_STATE__ !== 'undefined') {
                    return JSON.stringify(window.__INITIAL_STATE__);
                }
                return null;
                """
                result2 = self.driver.execute_script(js_script2)
                if result2:
                    print("找到 window.__INITIAL_STATE__")
                    import json
                    return json.loads(result2)
                
                return None
                
        except Exception as e:
            print(f"提取页面数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def collect_data(self, url: str, output_dir: str = None) -> Optional[dict]:
        """采集页面数据并返回结构化数据"""
        product_id = get_product_id_from_url(url)
        if not product_id:
            print(f"无法从URL提取商品ID: {url}")
            return None
        
        try:
            print(f"正在访问: {url}")
            self.driver.get(url)
            
            WebDriverWait(self.driver, 60).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            print("等待页面加载...")
            time.sleep(5)
            
            print("滚动页面加载懒加载内容...")
            scroll_height = self.driver.execute_script("return document.body.scrollHeight;")
            scroll_step = 500
            current_position = 0
            while current_position < scroll_height:
                self.driver.execute_script(f"window.scrollTo(0, {current_position});")
                time.sleep(0.3)
                current_position += scroll_step
                scroll_height = self.driver.execute_script("return document.body.scrollHeight;")
            
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            try:
                detail_div = self.driver.find_element(By.ID, "detail")
                if detail_div:
                    self.driver.execute_script("arguments[0].scrollIntoView();", detail_div)
                    time.sleep(2)
            except:
                pass
            
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            print("提取页面数据...")
            data = self.extract_page_data()
            
            print("提取页面HTML...")
            html_content = self.driver.page_source
            
            detail_html = ""
            if data:
                try:
                    detail_url = data.get('result', {}).get('data', {}).get('description', {}).get('fields', {}).get('detailUrl', '')
                    if detail_url:
                        self.driver.get(detail_url)
                        time.sleep(2)
                        detail_html = self.driver.page_source
                except:
                    pass
            
            if data:
                data['_productId'] = product_id
                data['_url'] = url
                data['_collectTime'] = datetime.now().isoformat()
                data['_htmlContent'] = html_content
                data['_detailHtml'] = detail_html
                
                return data
            else:
                return None
                
        except Exception as e:
            print(f"采集数据失败: {e}")
            return None
    
    def collect_urls(self, urls: List[str], delay: int = 3):
        """批量采集URL"""
        success_count = 0
        fail_count = 0
        
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] 处理: {url}")
            try:
                result = self.save_page(url)
                if result:
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                print(f"处理URL时出错: {e}")
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
        print("  --interactive 交互模式，先登录和安装插件")
        print("  --chrome      使用 Chrome 浏览器（默认）")
        print("  --edge        使用 Edge 浏览器")
        print("")
        print("示例:")
        print("  python auto_collector.py --interactive")
        print("  python auto_collector.py https://detail.1688.com/offer/123456789.html")
        print("  python auto_collector.py --file urls.txt --headless")
        print("  python auto_collector.py --interactive --chrome https://detail.1688.com/offer/123456789.html")
        print("  python auto_collector.py --interactive --edge https://detail.1688.com/offer/123456789.html")
        sys.exit(1)
    
    urls = []
    headless = '--headless' in sys.argv
    extension_paths = []
    delay = 3
    interactive = '--interactive' in sys.argv
    browser_type = 'chrome'
    
    if '--edge' in sys.argv:
        browser_type = 'edge'
    
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
    
    print(f"交互模式: {'是' if interactive else '否'}")
    print(f"无头模式: {headless}")
    print(f"浏览器类型: {browser_type}")
    print(f"请求间隔: {delay}秒")
    
    collector = AutoCollector(
        output_dir='products',
        headless=headless,
        browser_type=browser_type
    )
    
    try:
        collector.start_browser(extension_paths=extension_paths if extension_paths else None)
        
        if interactive:
            target_url = urls[0] if urls else None
            collector.interactive_mode(target_url)
        elif urls:
            collector.collect_urls(urls, delay)
        else:
            print("请提供URL或使用 --interactive 模式")
        
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        collector.close_browser()


if __name__ == '__main__':
    main()
