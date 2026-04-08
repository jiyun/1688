#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HTML价格提取模块"""

import re
from bs4 import BeautifulSoup
from typing import List, Dict, Tuple, Optional


class PriceExtractor:
    """从1688 HTML中提取价格信息"""
    
    def __init__(self, html_content: str):
        self.soup = BeautifulSoup(html_content, 'html.parser')
    
    def extract_all_prices(self) -> Dict:
        """提取所有价格信息"""
        result = {
            'main_price': None,
            'sku_prices': [],
            'consign_prices': [],
            'ladder_prices': [],
            'shipping_cost': 0
        }
        
        result['main_price'] = self._extract_main_price()
        result['sku_prices'] = self._extract_sku_prices()
        result['consign_prices'] = self._extract_consign_prices()
        result['ladder_prices'] = self._extract_ladder_prices()
        result['shipping_cost'] = self._extract_shipping_cost()
        
        return result
    
    def _extract_main_price(self) -> Optional[Dict]:
        """提取主价格"""
        main_price_div = self.soup.find('div', id='mainPrice')
        if not main_price_div:
            return None
        
        price_info = {}
        
        price_comp = main_price_div.find('div', class_='price-comp')
        if price_comp:
            price_spans = price_comp.find_all('span')
            if price_spans:
                price_text = ''.join([span.get_text() for span in price_spans])
                price_match = re.search(r'[\d.]+', price_text)
                if price_match:
                    price_info['price'] = float(price_match.group())
        
        min_amount_p = main_price_div.find('p')
        if min_amount_p:
            amount_match = re.search(r'(\d+)', min_amount_p.get_text())
            if amount_match:
                price_info['min_amount'] = int(amount_match.group(1))
        
        return price_info if price_info else None
    
    def _extract_sku_prices(self) -> List[Dict]:
        """提取SKU价格（颜色-尺码-价格）"""
        sku_prices = []
        
        sku_selection = self.soup.find('div', id='skuSelection')
        if not sku_selection:
            return sku_prices
        
        colors = []
        color_buttons = sku_selection.find_all('button', class_=lambda x: x and 'sku-filter-button' in x.split())
        for button in color_buttons:
            label_name = button.find('span', class_='label-name')
            if label_name:
                colors.append(label_name.get_text().strip())
        
        sizes = []
        expand_view_list = sku_selection.find('div', class_='expand-view-list')
        if expand_view_list:
            size_items = expand_view_list.find_all('div', class_=lambda x: x and 'expand-view-item' in x.split())
            for item in size_items:
                item_label = item.find('span', class_='item-label')
                if item_label:
                    size_text = item_label.get_text().strip()
                    
                    item_price = item.find('span', class_='item-price-stock')
                    price = None
                    if item_price:
                        price_match = re.search(r'[\d.]+', item_price.get_text())
                        if price_match:
                            price = float(price_match.group())
                    
                    sizes.append({
                        'size': size_text,
                        'price': price
                    })
        
        if colors and sizes:
            for color in colors:
                for size_info in sizes:
                    sku_prices.append({
                        'color': color,
                        'size': size_info['size'],
                        'price': size_info['price']
                    })
        elif colors:
            for color in colors:
                sku_prices.append({
                    'color': color,
                    'size': None,
                    'price': None
                })
        
        return sku_prices
    
    def _extract_consign_prices(self) -> List[Dict]:
        """提取代发价格"""
        consign_prices = []
        
        consign_div = self.soup.find('div', id='consign')
        if not consign_div:
            return consign_prices
        
        consign_info = consign_div.find('div', class_='od-consign-info')
        if consign_info:
            p_tag = consign_info.find('p')
            if p_tag:
                text = p_tag.get_text()
                
                patterns = [
                    (r'(\d+)件包邮.*?￥?([\d.]+)', 'single'),
                    (r'≥(\d+)件.*?￥?([\d.]+)', 'multi'),
                ]
                
                for pattern, price_type in patterns:
                    matches = re.findall(pattern, text)
                    for match in matches:
                        consign_prices.append({
                            'type': price_type,
                            'min_amount': int(match[0]),
                            'price': float(match[1])
                        })
        
        return consign_prices
    
    def _extract_ladder_prices(self) -> List[Dict]:
        """提取阶梯价格"""
        ladder_prices = []
        
        ladder_patterns = [
            r'"beginAmount":\s*(\d+),\s*"price":\s*([\d.]+)',
            r'"beginAmount":\s*(\d+),\s*"priceText":\s*"([\d.]+)"',
        ]
        
        html_text = str(self.soup)
        
        for pattern in ladder_patterns:
            matches = re.findall(pattern, html_text)
            for match in matches:
                ladder_prices.append({
                    'min_amount': int(match[0]),
                    'price': float(match[1])
                })
        
        return ladder_prices
    
    def _extract_shipping_cost(self) -> float:
        """提取运费"""
        shipping_cost = 0.0
        
        shipping_div = self.soup.find('div', class_=lambda x: x and 'shipping' in str(x).lower())
        if shipping_div:
            price_match = re.search(r'[\d.]+', shipping_div.get_text())
            if price_match:
                shipping_cost = float(price_match.group())
        
        if shipping_cost == 0:
            html_text = str(self.soup)
            
            patterns = [
                r'"freight"\s*:\s*([\d.]+)',
                r'"shippingFee"\s*:\s*([\d.]+)',
                r'"postFee"\s*:\s*([\d.]+)',
                r'运费[：:]\s*[￥¥]?\s*([\d.]+)',
                r'快递[：:]\s*[￥¥]?\s*([\d.]+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, html_text)
                if match:
                    try:
                        shipping_cost = float(match.group(1))
                        break
                    except ValueError:
                        continue
        
        return shipping_cost
    
    def get_price_summary(self) -> str:
        """获取价格摘要"""
        prices = self.extract_all_prices()
        lines = []
        
        if prices['main_price']:
            mp = prices['main_price']
            lines.append(f"主价格: ¥{mp.get('price', 'N/A')} ({mp.get('min_amount', 1)}件起批)")
        
        if prices['sku_prices']:
            lines.append(f"\nSKU价格 ({len(prices['sku_prices'])}条):")
            for sku in prices['sku_prices'][:10]:
                color = sku.get('color', 'N/A')
                size = sku.get('size', 'N/A')
                price = sku.get('price', 'N/A')
                lines.append(f"  {color} - {size}: ¥{price}")
        
        if prices['consign_prices']:
            lines.append(f"\n代发价格:")
            for cp in prices['consign_prices']:
                lines.append(f"  {cp['min_amount']}件: ¥{cp['price']}")
        
        if prices['ladder_prices']:
            lines.append(f"\n阶梯价格:")
            for lp in prices['ladder_prices']:
                lines.append(f"  ≥{lp['min_amount']}件: ¥{lp['price']}")
        
        return '\n'.join(lines) if lines else '未找到价格信息'


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python price_extractor.py <html_file>")
        sys.exit(1)
    
    html_file = sys.argv[1]
    
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    extractor = PriceExtractor(html_content)
    print(extractor.get_price_summary())
    
    print("\n" + "="*50)
    print("完整价格数据:")
    import json
    print(json.dumps(extractor.extract_all_prices(), ensure_ascii=False, indent=2))
