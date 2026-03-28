# HTML解析器工厂
from typing import Optional
from .base_parser import BaseParser
from .alibaba_parser import AlibabaParser
from .jd_parser import JDParser


class ParserFactory:
    """解析器工厂，根据HTML内容自动选择合适的解析器"""
    
    _parsers = {
        'alibaba': AlibabaParser,
        'jd': JDParser,
    }
    
    @classmethod
    def create_parser(cls, html_content: str, keep_avif: bool = False, webp_support: bool = False) -> Optional[BaseParser]:
        """根据HTML内容创建合适的解析器
        
        Args:
            html_content: HTML内容
            keep_avif: 是否保留AVIF格式（仅京东平台有效）
            webp_support: 是否支持WebP格式（仅阿里平台有效）
        
        Returns:
            对应平台的解析器实例，如果无法识别则返回None
        """
        platform = cls.detect_platform(html_content)
        
        if platform == 'unknown':
            return None
        
        parser_class = cls._parsers.get(platform)
        if parser_class:
            # 京东解析器支持keep_avif参数
            if platform == 'jd':
                return parser_class(html_content, keep_avif=keep_avif)
            # 阿里解析器支持webp_support参数
            elif platform == 'alibaba':
                return parser_class(html_content, keep_avif=keep_avif, webp_support=webp_support)
            return parser_class(html_content)
        
        return None
    
    @classmethod
    def detect_platform(cls, html_content: str) -> str:
        """检测HTML内容所属平台
        
        优先通过资源URL特征判断：
        - 360buyimg.com / vod.300hu.com -> 京东
        - alicdn.com / 1688.com -> 阿里巴巴
        
        Args:
            html_content: HTML内容
        
        Returns:
            平台标识: 'jd', 'alibaba', 'unknown'
        """
        # 京东特征
        jd_indicators = [
            '360buyimg.com',
            'vod.300hu.com',
            'item.jd.com',
            'jd.com',
        ]
        
        # 阿里巴巴特征
        alibaba_indicators = [
            'alicdn.com',
            '1688.com',
            'O1CN01',
        ]
        
        # 统计各平台特征出现次数
        jd_count = sum(1 for indicator in jd_indicators if indicator in html_content)
        alibaba_count = sum(1 for indicator in alibaba_indicators if indicator in html_content)
        
        # 根据特征数量判断平台
        if jd_count > alibaba_count:
            return 'jd'
        elif alibaba_count > jd_count:
            return 'alibaba'
        elif jd_count > 0:
            return 'jd'
        elif alibaba_count > 0:
            return 'alibaba'
        
        return 'unknown'
    
    @classmethod
    def get_supported_platforms(cls) -> list:
        """获取支持的平台列表"""
        return list(cls._parsers.keys())
    
    @classmethod
    def register_parser(cls, platform: str, parser_class: type):
        """注册新的解析器
        
        Args:
            platform: 平台标识
            parser_class: 解析器类
        """
        cls._parsers[platform] = parser_class
