#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一弹窗提醒组件 (CustomTkinter版本)
确保所有弹窗在视觉风格、交互方式和信息展示格式上保持一致
包含智能导入对话框功能
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import re
from typing import Optional, Callable, List, Dict, Any
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
        
        # 获取父窗口的字体设置
        self.font_name = getattr(parent, 'available_font', 'Microsoft YaHei')
        self.font_size = getattr(parent, 'font_size', 10)
        
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
            font=(self.font_name, self.font_size + 4, 'bold'),
            text_color=style['text_color']
        )
        title_label.pack(anchor='w')
        
        message_label = ctk.CTkLabel(
            content_frame,
            text=self.message,
            font=(self.font_name, self.font_size + 2),
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
                hover_color=style['button_hover_color'],
                font=(self.font_name, self.font_size + 1)
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


class ImportDialog:
    """智能导入对话框 - 从混合文本中提取商品信息并导入数据库"""
    
    def __init__(self, parent):
        self.parent = parent
        self.result: List[Dict[str, Any]] = []
        self.parsed_data: List[Dict[str, Any]] = []
        
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("智能导入")
        self.dialog.geometry("900x600")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.focus_force()
        self.dialog.lift()
        
        self._create_widgets()
        
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
        self.dialog.wait_window()
    
    def _create_widgets(self):
        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        import_btn = create_button(button_frame, "确认导入", self._on_import, 'success')
        import_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = create_button(button_frame, "取消", self._on_cancel, 'secondary')
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        self.status_label = ctk.CTkLabel(button_frame, text="")
        self.status_label.pack(side=tk.RIGHT, padx=10)
        
        input_frame = ctk.CTkFrame(main_frame)
        input_frame.pack(fill=tk.X, pady=(0, 5))
        
        ctk.CTkLabel(input_frame, text="粘贴混合文本:", font=("", 12, "bold")).pack(anchor=tk.W, padx=5, pady=5)
        
        self.input_text = ctk.CTkTextbox(input_frame, height=120)
        self.input_text.pack(fill=tk.X, padx=5, pady=5)
        
        parse_btn = create_button(input_frame, "解析文本", self._parse_text, 'primary')
        parse_btn.pack(pady=5)
        
        preview_frame = ctk.CTkFrame(main_frame)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ctk.CTkLabel(preview_frame, text="解析结果预览 (点击勾选确认导入):", font=("", 12, "bold")).pack(anchor=tk.W, padx=5, pady=5)
        
        select_frame = ctk.CTkFrame(preview_frame, fg_color="transparent")
        select_frame.pack(fill=tk.X, padx=5, pady=2)
        
        select_all_btn = create_button(select_frame, "全选", self._select_all, 'secondary', width=60)
        select_all_btn.pack(side=tk.LEFT, padx=3)
        
        deselect_all_btn = create_button(select_frame, "全不选", self._deselect_all, 'secondary', width=60)
        deselect_all_btn.pack(side=tk.LEFT, padx=3)
        
        tree_container = ctk.CTkFrame(preview_frame, fg_color="transparent")
        tree_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ("select", "product_id", "dsid", "price", "platform", "source_url")
        self.preview_tree = ttk.Treeview(tree_container, columns=columns, show="headings", selectmode="none")
        
        self.preview_tree.heading("select", text="导入")
        self.preview_tree.heading("product_id", text="商品ID")
        self.preview_tree.heading("dsid", text="DSID")
        self.preview_tree.heading("price", text="价格")
        self.preview_tree.heading("platform", text="平台")
        self.preview_tree.heading("source_url", text="来源URL")
        
        self.preview_tree.column("select", width=50, anchor="center")
        self.preview_tree.column("product_id", width=120, anchor="center")
        self.preview_tree.column("dsid", width=140, anchor="center")
        self.preview_tree.column("price", width=80, anchor="center")
        self.preview_tree.column("platform", width=80, anchor="center")
        self.preview_tree.column("source_url", width=350, anchor="w")
        
        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.preview_tree.yview)
        self.preview_tree.configure(yscrollcommand=scrollbar.set)
        
        self.preview_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.preview_tree.bind("<Button-1>", self._on_tree_click)
    
    def _parse_text(self):
        self.parsed_data = []
        
        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)
        
        text = self.input_text.get("1.0", tk.END).strip()
        if not text:
            show_warning(self.dialog, "提示", "请先粘贴要解析的文本")
            return
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            parsed = self._parse_line(line)
            if parsed:
                self.parsed_data.append(parsed)
        
        if not self.parsed_data:
            show_warning(self.dialog, "提示", "未能从文本中解析出有效的商品信息")
            return
        
        for data in self.parsed_data:
            self.preview_tree.insert("", tk.END, values=(
                "✓",
                data.get("product_id", ""),
                data.get("dsid", ""),
                data.get("price", ""),
                data.get("platform", ""),
                data.get("source_url", "")
            ), tags=("checked",))
        
        self.status_label.configure(text=f"共解析出 {len(self.parsed_data)} 条记录")
    
    def _parse_line(self, line: str) -> Optional[Dict[str, Any]]:
        result = {
            "product_id": "",
            "dsid": "",
            "price": "",
            "platform": "",
            "source_url": "",
            "selected": True
        }
        
        url_patterns = [
            (r'detail\.1688\.com/offer/(\d+)\.html', "1688"),
            (r'item\.jd\.com/(\d+)\.html', "JD"),
            (r'detail\.taobao\.com/item\.htm\?id=(\d+)', "淘宝"),
            (r'item\.taobao\.com/item\.htm\?id=(\d+)', "淘宝"),
            (r'(\d{12,})', "未知"),
        ]
        
        for pattern, platform in url_patterns:
            match = re.search(pattern, line)
            if match:
                result["product_id"] = match.group(1)
                result["platform"] = platform
                
                if "1688.com" in line or "1688" in platform:
                    result["source_url"] = f"https://detail.1688.com/offer/{match.group(1)}.html"
                elif "jd.com" in line or platform == "JD":
                    result["source_url"] = f"https://item.jd.com/{match.group(1)}.html"
                elif "taobao" in line or platform == "淘宝":
                    result["source_url"] = f"https://detail.taobao.com/item.htm?id={match.group(1)}"
                else:
                    result["source_url"] = line
                break
        
        if not result["product_id"]:
            return None
        
        price_patterns = [
            r'价格[：:]\s*[\￥¥]?\s*(\d+\.?\d*)\s*[Rr][Mm][Bb]',
            r'价格[：:]\s*[\￥¥]?\s*(\d+\.?\d*)',
            r'[\￥¥]\s*(\d+\.?\d*)\s*[Rr][Mm][Bb]',
            r'[\￥¥]\s*(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*[Rr][Mm][Bb]',
            r'(\d+\.?\d{1,2})\s*(?:rmb|元)',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                result["price"] = match.group(1)
                break
        
        dsid_pattern = r'\b(\d{13,})\b'
        dsid_matches = re.findall(dsid_pattern, line)
        
        for dsid in dsid_matches:
            if dsid != result["product_id"]:
                result["dsid"] = dsid
                break
        
        return result
    
    def _on_tree_click(self, event):
        region = self.preview_tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        
        column = self.preview_tree.identify_column(event.x)
        if column != "#1":
            return
        
        item = self.preview_tree.identify_row(event.y)
        if not item:
            return
        
        values = list(self.preview_tree.item(item, "values"))
        current_tag = self.preview_tree.item(item, "tags")
        
        if values[0] == "✓":
            values[0] = ""
            self.preview_tree.item(item, values=values, tags=("unchecked",))
        else:
            values[0] = "✓"
            self.preview_tree.item(item, values=values, tags=("checked",))
        
        idx = self.preview_tree.index(item)
        if idx < len(self.parsed_data):
            self.parsed_data[idx]["selected"] = (values[0] == "✓")
    
    def _select_all(self):
        for item in self.preview_tree.get_children():
            values = list(self.preview_tree.item(item, "values"))
            values[0] = "✓"
            self.preview_tree.item(item, values=values, tags=("checked",))
        
        for data in self.parsed_data:
            data["selected"] = True
    
    def _deselect_all(self):
        for item in self.preview_tree.get_children():
            values = list(self.preview_tree.item(item, "values"))
            values[0] = ""
            self.preview_tree.item(item, values=values, tags=("unchecked",))
        
        for data in self.parsed_data:
            data["selected"] = False
    
    def _on_import(self):
        selected_data = [d for d in self.parsed_data if d.get("selected", False)]
        
        if not selected_data:
            show_warning(self.dialog, "提示", "请至少选择一条记录进行导入")
            return
        
        confirm = ask_yes_no(self.dialog, "确认导入", f"确定要导入 {len(selected_data)} 条记录吗？")
        if not confirm:
            return
        
        self.result = selected_data
        self.dialog.destroy()
    
    def _on_cancel(self):
        self.result = []
        self.dialog.destroy()
    
    def get_result(self) -> List[Dict[str, Any]]:
        return self.result


def show_import_dialog(parent) -> List[Dict[str, Any]]:
    """显示智能导入对话框"""
    dialog = ImportDialog(parent)
    return dialog.get_result()
