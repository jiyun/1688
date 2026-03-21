#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拖放功能模块 (CustomTkinter版本)
支持将HTML文件拖放到应用程序窗口
实现动态显示的覆盖层效果
"""

import os
import tkinter as tk
import customtkinter as ctk

try:
    from tkinterdnd2 import DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False


class DynamicDropOverlay:
    """动态拖放覆盖层管理器 (CustomTkinter版本)
    
    实现拖放区域的动态显示和隐藏：
    - 默认隐藏，不占用界面空间
    - 检测到拖放操作时显示覆盖层
    - 拖放完成或取消时自动隐藏
    """
    
    def __init__(self, root, target_frame, on_drop_callback):
        """初始化拖放覆盖层
        
        Args:
            root: 根窗口（必须是TkinterDnD.Tk实例）
            target_frame: 目标框架（覆盖层将显示在此框架上）
            on_drop_callback: 放置回调函数，接收文件路径列表
        """
        self.root = root
        self.target_frame = target_frame
        self.on_drop_callback = on_drop_callback
        
        self.overlay_frame = None
        self.is_visible = False
        
        self._create_overlay()
        self._bind_events()
    
    def _create_overlay(self):
        """创建覆盖层（初始隐藏）"""
        self.overlay_frame = ctk.CTkFrame(
            self.target_frame,
            fg_color='#E3F2FD',
            corner_radius=10
        )
        
        inner_frame = ctk.CTkFrame(self.overlay_frame, fg_color="transparent")
        inner_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        self.overlay_icon = ctk.CTkLabel(
            inner_frame,
            text='📁',
            font=('Segoe UI Emoji', 48),
            text_color='#1976D2'
        )
        self.overlay_icon.pack(pady=(0, 10))
        
        self.overlay_label = ctk.CTkLabel(
            inner_frame,
            text='将 HTML 文件拖放到此处\n添加到处理队列',
            font=('Microsoft YaHei', 16, 'bold'),
            text_color='#1976D2'
        )
        self.overlay_label.pack()
        
        self.hint_label = ctk.CTkLabel(
            inner_frame,
            text='仅支持 .html 文件',
            font=('Microsoft YaHei', 12),
            text_color='#64B5F6'
        )
        self.hint_label.pack(pady=(10, 0))
    
    def _bind_events(self):
        """绑定拖放事件到根窗口"""
        if HAS_DND:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self._on_drop)
            self.root.dnd_bind('<<DropEnter>>', self._on_drag_enter)
            self.root.dnd_bind('<<DropLeave>>', self._on_drag_leave)
            self.root.dnd_bind('<<DropPosition>>', self._on_drag_over)
    
    def _on_drag_enter(self, event):
        """处理拖入事件 - 显示覆盖层"""
        if not self.is_visible:
            self.show_overlay()
        self._set_style('active')
        return event.action if hasattr(event, 'action') else None
    
    def _on_drag_leave(self, event):
        """处理拖出事件 - 隐藏覆盖层"""
        self.hide_overlay()
    
    def _on_drag_over(self, event):
        """处理悬停事件"""
        if not self.is_visible:
            self.show_overlay()
        if event.data:
            files = self._parse_dropped_files(event.data)
            valid_files, _ = self._validate_files(files)
            if valid_files:
                self._set_style('valid')
            else:
                self._set_style('invalid')
        return event.action if hasattr(event, 'action') else None
    
    def _on_drop(self, event):
        """处理放置事件"""
        self.hide_overlay()
        
        if event.data:
            files = self._parse_dropped_files(event.data)
            valid_files, invalid_files = self._validate_files(files)
            
            if valid_files:
                self.on_drop_callback(valid_files)
            
            if invalid_files:
                self._show_invalid_files_warning(invalid_files)
    
    def show_overlay(self):
        """显示覆盖层"""
        if not self.is_visible:
            self.is_visible = True
            self.overlay_frame.place(
                x=0, y=0,
                relwidth=1, relheight=1
            )
            self.overlay_frame.lift()
            self._set_style('active')
    
    def hide_overlay(self):
        """隐藏覆盖层"""
        if self.is_visible:
            self.is_visible = False
            self.overlay_frame.place_forget()
    
    def _set_style(self, state):
        """设置覆盖层样式
        
        Args:
            state: 'active' | 'valid' | 'invalid'
        """
        styles = {
            'active': {
                'fg_color': '#E3F2FD',
                'text_color': '#1976D2',
                'hint_color': '#64B5F6',
                'icon': '📁'
            },
            'valid': {
                'fg_color': '#E8F5E9',
                'text_color': '#2E7D32',
                'hint_color': '#81C784',
                'icon': '✅'
            },
            'invalid': {
                'fg_color': '#FFEBEE',
                'text_color': '#C62828',
                'hint_color': '#EF9A9A',
                'icon': '⚠️'
            }
        }
        
        style = styles.get(state, styles['active'])
        
        self.overlay_frame.configure(fg_color=style['fg_color'])
        self.overlay_icon.configure(text_color=style['text_color'], text=style['icon'])
        self.overlay_label.configure(text_color=style['text_color'])
        self.hint_label.configure(text_color=style['hint_color'])
    
    def _parse_dropped_files(self, data):
        """解析拖放的文件路径"""
        files = []
        
        if not data:
            return files
        
        if data.startswith('{'):
            end = data.find('}')
            if end != -1:
                files.append(data[1:end])
                remaining = data[end+1:].strip()
                if remaining:
                    files.extend(self._parse_dropped_files(remaining))
        else:
            parts = data.split()
            for part in parts:
                if os.path.exists(part):
                    files.append(part)
        
        return files
    
    def _validate_files(self, files):
        """验证文件类型"""
        valid_files = []
        invalid_files = []
        
        for file_path in files:
            if os.path.isfile(file_path):
                ext = os.path.splitext(file_path)[1].lower()
                if ext == '.html':
                    valid_files.append(file_path)
                else:
                    invalid_files.append(file_path)
        
        return valid_files, invalid_files
    
    def _show_invalid_files_warning(self, invalid_files):
        """显示无效文件警告"""
        from gui.dialog import show_warning
        count = len(invalid_files)
        if count == 1:
            message = f"以下文件不是HTML文件，已忽略：\n{invalid_files[0]}"
        else:
            file_list = '\n'.join(invalid_files[:5])
            if count > 5:
                file_list += f"\n... 还有 {count - 5} 个文件"
            message = f"以下 {count} 个文件不是HTML文件，已忽略：\n{file_list}"
        
        show_warning(self.root, "文件类型警告", message)
    
    def destroy(self):
        """销毁拖放目标"""
        if HAS_DND:
            try:
                self.root.drop_target_unregister()
            except:
                pass


def check_dnd_support():
    """检查拖放功能支持情况"""
    if HAS_DND:
        return True, "拖放功能已启用（使用tkinterdnd2）"
    else:
        return False, "拖放功能未启用（需要安装tkinterdnd2库）"


def create_dnd_root():
    """创建支持拖放的根窗口"""
    if HAS_DND:
        from tkinterdnd2 import TkinterDnD
        return TkinterDnD.Tk()
    else:
        return tk.Tk()
