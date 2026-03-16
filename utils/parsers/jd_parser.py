# 京东详情页解析器
import re
from typing import List, Tuple, Dict, Optional
from .base_parser import BaseParser


class JDParser(BaseParser):
    """京东详情页解析器"""
    
    PLATFORM = 'jd'
    
    def __init__(self, html_content: str, keep_avif: bool = False):
        super().__init__(html_content)
        self.keep_avif = keep_avif
    
    @staticmethod
    def detect_platform(html_content: str) -> bool:
        """检测是否为京东页面"""
        indicators = [
            '360buyimg.com',
            'jd.com',
            '京东',
            'item.jd.com',
            'vod.300hu.com'
        ]
        return any(indicator in html_content for indicator in indicators)
    
    def _clean_image_url(self, url: str, size: int = 1600) -> str:
        """清理图片URL，获取高清图
        
        Args:
            url: 原始URL
            size: 目标尺寸，默认1600px高清图，0表示原图
        
        Returns:
            处理后的URL
        """
        if not url:
            return url
        
        # 去除尺寸参数获取原图: /s228x228_jfs/ -> /jfs/
        # 或替换为高清尺寸: /s228x228_jfs/ -> /s1600x1600_jfs/
        if size > 0:
            url = re.sub(r'/s\d+x\d+_jfs/', f'/s{size}x{size}_jfs/', url)
        else:
            url = re.sub(r'/s\d+x\d+_jfs/', '/jfs/', url)
        
        # AVIF格式处理：默认移除.avif后缀获取jpg
        # 京东图片URL格式: xxx.jpg.avif 或 xxx.png.avif
        if not self.keep_avif and url.endswith('.avif'):
            url = url[:-5]  # 移除 .avif
        
        return url
    
    def get_main_images(self) -> List[str]:
        """获取主图链接"""
        main_images = []
        seen_urls = set()
        
        container = self.soup.select_one('#main-image .image-carousel-track')
        if not container:
            return main_images
        
        items = container.select('.item')
        for item in items:
            if item.select_one('.parameter'):
                continue
            
            imgs = item.select('img[data-sf-original-src]')
            for img in imgs:
                if 'thumbnails-play-icon' in img.get('class', []):
                    continue
                
                url = img.get('data-sf-original-src', '')
                if url:
                    clean_url = self._clean_image_url(url, size=0)
                    if clean_url not in seen_urls:
                        seen_urls.add(clean_url)
                        main_images.append(clean_url)
        
        return main_images
    
    def get_color_options(self) -> List[Tuple[str, Optional[str]]]:
        """获取颜色选项，返回 (颜色名称, 颜色图片URL) 列表
        
        包含所有色卡，包括无货的
        """
        color_options = []
        
        # 色卡容器: #specification-panel .specification-item-sku
        items = self.soup.select('#specification-panel .specification-item-sku')
        for item in items:
            # 获取颜色名称
            text_elem = item.select_one('.specification-item-sku-text')
            if not text_elem:
                continue
            
            color_name = text_elem.get_text(strip=True)
            
            # 获取颜色图片
            img = item.select_one('img[data-sf-original-src]')
            color_image = None
            if img:
                url = img.get('data-sf-original-src', '')
                # 色卡图获取原图
                color_image = self._clean_image_url(url, size=0)
            
            color_options.append((color_name, color_image))
        
        return color_options
    
    def get_detail_images(self) -> List[str]:
        """获取详情图链接"""
        detail_images = []
        
        # 详情图容器: #detail-main .shop-editor-floor
        images = self.soup.select('#detail-main .shop-editor-floor[data-sf-original-src]')
        for img in images:
            url = img.get('data-sf-original-src', '')
            if url:
                # 详情图也需要处理AVIF
                clean_url = self._clean_image_url(url, size=0)
                detail_images.append(clean_url)
        
        return detail_images
    
    def get_videos(self) -> List[str]:
        """获取视频链接"""
        videos = []
        seen_urls = set()
        
        # 查找所有video标签
        video_tags = self.soup.find_all('video')
        for video in video_tags:
            url = video.get('data-sf-original-src', '') or video.get('src', '')
            if url and url not in seen_urls:
                if not url.startswith('http'):
                    url = 'https:' + url
                videos.append(url)
                seen_urls.add(url)
        
        return videos
    
    def get_attributes(self) -> List[Tuple[str, str]]:
        """获取商品属性"""
        attributes = []
        
        # 京东的属性通常在参数区域
        # 尝试从页面中提取
        param_items = self.soup.select('.Ptable-item')
        for item in param_items:
            name_elem = item.select_one('.Ptable-item-name')
            value_elem = item.select_one('.Ptable-item-value')
            if name_elem and value_elem:
                name = name_elem.get_text(strip=True)
                value = value_elem.get_text(strip=True)
                if name and value:
                    attributes.append((name, value))
        
        return attributes
    
    def get_price(self) -> Optional[Dict]:
        """获取价格信息"""
        price_info = {}
        
        # 主价格: .summary-price .price
        price_elem = self.soup.select_one('.summary-price .price')
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            price_match = re.search(r'[\d.]+', price_text)
            if price_match:
                price_info['price'] = float(price_match.group())
        
        # 获取SKU价格
        sku_prices = []
        items = self.soup.select('#specification-panel .specification-item-sku')
        for item in items:
            text_elem = item.select_one('.specification-item-sku-text')
            if text_elem:
                sku_name = text_elem.get_text(strip=True)
                # 京东的SKU价格通常需要动态加载，这里只记录名称
                sku_prices.append({
                    'name': sku_name,
                    'price': None
                })
        
        if sku_prices:
            price_info['sku_prices'] = sku_prices
        
        return price_info if price_info else None
