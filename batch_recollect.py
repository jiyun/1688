#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量重新采集 products 目录中的 HTML 文件
使用浏览器访问原始链接，更新本地 HTML 文件
"""

import os
import sys
import time
import subprocess

def main():
    products_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'products')
    
    # 获取所有 HTML 文件
    html_files = [f for f in os.listdir(products_dir) if f.endswith('.html')]
    
    if not html_files:
        print("没有找到 HTML 文件")
        return
    
    print(f"找到 {len(html_files)} 个 HTML 文件")
    print("=" * 50)
    
    auto_collector = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auto_collector.py')
    
    success_count = 0
    fail_count = 0
    
    for i, html_file in enumerate(html_files, 1):
        # 从文件名提取商品ID（去掉可能的后缀如 -.html）
        product_id = html_file.replace('.html', '').replace('-', '')
        
        # 构造原始链接
        url = f"https://detail.1688.com/offer/{product_id}.html"
        
        print(f"\n[{i}/{len(html_files)}] 处理: {html_file}")
        print(f"  URL: {url}")
        
        try:
            # 调用 auto_collector.py 重新采集（非无头模式，使用已有登录状态）
            result = subprocess.run(
                ['python', auto_collector, url],
                capture_output=True,
                text=True,
                encoding='gbk',
                errors='ignore',
                timeout=180
            )
            
            if result.returncode == 0:
                success_count += 1
                print(f"  ✓ 成功")
            else:
                fail_count += 1
                print(f"  ✗ 失败")
                if result.stderr:
                    print(f"  错误: {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            fail_count += 1
            print(f"  ✗ 超时")
        except Exception as e:
            fail_count += 1
            print(f"  ✗ 异常: {e}")
        
        # 等待间隔，避免触发反爬虫
        if i < len(html_files):
            wait_time = 5
            print(f"  等待 {wait_time} 秒...")
            time.sleep(wait_time)
    
    print("\n" + "=" * 50)
    print(f"处理完成: 成功 {success_count}, 失败 {fail_count}")

if __name__ == '__main__':
    main()
