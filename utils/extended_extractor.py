# -*- coding: utf-8 -*-
"""
扩展数据提取器
从1688采购助手插件生成的HTML内容中提取数据
"""

import re
import json
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup


class ExtendedDataExtractor:
    """扩展数据提取器
    
    从HTML中提取：
    - 插件导航数据（类目、上架时间、月成交等）
    - 核心容器数据（采购风向标、功能亮点、供应商亮点）
    - 店铺数据（店铺名称、评分等）
    """
    
    def __init__(self, html_content: str):
        self.html_content = html_content
        self.soup = BeautifulSoup(html_content, 'html.parser')
    
    def extract_all(self) -> Dict[str, Any]:
        """提取所有扩展数据"""
        return {
            'plugin_nav': self.extract_plugin_nav(),
            'core_container': self.extract_core_container(),
            'shop_info': self.extract_shop_info()
        }
    
    def extract_plugin_nav(self) -> Dict[str, Any]:
        """提取插件导航数据"""
        result = {
            'category': None,
            'listing_date': None,
            'monthly_sales': None,
            'monthly_dropship': None,
            'yearly_volume': None,
            'yearly_orders': None,
            'review_count': None,
            'positive_rate': None,
            'pickup_rate': None
        }
        
        try:
            plugin_nav_start = self.html_content.find('<!-- 插件导航 -->')
            if plugin_nav_start == -1:
                return result
            
            plugin_nav_end = self.html_content.find('<!-- 核心容器 -->', plugin_nav_start)
            if plugin_nav_end == -1:
                plugin_nav_section = self.html_content[plugin_nav_start:]
            else:
                plugin_nav_section = self.html_content[plugin_nav_start:]
            
            patterns = {
                'category': r'类目<span[^>]*>([^<]+)</span>',
                'listing_date': r'上架时间<span[^>]*>([^<]+)</span>',
                'monthly_sales': r'月成交<span[^>]*>([^<]+)</span>',
                'monthly_dropship': r'月代销<span[^>]*>([^<]+)</span>',
                'yearly_volume': r'年成交件数<span[^>]*>([^<]+)</span>',
                'yearly_orders': r'年成交笔数<span[^>]*>([^<]+)</span>',
                'review_count': r'评论数<span[^>]*>([^<]+)</span>',
                'positive_rate': r'好评率<span[^>]*>([^<]+)</span>',
                'pickup_rate': r'揽收率<span[^>]*>([^<]+)</span>'
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, plugin_nav_section)
                if match:
                    value = match.group(1).strip()
                    if key in ['monthly_sales', 'monthly_dropship', 'yearly_volume', 'yearly_orders', 'review_count']:
                        value = self._parse_number(value)
                    elif key in ['positive_rate', 'pickup_rate']:
                        value = self._parse_percentage(value)
                    elif key == 'listing_date':
                        value = self._parse_date(value)
                    result[key] = value
        
        return result
    
    def extract_core_container(self) -> Dict[str, Any]:
        """提取核心容器数据"""
        result = {
            'procurement_trend': [],
            'features': [],
            'supplier_highlights': []
        }
        
        try:
            core_start = self.html_content.find('<!-- 核心容器 -->')
            if core_start == -1:
                return result
            
            
            procurement_trend = self._extract_procurement_trend()
            features = self._extract_features()
            supplier_highlights = self._extract_supplier_highlights()
            
            return {
                'procurement_trend': procurement_trend,
                'features': features,
                'supplier_highlights': supplier_highlights
            }
        except Exception:
            return result
    
    def _extract_procurement_trend(self) -> List[Dict]:
        """提取采购风向标"""
        trends = []
        
        try:
            patterns = [
                r'近\d+周采购量[\s\S]*?(\d+)',
                r'近30天销量[\s\S]*?([\d,]+)',
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, self.html_content)
                for match in matches:
                    platform_match = re.search(r'(1688|TikTok[^/]*)', match.group())
                    platform = platform_match.group(1) if platform_match else '未知平台'
                    
                    value_match = re.search(r'(\d+(?:,\d+)*)', match.group())
                    value = self._parse_number(value_match.group(1))
                    
                    trends.append({
                        'platform': platform,
                        'metric': '采购量' if '采购量' in pattern else '销量',
                        'value': value
                    })
            
            return trends
        except Exception:
            return []
    
    def _extract_features(self) -> List[str]:
        """提取功能亮点"""
        features = []
        
        try:
            feature_section = re.search(r'功能亮点(.*?)</div>', self.html_content, re.DOTALL)
            if feature_section:
                feature_items = re.findall(r'<div[^>]*>([^<]+)</div>', feature_section.group(1))
                features = [item.strip() for item in feature_items]
            
            return features
        except Exception:
            return []
    
    def _extract_supplier_highlights(self) -> List[str]:
        """提取供应商亮点"""
        highlights = []
        
        try:
            highlight_section = re.search(r'供应商亮点(.*?)</div>', self.html_content, re.DOTALL)
            if highlight_section:
                highlight_items = re.findall(r'<div[^>]*>([^<]+)</div>', highlight_section.group(1))
                highlights = [item.strip() for item in highlight_items]
            
            return highlights
        except Exception:
            return []
    
    def extract_shop_info(self) -> Dict[str, Any]:
        """提取店铺数据"""
        result = {
            'shop_name': None,
            'shop_years': None,
            'shop_category': None,
            'shop_return_rate': None,
            'shop_service_score': None,
            'shop_delivery_rate': None,
            'shop_positive_rate': None
        }
        
        try:
            patterns = {
                'shop_name': r'<span[^>]*>([^<]+)</span>(?:有限公司|服饰|纺织)?',
                'shop_years': r'入驻(\d+)年',
                'shop_category': r'主营[：：]([^<]+)',
                'shop_return_rate': r'店铺回头率[\s\S]*?(\d+(?:\.\d+)?%)',
                'shop_service_score': r'店铺服务分[\s\S]*?(\d+(?:\.\d+)?)分',
                'shop_delivery_rate': r'准时发货率[\s\S]*?(\d+(?:\.\d+)?%)',
                'shop_positive_rate': r'店铺好评率[\s\S]*?(\d+(?:\.\d+)?%)',
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, self.html_content)
                if match:
                    value = match.group(1).strip()
                    if key == 'shop_years':
                        value = self._parse_number(value)
                    elif key in ['shop_return_rate', 'shop_delivery_rate', 'shop_positive_rate']:
                        value = self._parse_percentage(value)
                    elif key == 'shop_service_score':
                        value = self._parse_float(value)
                    result[key] = value
            
            return result
        except Exception:
            return result
    
    def _parse_number(self, text: str) -> Optional[int]:
        """解析数字"""
        if not text:
            return None
        text = re.sub(r'[^\d]', '', text)
        if text:
            return int(text)
        return None
    
    def _parse_percentage(self, text: str) -> Optional[float]:
        """解析百分比"""
        if not text:
            return None
        match = re.search(r'(\d+(?:\.\d+)?)%', text)
        if match:
            return float(match.group(1))
        return None
    
    def _parse_float(self, text: str) -> Optional[float]:
        """解析浮点数"""
        if not text:
            return None
        try:
                return float(text)
        except ValueError:
            return None
    
    def _parse_date(self, text: str) -> Optional[str]:
        """解析日期"""
        if not text:
            return None
        text = text.strip()
        if re.match(r'\d{4}-\d{2}-\d{2}', text):
            return text
        return None
