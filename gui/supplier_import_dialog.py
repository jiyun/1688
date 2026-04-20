# -*- coding: utf-8 -*-
"""
供应商数据导入对话框
从Excel导入商品数据并添加到在线采集队列
"""

import customtkinter as ctk
from tkinter import ttk, filedialog
from typing import Callable, List, Dict, Any, Optional
import os
import sys

sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

from gui.utils import create_button, get_font


class SupplierImportDialog:
    """供应商Excel导入对话框
    
    功能：
    - 选择Excel文件（支持多选）
    - 预览商品数据（商品ID、标题）
    - 确认后添加到在线采集队列
    """
    
    def __init__(self, parent, on_import_callback: Callable = None,
                 log_callback: Callable = None,
                 font_name: str = 'Microsoft YaHei', font_size: int = 10):
        self.parent = parent
        self.on_import = on_import_callback
        self.log = log_callback or (lambda msg, level='info': print(f"[{level}] {msg}"))
        self.font_name = font_name
        self.font_size = font_size
        
        self.parsed_products: List[Dict[str, Any]] = []
        self.dialog = None
        self.preview_tree = None
        self.status_label = None
        self.file_list_label = None
        
        # 检查pandas
        try:
            import pandas as pd
            self._has_pandas = True
        except ImportError:
            self._has_pandas = False
        
        if not self._has_pandas:
            self._show_error("需要安装pandas库:\npip install pandas openpyxl")
            return
        
        self._create_dialog()
    
    def _create_dialog(self):
        """创建对话框界面"""
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title("供应商数据导入")
        self.dialog.geometry("800x600")
        self.dialog.minsize(700, 500)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # 主框架
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        # 标题
        title_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(
            title_frame,
            text="从供应商Excel导入商品",
            font=get_font(self.font_name, 'lg', 'bold')
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            title_frame,
            text="支持1688采购助手导出的商品列表Excel文件（每文件约30条记录）",
            font=get_font(self.font_name, 'sm'),
            text_color="gray"
        ).pack(anchor="w", pady=(2, 0))
        
        # 文件选择区域
        file_frame = ctk.CTkFrame(main_frame)
        file_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(file_frame, text="选择文件:").pack(side="left", padx=5)
        
        create_button(
            file_frame, "浏览...",
            self._browse_files,
            'primary',
            size='compact',
            width=80
        ).pack(side="left", padx=5)
        
        self.file_list_label = ctk.CTkLabel(
            file_frame,
            text="未选择文件",
            font=get_font(self.font_name, 'sm'),
            text_color="gray"
        )
        self.file_list_label.pack(side="left", padx=10)
        
        # 数据预览区域
        preview_frame = ctk.CTkFrame(main_frame)
        preview_frame.pack(fill="both", expand=True, pady=10)
        
        ctk.CTkLabel(
            preview_frame,
            text="数据预览（商品ID与标题）:",
            font=get_font(self.font_name, 'base')
        ).pack(anchor="w", padx=5, pady=(5, 0))
        
        # Treeview
        tree_frame = ctk.CTkFrame(preview_frame)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        columns = ("product_id", "title", "source_file")
        self.preview_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            height=15
        )
        
        self.preview_tree.heading("product_id", text="商品ID")
        self.preview_tree.heading("title", text="商品标题")
        self.preview_tree.heading("source_file", text="来源文件")
        
        self.preview_tree.column("product_id", width=120, anchor="center")
        self.preview_tree.column("title", width=400, anchor="w")
        self.preview_tree.column("source_file", width=150, anchor="w")
        
        scrollbar = ttk.Scrollbar(
            tree_frame,
            orient="vertical",
            command=self.preview_tree.yview
        )
        self.preview_tree.configure(yscrollcommand=scrollbar.set)
        
        self.preview_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 状态标签
        self.status_label = ctk.CTkLabel(
            main_frame,
            text="请选择Excel文件",
            font=get_font(self.font_name, 'base')
        )
        self.status_label.pack(anchor="w", padx=5, pady=5)
        
        # 按钮区域
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)
        
        self.import_btn = create_button(
            btn_frame, "确认导入到队列",
            self._do_import,
            'success',
            size='compact',
            width=120
        )
        self.import_btn.pack(side="left", padx=10)
        self.import_btn.configure(state="disabled")
        
        create_button(
            btn_frame, "取消",
            self._on_cancel,
            'secondary',
            size='compact',
            width=80
        ).pack(side="left", padx=5)
    
    def _browse_files(self):
        """浏览并选择Excel文件"""
        files = filedialog.askopenfilenames(
            title="选择供应商Excel文件",
            filetypes=[
                ("Excel文件", "*.xlsx *.xls"),
                ("所有文件", "*.*")
            ]
        )
        
        if not files:
            return
        
        self._parse_files(files)
    
    def _parse_files(self, file_paths: tuple):
        """解析Excel文件"""
        from utils.excel_importer import parse_excel_file
        
        self.parsed_products = []
        file_count = len(file_paths)
        
        for filepath in file_paths:
            try:
                products, errors, shop_data = parse_excel_file(filepath)
                
                # 添加来源文件信息
                filename = os.path.basename(filepath)
                for p in products:
                    p['_source_file'] = filename
                
                self.parsed_products.extend(products)
                
                if errors:
                    self.log(f"文件 {filename} 解析警告: {', '.join(errors[:3])}", "warning")
                    
            except Exception as e:
                self.log(f"解析文件失败 {filepath}: {e}", "error")
        
        # 更新界面
        self._update_preview()
        
        # 更新文件标签
        if file_count == 1:
            self.file_list_label.configure(text=f"已选择: {os.path.basename(file_paths[0])}")
        else:
            self.file_list_label.configure(text=f"已选择 {file_count} 个文件")
    
    def _update_preview(self):
        """更新预览列表"""
        # 清空现有数据
        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)
        
        if not self.parsed_products:
            self.status_label.configure(text="未找到有效的商品数据")
            self.import_btn.configure(state="disabled")
            return
        
        # 添加数据到表格
        for product in self.parsed_products:
            self.preview_tree.insert(
                "",
                "end",
                values=(
                    product.get('product_id', ''),
                    product.get('title', '')[:50] + '...' if len(product.get('title', '')) > 50 else product.get('title', ''),
                    product.get('_source_file', '')
                )
            )
        
        # 更新状态
        self.status_label.configure(
            text=f"共找到 {len(self.parsed_products)} 个商品，确认后导入到在线采集队列",
            text_color="green"
        )
        self.import_btn.configure(state="normal")
    
    def _do_import(self):
        """执行导入"""
        if not self.parsed_products:
            return
        
        # 调用回调函数
        if self.on_import:
            self.on_import(self.parsed_products)
        
        self.log(f"供应商数据导入: {len(self.parsed_products)} 个商品已添加到队列")
        self.dialog.destroy()
    
    def _on_cancel(self):
        """取消导入"""
        self.dialog.destroy()
    
    def _show_error(self, message: str):
        """显示错误信息"""
        error_dialog = ctk.CTkToplevel(self.parent)
        error_dialog.title("错误")
        error_dialog.geometry("400x200")
        error_dialog.transient(self.parent)
        
        ctk.CTkLabel(
            error_dialog,
            text=message,
            font=get_font(self.font_name, 'base'),
            wraplength=350
        ).pack(expand=True, padx=20, pady=20)
        
        create_button(
            error_dialog, "确定",
            error_dialog.destroy,
            'primary',
            size='compact',
            width=80
        ).pack(pady=10)


def show_supplier_import_dialog(parent, on_import_callback: Callable = None,
                                log_callback: Callable = None,
                                font_name: str = 'Microsoft YaHei',
                                font_size: int = 10):
    """显示供应商导入对话框
    
    Args:
        parent: 父窗口
        on_import_callback: 导入回调函数，接收商品列表参数
        log_callback: 日志回调函数
        font_name: 字体名称
        font_size: 字体大小
    """
    dialog = SupplierImportDialog(
        parent,
        on_import_callback=on_import_callback,
        log_callback=log_callback,
        font_name=font_name,
        font_size=font_size
    )
    return dialog


if __name__ == '__main__':
    # 测试代码
    ctk.set_appearance_mode("light")
    root = ctk.CTk()
    root.geometry("900x700")
    
    def test_import(products):
        print(f"导入 {len(products)} 个商品:")
        for p in products[:5]:
            print(f"  - {p.get('product_id')}: {p.get('title', '')[:30]}")
    
    btn = create_button(
        root, "测试导入",
        lambda: show_supplier_import_dialog(root, test_import),
        'primary'
    )
    btn.pack(pady=50)
    
    root.mainloop()
