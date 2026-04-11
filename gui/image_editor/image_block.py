"""
图片块数据模型

定义图片块的数据结构，支持:
- 单图块
- 组合块(多张图横向拼接)
- 缩略图管理
- 娱乐图按需加载
"""

import os
from typing import List, Optional
from PIL import Image
from dataclasses import dataclass, field
from config import IMAGE_PROCESSING


@dataclass
class ImageBlock:
    """图片块数据模型"""
    
    image_path: str
    index: int
    width: int = 0
    height: int = 0
    thumbnail: Optional[Image.Image] = None
    original_image: Optional[Image.Image] = None
    sub_blocks: List['ImageBlock'] = field(default_factory=list)
    
    _thumbnail_size = (200, 200)
    _target_width = IMAGE_PROCESSING['detail_min_width']
    
    def __post_init__(self):
        """初始化后自动加载图片信息"""
        if self.image_path and os.path.exists(self.image_path):
            self._load_image_info()
    
    def _load_image_info(self):
        """加载图片基本信息"""
        try:
            with Image.open(self.image_path) as img:
                self.width = img.width
                self.height = img.height
        except Exception as e:
                print(f"加载图片信息失败: {e}")
    
    def is_composite(self) -> bool:
        """是否为组合块(多张图横向拼接)"""
        return len(self.sub_blocks) > 0
    
    def is_horizontal(self) -> bool:
        """是否为横图(宽度>=高度)"""
        return self.width >= self.height
    
    def is_vertical(self) -> bool:
        """是否为竖图(宽度<高度)"""
        return self.width < self.height
    
    def get_thumbnail(self) -> Image.Image:
        """获取缩略图,按需生成"""
        if self.thumbnail is None:
            self._generate_thumbnail()
        return self.thumbnail
    
    def _generate_thumbnail(self):
        """生成缩略图"""
        try:
            if self.original_image:
                img = self.original_image
            elif self.image_path and os.path.exists(self.image_path):
                img = Image.open(self.image_path)
            else:
                return
            
            img.thumbnail(self._thumbnail_size)
            self.thumbnail = img
        except Exception as e:
            print(f"生成缩略图失败: {e}")
    
    def get_original_image(self) -> Image.Image:
        """获取原图,按需加载"""
        if self.original_image is None:
            self._load_original_image()
        return self.original_image
    
    def _load_original_image(self):
        """加载原图并自动放大到目标宽度(1440px)"""
        try:
            if self.image_path and os.path.exists(self.image_path):
                img = Image.open(self.image_path)
                
                if img.width < self._target_width:
                    scale = self._target_width / img.width
                    new_height = int(img.height * scale)
                    img = img.resize((self._target_width, new_height), Image.LANCZOS)
                
                self.original_image = img
                self.width = img.width
                self.height = img.height
        except Exception as e:
            print(f"加载原图失败: {e}")
    
    def release_memory(self):
        """释放内存(清除原图和缩略图缓存)"""
        self.original_image = None
        self.thumbnail = None
    
    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            'image_path': self.image_path,
            'index': self.index,
            'width': self.width,
            'height': self.height,
            'is_composite': self.is_composite(),
            'sub_blocks': [b.to_dict() for b in self.sub_blocks]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ImageBlock':
        """从字典反序列化"""
        block = cls(
            image_path=data['image_path'],
            index=data['index']
        )
        block.width = data.get('width', 0)
        block.height = data.get('height', 0)
        
        if data.get('sub_blocks'):
            block.sub_blocks = [cls.from_dict(b) for b in data['sub_blocks']]
        
        return block
    
    def __repr__(self) -> str:
        if self.is_composite():
            return f"ImageBlock(composite, {len(self.sub_blocks)} blocks, index={self.index})"
        return f"ImageBlock({os.path.basename(self.image_path) if self.image_path else 'None'}, {self.width}x{self.height}, index={self.index})"
