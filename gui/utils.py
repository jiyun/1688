#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI工具模块
"""

import ctypes
import os
import sys
import tkinter as tk
from tkinter import scrolledtext


def hide_console():
    """隐藏控制台窗口（仅在Windows系统中）"""
    if os.name == 'nt':  # Windows系统
        try:
            # 获取当前进程句柄
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd != 0:
                # 隐藏窗口
                ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0
                # 更新窗口状态
                ctypes.windll.user32.UpdateWindow(hwnd)
        except Exception:
            pass  # 忽略控制台隐藏失败，不影响主程序运行


class ScrolledTextFallback:
    """如果scrolledtext不可用，创建一个简单的替代类"""
    def __init__(self, master=None, **kwargs):
        self.frame = tk.Frame(master)
        self.scrollbar = tk.Scrollbar(self.frame, orient=tk.VERTICAL)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text = tk.Text(self.frame, yscrollcommand=self.scrollbar.set, **kwargs)
        self.text.pack(fill=tk.BOTH, expand=True)
        self.scrollbar.config(command=self.text.yview)
    
    def pack(self, **kwargs):
        self.frame.pack(**kwargs)
    
    def config(self, **kwargs):
        self.text.config(**kwargs)
    
    def insert(self, *args, **kwargs):
        self.text.insert(*args, **kwargs)
    
    def see(self, *args, **kwargs):
        self.text.see(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        self.text.delete(*args, **kwargs)
    
    def tag_configure(self, *args, **kwargs):
        self.text.tag_configure(*args, **kwargs)


# 尝试导入scrolledtext，如果失败则使用替代方案
try:
    from tkinter import scrolledtext
    ScrolledText = scrolledtext.ScrolledText
except ImportError:
    # 如果scrolledtext不可用，使用我们的替代类
    class scrolledtext:
        ScrolledText = ScrolledTextFallback
    ScrolledText = ScrolledTextFallback
