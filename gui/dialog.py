#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一弹窗提醒组件
确保所有弹窗在视觉风格、交互方式和信息展示格式上保持一致
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable

DIALOG_COLORS = {
    'info': {
        'bg': '#E3F2FD',
        'fg': '#1565C0',
        'icon': 'ℹ️',
        'button_bg': '#2196F3',
        'button_fg': 'white'
    },
    'success': {
        'bg': '#E8F5E9',
        'fg': '#2E7D32',
        'icon': '✅',
        'button_bg': '#4CAF50',
        'button_fg': 'white'
    },
    'warning': {
        'bg': '#FFF3E0',
        'fg': '#E65100',
        'icon': '⚠️',
        'button_bg': '#FF9800',
        'button_fg': 'white'
    },
    'error': {
        'bg': '#FFEBEE',
        'fg': '#C62828',
        'icon': '❌',
        'button_bg': '#F44336',
        'button_fg': 'white'
    },
    'question': {
        'bg': '#F3E5F5',
        'fg': '#7B1FA2',
        'icon': '❓',
        'button_bg': '#9C27B0',
        'button_fg': 'white'
    }
}


class CustomDialog:
    """自定义弹窗基类"""
    
    def __init__(self, parent: tk.Tk, title: str, message: str, 
                 dialog_type: str = 'info', buttons: list = None):
        self.parent = parent
        self.title = title
        self.message = message
        self.dialog_type = dialog_type
        self.buttons = buttons or [('确定', None)]
        self.result = None
        
        self._create_dialog()
    
    def _create_dialog(self):
        """创建弹窗"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(self.title)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        style = DIALOG_COLORS.get(self.dialog_type, DIALOG_COLORS['info'])
        
        self.dialog.configure(bg=style['bg'])
        
        self.dialog.geometry("400x180")
        self.dialog.resizable(False, False)
        
        self._center_dialog()
        
        main_frame = tk.Frame(self.dialog, bg=style['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        icon_label = tk.Label(
            main_frame,
            text=style['icon'],
            font=('Segoe UI Emoji', 32),
            bg=style['bg'],
            fg=style['fg']
        )
        icon_label.pack(side=tk.LEFT, padx=(0, 15))
        
        content_frame = tk.Frame(main_frame, bg=style['bg'])
        content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        title_label = tk.Label(
            content_frame,
            text=self.title,
            font=('Microsoft YaHei', 12, 'bold'),
            bg=style['bg'],
            fg=style['fg']
        )
        title_label.pack(anchor='w')
        
        message_label = tk.Label(
            content_frame,
            text=self.message,
            font=('Microsoft YaHei', 10),
            bg=style['bg'],
            fg=style['fg'],
            wraplength=280,
            justify=tk.LEFT
        )
        message_label.pack(anchor='w', pady=(5, 0))
        
        button_frame = tk.Frame(self.dialog, bg=style['bg'])
        button_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        for text, command in self.buttons:
            btn = tk.Button(
                button_frame,
                text=text,
                font=('Microsoft YaHei', 10),
                bg=style['button_bg'],
                fg=style['button_fg'],
                width=10,
                relief=tk.FLAT,
                cursor='hand2',
                command=lambda cmd=command: self._on_button_click(cmd)
            )
            btn.pack(side=tk.RIGHT, padx=5)
        
        self.dialog.protocol("WM_DELETE_WINDOW", lambda: self._on_button_click(None))
        
        self.dialog.bind('<Escape>', lambda e: self._on_button_click(None))
        self.dialog.bind('<Return>', lambda e: self._on_button_click(self.buttons[0][1] if self.buttons else None))
        
        self.dialog.wait_window()
    
    def _center_dialog(self):
        """将弹窗相对于父窗体居中显示"""
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        x = parent_x + (parent_width - width) // 2
        y = parent_y + (parent_height - height) // 2
        
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')
    
    def _on_button_click(self, command):
        """按钮点击处理"""
        self.result = command
        if command:
            command()
        self.dialog.destroy()
    
    def get_result(self):
        """获取结果"""
        return self.result


def show_info(parent: tk.Tk, title: str, message: str):
    """显示信息弹窗"""
    dialog = CustomDialog(parent, title, message, 'info')
    return dialog.get_result()


def show_success(parent: tk.Tk, title: str, message: str):
    """显示成功弹窗"""
    dialog = CustomDialog(parent, title, message, 'success')
    return dialog.get_result()


def show_warning(parent: tk.Tk, title: str, message: str):
    """显示警告弹窗"""
    dialog = CustomDialog(parent, title, message, 'warning')
    return dialog.get_result()


def show_error(parent: tk.Tk, title: str, message: str):
    """显示错误弹窗"""
    dialog = CustomDialog(parent, title, message, 'error')
    return dialog.get_result()


def ask_yes_no(parent: tk.Tk, title: str, message: str) -> bool:
    """显示是/否确认弹窗"""
    dialog = CustomDialog(
        parent, title, message, 'question',
        buttons=[('否', False), ('是', True)]
    )
    return dialog.get_result()


def ask_ok_cancel(parent: tk.Tk, title: str, message: str) -> bool:
    """显示确定/取消弹窗"""
    dialog = CustomDialog(
        parent, title, message, 'question',
        buttons=[('取消', False), ('确定', True)]
    )
    return dialog.get_result()
