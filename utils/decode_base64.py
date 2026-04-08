#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将HTML文件中的base64编码转码为原始内容
"""

import re
import base64
import os


def decode_base64_in_html(html_file):
    """解码HTML文件中的base64编码"""
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    img_pattern = re.compile(r'data:image/(\w+);base64,([^"\']+)')
    img_matches = img_pattern.findall(html_content)
    
    print(f"找到 {len(img_matches)} 个base64编码的图片")
    
    for i, (img_type, base64_data) in enumerate(img_matches):
        try:
            decoded_data = base64.b64decode(base64_data)
            
            output_dir = 'decoded_resources'
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f'image_{i}.{img_type}')
            
            with open(output_file, 'wb') as f:
                f.write(decoded_data)
            
            print(f"已解码并保存图片: {output_file}")
        except Exception as e:
            print(f"解码图片时出错: {e}")
    
    font_pattern = re.compile(r'data:font/(\w+);base64,([^"\']+)')
    font_matches = font_pattern.findall(html_content)
    
    print(f"找到 {len(font_matches)} 个base64编码的字体")
    
    for i, (font_type, base64_data) in enumerate(font_matches):
        try:
            decoded_data = base64.b64decode(base64_data)
            
            output_dir = 'decoded_resources'
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f'font_{i}.{font_type}')
            
            with open(output_file, 'wb') as f:
                f.write(decoded_data)
            
            print(f"已解码并保存字体: {output_file}")
        except Exception as e:
            print(f"解码字体时出错: {e}")
    
    js_pattern = re.compile(r'data:application/javascript;base64,([^"\']+)')
    js_matches = js_pattern.findall(html_content)
    
    print(f"找到 {len(js_matches)} 个base64编码的JavaScript脚本")
    
    for i, base64_data in enumerate(js_matches):
        try:
            decoded_data = base64.b64decode(base64_data)
            
            output_dir = 'decoded_resources'
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f'script_{i}.js')
            
            with open(output_file, 'wb') as f:
                f.write(decoded_data)
            
            print(f"已解码并保存JavaScript脚本: {output_file}")
        except Exception as e:
            print(f"解码JavaScript脚本时出错: {e}")
    
    print("解码完成！")


if __name__ == '__main__':
    html_file = '724609852628 (1).html'
    if os.path.exists(html_file):
        decode_base64_in_html(html_file)
    else:
        print(f"文件不存在: {html_file}")
