#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI日志模块 (CustomTkinter版本)
"""

import re
import tkinter as tk
from gui.utils import ScrolledText
from config import GUI_CONF


class GUILogger:
    """GUI日志处理类"""
    
    def __init__(self, log_text_widget):
        """初始化日志处理器
        
        Args:
            log_text_widget: 用于显示日志的文本控件
        """
        self.log_text = log_text_widget
        self._init_log_tags()
    
    def _init_log_tags(self):
        """初始化日志标签样式"""
        for log_type, color in GUI_CONF['log_colors'].items():
            self.log_text.tag_configure(color, foreground=color)
    
    def log(self, message, message_type="info"):
        """添加日志信息到日志窗口
        
        Args:
            message: 日志消息
            message_type: 消息类型，可选值：info, success, warning, error, input
        """
        self.log_text.config(state=tk.NORMAL)
        
        color = GUI_CONF['log_colors'].get(message_type, "white")
        
        if message_type == "info":
            if "开始清理小文件..." in message or "没有需要删除的小文件" in message:
                self.log_text.tag_configure("yellow", foreground="yellow")
                self.log_text.insert(tk.END, message + "\n", "yellow")
            elif "aria2c.exe" in message and ("--console-log-level" in message or "--dir=" in message):
                self.log_text.tag_configure(color, foreground=color)
                self.log_text.insert(tk.END, message + "\n", color)
            else:
                path_pattern = r'([A-Za-z]:\\[\\\w\s#.-]+|[./][\\\w\s#.-]+|\\b[\w#.-]+\\.[\w]+\\b)'
                paths = re.findall(path_pattern, message)
                
                if paths:
                    current_pos = 0
                    for path in paths:
                        path_pos = message.find(path, current_pos)
                        if path_pos != -1:
                            if path_pos > current_pos:
                                self.log_text.tag_configure(color, foreground=color)
                                self.log_text.insert(tk.END, message[current_pos:path_pos], color)
                            self.log_text.tag_configure("yellow", foreground="yellow")
                            self.log_text.insert(tk.END, path, "yellow")
                            current_pos = path_pos + len(path)
                    if current_pos < len(message):
                        self.log_text.tag_configure(color, foreground=color)
                        self.log_text.insert(tk.END, message[current_pos:] + "\n", color)
                    else:
                        self.log_text.insert(tk.END, "\n")
                else:
                    self.log_text.tag_configure(color, foreground=color)
                    self.log_text.insert(tk.END, message + "\n", color)
        else:
            self.log_text.tag_configure(color, foreground=color)
            self.log_text.insert(tk.END, message + "\n", color)
        
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
