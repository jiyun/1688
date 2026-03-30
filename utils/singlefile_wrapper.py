#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SingleFile CLI 封装工具
使用 single-file-cli 保存完整网页
"""

import subprocess
import sys
import os
import re
from typing import Optional, List

def check_nodejs():
    """检查 Node.js 是否安装"""
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Node.js 版本: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    return False

def check_npx():
    """检查 npx 是否可用"""
    try:
        result = subprocess.run(['npx', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            return True
    except FileNotFoundError:
        pass
    return False

def get_product_id_from_url(url: str) -> Optional[str]:
    """从URL中提取商品ID"""
    match = re.search(r'offer/(\d+)\.html', url)
    if match:
        return match.group(1)
    return None

def save_page_singlefile(
    url: str,
    output_file: str = None,
    output_dir: str = 'products',
    save_original_urls: bool = True,
    compress_html: bool = True,
    load_deferred_images: bool = True,
    browser_executable_path: str = None
) -> Optional[str]:
    """使用 SingleFile CLI 保存页面
    
    Args:
        url: 目标URL
        output_file: 输出文件名（不含路径）
        output_dir: 输出目录
        save_original_urls: 保存原始资源URL
        compress_html: 压缩HTML
        load_deferred_images: 加载延迟图片
        browser_executable_path: 浏览器可执行文件路径
    
    Returns:
        保存的文件路径，失败返回 None
    """
    if not check_npx():
        print("错误: 需要安装 Node.js")
        print("下载地址: https://nodejs.org/")
        return None
    
    if not output_file:
        product_id = get_product_id_from_url(url)
        if product_id:
            output_file = f"{product_id}.html"
        else:
            output_file = "page.html"
    
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_file)
    
    cmd = [
        'npx', 'single-file-cli',
        url,
        output_path,
        f'--save-original-urls={str(save_original_urls).lower()}',
        f'--compress-html={str(compress_html).lower()}',
        f'--load-deferred-images={str(load_deferred_images).lower()}',
    ]
    
    if browser_executable_path:
        cmd.append(f'--browser-executable-path={browser_executable_path}')
    
    print(f"执行命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"页面保存成功: {output_path} ({file_size} 字节)")
                return output_path
            else:
                print("警告: 命令执行成功但文件未创建")
                print(f"stdout: {result.stdout}")
                return None
        else:
            print(f"SingleFile CLI 执行失败: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print("错误: 命令执行超时")
        return None
    except Exception as e:
        print(f"错误: {e}")
        return None

def save_pages_batch(urls: List[str], output_dir: str = 'products', delay: int = 3) -> dict:
    """批量保存页面
    
    Args:
        urls: URL列表
        output_dir: 输出目录
        delay: 每次保存之间的延迟（秒）
    
    Returns:
        统计结果 {'success': int, 'failed': int, 'files': list}
    """
    import time
    
    results = {'success': 0, 'failed': 0, 'files': []}
    
    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] 处理: {url}")
        
        result = save_page_singlefile(url, output_dir=output_dir)
        if result:
            results['success'] += 1
            results['files'].append(result)
        else:
            results['failed'] += 1
        
        if i < len(urls):
            print(f"等待 {delay} 秒...")
            time.sleep(delay)
    
    print(f"\n批量保存完成: 成功 {results['success']}, 失败 {results['failed']}")
    return results

def main():
    print("SingleFile CLI 封装工具")
    print("")
    
    if not check_nodejs():
        print("错误: 未检测到 Node.js")
        print("请从 https://nodejs.org/ 下载安装")
        return
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python singlefile_wrapper.py <url> [output_file]")
        print("  python singlefile_wrapper.py --batch <urls_file>")
        print("")
        print("示例:")
        print("  python singlefile_wrapper.py https://detail.1688.com/offer/724609852628.html")
        print("  python singlefile_wrapper.py https://detail.1688.com/offer/724609852628.html 724609852628.html")
        return
    
    if sys.argv[1] == '--batch' and len(sys.argv) >= 3:
        urls_file = sys.argv[2]
        if os.path.exists(urls_file):
            with open(urls_file, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip()]
            save_pages_batch(urls)
        else:
            print(f"错误: 文件不存在 {urls_file}")
    else:
        url = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) >= 3 else None
        save_page_singlefile(url, output_file)

if __name__ == '__main__':
    main()
