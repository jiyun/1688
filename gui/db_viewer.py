#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库查看器模块
提供优化的数据库展示功能
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from config import get_font
from typing import Dict, List, Any, Optional


class DatabaseViewer:
    """数据库查看器
    
    提供以下功能：
    - 商品基础信息查看
    - 资源链接查看
    - 价格矩阵查看
    - 店铺信息查看
    """
    
    def __init__(self, parent, db):
        self.parent = parent
        self.db = db
        self.current_product_id = None
        
    def create_product_info_panel(self, frame: ctk.CTkFrame):
        """创建商品信息面板"""
        # 标题
        title_frame = ctk.CTkFrame(frame)
        title_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(title_frame, text="商品信息", font=get_font('', 'xl', 'bold')).pack(side="left", padx=5)
        
        # 信息网格
        info_frame = ctk.CTkFrame(frame)
        info_frame.pack(fill="x", padx=5, pady=5)
        
        self.info_labels = {}
        info_items = [
            ('product_id', '商品ID'),
            ('title', '商品标题'),
            ('category', '类目'),
            ('sales_count', '销量'),
            ('min_order', '起批量'),
            ('ship_from', '发货地'),
            ('shop_name', '店铺'),
            ('created_at', '创建时间'),
        ]
        
        for i, (key, label) in enumerate(info_items):
            row = i // 2
            col = i % 2
            
            item_frame = ctk.CTkFrame(info_frame)
            item_frame.grid(row=row, column=col, padx=5, pady=2, sticky="w")
            
            ctk.CTkLabel(item_frame, text=f"{label}:", width=80).pack(side="left")
            self.info_labels[key] = ctk.CTkLabel(item_frame, text="-", width=200)
            self.info_labels[key].pack(side="left")
    
    def create_resource_panel(self, frame: ctk.CTkFrame):
        """创建资源面板"""
        # 标题
        title_frame = ctk.CTkFrame(frame)
        title_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(title_frame, text="资源链接", font=get_font('', 'xl', 'bold')).pack(side="left", padx=5)
        
        # 资源统计
        stats_frame = ctk.CTkFrame(frame)
        stats_frame.pack(fill="x", padx=5, pady=5)
        
        self.resource_stats = {}
        resource_types = [
            ('main_images', '主图'),
            ('color_cards', '色卡图'),
            ('details', '详情图'),
            ('videos', '视频'),
        ]
        
        for key, label in resource_types:
            item_frame = ctk.CTkFrame(stats_frame)
            item_frame.pack(side="left", padx=10)
            
            ctk.CTkLabel(item_frame, text=label, font=get_font('', 'base')).pack(side="left")
            self.resource_stats[key] = ctk.CTkLabel(item_frame, text="0", font=get_font('', 'lg', 'bold'))
            self.resource_stats[key].pack(side="left", padx=5)
        
        # 资源列表
        list_frame = ctk.CTkFrame(frame)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        columns = ("type", "url", "status")
        self.resource_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=6)
        
        self.resource_tree.heading("type", text="类型")
        self.resource_tree.heading("url", text="链接")
        self.resource_tree.heading("status", text="状态")
        
        self.resource_tree.column("type", width=80)
        self.resource_tree.column("url", width=300)
        self.resource_tree.column("status", width=60)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.resource_tree.yview)
        self.resource_tree.configure(yscrollcommand=scrollbar.set)
        
        self.resource_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_price_panel(self, frame: ctk.CTkFrame):
        """创建价格面板"""
        # 标题
        title_frame = ctk.CTkFrame(frame)
        title_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(title_frame, text="价格矩阵", font=get_font('', 'xl', 'bold')).pack(side="left", padx=5)
        
        # 价格统计
        stats_frame = ctk.CTkFrame(frame)
        stats_frame.pack(fill="x", padx=5, pady=5)
        
        self.price_stats = {}
        price_items = [
            ('min_price', '最低价'),
            ('max_price', '最高价'),
            ('avg_price', '平均价'),
            ('total_stock', '总库存'),
        ]
        
        for key, label in price_items:
            item_frame = ctk.CTkFrame(stats_frame)
            item_frame.pack(side="left", padx=10)
            
            ctk.CTkLabel(item_frame, text=label, font=get_font('', 'base')).pack(side="left")
            self.price_stats[key] = ctk.CTkLabel(item_frame, text="-", font=get_font('', 'lg', 'bold'))
            self.price_stats[key].pack(side="left", padx=5)
        
        # 价格列表
        list_frame = ctk.CTkFrame(frame)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        columns = ("color", "size", "price", "stock")
        self.price_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=6)
        
        self.price_tree.heading("color", text="颜色")
        self.price_tree.heading("size", text="规格")
        self.price_tree.heading("price", text="价格")
        self.price_tree.heading("stock", text="库存")
        
        self.price_tree.column("color", width=100)
        self.price_tree.column("size", width=100)
        self.price_tree.column("price", width=80)
        self.price_tree.column("stock", width=60)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.price_tree.yview)
        self.price_tree.configure(yscrollcommand=scrollbar.set)
        
        self.price_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def load_product(self, product_id: str):
        """加载商品数据"""
        self.current_product_id = product_id
        
        # 加载商品基础信息
        product = self.db.get_product(product_id)
        if product:
            for key, label in self.info_labels.items():
                value = product.get(key, '-') or '-'
                if key == 'title' and len(str(value)) > 30:
                    value = str(value)[:30] + '...'
                self.info_labels[key].configure(text=str(value))
        
        # 加载资源统计
        try:
            stats = self.db.conn.execute(
                "SELECT * FROM v_resource_stats WHERE product_id = ?",
                [product_id]
            ).fetchone()
            
            if stats:
                self.resource_stats['main_images'].configure(text=str(stats['main_images'] or 0))
                self.resource_stats['color_cards'].configure(text=str(stats['color_cards'] or 0))
                self.resource_stats['details'].configure(text=str(stats['details'] or 0))
                self.resource_stats['videos'].configure(text=str(stats['videos'] or 0))
        except Exception:
            pass
        
        # 加载价格统计
        try:
            price_stats = self.db.conn.execute(
                "SELECT * FROM v_price_stats WHERE product_id = ?",
                [product_id]
            ).fetchone()
            
            if price_stats:
                self.price_stats['min_price'].configure(text=f"¥{price_stats['min_price']:.2f}" if price_stats['min_price'] else "-")
                self.price_stats['max_price'].configure(text=f"¥{price_stats['max_price']:.2f}" if price_stats['max_price'] else "-")
                self.price_stats['avg_price'].configure(text=f"¥{price_stats['avg_price']:.2f}" if price_stats['avg_price'] else "-")
                self.price_stats['total_stock'].configure(text=str(price_stats['total_stock'] or 0))
        except Exception:
            pass
        
        # 加载资源列表
        for item in self.resource_tree.get_children():
            self.resource_tree.delete(item)
        
        resources = self.db.get_resources(product_id)
        for resource in resources[:20]:  # 限制显示20条
            resource_type = resource.get('resource_type', '-')
            url = resource.get('resource_url', '')[:50]
            status = "✓" if resource.get('downloaded') else "○"
            
            self.resource_tree.insert("", "end", values=(resource_type, url, status))
        
        # 加载价格列表
        for item in self.price_tree.get_children():
            self.price_tree.delete(item)
        
        sku_prices = self.db.get_sku_prices(product_id)
        for sku in sku_prices[:20]:  # 限制显示20条
            color = sku.get('color', sku.get('sku_name', '').split('>')[0] if '>' in sku.get('sku_name', '') else sku.get('sku_name', ''))
            size = sku.get('size', sku.get('sku_name', '').split('>')[1] if '>' in sku.get('sku_name', '') else '-')
            price = f"¥{sku.get('price', 0):.2f}" if sku.get('price') else "-"
            stock = str(sku.get('stock', 0)) if sku.get('stock') else "-"
            
            self.price_tree.insert("", "end", values=(color, size, price, stock))
    
    def clear(self):
        """清空显示"""
        for key in self.info_labels:
            self.info_labels[key].configure(text="-")
        
        for key in self.resource_stats:
            self.resource_stats[key].configure(text="0")
        
        for key in self.price_stats:
            self.price_stats[key].configure(text="-")
        
        for item in self.resource_tree.get_children():
            self.resource_tree.delete(item)
        
        for item in self.price_tree.get_children():
            self.price_tree.delete(item)
