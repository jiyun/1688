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


class ExcelImportDialog:
    """Excel导入对话框 - 导入1688采购助手导出的商品数据"""
    
    def __init__(self, parent, log_callback: Callable = None, 
                 info_callback: Callable = None, confirm_callback: Callable = None,
                 refresh_callback: Callable = None,
                 font_name: str = 'Microsoft YaHei', font_size: int = 10):
        self.parent = parent
        self.log = log_callback or (lambda msg, level: print(f"[{level}] {msg}"))
        self.show_info = info_callback or (lambda title, msg: print(f"{title}: {msg}"))
        self.ask_yes_no = confirm_callback or (lambda title, msg: True)
        self.refresh = refresh_callback
        self.font_name = font_name
        self.font_size = font_size
        self.font_size_large = font_size + 4
        self.font_size_small = max(font_size - 2, 8)
        self.result = False
        
        try:
            from utils.excel_importer import parse_excel_file, get_excel_preview, import_to_database, HAS_PANDAS
            self._parse_excel_file = parse_excel_file
            self._import_to_database = import_to_database
            self._has_pandas = HAS_PANDAS
        except ImportError:
            self._has_pandas = False
        
        if not self._has_pandas:
            self.show_info("错误", "需要安装pandas库:\npip install pandas openpyxl")
            return
        
        self._parsed_products = []
        self._shop_data = {}
        
        self._create_dialog()
    
    def _create_dialog(self):
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title("导入Excel数据")
        self.dialog.geometry("1000x750")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        title_frame = ctk.CTkFrame(main_frame)
        title_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(
            title_frame, 
            text="导入1688采购助手导出的全店商品Excel文件",
            font=(self.font_name, self.font_size_large, "bold")
        ).pack(anchor="w", padx=8)
        
        ctk.CTkLabel(
            title_frame, 
            text="支持格式：1688采购助手导出的xlsx文件，包含商品标题、宝贝ID、价格、销量等信息",
            font=(self.font_name, self.font_size),
            text_color="gray"
        ).pack(anchor="w", padx=20)
        
        file_frame = ctk.CTkFrame(main_frame)
        file_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(file_frame, text="选择文件:").pack(side="left", padx=5)
        
        self._file_path_var = ctk.StringVar()
        file_entry = ctk.CTkEntry(file_frame, textvariable=self._file_path_var, width=500)
        file_entry.pack(side="left", padx=5)
        
        create_button(file_frame, "浏览...", self._browse_file, 'primary', width=80).pack(side="left", padx=5)
        
        preview_frame = ctk.CTkFrame(main_frame)
        preview_frame.pack(fill="both", expand=True, pady=10)
        
        ctk.CTkLabel(preview_frame, text="数据预览:", font=(self.font_name, self.font_size)).pack(anchor="w", padx=5)
        
        preview_columns = ("product_id", "title", "price", "dropship_price", "sales_count", "review_count", "monthly_orders", "monthly_dropship", "ship_time", "list_time", "category", "tags")
        self._preview_tree = ttk.Treeview(preview_frame, columns=preview_columns, show="headings", height=12)
        
        col_config = {
            "product_id": ("商品ID", 90, "center"),
            "title": ("商品标题", 180, "w"),
            "price": ("价格", 60, "center"),
            "dropship_price": ("代发价", 60, "center"),
            "sales_count": ("销量", 50, "center"),
            "review_count": ("评论数", 50, "center"),
            "monthly_orders": ("月成交", 55, "center"),
            "monthly_dropship": ("月代销", 55, "center"),
            "ship_time": ("发货时间", 60, "center"),
            "list_time": ("上架时间", 70, "center"),
            "category": ("类目", 70, "w"),
            "tags": ("标签", 60, "w"),
        }
        for col, (text, width, anchor) in col_config.items():
            self._preview_tree.heading(col, text=text)
            self._preview_tree.column(col, width=width, anchor=anchor)
        
        preview_scrollbar = ttk.Scrollbar(preview_frame, orient="vertical", command=self._preview_tree.yview)
        self._preview_tree.configure(yscrollcommand=preview_scrollbar.set)
        self._preview_tree.pack(side="left", fill="both", expand=True, padx=5)
        preview_scrollbar.pack(side="right", fill="y")
        
        self._status_label = ctk.CTkLabel(main_frame, text="请选择Excel文件")
        self._status_label.pack(anchor="w", padx=5, pady=5)
        
        option_frame = ctk.CTkFrame(main_frame)
        option_frame.pack(fill="x", pady=5)
        
        self._support_dropship_var = ctk.IntVar(value=0)
        ctk.CTkCheckBox(
            option_frame, 
            text="标记为支持一件代发", 
            variable=self._support_dropship_var,
            onvalue=1, 
            offvalue=0
        ).pack(side="left", padx=10)
        
        ctk.CTkLabel(
            option_frame, 
            text="(如果是从'支持一件代发'筛选后导出的数据，请勾选此项)", 
            text_color="gray",
            font=(self.font_name, self.font_size_small)
        ).pack(side="left", padx=5)
        
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x", pady=10)
        
        create_button(btn_frame, "导入数据", self._do_import, 'success', width=100).pack(side="left", padx=10)
        create_button(btn_frame, "取消", self._on_cancel, 'secondary', width=80).pack(side="left", padx=5)
    
    def _browse_file(self):
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="选择Excel文件",
            filetypes=[("Excel文件", "*.xlsx *.xls"), ("所有文件", "*.*")]
        )
        if file_path:
            self._file_path_var.set(file_path)
            self._preview_excel(file_path)
    
    def _preview_excel(self, file_path: str):
        for item in self._preview_tree.get_children():
            self._preview_tree.delete(item)
        
        self._parsed_products, errors, self._shop_data = self._parse_excel_file(file_path)
        
        if errors:
            self._status_label.configure(text=f"解析错误: {'; '.join(errors)}", text_color="red")
            return
        
        preview_limit = min(500, len(self._parsed_products))
        for product in self._parsed_products[:preview_limit]:
            title = product.get('title', '')
            if len(title) > 20:
                title = title[:20] + '...'
            self._preview_tree.insert("", "end", values=(
                product.get('product_id', ''),
                title,
                f"¥{product.get('price', 0):.2f}" if product.get('price') else '-',
                f"¥{product.get('dropship_price', 0):.2f}" if product.get('dropship_price') else '-',
                product.get('sales_count', 0),
                product.get('review_count', 0),
                product.get('monthly_orders', 0),
                product.get('monthly_dropship', 0),
                product.get('ship_time', '')[:8],
                product.get('list_time', '')[:10] if product.get('list_time') else product.get('listing_date', '')[:10],
                product.get('category', '')[:10],
                product.get('tags', '')[:8]
            ))
        
        shop_info = ""
        if self._shop_data.get('shop_name'):
            shop_info = f" | 店铺: {self._shop_data.get('shop_name')}"
        
        if len(self._parsed_products) > preview_limit:
            self._status_label.configure(
                text=f"解析完成: 共 {len(self._parsed_products)} 条商品数据 (预览前{preview_limit}条){shop_info}", 
                text_color="green"
            )
        else:
            self._status_label.configure(
                text=f"解析完成: 共 {len(self._parsed_products)} 条商品数据{shop_info}", 
                text_color="green"
            )
    
    def _do_import(self):
        if not self._parsed_products:
            self.show_info("提示", "请先选择并预览Excel文件")
            return
        
        support_dropship = self._support_dropship_var.get()
        dropship_text = "并标记为支持一件代发" if support_dropship else ""
        confirm = self.ask_yes_no("确认导入", f"确定要导入 {len(self._parsed_products)} 条商品数据{dropship_text}吗？")
        if not confirm:
            return
        
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            
            shop_name = self._shop_data.get('shop_name')
            imported, errors = self._import_to_database(
                self._parsed_products, 
                db, 
                shop_name=shop_name, 
                support_dropship=support_dropship if support_dropship else None,
                shop_data=self._shop_data
            )
            db.close()
            
            if errors:
                self.log(f"导入完成，但有 {len(errors)} 个错误", "warning")
                for err in errors[:5]:
                    self.log(f"  {err}", "warning")
            
            self.log(f"成功导入 {imported} 条商品数据", "success")
            self.result = True
            if self.refresh:
                self.refresh()
            self.dialog.destroy()
            
        except Exception as e:
            self.log(f"导入失败: {e}", "error")
            self.show_info("错误", f"导入失败: {e}")
    
    def _on_cancel(self):
        self.result = False
        self.dialog.destroy()
    
    def get_result(self) -> bool:
        return self.result


def show_excel_import_dialog(parent, log_callback: Callable = None,
                              info_callback: Callable = None, 
                              confirm_callback: Callable = None,
                              refresh_callback: Callable = None,
                              font_name: str = 'Microsoft YaHei',
                              font_size: int = 10) -> bool:
    """显示Excel导入对话框"""
    dialog = ExcelImportDialog(
        parent, 
        log_callback=log_callback,
        info_callback=info_callback,
        confirm_callback=confirm_callback,
        refresh_callback=refresh_callback,
        font_name=font_name,
        font_size=font_size
    )
    return dialog.get_result()


import math


class AnalysisDialog:
    """商品分析对话框 - 雷达图展示"""
    
    def __init__(self, parent, products: List[Dict], font_name: str = 'Microsoft YaHei'):
        self.parent = parent
        self.products = products
        self.font_name = font_name
        
        self._max_sales = max((p.get('monthly_sales', 0) or 0) for p in products) or 1
        self._max_reviews = max((p.get('review_count', 0) or 0) for p in products) or 1
        self._max_price = max((p.get('price', 0) or 0) for p in products) or 1
        self._max_dropship = max((p.get('dropship_price', 0) or 0) for p in products if p.get('dropship_price')) or 1
        
        self._create_dialog()
    
    def _create_dialog(self):
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title("商品分析 - 战力图")
        self.dialog.geometry("900x700")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        top_frame = ctk.CTkFrame(main_frame)
        top_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(top_frame, text="商品分析", font=(self.font_name, 16, "bold")).pack(side="left", padx=10)
        
        canvas_frame = ctk.CTkFrame(main_frame)
        canvas_frame.pack(fill="both", expand=True, pady=10)
        
        self._canvas = tk.Canvas(canvas_frame, bg='white', highlightthickness=0)
        self._canvas.pack(fill="both", expand=True)
        
        self._canvas.bind('<Configure>', lambda e: self._draw_radar_chart())
        
        list_frame = ctk.CTkFrame(main_frame)
        list_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(list_frame, text="Top 10 商品:", font=(self.font_name, 12, "bold")).pack(anchor="w", padx=5)
        
        for i, p in enumerate(self.products[:10], 1):
            title = p.get('title', '')
            if len(title) > 25:
                title = title[:25] + '...'
            text = f"{i}. [{p.get('product_id')}] {title} - 销量:{p.get('monthly_sales', 0)} 评论:{p.get('review_count', 0)}"
            ctk.CTkLabel(list_frame, text=text, font=(self.font_name, 10)).pack(anchor="w", padx=20)
    
    def _draw_radar_chart(self):
        canvas = self._canvas
        canvas.update()
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        
        if width < 100 or height < 100:
            return
        
        canvas.delete("all")
        
        cx, cy = width // 2, height // 2
        radius = min(width, height) // 2 - 50
        
        dimensions = ['销量', '评论', '价格', '代发价', '采集']
        num_dims = len(dimensions)
        angle_step = 2 * math.pi / num_dims
        
        for i in range(5, 0, -1):
            r = radius * i / 5
            points = []
            for j in range(num_dims):
                angle = angle_step * j - math.pi / 2
                x = cx + r * math.cos(angle)
                y = cy + r * math.sin(angle)
                points.extend([x, y])
            canvas.create_polygon(points, outline='#ddd', fill='', width=1)
        
        for i, dim in enumerate(dimensions):
            angle = angle_step * i - math.pi / 2
            x = cx + (radius + 20) * math.cos(angle)
            y = cy + (radius + 20) * math.sin(angle)
            canvas.create_text(x, y, text=dim, font=(self.font_name, 10))
        
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F']
        
        for idx, product in enumerate(self.products[:20]):
            sales = (product.get('monthly_sales', 0) or 0) / self._max_sales
            reviews = (product.get('review_count', 0) or 0) / self._max_reviews
            price = (product.get('price', 0) or 0) / self._max_price
            dropship = (product.get('dropship_price', 0) or 0) / self._max_dropship if product.get('dropship_price') else 0
            collected = 1 if (product.get('resource_count', 0) or 0) > 0 else 0
            
            values = [sales, reviews, price, dropship, collected]
            points = []
            
            for i, val in enumerate(values):
                angle = angle_step * i - math.pi / 2
                r = radius * min(val, 1)
                x = cx + r * math.cos(angle)
                y = cy + r * math.sin(angle)
                points.extend([x, y])
            
            color = colors[idx % len(colors)]
            canvas.create_polygon(points, outline=color, fill='', width=2)


def show_analysis_dialog(parent, products: List[Dict], font_name: str = 'Microsoft YaHei'):
    """显示商品分析对话框"""
    AnalysisDialog(parent, products, font_name)


import re as _re
from datetime import datetime as _datetime


def parse_import_line(line: str) -> dict:
    """解析单行导入数据
    
    格式：URL [中间内容] DSID
    - URL开头
    - DSID在结尾（主要目的）
    - 中间内容可选，可能包含价格
    """
    result = {
        'valid': False,
        'product_id': None,
        'target_price': None,
        'dsid': None,
        'error': None
    }
    
    try:
        line = line.strip()
        if not line:
            result['error'] = '空行'
            return result
        
        url_match = _re.match(r'(https?://[^\s]+)', line)
        if not url_match:
            result['error'] = '行首未找到URL'
            return result
        
        url = url_match.group(1)
        
        id_match = _re.search(r'offer/(\d+)\.html', url)
        if not id_match:
            id_match = _re.search(r'/(\d{10,})', url)
        
        if not id_match:
            result['error'] = 'URL中未找到商品ID'
            return result
        
        result['product_id'] = id_match.group(1)
        
        remaining = line[len(url):].strip()
        
        if remaining:
            parts = remaining.split()
            
            if len(parts) >= 1:
                last_part = parts[-1]
                if last_part.isdigit():
                    result['dsid'] = last_part
                
                if len(parts) >= 2:
                    middle_parts = parts[:-1]
                    middle_text = ' '.join(middle_parts)
                    
                    price_match = _re.search(r'【[^】]*?(\d+\.?\d*)[^】]*?】', middle_text)
                    if price_match:
                        try:
                            result['target_price'] = float(price_match.group(1))
                        except ValueError:
                            pass
                    else:
                        price_patterns = [
                            r'价格\s*(\d+\.?\d*)',
                            r'售价\s*(\d+\.?\d*)',
                            r'[¥￥]\s*(\d+\.?\d*)',
                            r'(\d+\.?\d*)\s*元',
                        ]
                        
                        for pattern in price_patterns:
                            match = _re.search(pattern, middle_text)
                            if match:
                                try:
                                    result['target_price'] = float(match.group(1))
                                    break
                                except ValueError:
                                    pass
                        
                        if result['target_price'] is None:
                            numbers = _re.findall(r'(?<![a-zA-Z0-9.])(\d+\.?\d*)(?![a-zA-Z0-9.])', middle_text)
                            for num_str in numbers:
                                try:
                                    num = float(num_str)
                                    if 1 <= num <= 10000:
                                        result['target_price'] = num
                                        break
                                except ValueError:
                                    pass
        
        result['valid'] = True
        
    except Exception as e:
        result['error'] = str(e)
    
    return result


class ImportDialog:
    """导入数据对话框 - 从文本解析并导入商品数据"""
    
    def __init__(self, parent, parse_line_fn, info_callback: Callable = None,
                 confirm_callback: Callable = None, refresh_callback: Callable = None,
                 font_name: str = 'Microsoft YaHei', font_size: int = 10):
        self.parent = parent
        self.parse_line_fn = parse_line_fn
        self.show_info = info_callback or (lambda title, msg: print(f"{title}: {msg}"))
        self.ask_yes_no = confirm_callback or (lambda title, msg: True)
        self.refresh = refresh_callback
        self.font_name = font_name
        self.font_size = font_size
        self.font_size_large = font_size + 4
        self.font_size_small = max(font_size - 2, 8)
        self.parsed_data = []
        
        self._create_dialog()
    
    def _create_dialog(self):
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title("导入数据")
        self.dialog.geometry("950x850")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        format_frame = ctk.CTkFrame(main_frame)
        format_frame.pack(fill="x", pady=8)
        
        ctk.CTkLabel(
            format_frame,
            text="导入格式说明",
            font=(self.font_name, self.font_size_large, "bold")
        ).pack(anchor="w", padx=8)
        
        ctk.CTkLabel(
            format_frame,
            text="• 格式：URL [中间内容] DSID（空格分隔）\n• URL：商品链接，从中解析商品ID\n• 中间内容：可选，包含价格数字的文本\n• DSID：店铺商品ID（主要目的）",
            font=(self.font_name, self.font_size),
            justify="left"
        ).pack(anchor="w", padx=20)
        
        ctk.CTkLabel(
            format_frame,
            text="示例：\n  https://detail.1688.com/offer/123456789.html ABC123\n  https://detail.1688.com/offer/123456789.html 【¥25.00】 ABC123",
            font=(self.font_name, self.font_size),
            text_color="gray"
        ).pack(anchor="w", padx=20, pady=5)
        
        input_frame = ctk.CTkFrame(main_frame)
        input_frame.pack(fill="both", expand=True, pady=8)
        
        ctk.CTkLabel(input_frame, text="请粘贴数据（每行一条）：", font=(self.font_name, self.font_size)).pack(anchor="w", padx=8)
        
        self._text_input = ctk.CTkTextbox(input_frame, height=200, font=(self.font_name, self.font_size))
        self._text_input.pack(fill="both", expand=True, padx=8, pady=8)
        
        preview_frame = ctk.CTkFrame(main_frame)
        preview_frame.pack(fill="both", expand=True, pady=8)
        
        ctk.CTkLabel(preview_frame, text="解析预览：", font=(self.font_name, self.font_size)).pack(anchor="w", padx=8)
        
        preview_columns = ("行号", "商品ID", "目标售价", "DSID", "状态")
        self._preview_tree = ttk.Treeview(preview_frame, columns=preview_columns, show="headings", height=8)
        
        self._preview_tree.heading("行号", text="行号")
        self._preview_tree.heading("商品ID", text="商品ID")
        self._preview_tree.heading("目标售价", text="目标售价")
        self._preview_tree.heading("DSID", text="DSID")
        self._preview_tree.heading("状态", text="状态")
        
        self._preview_tree.column("行号", width=50, anchor="center")
        self._preview_tree.column("商品ID", width=120, anchor="center")
        self._preview_tree.column("目标售价", width=100, anchor="center")
        self._preview_tree.column("DSID", width=120, anchor="center")
        self._preview_tree.column("状态", width=100, anchor="center")
        
        preview_scrollbar = ttk.Scrollbar(preview_frame, orient="vertical", command=self._preview_tree.yview)
        self._preview_tree.configure(yscrollcommand=preview_scrollbar.set)
        self._preview_tree.pack(side="left", fill="both", expand=True, padx=5)
        preview_scrollbar.pack(side="right", fill="y")
        
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x", pady=10)
        
        self._count_label = ctk.CTkLabel(btn_frame, text="共 0 行", font=(self.font_name, self.font_size_small))
        self._count_label.pack(side="left", padx=10)
        
        ctk.CTkButton(btn_frame, text="解析预览", command=self._parse_input).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="确认导入", command=self._confirm_import).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="取消", command=self.dialog.destroy).pack(side="right", padx=5)
    
    def _parse_input(self):
        self.parsed_data = []
        
        for item in self._preview_tree.get_children():
            self._preview_tree.delete(item)
        
        text = self._text_input.get("1.0", "end-1c")
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        for idx, line in enumerate(lines, 1):
            result = self.parse_line_fn(line)
            self.parsed_data.append(result)
            
            status = "✓ 有效" if result['valid'] else f"✗ {result['error']}"
            
            self._preview_tree.insert("", "end", values=(
                idx,
                result.get('product_id', '-'),
                result.get('target_price', '-'),
                result.get('dsid', '-'),
                status
            ))
        
        valid_count = sum(1 for d in self.parsed_data if d['valid'])
        self._count_label.configure(text=f"共 {len(lines)} 行，有效 {valid_count} 行")
    
    def _confirm_import(self):
        valid_data = [d for d in self.parsed_data if d['valid']]
        
        if not valid_data:
            self.show_info("提示", "没有有效数据可导入")
            return
        
        confirm = self.ask_yes_no("确认导入", f"将导入 {len(valid_data)} 条记录，是否继续？")
        if not confirm:
            return
        
        success_count = 0
        fail_count = 0
        errors = []
        
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            
            for data in valid_data:
                try:
                    product_id = data['product_id']
                    target_price = data.get('target_price')
                    dsid = data.get('dsid')
                    
                    existing = db.get_product(product_id)
                    
                    if existing:
                        update_data = {'updated_at': _datetime.now()}
                        if target_price is not None:
                            update_data['target_price'] = target_price
                        if dsid:
                            update_data['shop_product_id'] = dsid
                        
                        db.update('products', update_data, 'product_id = ?', [product_id])
                    else:
                        insert_data = {
                            'product_id': product_id,
                            'status': 'pending',
                            'created_at': _datetime.now()
                        }
                        if target_price is not None:
                            insert_data['target_price'] = target_price
                        if dsid:
                            insert_data['shop_product_id'] = dsid
                        
                        db.insert('products', insert_data)
                    
                    success_count += 1
                except Exception as e:
                    fail_count += 1
                    errors.append(f"商品ID {data.get('product_id', '?')}: {str(e)}")
            
            db.close()
        except Exception as e:
            self.show_info("错误", f"数据库操作失败: {e}")
            return
        
        report = f"导入完成！\n\n成功: {success_count} 条\n失败: {fail_count} 条"
        if errors:
            report += f"\n\n失败原因:\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                report += f"\n... 还有 {len(errors) - 10} 条错误"
        
        self.show_info("导入报告", report)
        if self.refresh:
            self.refresh()
        self.dialog.destroy()


def show_import_dialog(parent, parse_line_fn=None, info_callback: Callable = None,
                       confirm_callback: Callable = None, refresh_callback: Callable = None,
                       font_name: str = 'Microsoft YaHei', font_size: int = 10):
    """显示导入数据对话框"""
    if parse_line_fn is None:
        parse_line_fn = parse_import_line
    ImportDialog(parent, parse_line_fn, info_callback, confirm_callback,
                 refresh_callback, font_name, font_size)


class DSStatusDialog:
    """DS关联状态对话框 - 显示商品的代发店铺关联信息"""
    
    STATUS_MAP = {'pending': '待处理', 'listed': '已上架', 'delisted': '已下架'}
    
    def __init__(self, parent, product_id: str, status: Dict,
                 font_name: str = 'Microsoft YaHei'):
        self.parent = parent
        self.product_id = product_id
        self.status = status
        self.font_name = font_name
        
        self._create_dialog()
    
    def _create_dialog(self):
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title(f"DS关联状态 - {self.product_id}")
        self.dialog.geometry("700x400")
        self.dialog.transient(self.parent)
        
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        info_frame = ctk.CTkFrame(main_frame)
        info_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(info_frame, text=f"商品ID: {self.product_id}",
                     font=(self.font_name, 12, "bold")).pack(side="left", padx=10)
        ctk.CTkLabel(info_frame,
                     text=f"关联店铺: {self.status['total_shops']} | 已上架: {self.status['listed_count']} | 待处理: {self.status['pending_count']}"
                     ).pack(side="left", padx=10)
        
        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=5)
        
        columns = ("ds_shop_name", "ds_platform", "ds_product_id", "listing_status", "price_adjust", "remark")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        
        tree.heading("ds_shop_name", text="店铺名称")
        tree.heading("ds_platform", text="平台")
        tree.heading("ds_product_id", text="DS商品ID")
        tree.heading("listing_status", text="状态")
        tree.heading("price_adjust", text="价格调整")
        tree.heading("remark", text="备注")
        
        tree.column("ds_shop_name", width=120, anchor="w")
        tree.column("ds_platform", width=60, anchor="center")
        tree.column("ds_product_id", width=120, anchor="center")
        tree.column("listing_status", width=80, anchor="center")
        tree.column("price_adjust", width=80, anchor="center")
        tree.column("remark", width=150, anchor="w")
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        for shop in self.status['shops']:
            tree.insert("", "end", values=(
                shop.get('ds_shop_name', ''),
                shop.get('ds_platform', ''),
                shop.get('ds_product_id', '-'),
                self.STATUS_MAP.get(shop.get('listing_status'), shop.get('listing_status', '')),
                shop.get('price_adjust', 0),
                shop.get('remark', '')
            ))
        
        create_button(main_frame, "关闭", self.dialog.destroy, 'secondary', width=60).pack(pady=10)


def show_ds_status_dialog(parent, product_id: str, status: Dict,
                          font_name: str = 'Microsoft YaHei'):
    """显示DS关联状态对话框"""
    DSStatusDialog(parent, product_id, status, font_name)
