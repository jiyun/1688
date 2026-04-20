import sys
import os
sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

"""
图片编辑器模块

提供商品图片的可视化编辑功能，包括:
- 图片块管理
- 画布编辑
- 噪音历史记录
- 智能布局拼接
"""

from .image_block import ImageBlock
from .history import HistoryManager
from .editor_canvas import EditorCanvas
from .editor_window import ImageEditorWindow

__all__ = ['ImageBlock', 'HistoryManager', 'EditorCanvas', 'ImageEditorWindow']
