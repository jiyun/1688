#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
价格模型转换工具
将颜色×规格的价格矩阵转换为"本体+附件"结构
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from typing import List, Dict, Any
from gui.dialog import show_info, show_warning, show_error
from gui.utils import create_button


class PriceModelTransformer:
    """价格模型转换工具"""
    
    def __init__(self, parent, product_id=None):
        self.parent = parent
        self.product_id = product_id
        self.price_matrix = {}
        self.colors = []
        self.sizes = []
        self.transformed_bases = []
        self.transformed_attachments = []
        self.transformed_shipping = 0.0
        
        self._create_widgets()
    
    def _create_widgets(self):
        # 说明
        info_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        info_frame.pack(fill=tk.X, pady=5)
        ctk.CTkLabel(info_frame, text="价格模型转换工具", font=("Arial", 14, "bold")).pack(anchor=tk.W)
        ctk.CTkLabel(info_frame, text="将颜色×规格的价格矩阵转换为\"本体+附件\"结构", text_color="gray").pack(anchor=tk.W)
        
        # 加载数据按钮
        load_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        load_frame.pack(fill=tk.X, pady=10)
        
        load_btn = create_button(load_frame, "从数据库加载SKU价格", self._load_sku_prices, 'primary')
        load_btn.pack(side=tk.LEFT, padx=5)
        
        # 价格矩阵显示区域
        matrix_frame = ctk.CTkFrame(self.parent)
        matrix_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        ctk.CTkLabel(matrix_frame, text="价格矩阵:", font=("Arial", 12, "bold")).pack(anchor=tk.W, padx=5, pady=5)
        
        self.matrix_text = ctk.CTkTextbox(matrix_frame, height=150)
        self.matrix_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 匉钮区域
        btn_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        btn_frame.pack(fill=tk.X, pady=10)
        
        transform_btn = create_button(btn_frame, "转换", self._transform_model, 'success')
        transform_btn.pack(side=tk.LEFT, padx=5)
        
        apply_btn = create_button(btn_frame, "应用到成本配置", self._apply_model, 'primary')
        apply_btn.pack(side=tk.LEFT, padx=5)
        
        # 转换结果显示
        result_frame = ctk.CTkFrame(self.parent)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        ctk.CTkLabel(result_frame, text="转换结果:", font=("Arial", 12, "bold")).pack(anchor=tk.W, padx=5, pady=5)
        
        self.result_text = ctk.CTkTextbox(result_frame, height=150)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def _load_sku_prices(self):
        """从数据库加载SKU价格数据"""
        if not self.product_id:
            show_warning(self.parent, "警告", "请先选择商品")
            return
        
        try:
            from utils.database import Database
            db = Database()
            sku_prices = db.get_sku_prices(self.product_id)
            db.close()
            
            if not sku_prices:
                show_warning(self.parent, "警告", "该商品没有SKU价格数据")
                return
            
            # 解析SKU名称，提取颜色和规格
            self.colors = []
            self.sizes = []
            self.price_matrix = {}
            
            for sku in sku_prices:
                sku_name = sku['sku_name']
                price = sku['price']
                
                # 尝试解析 "颜色 规格" 格式
                parts = sku_name.split()
                if len(parts) >= 2:
                    color = parts[0]
                    size = parts[1]
                    
                    if color not in self.colors:
                        self.colors.append(color)
                    if size not in self.sizes:
                        self.sizes.append(size)
                    
                    if color not in self.price_matrix:
                        self.price_matrix[color] = {}
                    self.price_matrix[color][size] = price
            
            # 显示价格矩阵
            self._display_matrix()
            
        except Exception as e:
            show_error(self.parent, "错误", f"加载SKU价格失败: {e}")
    
    def _display_matrix(self):
        """显示价格矩阵"""
        self.matrix_text.delete("1.0", tk.END)
        
        # 表头
        header = "        " + "  ".join(f"{c:>10}" for c in self.colors) + "\n"
        self.matrix_text.insert(tk.END, header)
        
        # 数据行
        for size in self.sizes:
            row = f"{size:>10}" + "  ".join(f"{self.price_matrix.get(c, {}).get(size, 0):>10.2f}" for c in self.colors) + "\n"
            self.matrix_text.insert(tk.END, row)
    
    def _transform_model(self):
        """转换价格模型"""
        if not self.price_matrix:
            show_warning(self.parent, "警告", "请先加载SKU价格数据")
            return
        
        try:
            # 找到最低价格作为基准
            min_price = float('inf')
            for color in self.colors:
                for size in self.sizes:
                    price = self.price_matrix.get(color, {}).get(size, 0)
                    if price > 0 and price < min_price:
                        min_price = price
            
            # 转换为本体+附件结构
            self.transformed_bases = []
            self.transformed_attachments = []
            
            # 本体：每个颜色的基准价格（第一个规格的价格）
            base_size = self.sizes[0] if self.sizes else None
            for color in self.colors:
                base_cost = self.price_matrix.get(color, {}).get(base_size, min_price)
                self.transformed_bases.append({
                    "name": color,
                    "cost": base_cost
                })
            
            # 附件：每个规格相对于基准价格的差价
            for i, size in enumerate(self.sizes):
                if i == 0:
                    # 第一个规格是基准，附件成本为0
                    self.transformed_attachments.append({
                        "name": size,
                        "cost": 0.0
                    })
                else:
                    # 其他规格的差价
                    base_color = self.colors[0] if self.colors else None
                    base_price = self.price_matrix.get(base_color, {}).get(base_size, min_price)
                    size_price = self.price_matrix.get(base_color, {}).get(size, base_price)
                    diff = size_price - base_price
                    self.transformed_attachments.append({
                        "name": size,
                        "cost": diff
                    })
            
            # 显示转换结果
            self._display_result()
            
        except Exception as e:
            show_error(self.parent, "错误", f"转换失败: {e}")
    
    def _display_result(self):
        """显示转换结果"""
        self.result_text.delete("1.0", tk.END)
        
        # 本体
        self.result_text.insert(tk.END, "=== 本体 ===\n\n")
        for base in self.transformed_bases:
            self.result_text.insert(tk.END, f"{base['name']} {base['cost']:.2f}\n")
        
        # 附件
        self.result_text.insert(tk.END, "\n=== 附件 ===\n\n")
        for attachment in self.transformed_attachments:
            self.result_text.insert(tk.END, f"{attachment['name']} {attachment['cost']:.2f}\n")
    
    def _apply_model(self):
        """应用转换后的模型到成本配置"""
        if not self.transformed_bases:
            show_warning(self.parent, "警告", "请先转换价格模型")
            return
        
        # 这里需要调用父窗口的方法来应用数据
        # 由于父窗口是 PricingToolGUI，我们需要通过回调或其他方式传递数据
        show_info(self.parent, "成功", "转换结果已生成，请手动复制到成本配置")
    
    def get_transformed_data(self):
        """获取转换后的数据"""
        return {
            "bases": self.transformed_bases,
            "attachments": self.transformed_attachments,
            "shipping": self.transformed_shipping
        }
