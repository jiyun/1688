"""
图片编辑器UI组件

提供:
- 平台规则选择器
- 保存格式选择器
- 画笔大小选择器
- 视频时长选择器
"""

import tkinter as tk
from typing import Optional, Callable
import customtkinter as ctk

from .tools import PLATFORM_PRESETS, SUPPORTED_FORMATS


class PlatformPresetSelector(ctk.CTkFrame):
    """平台规则套餐选择器"""
    
    def __init__(self, master, on_change_callback: Optional[Callable] = None):
        super().__init__(master)
        
        self._on_change = on_change_callback
        self._current_preset = PLATFORM_PRESETS['1688']
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        self._platform_label = ctk.CTkLabel(self, text="平台规则:")
        self._platform_label.pack(side='left', padx=5)
        
        self._platform_var = tk.StringVar(value='1688')
        self._platform_combo = ctk.CTkComboBox(
            self,
            values=list(PLATFORM_PRESETS.keys()),
            variable=self._platform_var,
            command=self._on_platform_change,
            width=100
        )
        self._platform_combo.pack(side='left', padx=5)
        
        self._preset_label = ctk.CTkLabel(self, text="")
        self._preset_label.pack(side='left', padx=10)
        
        self._update_preset_display()
    
    def _on_platform_change(self, value: str):
        """平台变更"""
        self._current_preset = PLATFORM_PRESETS.get(value, PLATFORM_PRESETS['1688'])
        self._update_preset_display()
        
        if self._on_change:
            self._on_change(self._current_preset)
    
    def _update_preset_display(self):
        """更新显示"""
        preset = self._current_preset
        text = f"详情宽度:{preset['detail_width']} | 主图比例:{preset['main_ratio']} | 格式:{preset['detail_format']}"
        self._preset_label.configure(text=text)
    
    def get_current_preset(self) -> dict:
        """获取当前套餐"""
        return self._current_preset
    
    def get_platform(self) -> str:
        """获取当前平台"""
        return self._platform_var.get()


class FormatSelector(ctk.CTkFrame):
    """保存格式选择器"""
    
    def __init__(self, master, on_change_callback: Optional[Callable] = None):
        super().__init__(master)
        
        self._on_change = on_change_callback
        self._formats = SUPPORTED_FORMATS
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        self._format_label = ctk.CTkLabel(self, text="格式:")
        self._format_label.pack(side='left', padx=5)
        
        self._format_var = tk.StringVar(value='jpg')
        self._format_combo = ctk.CTkComboBox(
            self,
            values=list(self._formats.keys()),
            variable=self._format_var,
            command=self._on_format_change,
            width=80
        )
        self._format_combo.pack(side='left', padx=5)
        
        self._quality_label = ctk.CTkLabel(self, text="质量:")
        self._quality_label.pack(side='left', padx=5)
        
        self._quality_var = tk.IntVar(value=95)
        self._quality_slider = ctk.CTkSlider(
            self,
            from_=1,
            to=100,
            variable=self._quality_var,
            command=self._on_quality_change,
            width=100
        )
        self._quality_slider.pack(side='left', padx=5)
        
        self._quality_value_label = ctk.CTkLabel(self, text="95")
        self._quality_value_label.pack(side='left', padx=5)
    
    def _on_format_change(self, value: str):
        """格式变更"""
        fmt_config = self._formats.get(value, self._formats['jpg'])
        default_quality = fmt_config['default_quality']
        self._quality_var.set(default_quality)
        self._quality_value_label.configure(text=str(default_quality))
        
        if self._on_change:
            self._on_change(value, default_quality)
    
    def _on_quality_change(self, value):
        """质量变更"""
        quality = int(float(value))
        self._quality_value_label.configure(text=str(quality))
        
        if self._on_change:
            self._on_change(self._format_var.get(), quality)
    
    def get_format(self) -> str:
        """获取当前格式"""
        return self._format_var.get()
    
    def get_quality(self) -> int:
        """获取当前质量"""
        return self._quality_var.get()
    
    def get_format_config(self) -> dict:
        """获取格式配置"""
        return self._formats.get(self._format_var.get(), self._formats['jpg'])


class BrushSizeSelector(ctk.CTkFrame):
    """画笔大小选择器"""
    
    def __init__(self, master, on_change_callback: Optional[Callable] = None):
        super().__init__(master)
        
        self._on_change = on_change_callback
        
        from config import IMAGE_EDITOR_CONF
        self._brush_sizes = IMAGE_EDITOR_CONF['brush_sizes']
        self._default_level = IMAGE_EDITOR_CONF['default_brush_level']
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        self._label = ctk.CTkLabel(self, text="画笔:")
        self._label.pack(side='left', padx=5)
        
        self._level_var = tk.IntVar(value=self._default_level)
        
        for level in range(1, 6):
            btn = ctk.CTkButton(
                self,
                text=str(level),
                width=30,
                command=lambda l=level: self._on_level_change(l)
            )
            btn.pack(side='left', padx=2)
        
        self._size_label = ctk.CTkLabel(self, text=f"({self._brush_sizes[self._default_level]}px)")
        self._size_label.pack(side='left', padx=5)
    
    def _on_level_change(self, level: int):
        """档位变更"""
        self._level_var.set(level)
        size = self._brush_sizes[level]
        self._size_label.configure(text=f"({size}px)")
        
        if self._on_change:
            self._on_change(level, size)
    
    def get_level(self) -> int:
        """获取当前档位"""
        return self._level_var.get()
    
    def get_size(self) -> int:
        """获取当前大小"""
        return self._brush_sizes[self._level_var.get()]


class VideoDurationSelector(ctk.CTkFrame):
    """视频时长选择器"""
    
    def __init__(self, master, on_change_callback: Optional[Callable] = None):
        super().__init__(master)
        
        self._on_change = on_change_callback
        
        from config import IMAGE_EDITOR_CONF
        self._duration_options = IMAGE_EDITOR_CONF['video_duration_options']
        self._default_duration = IMAGE_EDITOR_CONF['default_video_duration']
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        self._label = ctk.CTkLabel(self, text="时长:")
        self._label.pack(side='left', padx=5)
        
        self._duration_var = tk.IntVar(value=self._default_duration)
        
        for duration in self._duration_options:
            btn = ctk.CTkButton(
                self,
                text=f"{duration}秒",
                width=50,
                command=lambda d=duration: self._on_duration_change(d)
            )
            btn.pack(side='left', padx=2)
    
    def _on_duration_change(self, duration: int):
        """时长变更"""
        self._duration_var.set(duration)
        
        if self._on_change:
            self._on_change(duration)
    
    def get_duration(self) -> int:
        """获取当前时长"""
        return self._duration_var.get()
