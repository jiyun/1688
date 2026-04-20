#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI工具模块 (CustomTkinter版本)
"""

import ctypes
import os
import sys
import tkinter as tk
import customtkinter as ctk
from config import get_button_config, BUTTON_CONF, UI_TYPOGRAPHY, get_font_size, get_font


def create_button(master, text, command=None, style_type='primary', size='default',
                  font_family=None, **kwargs):
    config = get_button_config(style_type, size)
    width = kwargs.pop('width', config['width'])
    height = kwargs.pop('height', config['height'])
    corner_radius = kwargs.pop('corner_radius', config['corner_radius'])
    border_width = kwargs.pop('border_width', config['border_width'])
    fg_color = kwargs.pop('fg_color', config['fg_color'])
    hover_color = kwargs.pop('hover_color', config['hover_color'])
    text_color = kwargs.pop('text_color', config['text_color'])
    
    font_size_key = config.get('font_size_key', 'base')
    font_size = get_font_size(font_size_key)
    if font_family:
        font = (font_family, font_size)
    else:
        font = kwargs.pop('font', None)
    
    btn_kwargs = dict(
        master=master,
        text=text,
        command=command,
        width=width,
        height=height,
        corner_radius=corner_radius,
        border_width=border_width,
        fg_color=fg_color,
        hover_color=hover_color,
        text_color=text_color,
    )
    if font:
        btn_kwargs['font'] = font
    
    return ctk.CTkButton(**btn_kwargs, **kwargs)


def set_button_theme(theme_name):
    if theme_name in BUTTON_CONF['themes']:
        BUTTON_CONF['current_theme'] = theme_name
        return True
    return False


def center_window(window, parent=None, width=None, height=None):
    if width is None:
        width = window.winfo_reqwidth()
    if height is None:
        height = window.winfo_reqheight()
    
    if parent:
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        x = parent_x + (parent_w - width) // 2
        y = parent_y + (parent_h - height) // 2
    else:
        screen_w = window.winfo_screenwidth()
        screen_h = window.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
    
    x = max(x, 0)
    y = max(y, 0)
    window.geometry(f'{width}x{height}+{x}+{y}')


def hide_console():
    """隐藏控制台窗口（仅在Windows系统中）"""
    if os.name == 'nt':
        try:
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd != 0:
                ctypes.windll.user32.ShowWindow(hwnd, 0)
                ctypes.windll.user32.UpdateWindow(hwnd)
        except Exception:
            pass


class ScrolledText:
    """CustomTkinter兼容的滚动文本控件"""
    
    def __init__(self, master=None, **kwargs):
        self.frame = ctk.CTkFrame(master, fg_color="transparent")
        
        self.scrollbar = ctk.CTkScrollbar(self.frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        width = kwargs.pop('width', 80)
        height = kwargs.pop('height', 24)
        
        bg_color = kwargs.pop('bg', '#1a1a1a')
        fg_color = kwargs.pop('fg', '#ffffff')
        
        self.text = tk.Text(
            self.frame,
            yscrollcommand=self.scrollbar.set,
            width=width,
            height=height,
            bg=bg_color,
            fg=fg_color,
            insertbackground=fg_color,
            selectbackground='#3a3a3a',
            relief=tk.FLAT,
            padx=10,
            pady=10,
            **kwargs
        )
        self.text.pack(fill=tk.BOTH, expand=True)
        self.scrollbar.configure(command=self.text.yview)
    
    def pack(self, **kwargs):
        self.frame.pack(**kwargs)
    
    def config(self, **kwargs):
        self.text.config(**kwargs)
    
    def configure(self, **kwargs):
        self.text.configure(**kwargs)
    
    def insert(self, *args, **kwargs):
        self.text.insert(*args, **kwargs)
    
    def see(self, *args, **kwargs):
        self.text.see(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        self.text.delete(*args, **kwargs)
    
    def tag_configure(self, *args, **kwargs):
        self.text.tag_configure(*args, **kwargs)
    
    def get(self, *args, **kwargs):
        return self.text.get(*args, **kwargs)
    
    def bind(self, *args, **kwargs):
        self.text.bind(*args, **kwargs)
    
    def unbind(self, *args, **kwargs):
        self.text.unbind(*args, **kwargs)
    
    def winfo_children(self):
        return self.text.winfo_children()
