#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在线采集模块 - 使用 Selenium 直接从浏览器提取数据
"""

import os
import threading
import time
import re
import json
from typing import Optional

try:
    from utils.auto_collector import AutoCollector
    from utils.extension_manager import ExtensionManager
    HAS_AUTO_COLLECTOR = True
except ImportError:
    HAS_AUTO_COLLECTOR = False


def get_product_id_from_filename(filename: str) -> Optional[str]:
    """从文件名中提取商品ID"""
    match = re.search(r'(\d{10,12})\.html', filename)
    if match:
        return match.group(1)
    return None


def build_product_url(product_id: str) -> str:
    """构建商品页面URL"""
    return f"https://detail.1688.com/offer/{product_id}.html"


class OnlineCollector:
    """在线采集器 - 直接从浏览器提取数据"""
    
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.collector = None
        self.browser_started = False
    
    def log(self, message):
        """输出日志"""
        if self.log_callback:
            self.log_callback(message)
        print(message)
    
    def check_dependencies(self) -> bool:
        """检查依赖"""
        if not HAS_AUTO_COLLECTOR:
            self.log("错误: auto_collector 模块未安装")
            return False
        
        manager = ExtensionManager()
        status = manager.get_status()
        
        all_ready = all(status.values())
        
        if all_ready:
            self.log("所有依赖已就绪")
            return True
        else:
            missing = [k for k, v in status.items() if not v]
            for k in missing:
                self.log(f"缺少: {k}")
            return False
    
    def start_browser(self):
        """启动浏览器"""
        if self.browser_started:
            return True
        
        try:
            self.log("正在启动浏览器...")
            self.collector = AutoCollector(headless=False)
            self.collector.start_browser()
            self.browser_started = True
            self.log("浏览器启动成功")
            return True
        except Exception as e:
            self.log(f"启动浏览器失败: {e}")
            return False
    
    def open_product_page(self, product_id: str):
        """打开商品页面"""
        if not self.browser_started:
            if not self.start_browser():
                return False
        
        url = build_product_url(product_id)
        
        try:
            self.log(f"正在打开页面: {url}")
            self.collector.driver.get(url)
            self.log("页面已打开，请使用 SingleFile 保存页面 (Ctrl+Shift+Y)")
            return True
        except Exception as e:
            self.log(f"打开页面失败: {e}")
            return False
    
    def collect_data_direct(self, product_id: str, output_dir: str = None) -> Optional[dict]:
        """直接从浏览器采集数据
        
        Args:
            product_id: 商品ID
            output_dir: 输出目录，默认为 tools 目录
            
        Returns:
            提取的数据字典
        """
        if not self.browser_started:
            if not self.start_browser():
                return None
        
        url = build_product_url(product_id)
        
        if output_dir is None:
            output_dir = os.path.abspath(os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'tools'
            ))
        
        try:
            self.log(f"正在采集: {url}")
            data = self.collector.collect_data(url, output_dir)
            
            if data:
                self.log(f"数据采集成功: {product_id}")
                
                from tools.extract_product_data import (
                    extract_sku_prices,
                    extract_color_images,
                    extract_main_images,
                    extract_detail_images,
                    extract_product_info,
                    extract_rate_info,
                    extract_video_info,
                    extract_attributes,
                )
                
                sku_prices = extract_sku_prices(data)
                color_images = extract_color_images(data)
                main_images = extract_main_images(data)
                detail_images = extract_detail_images(data)
                product_info = extract_product_info(data)
                rate_info = extract_rate_info(data)
                video_info = extract_video_info(data)
                attributes = extract_attributes(data)
                
                self.log(f"  SKU数量: {len(sku_prices)}")
                self.log(f"  色卡数量: {len(color_images)}")
                self.log(f"  主图数量: {len(main_images)}")
                self.log(f"  详情图数量: {len(detail_images)}")
                self.log(f"  属性数量: {len(attributes)}")
                
                return {
                    'product_id': product_id,
                    'sku_prices': sku_prices,
                    'color_images': color_images,
                    'main_images': main_images,
                    'detail_images': detail_images,
                    'product_info': product_info,
                    'rate_info': rate_info,
                    'video_info': video_info,
                    'attributes': attributes,
                }
            else:
                self.log(f"数据采集失败: {product_id}")
                return None
                
        except Exception as e:
            self.log(f"采集数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def close_browser(self):
        """关闭浏览器"""
        if self.collector:
            try:
                self.collector.close_browser()
            except Exception:
                pass
        self.browser_started = False


_instance = None
_instance_lock = threading.Lock()


def get_collector(log_callback=None) -> OnlineCollector:
    """获取全局采集器实例"""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = OnlineCollector(log_callback)
        elif log_callback:
            _instance.log_callback = log_callback
        return _instance


def start_online_collect(log_callback, product_id: str = None, filename: str = None, direct_collect: bool = False):
    """启动在线采集
    
    Args:
        log_callback: 日志回调函数
        product_id: 商品ID (可选)
        filename: 文件名，用于提取商品ID (可选)
        direct_collect: 是否直接采集数据（不需要 SingleFile）
    """
    if product_id is None and filename:
        product_id = get_product_id_from_filename(filename)
    
    if not product_id:
        if log_callback:
            log_callback("无法获取商品ID")
        return False
    
    def collect_thread():
        collector = get_collector(log_callback)
        
        if not collector.check_dependencies():
            return
        
        if direct_collect:
            collector.collect_data_direct(product_id)
        else:
            if not collector.browser_started:
                if not collector.start_browser():
                    return
            
            collector.open_product_page(product_id)
    
    thread = threading.Thread(target=collect_thread, daemon=True)
    thread.start()
    return True
