#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI日志模块
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
        
        # 根据消息类型设置不同的颜色
        color = GUI_CONF['log_colors'].get(message_type, "white")
        
        # 检查是否需要特殊处理
        if message_type == "info":
            # 检查是否包含特定提示词
            if "开始清理小文件..." in message or "没有需要删除的小文件" in message:
                # 整个句子标记为黄色
                self.log_text.tag_configure("yellow", foreground="yellow")
                self.log_text.insert(tk.END, message + "\n", "yellow")
            # 检查是否是复杂命令行参数（包含多个空格和特殊字符）
            elif "aria2c.exe" in message and ("--console-log-level" in message or "--dir=" in message):
                # 复杂命令行参数，不进行染色
                self.log_text.tag_configure(color, foreground=color)
                self.log_text.insert(tk.END, message + "\n", color)
            else:
                # 检查是否包含路径或文件信息
                # 匹配路径模式（改进版，支持更多路径格式）
                # 1. 完整路径（包含盘符）
                # 2. 相对路径（以 ./ 或 ../ 开头）
                # 3. 简单文件名（包含扩展名）
                path_pattern = r'([A-Za-z]:\\[\\\w\s#.-]+|[./][\\\w\s#.-]+|\\b[\w#.-]+\\.[\w]+\\b)'
                paths = re.findall(path_pattern, message)
                
                if paths:
                    # 分段插入文本，路径部分标记为黄色
                    current_pos = 0
                    for path in paths:
                        # 找到路径在消息中的位置
                        path_pos = message.find(path, current_pos)
                        if path_pos != -1:
                            # 插入路径前的文本
                            if path_pos > current_pos:
                                self.log_text.tag_configure(color, foreground=color)
                                self.log_text.insert(tk.END, message[current_pos:path_pos], color)
                            # 插入路径文本，标记为黄色
                            self.log_text.tag_configure("yellow", foreground="yellow")
                            self.log_text.insert(tk.END, path, "yellow")
                            # 更新当前位置
                            current_pos = path_pos + len(path)
                    # 插入剩余的文本
                    if current_pos < len(message):
                        self.log_text.tag_configure(color, foreground=color)
                        self.log_text.insert(tk.END, message[current_pos:] + "\n", color)
                    else:
                        self.log_text.insert(tk.END, "\n")
                else:
                    # 普通文本，使用默认颜色
                    self.log_text.tag_configure(color, foreground=color)
                    self.log_text.insert(tk.END, message + "\n", color)
        else:
            # 其他消息类型，使用默认颜色
            self.log_text.tag_configure(color, foreground=color)
            self.log_text.insert(tk.END, message + "\n", color)
        
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
