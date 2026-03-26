# HTML解析工具 - 兼容层
import re
from bs4 import BeautifulSoup
from os.path import splitext
from typing import List, Tuple, Optional, Dict

from utils.parsers.factory import ParserFactory
from utils.parsers.base_parser import BaseParser


class HTMLParser:
    """HTML解析器 - 兼容层，自动选择平台解析器"""
    
    def __init__(self, html_content: str, keep_avif: bool = False):
        self.html_content = html_content
        self.soup = BeautifulSoup(html_content, 'html.parser')
        
        # 使用工厂创建解析器
        self._parser = ParserFactory.create_parser(html_content, keep_avif=keep_avif)
        self._platform = self._parser.get_platform() if self._parser else 'unknown'
    
    def get_platform(self) -> str:
        """获取当前HTML的平台标识"""
        return self._platform
    
    def _extract_image_id(self, url: str) -> Optional[str]:
        """从URL中提取图片唯一标识ID"""
        match = re.search(r'O1CN01\w+', url)
        return match.group() if match else None
    
    def _normalize_url(self, url: str) -> str:
        """标准化URL，移除后缀参数"""
        if url.endswith('_.webp'):
            url = url[:-6]
        if '.jpg_sum' in url:
            url = url.replace('.jpg_sum', '')
        return url
    
    def _get_color_card_urls(self) -> Tuple[List[str], set]:
        """获取色卡区所有图片URL（优先完整获取）"""
        if self._parser:
            color_options = self._parser.get_color_options()
            urls = [img for name, img in color_options if img]
            ids = set()
            for url in urls:
                img_id = self._extract_image_id(url)
                if img_id:
                    ids.add(img_id)
            return urls, ids
        return [], set()
    
    def get_main_images(self) -> List[str]:
        """获取主图链接"""
        if self._parser:
            return self._parser.get_main_images()
        return []
    
    def get_color_options(self) -> List[Tuple[str, Optional[str]]]:
        """获取颜色选项"""
        if self._parser:
            return self._parser.get_color_options()
        return []
    
    def get_detail_images(self) -> List[str]:
        """获取详情图链接"""
        if self._parser:
            return self._parser.get_detail_images()
        return []
    
    def get_videos(self) -> List[str]:
        """获取视频链接"""
        if self._parser:
            return self._parser.get_videos()
        return []
    
    def get_attributes(self) -> List[Tuple[str, str]]:
        """获取商品属性"""
        if self._parser:
            return self._parser.get_attributes()
        return []
    
    def get_price(self) -> Optional[Dict]:
        """获取价格信息"""
        if self._parser:
            return self._parser.get_price()
        return None
    
    def get_title(self) -> Optional[str]:
        """获取商品标题"""
        if self._parser:
            return self._parser.get_title()
        return None
    
    def get_description(self) -> Optional[str]:
        """获取商品描述"""
        if self._parser:
            return self._parser.get_description()
        return None
    
    def get_product_url(self) -> Optional[str]:
        """获取商品链接"""
        if self._parser:
            return self._parser.get_product_url()
        return None
    
    def get_product_code(self) -> Optional[str]:
        """获取商品编码"""
        if self._parser:
            return self._parser.get_product_code()
        return None
    
    def get_shop_info(self) -> Optional[Dict]:
        """获取店铺信息"""
        if self._parser:
            return self._parser.get_shop_info()
        return None
    
    def get_ship_from(self) -> Optional[str]:
        """获取发货地"""
        if self._parser:
            return self._parser.get_ship_from()
        return None
    
    def get_sales_count(self) -> int:
        """获取销量"""
        if self._parser:
            return self._parser.get_sales_count()
        return 0
    
    def get_min_order(self) -> int:
        """获取起批量"""
        if self._parser:
            return self._parser.get_min_order()
        return 1
    
    def get_all_info(self) -> Dict:
        """获取所有信息"""
        if self._parser:
            return self._parser.get_all_info()
        return {}
