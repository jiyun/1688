#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一弹窗提醒组件 (CustomTkinter版本)
确保所有弹窗在视觉风格、交互方式和信息展示格式上保持一致
包含智能导入对话框功能
"""

import os
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


class PathLocatorDialog:
    """路径定位对话框 - 用于跨机器操作时定位输出路径"""
    
    def __init__(self, parent, product_id: str, original_path: str, 
                 suggestions: List[str] = None, matched_path: str = None):
        self.parent = parent
        self.product_id = product_id
        self.original_path = original_path
        self.suggestions = suggestions or []
        self.matched_path = matched_path
        self.result: Optional[str] = None
        
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(f"定位输出路径 - {product_id}")
        
        dialog_height = 520 if self.suggestions else 320
        self.dialog.geometry(f"700x{dialog_height}")
        self.dialog.minsize(600, 300)
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.focus_force()
        self.dialog.lift()
        
        self._create_widgets()
        
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
        self.dialog.wait_window()
    
    def _create_widgets(self):
        button_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=10)
        
        self.status_label = ctk.CTkLabel(button_frame, text="", text_color="gray")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        skip_btn = create_button(button_frame, "跳过", self._on_skip, 'secondary', width=80)
        skip_btn.pack(side=tk.RIGHT, padx=5)
        
        confirm_btn = create_button(button_frame, "确认", self._on_confirm, 'primary', width=80)
        confirm_btn.pack(side=tk.RIGHT, padx=5)
        
        cancel_btn = create_button(button_frame, "取消", self._on_cancel, 'secondary', width=80)
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        info_frame = ctk.CTkFrame(main_frame)
        info_frame.pack(fill=tk.X, pady=(0, 5))
        
        ctk.CTkLabel(
            info_frame, 
            text=f"商品ID: {self.product_id}", 
            font=("", 12, "bold")
        ).pack(anchor=tk.W, padx=10, pady=3)
        
        ctk.CTkLabel(
            info_frame, 
            text=f"原始路径: {self.original_path}", 
            font=("", 10),
            text_color="gray"
        ).pack(anchor=tk.W, padx=10, pady=2)
        
        status_text = "路径不可用，请选择正确的输出路径"
        status_color = "#f44336"
        ctk.CTkLabel(
            info_frame, 
            text=status_text, 
            font=("", 11),
            text_color=status_color
        ).pack(anchor=tk.W, padx=10, pady=3)
        
        manual_frame = ctk.CTkFrame(main_frame)
        manual_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(manual_frame, text="手动选择路径:", font=("", 11, "bold")).pack(anchor=tk.W, padx=10, pady=3)
        
        path_input_frame = ctk.CTkFrame(manual_frame, fg_color="transparent")
        path_input_frame.pack(fill=tk.X, padx=10, pady=3)
        
        self.path_var = tk.StringVar(value=self.matched_path or "")
        self.path_entry = ctk.CTkEntry(path_input_frame, textvariable=self.path_var, width=500)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        browse_btn = create_button(path_input_frame, "浏览...", self._browse_path, 'secondary', width=80)
        browse_btn.pack(side=tk.LEFT)
        
        if self.suggestions:
            suggest_frame = ctk.CTkFrame(main_frame)
            suggest_frame.pack(fill=tk.BOTH, expand=True, pady=5)
            
            ctk.CTkLabel(
                suggest_frame, 
                text=f"智能匹配建议 (找到 {len(self.suggestions)} 个，双击选择):", 
                font=("", 11, "bold")
            ).pack(anchor=tk.W, padx=10, pady=3)
            
            tree_container = ctk.CTkFrame(suggest_frame, fg_color="transparent")
            tree_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=3)
            
            columns = ("path", "status")
            self.suggest_tree = ttk.Treeview(tree_container, columns=columns, show="headings", height=3)
            
            self.suggest_tree.heading("path", text="路径")
            self.suggest_tree.heading("status", text="状态")
            
            self.suggest_tree.column("path", width=450, anchor=tk.W)
            self.suggest_tree.column("status", width=80, anchor="center")
            
            scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.suggest_tree.yview)
            self.suggest_tree.configure(yscrollcommand=scrollbar.set)
            
            self.suggest_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            for path in self.suggestions:
                rel_path = os.path.relpath(path) if os.path.isabs(path) else path
                exists = "可用" if os.path.exists(path) else "不存在"
                self.suggest_tree.insert("", tk.END, values=(rel_path, exists), tags=(path,))
            
            self.suggest_tree.bind("<Double-1>", self._on_suggestion_double_click)
        else:
            no_suggest_frame = ctk.CTkFrame(main_frame)
            no_suggest_frame.pack(fill=tk.X, pady=5)
            
            ctk.CTkLabel(
                no_suggest_frame, 
                text="未找到智能匹配建议，请手动选择路径", 
                font=("", 10),
                text_color="orange"
            ).pack(anchor=tk.W, padx=10, pady=5)
    
    def _browse_path(self):
        from tkinter import filedialog
        selected = filedialog.askdirectory(
            title=f"选择商品 {self.product_id} 的输出路径",
            initialdir=self.path_var.get() or None
        )
        if selected:
            self.path_var.set(selected)
    
    def _on_suggestion_double_click(self, event):
        item = self.suggest_tree.selection()
        if item:
            tags = self.suggest_tree.item(item[0], "tags")
            if tags:
                self.path_var.set(tags[0])
    
    def _on_confirm(self):
        path = self.path_var.get().strip()
        
        if not path:
            self.status_label.configure(text="请输入或选择路径", text_color="#f44336")
            return
        
        if not os.path.exists(path):
            self.status_label.configure(text="路径不存在", text_color="#f44336")
            return
        
        if not os.path.isdir(path):
            self.status_label.configure(text="路径不是目录", text_color="#f44336")
            return
        
        self.result = path
        self.dialog.destroy()
    
    def _on_skip(self):
        self.result = "__SKIP__"
        self.dialog.destroy()
    
    def _on_cancel(self):
        self.result = None
        self.dialog.destroy()
    
    def get_result(self) -> Optional[str]:
        return self.result


def show_path_locator_dialog(parent, product_id: str, original_path: str,
                             suggestions: List[str] = None, 
                             matched_path: str = None) -> Optional[str]:
    """显示路径定位对话框"""
    dialog = PathLocatorDialog(parent, product_id, original_path, suggestions, matched_path)
    return dialog.get_result()


class DSIDLinkDialog:
    """DSID链接解析对话框 - 支持解析1688和京麦平台的编辑链接"""
    
    PLATFORM_1688 = '1688'
    PLATFORM_JD = 'jd'
    
    def __init__(self, parent, product_id: str, current_dsid: str = "", current_remark: str = ""):
        self.parent = parent
        self.product_id = product_id
        self.current_dsid = current_dsid
        self.current_remark = current_remark
        self.result: Optional[Dict[str, Any]] = None
        
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("编辑DSID - 支持链接解析")
        self.dialog.geometry("550x400")
        self.dialog.minsize(500, 350)
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.focus_force()
        self.dialog.lift()
        
        self._create_widgets()
        
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.dialog.wait_window()
    
    def _create_widgets(self):
        button_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=10)
        
        self.status_label = ctk.CTkLabel(button_frame, text="", text_color="gray")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = create_button(button_frame, "取消", self._on_cancel, 'secondary', width=80)
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        confirm_btn = create_button(button_frame, "确认", self._on_confirm, 'primary', width=80)
        confirm_btn.pack(side=tk.RIGHT, padx=5)
        
        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        info_frame = ctk.CTkFrame(main_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        ctk.CTkLabel(
            info_frame, 
            text=f"商品ID: {self.product_id}", 
            font=("", 12, "bold")
        ).pack(anchor=tk.W, padx=10, pady=5)
        
        ctk.CTkLabel(
            info_frame, 
            text="支持输入：纯数字ID、1688编辑链接、京麦编辑链接",
            font=("", 10),
            text_color="gray"
        ).pack(anchor=tk.W, padx=10, pady=2)
        
        input_frame = ctk.CTkFrame(main_frame)
        input_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(input_frame, text="输入内容:", font=("", 11, "bold")).pack(anchor=tk.W, padx=10, pady=3)
        
        self.input_var = tk.StringVar(value=self.current_dsid)
        self.input_entry = ctk.CTkEntry(input_frame, textvariable=self.input_var, width=500)
        self.input_entry.pack(fill=tk.X, padx=10, pady=3)
        self.input_entry.bind('<KeyRelease>', self._on_input_change)
        
        parse_frame = ctk.CTkFrame(main_frame)
        parse_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(parse_frame, text="解析结果:", font=("", 11, "bold")).pack(anchor=tk.W, padx=10, pady=3)
        
        result_frame = ctk.CTkFrame(parse_frame, fg_color="transparent")
        result_frame.pack(fill=tk.X, padx=10, pady=3)
        
        ctk.CTkLabel(result_frame, text="平台:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.platform_label = ctk.CTkLabel(result_frame, text="-", text_color="gray")
        self.platform_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ctk.CTkLabel(result_frame, text="DSID:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.dsid_label = ctk.CTkLabel(result_frame, text="-", text_color="gray")
        self.dsid_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ctk.CTkLabel(result_frame, text="编辑链接:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.edit_url_label = ctk.CTkLabel(result_frame, text="-", text_color="gray", wraplength=400)
        self.edit_url_label.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        remark_frame = ctk.CTkFrame(main_frame)
        remark_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(remark_frame, text="备注 (自动更新):", font=("", 11, "bold")).pack(anchor=tk.W, padx=10, pady=3)
        
        self.remark_var = tk.StringVar(value=self.current_remark)
        self.remark_entry = ctk.CTkEntry(remark_frame, textvariable=self.remark_var, width=500)
        self.remark_entry.pack(fill=tk.X, padx=10, pady=3)
        
        self.parsed_data: Dict[str, Any] = {
            'platform': None,
            'dsid': None,
            'edit_url': None,
            'remark': self.current_remark
        }
        
        if self.current_dsid:
            self._on_input_change(None)
    
    def _parse_input(self, input_text: str) -> Dict[str, Any]:
        """解析输入内容"""
        result = {
            'platform': None,
            'dsid': None,
            'edit_url': None,
            'remark': self.current_remark
        }
        
        input_text = input_text.strip()
        
        if not input_text:
            return result
        
        if input_text.isdigit():
            result['dsid'] = input_text
            result['platform'] = self.PLATFORM_1688
            result['edit_url'] = f"https://item.upload.taobao.com/sell/v2/publish.htm?itemId={input_text}&fromAIPublish=true"
            return result
        
        if 'item.upload.taobao.com' in input_text or 'itemId=' in input_text:
            result['platform'] = self.PLATFORM_1688
            
            item_id_match = re.search(r'itemId=(\d+)', input_text)
            if item_id_match:
                result['dsid'] = item_id_match.group(1)
            
            if 'fromAIPublish' in input_text:
                result['edit_url'] = input_text
            else:
                if result['dsid']:
                    result['edit_url'] = f"https://item.upload.taobao.com/sell/v2/publish.htm?itemId={result['dsid']}&fromAIPublish=true"
            
            return result
        
        if 'wares-jdm.jd.com' in input_text or 'productId=' in input_text:
            result['platform'] = self.PLATFORM_JD
            
            product_id_match = re.search(r'productId=(\d+)', input_text)
            if product_id_match:
                result['dsid'] = product_id_match.group(1)
            
            result['edit_url'] = input_text
            
            return result
        
        if '1688.com' in input_text or 'alibaba.com' in input_text:
            result['platform'] = self.PLATFORM_1688
            offer_match = re.search(r'offer/(\d+)', input_text)
            if offer_match:
                result['dsid'] = offer_match.group(1)
                result['edit_url'] = f"https://item.upload.taobao.com/sell/v2/publish.htm?itemId={result['dsid']}&fromAIPublish=true"
            return result
        
        if 'jd.com' in input_text:
            result['platform'] = self.PLATFORM_JD
            jd_id_match = re.search(r'/(\d+)\.html', input_text)
            if jd_id_match:
                result['dsid'] = jd_id_match.group(1)
            return result
        
        return result
    
    def _on_input_change(self, event):
        """输入内容变化时更新解析结果"""
        input_text = self.input_var.get()
        self.parsed_data = self._parse_input(input_text)
        
        if self.parsed_data['platform']:
            platform_text = "1688平台" if self.parsed_data['platform'] == self.PLATFORM_1688 else "京麦平台"
            self.platform_label.configure(text=platform_text, text_color="#2196F3")
        else:
            self.platform_label.configure(text="-", text_color="gray")
        
        if self.parsed_data['dsid']:
            self.dsid_label.configure(text=self.parsed_data['dsid'], text_color="#4CAF50")
        else:
            self.dsid_label.configure(text="-", text_color="gray")
        
        if self.parsed_data['edit_url']:
            url_display = self.parsed_data['edit_url']
            if len(url_display) > 60:
                url_display = url_display[:60] + "..."
            self.edit_url_label.configure(text=url_display, text_color="#2196F3")
        else:
            self.edit_url_label.configure(text="-", text_color="gray")
        
        if self.parsed_data['platform'] and self.parsed_data['dsid']:
            if self.parsed_data['platform'] == self.PLATFORM_1688:
                new_remark = f"1688编辑链接: itemId={self.parsed_data['dsid']}"
            else:
                new_remark = f"京麦编辑链接: productId={self.parsed_data['dsid']}"
            
            if self.current_remark and self.current_remark not in new_remark:
                new_remark = f"{self.current_remark} | {new_remark}"
            
            self.remark_var.set(new_remark)
    
    def _on_confirm(self):
        """确认按钮"""
        input_text = self.input_var.get().strip()
        
        if not input_text:
            self.status_label.configure(text="请输入DSID或链接", text_color="#f44336")
            return
        
        if not self.parsed_data['dsid']:
            self.status_label.configure(text="无法解析出有效的DSID", text_color="#f44336")
            return
        
        self.result = {
            'dsid': self.parsed_data['dsid'],
            'platform': self.parsed_data['platform'],
            'edit_url': self.parsed_data['edit_url'],
            'remark': self.remark_var.get().strip()
        }
        
        self.dialog.destroy()
    
    def _on_cancel(self):
        """取消按钮"""
        self.result = None
        self.dialog.destroy()
    
    def get_result(self) -> Optional[Dict[str, Any]]:
        """获取结果"""
        return self.result


def show_dsid_link_dialog(parent, product_id: str, current_dsid: str = "", 
                          current_remark: str = "") -> Optional[Dict[str, Any]]:
    """显示DSID链接解析对话框"""
    dialog = DSIDLinkDialog(parent, product_id, current_dsid, current_remark)
    return dialog.get_result()
