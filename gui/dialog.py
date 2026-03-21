#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一弹窗提醒组件 (CustomTkinter版本)
确保所有弹窗在视觉风格、交互方式和信息展示格式上保持一致
"""

import tkinter as tk
import customtkinter as ctk
from typing import Optional, Callable
from gui.utils import create_button

DIALOG_COLORS = {
    'info': {
        'fg_color': '#E3F2FD',
        'text_color': '#1565C0',
        'icon': 'ℹ️',
        'button_fg_color': '#2196F3',
        'button_hover_color': '#1976D2'
    },
    'success': {
        'fg_color': '#E8F5E9',
        'text_color': '#2E7D32',
        'icon': '✅',
        'button_fg_color': '#4CAF50',
        'button_hover_color': '#388E3C'
    },
    'warning': {
        'fg_color': '#FFF3E0',
        'text_color': '#E65100',
        'icon': '⚠️',
        'button_fg_color': '#FF9800',
        'button_hover_color': '#F57C00'
    },
    'error': {
        'fg_color': '#FFEBEE',
        'text_color': '#C62828',
        'icon': '❌',
        'button_fg_color': '#F44336',
        'button_hover_color': '#D32F2F'
    },
    'question': {
        'fg_color': '#F3E5F5',
        'text_color': '#7B1FA2',
        'icon': '❓',
        'button_fg_color': '#9C27B0',
        'button_hover_color': '#7B1FA2'
    }
}


class CustomDialog:
    """自定义弹窗基类 (CustomTkinter版本)"""
    
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
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title(self.title)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        style = DIALOG_COLORS.get(self.dialog_type, DIALOG_COLORS['info'])
        
        self.dialog.geometry("400x200")
        self.dialog.resizable(False, False)
        
        self._center_dialog()
        
        main_frame = ctk.CTkFrame(self.dialog, fg_color=style['fg_color'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        icon_label = ctk.CTkLabel(
            main_frame,
            text=style['icon'],
            font=('Segoe UI Emoji', 32),
            text_color=style['text_color']
        )
        icon_label.pack(side=tk.LEFT, padx=(0, 15))
        
        content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        title_label = ctk.CTkLabel(
            content_frame,
            text=self.title,
            font=('Microsoft YaHei', 14, 'bold'),
            text_color=style['text_color']
        )
        title_label.pack(anchor='w')
        
        message_label = ctk.CTkLabel(
            content_frame,
            text=self.message,
            font=('Microsoft YaHei', 12),
            text_color=style['text_color'],
            wraplength=280,
            justify=tk.LEFT
        )
        message_label.pack(anchor='w', pady=(5, 0))
        
        button_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        button_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        for text, command in self.buttons:
            btn = create_button(
                button_frame,
                text,
                lambda cmd=command: self._on_button_click(cmd),
                'primary',
                fg_color=style['button_fg_color'],
                hover_color=style['button_hover_color']
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
