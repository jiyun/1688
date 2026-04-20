# -*- coding: utf-8 -*-
"""
商品成交趋势数据提取器
从1688插件生成的商品成交趋势情况HTML中提取数据
"""

import re
import json
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup


class TrendDataExtractor:
    """商品成交趋势数据提取器
    
    从HTML中提取：
    - 销售统计（年销量、近30天销量、30天代发订单数、复购率、48小时揽收率）
    - 上架时间信息
    - 销量趋势图表数据
    - 成交价趋势图表数据
    """
    
    def __init__(self, html_content: str):
        self.html_content = html_content
        self.soup = BeautifulSoup(html_content, 'html.parser')
    
    def extract_all(self) -> Dict[str, Any]:
        """提取所有趋势数据"""
        return {
            'sales_stats': self.extract_sales_stats(),
            'listing_info': self.extract_listing_info(),
            'trend_charts': self.extract_trend_charts(),
            'raw_html': self._extract_trend_section_html()
        }
    
    def extract_sales_stats(self) -> Dict[str, Any]:
        """提取销售统计数据
        
        包括：
        - 年销量
        - 近30天销量
        - 30天代发订单数
        - 复购率
        - 48小时揽收率
        """
        result = {
            'yearly_sales': None,           # 年销量
            'monthly_sales_30d': None,      # 近30天销量
            'dropship_orders_30d': None,    # 30天代发订单数
            'repurchase_rate': None,        # 复购率
            'pickup_rate_48h': None,        # 48小时揽收率
        }
        
        try:
            # 查找商品成交趋势情况区域
            trend_container = self.soup.find('div', class_='goodsTrendPanel-container')
            if not trend_container:
                # 尝试通过文本查找
                trend_heading = self.soup.find(string=re.compile(r'商品成交趋势情况'))
                if trend_heading:
                    trend_container = trend_heading.find_parent('div', class_=re.compile(r'container|panel'))
            
            if trend_container:
                # 提取销售信息区域
                sale_info = trend_container.find('div', class_='sale-info')
                if sale_info:
                    sale_items = sale_info.find_all('div', class_='sale-item')
                    for item in sale_items:
                        title_elem = item.find('span', class_='title')
                        cont_elem = item.find('span', class_='cont')
                        
                        if title_elem and cont_elem:
                            title = title_elem.get_text(strip=True)
                            cont = cont_elem.get_text(strip=True)
                            
                            # 根据标题匹配字段
                            if '年销量' in title:
                                result['yearly_sales'] = self._parse_number(cont)
                            elif '近30天销量' in title or '30天销量' in title:
                                result['monthly_sales_30d'] = self._parse_number(cont)
                            elif '30天代发订单数' in title or '代发订单' in title:
                                result['dropship_orders_30d'] = self._parse_number(cont)
                            elif '复购率' in title:
                                result['repurchase_rate'] = self._parse_percentage(cont)
                            elif '48小时揽收率' in title or '揽收率' in title:
                                result['pickup_rate_48h'] = self._parse_percentage(cont)
            
            # 如果上面的方法没找到，尝试正则匹配
            if not any(result.values()):
                patterns = {
                    'yearly_sales': r'年销量.*?<span[^>]*class="cont"[^>]*>([\d,+]+)',
                    'monthly_sales_30d': r'近30天销量.*?<span[^>]*class="cont"[^>]*>([\d,+]+)',
                    'dropship_orders_30d': r'30天代发订单数.*?<span[^>]*class="cont"[^>]*>([\d,+]+)',
                    'repurchase_rate': r'复购率.*?<span[^>]*class="cont"[^>]*>([\d.%]+)',
                    'pickup_rate_48h': r'48小时揽收率.*?<span[^>]*class="cont"[^>]*>([\d.%]+)',
                }
                
                for key, pattern in patterns.items():
                    match = re.search(pattern, self.html_content, re.DOTALL)
                    if match:
                        value = match.group(1).strip()
                        if 'rate' in key:
                            result[key] = self._parse_percentage(value)
                        else:
                            result[key] = self._parse_number(value)
        
        except Exception as e:
            print(f"提取销售统计数据失败: {e}")
        
        return result
    
    def extract_listing_info(self) -> Dict[str, Optional[str]]:
        """提取上架时间信息"""
        result = {
            'first_listing_date': None,     # 最早上架时间
            'last_publish_date': None,      # 最新发布时间
        }
        
        try:
            # 查找更新时间区域
            update_time = self.soup.find('div', class_='update-time')
            if update_time:
                spans = update_time.find_all('span')
                for span in spans:
                    text = span.get_text(strip=True)
                    if '最早上架时间' in text:
                        result['first_listing_date'] = self._extract_datetime(text)
                    elif '最新发布时间' in text:
                        result['last_publish_date'] = self._extract_datetime(text)
            
            # 正则备用方案
            if not result['first_listing_date']:
                match = re.search(r'最早上架时间[：:]\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', self.html_content)
                if match:
                    result['first_listing_date'] = match.group(1)
            
            if not result['last_publish_date']:
                match = re.search(r'最新发布时间[：:]\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', self.html_content)
                if match:
                    result['last_publish_date'] = match.group(1)
        
        except Exception as e:
            print(f"提取上架时间信息失败: {e}")
        
        return result
    
    def extract_trend_charts(self) -> Dict[str, Any]:
        """提取趋势图表数据
        
        包括：
        - 销量趋势数据
        - 成交价趋势数据
        """
        result = {
            'sales_trend': [],      # 销量趋势数据点
            'price_trend': [],      # 成交价趋势数据点
            'has_chart_data': False,
        }
        
        try:
            # 查找iframe中的图表数据
            # 图表数据通常通过iframe加载，URL中包含趋势数据API
            trend_iframe = self.soup.find('iframe', class_='iframe-find-goods')
            if trend_iframe:
                src = trend_iframe.get('src', '')
                srcdoc = trend_iframe.get('srcdoc', '')
                
                # 从src中提取offerId
                offer_match = re.search(r'offerId=(\d+)', src)
                if offer_match:
                    result['offer_id'] = offer_match.group(1)
                
                # 尝试从srcdoc中提取图表数据
                if srcdoc:
                    # 查找可能的数据脚本
                    data_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?});', srcdoc)
                    if data_match:
                        try:
                            chart_data = json.loads(data_match.group(1))
                            result['chart_data'] = chart_data
                            result['has_chart_data'] = True
                        except:
                            pass
            
            # 查找图表容器
            trend_chart = self.soup.find('div', class_='trend-chart')
            if trend_chart:
                # 查找tab选择器
                tabs = trend_chart.find('div', class_='tab-select')
                if tabs:
                    tab_spans = tabs.find_all('span')
                    result['available_tabs'] = [s.get_text(strip=True) for s in tab_spans]
                
                # 查找SKU选择器
                sku_select = trend_chart.find('div', class_='filter-select')
                if sku_select:
                    result['has_sku_filter'] = True
        
        except Exception as e:
            print(f"提取趋势图表数据失败: {e}")
        
        return result
    
    def _extract_trend_section_html(self) -> Optional[str]:
        """提取趋势区域的原始HTML"""
        try:
            # 查找商品成交趋势情况容器
            trend_div = self.soup.find('div', {'data-nav-name': '成交趋势'})
            if trend_div:
                return str(trend_div)
            
            # 备用方案：通过class查找
            trend_container = self.soup.find('div', class_='goodsTrendPanel-container')
            if trend_container:
                return str(trend_container)
        except Exception:
            pass
        return None
    
    def _parse_number(self, text: str) -> Optional[int]:
        """解析数字（处理千分位和+号）"""
        if not text:
            return None
        try:
            # 移除+号、件、单位等
            cleaned = re.sub(r'[+件个套,\s]', '', text)
            return int(cleaned) if cleaned else None
        except:
            return None
    
    def _parse_percentage(self, text: str) -> Optional[float]:
        """解析百分比"""
        if not text:
            return None
        try:
            cleaned = text.replace('%', '').strip()
            return float(cleaned) if cleaned else None
        except:
            return None
    
    def _extract_datetime(self, text: str) -> Optional[str]:
        """从文本中提取日期时间"""
        match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', text)
        return match.group(1) if match else None


def extract_trend_data(html_content: str) -> Dict[str, Any]:
    """便捷函数：从HTML中提取所有趋势数据"""
    extractor = TrendDataExtractor(html_content)
    return extractor.extract_all()


if __name__ == '__main__':
    # 测试代码
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            html = f.read()
        data = extract_trend_data(html)
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print("用法: python trend_extractor.py <html文件路径>")
