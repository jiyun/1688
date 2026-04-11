"""
图片编辑器工具模块

提供:
- 平台规则套餐
- 保存格式支持
- 比例转换工具
"""

from typing import Dict, Tuple, Optional
from PIL import Image
import os


PLATFORM_PRESETS = {
    '1688': {
        'name': '1688默认',
        'detail_width': 1440,
        'main_ratio': '1:1',
        'color_ratio': '1:1',
        'detail_format': 'jpg',
        'detail_quality': 95,
        'main_format': 'jpg',
        'main_quality': 95,
    },
    'jd': {
        'name': '京东默认',
        'detail_width': 750,
        'main_ratio': '1:1',
        'color_ratio': '1:1',
        'detail_format': 'jpg',
        'detail_quality': 90,
        'main_format': 'jpg',
        'main_quality': 90,
    },
    'taobao': {
        'name': '淘宝默认',
        'detail_width': 750,
        'main_ratio': '1:1',
        'color_ratio': '1:1',
        'detail_format': 'jpg',
        'detail_quality': 90,
        'main_format': 'jpg',
        'main_quality': 90,
    },
    'pdd': {
        'name': '拼多多默认',
        'detail_width': 750,
        'main_ratio': '1:1',
        'color_ratio': '1:1',
        'detail_format': 'jpg',
        'detail_quality': 85,
        'main_format': 'jpg',
        'main_quality': 85,
    },
}

SUPPORTED_FORMATS = {
    'jpg': {
        'name': 'JPEG',
        'ext': '.jpg',
        'quality_param': 'quality',
        'quality_range': (1, 100),
        'default_quality': 95,
        'supports_alpha': False,
    },
    'webp': {
        'name': 'WebP',
        'ext': '.webp',
        'quality_param': 'quality',
        'quality_range': (1, 100),
        'default_quality': 80,
        'supports_alpha': True,
    },
    'avif': {
        'name': 'AVIF',
        'ext': '.avif',
        'quality_param': 'quality',
        'quality_range': (1, 100),
        'default_quality': 80,
        'supports_alpha': True,
        'requires_pillow_avif': True,
    },
    'png': {
        'name': 'PNG',
        'ext': '.png',
        'quality_param': 'compress_level',
        'quality_range': (0, 9),
        'default_quality': 6,
        'supports_alpha': True,
    },
}


def save_image(image: Image.Image, output_path: str, format: str = 'jpg', quality: int = None) -> bool:
    """
    保存图片（支持多种格式）
    
    Args:
        image: PIL图片对象
        output_path: 输出路径
        format: 格式 (jpg/webp/avif/png)
        quality: 质量
    
    Returns:
        是否保存成功
    """
    try:
        fmt_config = SUPPORTED_FORMATS.get(format, SUPPORTED_FORMATS['jpg'])
        
        if quality is None:
            quality = fmt_config['default_quality']
        
        quality = max(fmt_config['quality_range'][0], 
                      min(quality, fmt_config['quality_range'][1]))
        
        if not fmt_config['supports_alpha'] and image.mode in ('RGBA', 'LA'):
            image = image.convert('RGB')
        
        save_kwargs = {fmt_config['quality_param']: quality}
        
        if format == 'avif':
            try:
                import pillow_avif
            except ImportError:
                format = 'webp'
                fmt_config = SUPPORTED_FORMATS['webp']
                save_kwargs = {'quality': quality}
        
        image.save(output_path, format=fmt_config['name'], **save_kwargs)
        return True
    
    except Exception as e:
        print(f"保存图片失败: {e}")
        return False


def convert_aspect_ratio(image: Image.Image, target_ratio: str = "1:1",
                         fill_color: Tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
    """
    比例转换：1:1 <=> 3:4（智能填充，不裁切）
    
    Args:
        image: 原图
        target_ratio: 目标比例 "1:1" 或 "3:4"
        fill_color: 填充颜色（默认白色）
    
    Returns:
        转换后的图片
    """
    width, height = image.size
    
    if target_ratio == "1:1":
        size = max(width, height)
        result = Image.new('RGB', (size, size), fill_color)
        x = (size - width) // 2
        y = (size - height) // 2
        result.paste(image, (x, y))
        return result
        
    elif target_ratio == "3:4":
        if width / height > 3 / 4:
            target_width = width
            target_height = int(width * 4 / 3)
        else:
            target_height = height
            target_width = int(height * 3 / 4)
        
        result = Image.new('RGB', (target_width, target_height), fill_color)
        x = (target_width - width) // 2
        y = (target_height - height) // 2
        result.paste(image, (x, y))
        return result
    
    return image


def detect_image_ratio(image: Image.Image) -> str:
    """
    检测图片比例
    
    Args:
        image: PIL图片对象
    
    Returns:
        比例类型 "1:1" 或 "3:4" 或 "other"
    """
    width, height = image.size
    ratio = width / height
    
    if 0.95 <= ratio <= 1.05:
        return "1:1"
    elif 0.72 <= ratio <= 0.78:
        return "3:4"
    else:
        return "other"


def get_edge_color(image: Image.Image, edge: str) -> Tuple[int, int, int]:
    """
    获取图片边缘的平均颜色
    
    Args:
        image: PIL图片对象
        edge: 边缘方向 ('left', 'right', 'top', 'bottom')
    
    Returns:
        RGB颜色元组
    """
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    width, height = image.size
    sample_size = min(100, height if edge in ('left', 'right') else width)
    
    if edge == 'left':
        pixels = [image.getpixel((0, y)) for y in range(0, height, max(1, height // sample_size))]
    elif edge == 'right':
        pixels = [image.getpixel((width - 1, y)) for y in range(0, height, max(1, height // sample_size))]
    elif edge == 'top':
        pixels = [image.getpixel((x, 0)) for x in range(0, width, max(1, width // sample_size))]
    else:
        pixels = [image.getpixel((x, height - 1)) for x in range(0, width, max(1, width // sample_size))]
    
    r = sum(p[0] for p in pixels) // len(pixels)
    g = sum(p[1] for p in pixels) // len(pixels)
    b = sum(p[2] for p in pixels) // len(pixels)
    
    return (r, g, b)


def create_gradient(color1: Tuple[int, int, int], color2: Tuple[int, int, int], 
                    width: int, height: int = 1) -> Image.Image:
    """
    创建渐变图像
    
    Args:
        color1: 起始颜色
        color2: 结束颜色
        width: 宽度
        height: 高度
    
    Returns:
        渐变图像
    """
    img = Image.new('RGB', (width, height))
    
    for x in range(width):
        ratio = x / width if width > 0 else 0
        r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
        g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
        b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
        
        for y in range(height):
            img.putpixel((x, y), (r, g, b))
    
    return img
