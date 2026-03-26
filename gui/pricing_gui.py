#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
商品定价计算工具 - GUI版本 (CustomTkinter)
功能：基于成本数据和SKU组合，自动计算合理的商品价格
包含阶梯价格生成器功能
"""

import tkinter as tk
from tkinter import ttk, filedialog
import customtkinter as ctk
import csv
import json
import os
from typing import List, Dict, Any

from gui.dialog import show_info, show_warning, show_error, ask_yes_no
from gui.utils import create_button

try:
    from config import PRICING_CONF
except ImportError:
    PRICING_CONF = {
        'default_base_name': '本体1',
        'default_base_cost': 0.0,
        'default_pricing_strategy': 'multiplier',
        'default_rounding': 0,
        'default_max_price': 0.0,
        'window_geometry': '1000x850',
        'window_resizable': True,
        'canvas_height': 150,
        'listbox_height': 10,
        'listbox_width': 70,
    }


class TieredPriceGenerator:
    """阶梯价格生成器类"""
    
    def __init__(self):
        self.configurations = []
        self.highest_target_price = 0
    
    def add_configuration(self, name: str, total_cost: float):
        self.configurations.append({
            'name': name,
            'total_cost': total_cost
        })
    
    def set_highest_target_price(self, price: float):
        self.highest_target_price = price
    
    def calculate_tiered_prices(self, rounding: int = 0, strategy: str = 'multiplier') -> List[Dict[str, Any]]:
        if not self.configurations:
            raise ValueError("请先添加产品配置")
        
        if self.highest_target_price <= 0:
            raise ValueError("请设置有效的最高目标价格")
        
        sorted_configs = sorted(self.configurations, key=lambda x: x['total_cost'])
        highest_cost = sorted_configs[-1]['total_cost']
        
        result = []
        for config in sorted_configs:
            if strategy == 'multiplier':
                factor = self.highest_target_price / highest_cost
                target_price = round(config['total_cost'] * factor, rounding)
            elif strategy == 'margin':
                fixed_profit = self.highest_target_price - highest_cost
                target_price = round(config['total_cost'] + fixed_profit, rounding)
            else:
                raise ValueError(f"不支持的定价策略：{strategy}")
            
            profit = target_price - config['total_cost']
            profit_rate = (profit / config['total_cost']) * 100 if config['total_cost'] > 0 else 0
            
            result.append({
                'name': config['name'],
                'total_cost': config['total_cost'],
                'target_price': target_price,
                'profit': round(profit, 2),
                'profit_rate': round(profit_rate, 2)
            })
        
        return result
    
    def load_from_json_file(self, file_path: str):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在：{file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.configurations = data.get('configurations', [])
        self.highest_target_price = data.get('highest_target_price', 0)
    
    def save_to_json_file(self, file_path: str):
        data = {
            'configurations': self.configurations,
            'highest_target_price': self.highest_target_price
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def clear(self):
        self.configurations = []
        self.highest_target_price = 0


class PricingToolGUI:
    def __init__(self, root, product_id=None):
        self.root = root
        title_text = f"商品定价计算工具 - {product_id}" if product_id else "商品定价计算工具"
        self.root.title(title_text)
        self.root.geometry(PRICING_CONF.get('window_geometry', '1000x850'))
        self.root.resizable(PRICING_CONF.get('window_resizable', True), PRICING_CONF.get('window_resizable', True))
        
        self.product_id = product_id
        self.cost_prices_data = []
        
        # 获取父窗口的字体设置
        self.font_name = getattr(root, 'available_font', 'Microsoft YaHei')
        self.font_size = getattr(root, 'font_size', 10)
        self.button_font = (self.font_name, self.font_size)
        
        self.bases = [{"name": PRICING_CONF.get('default_base_name', '本体1'), "cost": PRICING_CONF.get('default_base_cost', 0.0)}]
        self.attachments = []
        self.sku_configs = []
        self.shipping_cost = 0.0
        
        self.pricing_strategy = PRICING_CONF.get('default_pricing_strategy', 'multiplier')
        self.target_sku = None
        self.max_price = PRICING_CONF.get('default_max_price', 0.0)
        self.rounding = PRICING_CONF.get('default_rounding', 0)
        
        self.bases_canvas = None
        self.attachments_canvas = None
        self.bases_frame = None
        self.attachments_frame = None
        
        self._create_widgets()
        
        if self.product_id:
            self._load_from_database(self.product_id)
    
    def _create_widgets(self):
        main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        cost_frame = ctk.CTkFrame(notebook, fg_color="transparent")
        notebook.add(cost_frame, text="成本配置")
        self._create_cost_config_tab(cost_frame)
        
        sku_frame = ctk.CTkFrame(notebook, fg_color="transparent")
        notebook.add(sku_frame, text="SKU配置")
        self._create_sku_config_tab(sku_frame)
        
        strategy_result_frame = ctk.CTkFrame(notebook, fg_color="transparent")
        notebook.add(strategy_result_frame, text="定价策略与结果")
        self._create_strategy_result_tab(strategy_result_frame)
        
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill=tk.X, pady=10)
        
        calculate_btn = create_button(button_frame, "计算价格", self._calculate_prices, 'success', font=self.button_font)
        calculate_btn.pack(side=tk.LEFT, padx=5)
        
        save_btn = create_button(button_frame, "保存到数据库", self._save_to_database, 'primary', font=self.button_font)
        save_btn.pack(side=tk.LEFT, padx=5)
        
        export_btn = create_button(button_frame, "导出结果", self._export_results, 'secondary', font=self.button_font)
        export_btn.pack(side=tk.RIGHT, padx=5)
    
    
    def _create_cost_config_tab(self, parent):
        ctk.CTkLabel(parent, text="一级：商品本体（可增减）", font=(self.font_name, self.font_size + 4, "bold")).pack(anchor=tk.W, pady=5)
        
        bases_container = ctk.CTkFrame(parent, fg_color="transparent")
        bases_container.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.bases_canvas = tk.Canvas(bases_container, height=PRICING_CONF['canvas_height'], highlightthickness=0)
        bases_scrollbar = ctk.CTkScrollbar(bases_container, command=self.bases_canvas.yview)
        self.bases_frame = ctk.CTkFrame(self.bases_canvas, fg_color="transparent")
        
        self.bases_frame.bind("<Configure>", lambda e: self.bases_canvas.configure(scrollregion=self.bases_canvas.bbox("all")))
        self.bases_canvas.create_window((0, 0), window=self.bases_frame, anchor="nw")
        self.bases_canvas.configure(yscrollcommand=bases_scrollbar.set)
        
        self.bases_canvas.bind("<MouseWheel>", lambda e: self.bases_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        self.bases_frame.bind("<MouseWheel>", lambda e: self.bases_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        self.bases_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        bases_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self._update_bases_list()
        
        base_btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        base_btn_frame.pack(fill=tk.X, pady=5)
        add_base_btn = create_button(base_btn_frame, "添加本体", self._add_base, 'primary', font=self.button_font)
        add_base_btn.pack(side=tk.LEFT, padx=5)
        
        ctk.CTkLabel(parent, text="次级：附件配置（可增减）", font=(self.font_name, self.font_size + 4, "bold")).pack(anchor=tk.W, pady=5, ipady=10)
        
        attachments_container = ctk.CTkFrame(parent, fg_color="transparent")
        attachments_container.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.attachments_canvas = tk.Canvas(attachments_container, height=PRICING_CONF['canvas_height'], highlightthickness=0)
        attachments_scrollbar = ctk.CTkScrollbar(attachments_container, command=self.attachments_canvas.yview)
        self.attachments_frame = ctk.CTkFrame(self.attachments_canvas, fg_color="transparent")
        
        self.attachments_frame.bind("<Configure>", lambda e: self.attachments_canvas.configure(scrollregion=self.attachments_canvas.bbox("all")))
        self.attachments_canvas.create_window((0, 0), window=self.attachments_frame, anchor="nw")
        self.attachments_canvas.configure(yscrollcommand=attachments_scrollbar.set)
        
        self.attachments_canvas.bind("<MouseWheel>", lambda e: self.attachments_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        self.attachments_frame.bind("<MouseWheel>", lambda e: self.attachments_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        self.attachments_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        attachments_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self._update_attachments_list()
        
        attachment_btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        attachment_btn_frame.pack(fill=tk.X, pady=5)
        add_attachment_btn = create_button(attachment_btn_frame, "添加附件", self._add_attachment, 'primary', font=self.button_font)
        add_attachment_btn.pack(side=tk.LEFT, padx=5)
        
        shipping_frame = ctk.CTkFrame(parent, fg_color="transparent")
        shipping_frame.pack(fill=tk.X, pady=10)
        
        shipping_label = ctk.CTkLabel(shipping_frame, text="运费：", font=(self.font_name, self.font_size + 2, "bold"))
        shipping_label.pack(side=tk.LEFT, padx=5)
        
        self.shipping_cost_var = tk.DoubleVar(value=self.shipping_cost)
        shipping_entry = ctk.CTkEntry(shipping_frame, textvariable=self.shipping_cost_var, width=100)
        shipping_entry.pack(side=tk.LEFT, padx=5)
        
        shipping_unit_label = ctk.CTkLabel(shipping_frame, text="元", width=20)
        shipping_unit_label.pack(side=tk.LEFT, padx=5)
        
        shipping_desc = ctk.CTkLabel(shipping_frame, text="(固定成本，计入总成本，不参与SKU生成)", font=(self.font_name, self.font_size), text_color="gray")
        shipping_desc.pack(side=tk.LEFT, padx=10)
        
        shipping_entry.bind("<FocusOut>", lambda e: self._update_shipping_cost())
    
    def _update_bases_list(self):
        for widget in self.bases_frame.winfo_children():
            widget.destroy()
        
        for i, base in enumerate(self.bases):
            base_frame = ctk.CTkFrame(self.bases_frame, fg_color="transparent")
            base_frame.pack(fill=tk.X, pady=5)
            
            ctk.CTkLabel(base_frame, text="本体名称：", width=70).pack(side=tk.LEFT, padx=5)
            name_var = tk.StringVar(value=base["name"])
            name_entry = ctk.CTkEntry(base_frame, textvariable=name_var, width=120)
            name_entry.pack(side=tk.LEFT, padx=5)
            
            ctk.CTkLabel(base_frame, text="成本：", width=50).pack(side=tk.LEFT, padx=5)
            cost_var = tk.DoubleVar(value=base["cost"])
            cost_entry = ctk.CTkEntry(base_frame, textvariable=cost_var, width=80)
            cost_entry.pack(side=tk.LEFT, padx=5)
            ctk.CTkLabel(base_frame, text="元", width=20).pack(side=tk.LEFT, padx=5)
            
            delete_btn = create_button(base_frame, "删除", lambda idx=i: self._delete_base(idx), 'danger', width=60, font=self.button_font)
            delete_btn.pack(side=tk.RIGHT, padx=5)
            
            name_entry.bind("<FocusOut>", lambda e, idx=i, nv=name_var, cv=cost_var: self._update_base(idx, nv.get(), cv.get()))
            cost_entry.bind("<FocusOut>", lambda e, idx=i, nv=name_var, cv=cost_var: self._update_base(idx, nv.get(), cv.get()))
        
        self.bases_frame.update_idletasks()
        if self.bases_canvas:
            self.bases_canvas.configure(scrollregion=self.bases_canvas.bbox("all"))
    
    def _add_base(self):
        new_index = len(self.bases) + 1
        self.bases.append({"name": f"本体{new_index}", "cost": 0.0})
        self._update_bases_list()
    
    def _update_base(self, index, name, cost):
        if 0 <= index < len(self.bases):
            self.bases[index] = {"name": name, "cost": cost}
    
    def _delete_base(self, index):
        if 0 <= index < len(self.bases):
            if len(self.bases) <= 1:
                show_warning(self.root, "警告", "至少需要保留一个本体")
                return
            
            base_name = self.bases[index]["name"]
            for sku in self.sku_configs:
                if sku["base_name"] == base_name:
                    show_warning(self.root, "警告", f"有SKU正在使用该本体：{base_name}，无法删除")
                    return
            
            del self.bases[index]
            self._update_bases_list()
    
    def _update_attachments_list(self):
        for widget in self.attachments_frame.winfo_children():
            widget.destroy()
        
        for i, attachment in enumerate(self.attachments):
            attachment_frame = ctk.CTkFrame(self.attachments_frame, fg_color="transparent")
            attachment_frame.pack(fill=tk.X, pady=5)
            
            ctk.CTkLabel(attachment_frame, text="附件名称：", width=70).pack(side=tk.LEFT, padx=5)
            name_var = tk.StringVar(value=attachment["name"])
            name_entry = ctk.CTkEntry(attachment_frame, textvariable=name_var, width=120)
            name_entry.pack(side=tk.LEFT, padx=5)
            
            ctk.CTkLabel(attachment_frame, text="成本：", width=50).pack(side=tk.LEFT, padx=5)
            cost_var = tk.DoubleVar(value=attachment["cost"])
            cost_entry = ctk.CTkEntry(attachment_frame, textvariable=cost_var, width=80)
            cost_entry.pack(side=tk.LEFT, padx=5)
            ctk.CTkLabel(attachment_frame, text="元", width=20).pack(side=tk.LEFT, padx=5)
            
            stackable_var = tk.BooleanVar(value=attachment.get("stackable", False))
            ctk.CTkCheckBox(attachment_frame, text="累加", variable=stackable_var, width=60).pack(side=tk.LEFT, padx=5)
            
            delete_btn = create_button(attachment_frame, "删除", lambda idx=i: self._delete_attachment(idx), 'danger', width=60, font=self.button_font)
            delete_btn.pack(side=tk.RIGHT, padx=5)
            
            name_entry.bind("<FocusOut>", lambda e, idx=i, nv=name_var, cv=cost_var, sv=stackable_var: self._update_attachment(idx, nv.get(), cv.get(), sv.get()))
            cost_entry.bind("<FocusOut>", lambda e, idx=i, nv=name_var, cv=cost_var, sv=stackable_var: self._update_attachment(idx, nv.get(), cv.get(), sv.get()))
            stackable_var.trace_add("write", lambda *args, idx=i, nv=name_var, cv=cost_var, sv=stackable_var: self._update_attachment(idx, nv.get(), cv.get(), sv.get()))
        
        self.attachments_frame.update_idletasks()
        if self.attachments_canvas:
            self.attachments_canvas.configure(scrollregion=self.attachments_canvas.bbox("all"))
    
    def _add_attachment(self):
        new_index = len(self.attachments) + 1
        self.attachments.append({"name": f"附件{chr(64 + new_index)}", "cost": 0.0, "stackable": False})
        self._update_attachments_list()
    
    def _update_attachment(self, index, name, cost, stackable=False):
        if 0 <= index < len(self.attachments):
            self.attachments[index] = {"name": name, "cost": cost, "stackable": stackable}
    
    def _delete_attachment(self, index):
        if 0 <= index < len(self.attachments):
            del self.attachments[index]
            self._update_attachments_list()
    
    def _update_shipping_cost(self):
        try:
            self.shipping_cost = self.shipping_cost_var.get()
        except:
            self.shipping_cost = 0.0
    
    def _create_sku_config_tab(self, parent):
        ctk.CTkLabel(parent, text="SKU组合配置", font=(self.font_name, self.font_size + 4, "bold")).pack(anchor=tk.W, pady=5)
        
        listbox_frame = ctk.CTkFrame(parent)
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.sku_listbox = tk.Listbox(listbox_frame, height=PRICING_CONF['listbox_height'], width=PRICING_CONF['listbox_width'])
        self.sku_listbox.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        self._update_sku_list()
        
        sku_btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        sku_btn_frame.pack(fill=tk.X, pady=5)
        
        create_button(sku_btn_frame, "添加SKU", self._add_sku, 'primary', font=self.button_font).pack(side=tk.LEFT, padx=5)
        create_button(sku_btn_frame, "自动生成SKU", self._auto_generate_sku, 'success', font=self.button_font).pack(side=tk.LEFT, padx=5)
        create_button(sku_btn_frame, "从数据库加载SKU价格", self._load_sku_prices_from_db, 'info', font=self.button_font).pack(side=tk.LEFT, padx=5)
        create_button(sku_btn_frame, "编辑SKU", self._edit_sku, 'secondary', font=self.button_font).pack(side=tk.LEFT, padx=5)
        create_button(sku_btn_frame, "删除SKU", self._delete_sku, 'danger', font=self.button_font).pack(side=tk.LEFT, padx=5)
    
    def _create_strategy_result_tab(self, parent):
        strategy_frame = ctk.CTkFrame(parent)
        strategy_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(strategy_frame, text="定价策略", font=(self.font_name, self.font_size + 4, "bold")).pack(anchor=tk.W, padx=10, pady=5)
        
        row1 = ctk.CTkFrame(strategy_frame, fg_color="transparent")
        row1.pack(fill=tk.X, pady=5, padx=10)
        
        self.strategy_var = tk.StringVar(value=self.pricing_strategy)
        ctk.CTkRadioButton(row1, text="统一倍率", variable=self.strategy_var, value="multiplier").pack(side=tk.LEFT, padx=10)
        ctk.CTkRadioButton(row1, text="统一利润率", variable=self.strategy_var, value="margin").pack(side=tk.LEFT, padx=10)
        
        row2 = ctk.CTkFrame(strategy_frame, fg_color="transparent")
        row2.pack(fill=tk.X, pady=5, padx=10)
        
        ctk.CTkLabel(row2, text="定价基准SKU：", width=100).pack(side=tk.LEFT, padx=5)
        self.target_sku_var = tk.StringVar(value=self.target_sku)
        self.target_sku_combobox = ctk.CTkComboBox(row2, variable=self.target_sku_var, width=120, state="readonly")
        self.target_sku_combobox.pack(side=tk.LEFT, padx=5)
        
        ctk.CTkLabel(row2, text="目标售价：", width=80).pack(side=tk.LEFT, padx=5)
        self.max_price_var = tk.StringVar(value=str(self.max_price) if self.max_price else "")
        self.max_price_entry = ctk.CTkEntry(row2, textvariable=self.max_price_var, width=80)
        self.max_price_entry.pack(side=tk.LEFT, padx=5)
        self.max_price_entry.bind('<KeyRelease>', self._on_price_change)
        ctk.CTkLabel(row2, text="元", width=20).pack(side=tk.LEFT, padx=2)
        
        # 默认比例输入框
        ctk.CTkLabel(row2, text="默认比例：", width=70).pack(side=tk.LEFT, padx=5)
        self.default_ratio_var = tk.StringVar(value="130")
        self.default_ratio_entry = ctk.CTkEntry(row2, textvariable=self.default_ratio_var, width=50)
        self.default_ratio_entry.pack(side=tk.LEFT, padx=2)
        self.default_ratio_entry.bind('<KeyRelease>', self._validate_ratio)
        ctk.CTkLabel(row2, text="%", width=15).pack(side=tk.LEFT, padx=2)
        
        # 计算默认售价按钮
        calc_default_btn = create_button(row2, "计算", self._calculate_default_price, 'secondary', width=50, font=self.button_font)
        calc_default_btn.pack(side=tk.LEFT, padx=5)
        
        ctk.CTkLabel(row2, text="小数位：", width=60).pack(side=tk.LEFT, padx=5)
        self.rounding_var = tk.StringVar(value=str(self.rounding))
        self.rounding_combo = ctk.CTkComboBox(row2, variable=self.rounding_var, width=60, state="readonly")
        self.rounding_combo.configure(values=['0', '1', '2'])
        self.rounding_combo.pack(side=tk.LEFT, padx=5)
        self.rounding_combo.bind('<Button-1>', self._on_rounding_click)
        self._rounding_extended = False
        
        self._update_target_sku_combobox()
        
        result_frame = ctk.CTkFrame(parent)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ctk.CTkLabel(result_frame, text="计算结果", font=(self.font_name, self.font_size + 4, "bold")).pack(anchor=tk.W, padx=10, pady=5)
        
        tree_frame = ctk.CTkFrame(result_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ("sku_name", "cost", "price", "profit", "profit_rate")
        self.result_tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        
        self.result_tree.heading("sku_name", text="SKU名称")
        self.result_tree.heading("cost", text="成本（元）")
        self.result_tree.heading("price", text="售价（元）")
        self.result_tree.heading("profit", text="利润（元）")
        self.result_tree.heading("profit_rate", text="利润率（%）")
        
        self.result_tree.column("sku_name", width=250)
        self.result_tree.column("cost", width=100, anchor=tk.CENTER)
        self.result_tree.column("price", width=100, anchor=tk.CENTER)
        self.result_tree.column("profit", width=100, anchor=tk.CENTER)
        self.result_tree.column("profit_rate", width=100, anchor=tk.CENTER)
        
        self.result_tree.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        stats_frame = ctk.CTkFrame(result_frame, fg_color="transparent")
        stats_frame.pack(fill=tk.X, pady=5, padx=10)
        
        self.total_cost_var = tk.StringVar(value="总生产成本：0.00 元")
        ctk.CTkLabel(stats_frame, textvariable=self.total_cost_var, font=(self.font_name, self.font_size + 2)).pack(side=tk.LEFT, padx=10)
        
        self.average_profit_rate_var = tk.StringVar(value="平均利润率：0.00%")
        ctk.CTkLabel(stats_frame, textvariable=self.average_profit_rate_var, font=(self.font_name, self.font_size + 2)).pack(side=tk.LEFT, padx=10)
    
    def _update_target_sku_combobox(self):
        sku_names = [sku["name"] for sku in self.sku_configs]
        self.target_sku_combobox.configure(values=sku_names)
        if self.target_sku not in sku_names and sku_names:
            self.target_sku = sku_names[0]
            self.target_sku_var.set(self.target_sku)
    
    def _on_price_change(self, event=None):
        price_str = self.max_price_var.get()
        try:
            if '.' in price_str:
                decimal_part = price_str.split('.')[1]
                decimal_count = len(decimal_part)
                current_rounding = int(self.rounding_var.get())
                if decimal_count > current_rounding and decimal_count <= 2:
                    self.rounding_var.set(str(decimal_count))
        except (ValueError, IndexError):
            pass
    
    def _on_rounding_click(self, event=None):
        shift_pressed = event.state & 0x1 if event else False
        if shift_pressed and not self._rounding_extended:
            self.rounding_combo.configure(values=['0', '1', '2', '3', '4'])
            self._rounding_extended = True
        elif not shift_pressed and self._rounding_extended:
            self.rounding_combo.configure(values=['0', '1', '2'])
            self._rounding_extended = False
    
    def _update_sku_list(self):
        self.sku_listbox.delete(0, tk.END)
        for sku in self.sku_configs:
            attachments = " + ".join(sku["attachments"]) if sku["attachments"] else "无附件"
            display_text = f"{sku['name']}: {sku['base_name']} + {attachments}"
            self.sku_listbox.insert(tk.END, display_text)
    
    def _add_sku(self):
        add_window = ctk.CTkToplevel(self.root)
        add_window.title("添加SKU")
        add_window.geometry("400x520")
        add_window.resizable(False, False)
        add_window.transient(self.root)
        add_window.grab_set()
        add_window.focus_force()
        add_window.lift()
        
        main_frame = ctk.CTkFrame(add_window, fg_color="transparent")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        ctk.CTkLabel(main_frame, text="SKU名称：").pack(pady=5, anchor=tk.W)
        sku_name_var = tk.StringVar()
        ctk.CTkEntry(main_frame, textvariable=sku_name_var, width=300).pack(pady=5)
        
        ctk.CTkLabel(main_frame, text="选择本体：").pack(pady=5, anchor=tk.W)
        base_var = tk.StringVar(value=self.bases[0]["name"] if self.bases else "")
        base_combobox = ctk.CTkComboBox(main_frame, variable=base_var, width=280, state="readonly")
        base_combobox.configure(values=[base["name"] for base in self.bases])
        base_combobox.pack(pady=5)
        
        ctk.CTkLabel(main_frame, text="选择附件：").pack(pady=5, anchor=tk.W)
        
        attachment_frame = ctk.CTkScrollableFrame(main_frame, height=180)
        attachment_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        attachment_vars = {}
        for attachment in self.attachments:
            var = tk.BooleanVar()
            cb = ctk.CTkCheckBox(attachment_frame, text=f"{attachment['name']} ({attachment['cost']}元)", variable=var)
            cb.pack(anchor=tk.W, pady=2)
            attachment_vars[attachment['name']] = var
        
        def do_add():
            sku_name = sku_name_var.get()
            base_name = base_var.get()
            selected_attachments = [name for name, var in attachment_vars.items() if var.get()]
            
            if not sku_name:
                show_warning(self.root, "警告", "请输入SKU名称")
                return
            
            self.sku_configs.append({
                "name": sku_name,
                "base_name": base_name,
                "attachments": selected_attachments
            })
            self._update_sku_list()
            self._update_target_sku_combobox()
            add_window.destroy()
        
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill=tk.X, pady=15)
        create_button(btn_frame, "添加", do_add, 'success', font=self.button_font).pack(pady=5)
    
    def _auto_generate_sku(self):
        if not self.bases:
            show_warning(self.root, "警告", "请先添加本体")
            return
        
        self.sku_configs = []
        sku_index = 1
        
        non_stackable = [a for a in self.attachments if not a.get("stackable", False)]
        stackable = [a for a in self.attachments if a.get("stackable", False)]
        
        for base in self.bases:
            self.sku_configs.append({
                "name": f"SKU{sku_index}",
                "base_name": base["name"],
                "attachments": []
            })
            sku_index += 1
            
            for attachment in non_stackable:
                self.sku_configs.append({
                    "name": f"SKU{sku_index}",
                    "base_name": base["name"],
                    "attachments": [attachment["name"]]
                })
                sku_index += 1
            
            for attachment in stackable:
                self.sku_configs.append({
                    "name": f"SKU{sku_index}",
                    "base_name": base["name"],
                    "attachments": [attachment["name"]]
                })
                sku_index += 1
            
            if non_stackable and stackable:
                for ns in non_stackable:
                    for s in stackable:
                        self.sku_configs.append({
                            "name": f"SKU{sku_index}",
                            "base_name": base["name"],
                            "attachments": [ns["name"], s["name"]]
                        })
                        sku_index += 1
            
            if len(stackable) > 1:
                from itertools import combinations
                for r in range(2, len(stackable) + 1):
                    for combo in combinations(stackable, r):
                        self.sku_configs.append({
                            "name": f"SKU{sku_index}",
                            "base_name": base["name"],
                            "attachments": [a["name"] for a in combo]
                        })
                        sku_index += 1
        
        self._update_sku_list()
        self._update_target_sku_combobox()
        show_info(self.root, "成功", f"已自动生成 {len(self.sku_configs)} 个SKU配置")
    
    def _load_sku_prices_from_db(self):
        """从数据库加载SKU价格数据并自动生成配置"""
        if not self.product_id:
            show_warning(self.root, "警告", "请先选择商品")
            return
        
        try:
            from utils.database import Database
            db = Database()
            sku_prices = db.get_sku_prices(self.product_id)
            db.close()
            
            if not sku_prices:
                show_warning(self.root, "警告", "该商品没有SKU价格数据")
                return
            
            # 解析SKU名称，提取颜色和规格
            colors = []
            sizes = []
            price_matrix = {}
            
            for sku in sku_prices:
                sku_name = sku['sku_name']
                price = sku['price']
                
                # 尝试解析 "颜色 规格" 格式
                parts = sku_name.split()
                if len(parts) >= 2:
                    color = parts[0]
                    size = parts[1]
                    
                    if color not in colors:
                        colors.append(color)
                    if size not in sizes:
                        sizes.append(size)
                    
                    if color not in price_matrix:
                        price_matrix[color] = {}
                    price_matrix[color][size] = price
            
            if not colors or not sizes:
                show_warning(self.root, "警告", "无法解析SKU名称格式，请手动配置")
                return
            
            # 找到最低价格作为基准
            min_price = float('inf')
            for color in colors:
                for size in sizes:
                    price = price_matrix.get(color, {}).get(size, 0)
                    if price > 0 and price < min_price:
                        min_price = price
            
            # 生成本体配置（每个颜色）
            self.bases = []
            for color in colors:
                base_cost = price_matrix.get(color, {}).get(sizes[0], min_price)
                self.bases.append({"name": color, "cost": base_cost})
            
            # 生成附件配置（每个规格相对于基准价格的差价）
            self.attachments = []
            for i, size in enumerate(sizes):
                if i == 0:
                    # 第一个规格是基准，附件成本为0
                    self.attachments.append({"name": size, "cost": 0.0, "stackable": False})
                else:
                    # 其他规格的差价
                    base_color = colors[0] if colors else None
                    base_price = price_matrix.get(base_color, {}).get(sizes[0], min_price)
                    size_price = price_matrix.get(base_color, {}).get(size, base_price)
                    diff = size_price - base_price
                    self.attachments.append({"name": size, "cost": diff, "stackable": False})
            
            # 生成SKU配置
            self.sku_configs = []
            for color in colors:
                for size in sizes:
                    self.sku_configs.append({
                        "name": f"{color} {size}",
                        "base_name": color,
                        "attachments": [size]
                    })
            
            # 更新界面
            self._update_bases_list()
            self._update_attachments_list()
            self._update_sku_list()
            self._update_target_sku_combobox()
            
            # 自动计算默认售价
            self._calculate_default_price()
            
            show_info(self.root, "成功", f"已加载 {len(sku_prices)} 条SKU价格数据\n生成 {len(self.bases)} 个本体，{len(self.attachments)} 个附件，{len(self.sku_configs)} 个SKU配置")
            
        except Exception as e:
            show_error(self.root, "错误", f"加载SKU价格失败: {e}")
    
    def _edit_sku(self):
        selection = self.sku_listbox.curselection()
        if not selection:
            show_warning(self.root, "警告", "请先选择要编辑的SKU")
            return
        
        index = selection[0]
        sku = self.sku_configs[index]
        
        edit_window = ctk.CTkToplevel(self.root)
        edit_window.title("编辑SKU")
        edit_window.geometry("400x520")
        edit_window.resizable(False, False)
        edit_window.transient(self.root)
        edit_window.grab_set()
        edit_window.focus_force()
        edit_window.lift()
        
        main_frame = ctk.CTkFrame(edit_window, fg_color="transparent")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        ctk.CTkLabel(main_frame, text="SKU名称：").pack(pady=5, anchor=tk.W)
        sku_name_var = tk.StringVar(value=sku["name"])
        ctk.CTkEntry(main_frame, textvariable=sku_name_var, width=300).pack(pady=5)
        
        ctk.CTkLabel(main_frame, text="选择本体：").pack(pady=5, anchor=tk.W)
        base_var = tk.StringVar(value=sku["base_name"])
        base_combobox = ctk.CTkComboBox(main_frame, variable=base_var, width=280, state="readonly")
        base_combobox.configure(values=[base["name"] for base in self.bases])
        base_combobox.pack(pady=5)
        
        ctk.CTkLabel(main_frame, text="选择附件：").pack(pady=5, anchor=tk.W)
        
        attachment_frame = ctk.CTkScrollableFrame(main_frame, height=180)
        attachment_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        attachment_vars = {}
        for attachment in self.attachments:
            var = tk.BooleanVar(value=attachment["name"] in sku["attachments"])
            cb = ctk.CTkCheckBox(attachment_frame, text=f"{attachment['name']} ({attachment['cost']}元)", variable=var)
            cb.pack(anchor=tk.W, pady=2)
            attachment_vars[attachment['name']] = var
        
        def do_edit():
            sku_name = sku_name_var.get()
            base_name = base_var.get()
            selected_attachments = [name for name, var in attachment_vars.items() if var.get()]
            
            if not sku_name:
                show_warning(self.root, "警告", "请输入SKU名称")
                return
            
            self.sku_configs[index] = {
                "name": sku_name,
                "base_name": base_name,
                "attachments": selected_attachments
            }
            self._update_sku_list()
            self._update_target_sku_combobox()
            edit_window.destroy()
        
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill=tk.X, pady=15)
        create_button(btn_frame, "保存", do_edit, 'success', font=self.button_font).pack(pady=5)
    
    def _delete_sku(self):
        selection = self.sku_listbox.curselection()
        if not selection:
            show_warning(self.root, "警告", "请先选择要删除的SKU")
            return
        
        index = selection[0]
        del self.sku_configs[index]
        self._update_sku_list()
        self._update_target_sku_combobox()
    
    def _calculate_prices(self):
        if not self.sku_configs:
            show_warning(self.root, "警告", "请先配置SKU")
            return
        
        target_sku = self.target_sku_var.get()
        try:
            max_price = float(self.max_price_var.get())
        except ValueError:
            max_price = 0
        
        if not target_sku or max_price <= 0:
            show_warning(self.root, "警告", "请选择定价基准SKU并设置最高售价")
            return
        
        target_sku_config = None
        for sku in self.sku_configs:
            if sku["name"] == target_sku:
                target_sku_config = sku
                break
        
        if not target_sku_config:
            show_warning(self.root, "警告", "找不到目标SKU配置")
            return
        
        target_cost = self._calculate_sku_cost(target_sku_config)
        if target_cost <= 0:
            show_warning(self.root, "警告", "目标SKU成本无效")
            return
        
        strategy = self.strategy_var.get()
        rounding = int(self.rounding_var.get())
        
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        
        total_cost = 0
        total_profit = 0
        
        for sku in self.sku_configs:
            cost = self._calculate_sku_cost(sku)
            
            if strategy == "multiplier":
                factor = max_price / target_cost
                price = round(cost * factor, rounding)
            else:
                fixed_profit = max_price - target_cost
                price = round(cost + fixed_profit, rounding)
            
            profit = price - cost
            profit_rate = (profit / cost) * 100 if cost > 0 else 0
            
            attachments_str = " + ".join(sku["attachments"]) if sku["attachments"] else "无附件"
            sku_display_name = f"{sku['name']}: {sku['base_name']} + {attachments_str}"
            
            self.result_tree.insert("", "end", values=(
                sku_display_name,
                f"{cost:.{rounding}f}",
                f"{price:.{rounding}f}",
                f"{profit:.{rounding}f}",
                f"{profit_rate:.2f}"
            ))
            
            total_cost += cost
            total_profit += profit
        
        avg_profit_rate = (total_profit / total_cost) * 100 if total_cost > 0 else 0
        self.total_cost_var.set(f"总生产成本：{total_cost:.{rounding}f} 元")
        self.average_profit_rate_var.set(f"平均利润率：{avg_profit_rate:.2f}%")
    
    def _calculate_default_price(self):
        """计算默认售价：成本 + 成本*比例% + 运费"""
        if not self.sku_configs:
            show_warning(self.root, "警告", "请先配置SKU")
            return
        
        # 获取默认比例，不允许负值
        try:
            ratio = float(self.default_ratio_var.get())
            if ratio < 0:
                show_warning(self.root, "警告", "默认比例不能为负值")
                return
        except ValueError:
            show_warning(self.root, "警告", "请输入有效的默认比例")
            return
        
        # 获取基准 SKU
        target_sku = self.target_sku_var.get()
        if not target_sku:
            # 如果没有选择基准 SKU，使用第一个 SKU
            if self.sku_configs:
                target_sku = self.sku_configs[0]["name"]
                self.target_sku_var.set(target_sku)
            else:
                show_warning(self.root, "警告", "请先配置SKU")
                return
        
        # 计算基准 SKU 的成本
        target_sku_config = None
        for sku in self.sku_configs:
            if sku["name"] == target_sku:
                target_sku_config = sku
                break
        
        if not target_sku_config:
            show_warning(self.root, "警告", "找不到目标SKU配置")
            return
        
        target_cost = self._calculate_sku_cost(target_sku_config)
        if target_cost <= 0:
            show_warning(self.root, "警告", "目标SKU成本无效")
            return
        
        # 计算默认售价：成本 + 成本*比例% + 运费
        default_price = target_cost + target_cost * (ratio / 100) + self.shipping_cost
        
        # 设置到目标售价输入框
        self.max_price_var.set(f"{default_price:.2f}")
    
    def _validate_ratio(self, event):
        """验证默认比例输入，自动过滤负号"""
        current_value = self.default_ratio_var.get()
        # 移除所有负号
        if '-' in current_value:
            new_value = current_value.replace('-', '')
            self.default_ratio_var.set(new_value)
    
    def _calculate_sku_cost(self, sku_config):
        cost = 0.0
        
        for base in self.bases:
            if base["name"] == sku_config["base_name"]:
                cost += base["cost"]
                break
        
        for attachment_name in sku_config["attachments"]:
            for attachment in self.attachments:
                if attachment["name"] == attachment_name:
                    cost += attachment["cost"]
                    break
        
        cost += self.shipping_cost
        
        return cost
    
    def _save_to_database(self):
        if not self.product_id:
            show_warning(self.root, "警告", "请先选择商品")
            return
        
        results = []
        for item in self.result_tree.get_children():
            values = self.result_tree.item(item, 'values')
            if values:
                results.append({
                    "sku_name": values[0],
                    "price": values[2]
                })
        
        if not results:
            show_warning(self.root, "警告", "请先计算价格")
            return
        
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            db.save_selling_prices(self.product_id, results)
            show_info(self.root, "成功", f"已保存 {len(results)} 条价格数据到数据库")
        except Exception as e:
            show_error(self.root, "错误", f"保存失败：{str(e)}")
    
    def _export_results(self):
        if not self.result_tree.get_children():
            show_warning(self.root, "警告", "请先计算价格")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")],
            title="导出结果"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["SKU名称", "成本（元）", "售价（元）", "利润（元）", "利润率（%）"])
                    
                    for item in self.result_tree.get_children():
                        values = self.result_tree.item(item, 'values')
                        writer.writerow(values)
                
                show_info(self.root, "成功", f"结果已导出到：{file_path}")
            except Exception as e:
                show_error(self.root, "错误", f"导出失败：{str(e)}")
    
    def _load_from_database(self, product_id):
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            product = db.get_product(product_id)
            
            if not product:
                return
            
            cost_prices_str = product.get('cost_prices')
            if not cost_prices_str:
                return
            
            cost_prices = json.loads(cost_prices_str)
            self.cost_prices_data = cost_prices
            
            color_names = set()
            size_names = set()
            
            for item in cost_prices:
                color = item[0] if len(item) > 0 else ""
                size = item[1] if len(item) > 1 else ""
                if color:
                    color_names.add(color)
                if size:
                    size_names.add(size)
            
            self.bases = []
            for color in sorted(color_names):
                for item in cost_prices:
                    if item[0] == color:
                        price = float(item[2]) if len(item) > 2 else 0.0
                        self.bases.append({"name": color, "cost": price})
                        break
            
            self.attachments = []
            for size in sorted(size_names):
                self.attachments.append({"name": size, "cost": 0.0})
            
            self.sku_configs = []
            for i, item in enumerate(cost_prices):
                color = item[0] if len(item) > 0 else ""
                size = item[1] if len(item) > 1 else ""
                
                sku_name = f"SKU{i+1}"
                base_name = color if color else "默认"
                attachments = [size] if size else []
                
                self.sku_configs.append({
                    "name": sku_name,
                    "base_name": base_name,
                    "attachments": attachments
                })
            
            self._update_bases_list()
            self._update_attachments_list()
            self._update_sku_list()
            self._update_target_sku_combobox()
            
            if self.sku_configs:
                self.target_sku = self.sku_configs[0]["name"]
                self.target_sku_var.set(self.target_sku)
            
        except Exception as e:
            print(f"加载数据失败：{str(e)}")


def main():
    root = ctk.CTk()
    app = PricingToolGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
