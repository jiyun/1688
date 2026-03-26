# HTML解析器基类
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from typing import List, Tuple, Dict, Optional


class BaseParser(ABC):
    """HTML解析器基类"""
    
    PLATFORM = 'unknown'
    
    def __init__(self, html_content: str):
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.html_content = html_content
    
    @staticmethod
    def detect_platform(html_content: str) -> str:
        """根据HTML内容检测平台"""
        if '360buyimg.com' in html_content or 'jd.com' in html_content:
            return 'jd'
        if '1688.com' in html_content or 'alicdn.com' in html_content:
            return 'alibaba'
        return 'unknown'
    
    @abstractmethod
    def get_main_images(self) -> List[str]:
        """获取主图链接"""
        pass
    
    @abstractmethod
    def get_color_options(self) -> List[Tuple[str, Optional[str]]]:
        """获取颜色选项，返回 (颜色名称, 颜色图片URL) 列表"""
        pass
    
    @abstractmethod
    def get_detail_images(self) -> List[str]:
        """获取详情图链接"""
        pass
    
    @abstractmethod
    def get_videos(self) -> List[str]:
        """获取视频链接"""
        pass
    
    @abstractmethod
    def get_attributes(self) -> List[Tuple[str, str]]:
        """获取商品属性，返回 (属性名, 属性值) 列表"""
        pass
    
    @abstractmethod
    def get_price(self) -> Optional[Dict]:
        """获取价格信息"""
        pass
    
    def get_title(self) -> Optional[str]:
        """获取商品标题"""
        return None
    
    def get_description(self) -> Optional[str]:
        """获取商品描述/卖点"""
        return None
    
    def get_product_url(self) -> Optional[str]:
        """获取商品原始链接"""
        return None
    
    def get_product_code(self) -> Optional[str]:
        """获取商品编码"""
        return None
    
    def get_shop_info(self) -> Optional[Dict]:
        """获取店铺信息"""
        return None
    
    def get_ship_from(self) -> Optional[str]:
        """获取发货地"""
        return None
    
    def get_sales_count(self) -> int:
        """获取销量"""
        return 0
    
    def get_min_order(self) -> int:
        """获取起批量"""
        return 1
    
    def get_all_info(self) -> Dict:
        """获取所有信息"""
        return {
            'platform': self.get_platform(),
            'title': self.get_title(),
            'description': self.get_description(),
            'product_url': self.get_product_url(),
            'product_code': self.get_product_code(),
            'shop_info': self.get_shop_info(),
            'ship_from': self.get_ship_from(),
            'sales_count': self.get_sales_count(),
            'min_order': self.get_min_order(),
            'main_images': self.get_main_images(),
            'color_options': self.get_color_options(),
            'detail_images': self.get_detail_images(),
            'videos': self.get_videos(),
            'attributes': self.get_attributes(),
            'price': self.get_price()
        }
    
    def get_platform(self) -> str:
        """获取平台标识"""
        return self.PLATFORM
