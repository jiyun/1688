#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
商品定价计算工具 - GUI版本
功能：基于成本数据和SKU组合，自动计算合理的商品价格
"""

import tkinter as tk
from tkinter import ttk, filedialog
import csv
import json
from typing import List, Dict, Any

from gui.dialog import show_info, show_warning, show_error, ask_yes_no

try:
    from config import PRICING_CONF
except ImportError:
    PRICING_CONF = {
        'default_base_name': '本体1',
        'default_base_cost': 0.0,
        'default_pricing_strategy': 'multiplier',
        'default_rounding': 0,
        'default_max_price': 0.0,
        'window_geometry': '1000x700',
        'window_resizable': True,
        'canvas_height': 150,
        'listbox_height': 10,
        'listbox_width': 70,
    }


class PricingToolGUI:
    def __init__(self, root, product_id=None):
        self.root = root
        self.root.title("商品定价计算工具")
        self.root.geometry(PRICING_CONF['window_geometry'])
        self.root.resizable(PRICING_CONF['window_resizable'], PRICING_CONF['window_resizable'])
        
        self.product_id = product_id
        self.cost_prices_data = []
        
        self.bases = [{"name": PRICING_CONF['default_base_name'], "cost": PRICING_CONF['default_base_cost']}]
        self.attachments = []
        self.sku_configs = []
        
        self.pricing_strategy = PRICING_CONF['default_pricing_strategy']
        self.target_sku = None
        self.max_price = PRICING_CONF['default_max_price']
        self.rounding = PRICING_CONF['default_rounding']
        
        self.bases_canvas = None
        self.attachments_canvas = None
        self.bases_frame = None
        self.attachments_frame = None
        
        self._create_widgets()
        
        if self.product_id:
            self._load_from_database(self.product_id)
    
    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title_text = f"商品定价计算工具 - {self.product_id}" if self.product_id else "商品定价计算工具"
        title_label = ttk.Label(main_frame, text=title_text, font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
        cost_frame = ttk.Frame(notebook, padding="10")
        notebook.add(cost_frame, text="成本配置")
        self._create_cost_config_tab(cost_frame)
        
        sku_frame = ttk.Frame(notebook, padding="10")
        notebook.add(sku_frame, text="SKU配置")
        self._create_sku_config_tab(sku_frame)
        
        strategy_result_frame = ttk.Frame(notebook, padding="10")
        notebook.add(strategy_result_frame, text="定价策略与结果")
        self._create_strategy_result_tab(strategy_result_frame)
        
        button_frame = ttk.Frame(main_frame, padding="10")
        button_frame.pack(fill=tk.X, pady=10)
        
        calculate_btn = ttk.Button(button_frame, text="计算价格", command=self._calculate_prices, style="Accent.TButton")
        calculate_btn.pack(side=tk.LEFT, padx=5)
        
        save_btn = ttk.Button(button_frame, text="保存到数据库", command=self._save_to_database)
        save_btn.pack(side=tk.LEFT, padx=5)
        
        export_btn = ttk.Button(button_frame, text="导出结果", command=self._export_results)
        export_btn.pack(side=tk.RIGHT, padx=5)
        
        self._setup_styles()
    
    def _setup_styles(self):
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Arial", 10, "bold"))
        style.configure("Header.TLabel", font=("Arial", 12, "bold"))
        style.configure("Result.TLabel", font=("Arial", 10))
    
    def _create_cost_config_tab(self, parent):
        ttk.Label(parent, text="一级：商品本体（可增减）", style="Header.TLabel").pack(anchor=tk.W, pady=5)
        
        bases_container = ttk.Frame(parent)
        bases_container.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.bases_canvas = tk.Canvas(bases_container, height=PRICING_CONF['canvas_height'])
        bases_scrollbar = ttk.Scrollbar(bases_container, orient=tk.VERTICAL, command=self.bases_canvas.yview)
        self.bases_frame = ttk.Frame(self.bases_canvas)
        
        self.bases_frame.bind("<Configure>", lambda e: self.bases_canvas.configure(scrollregion=self.bases_canvas.bbox("all")))
        self.bases_canvas.create_window((0, 0), window=self.bases_frame, anchor="nw")
        self.bases_canvas.configure(yscrollcommand=bases_scrollbar.set)
        
        self.bases_canvas.bind("<MouseWheel>", lambda e: self.bases_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        self.bases_frame.bind("<MouseWheel>", lambda e: self.bases_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        self.bases_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        bases_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self._update_bases_list()
        
        base_btn_frame = ttk.Frame(parent)
        base_btn_frame.pack(fill=tk.X, pady=5)
        add_base_btn = ttk.Button(base_btn_frame, text="添加本体", command=self._add_base)
        add_base_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(parent, text="次级：附件配置（可增减）", style="Header.TLabel").pack(anchor=tk.W, pady=5, ipady=10)
        
        attachments_container = ttk.Frame(parent)
        attachments_container.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.attachments_canvas = tk.Canvas(attachments_container, height=PRICING_CONF['canvas_height'])
        attachments_scrollbar = ttk.Scrollbar(attachments_container, orient=tk.VERTICAL, command=self.attachments_canvas.yview)
        self.attachments_frame = ttk.Frame(self.attachments_canvas)
        
        self.attachments_frame.bind("<Configure>", lambda e: self.attachments_canvas.configure(scrollregion=self.attachments_canvas.bbox("all")))
        self.attachments_canvas.create_window((0, 0), window=self.attachments_frame, anchor="nw")
        self.attachments_canvas.configure(yscrollcommand=attachments_scrollbar.set)
        
        self.attachments_canvas.bind("<MouseWheel>", lambda e: self.attachments_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        self.attachments_frame.bind("<MouseWheel>", lambda e: self.attachments_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        self.attachments_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        attachments_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self._update_attachments_list()
        
        attachment_btn_frame = ttk.Frame(parent)
        attachment_btn_frame.pack(fill=tk.X, pady=5)
        add_attachment_btn = ttk.Button(attachment_btn_frame, text="添加附件", command=self._add_attachment)
        add_attachment_btn.pack(side=tk.LEFT, padx=5)
    
    def _update_bases_list(self):
        for widget in self.bases_frame.winfo_children():
            widget.destroy()
        
        for i, base in enumerate(self.bases):
            base_frame = ttk.Frame(self.bases_frame)
            base_frame.pack(fill=tk.X, pady=5)
            
            ttk.Label(base_frame, text="本体名称：").pack(side=tk.LEFT, padx=5)
            name_var = tk.StringVar(value=base["name"])
            name_entry = ttk.Entry(base_frame, textvariable=name_var, width=15)
            name_entry.pack(side=tk.LEFT, padx=5)
            
            ttk.Label(base_frame, text="成本：").pack(side=tk.LEFT, padx=5)
            cost_var = tk.DoubleVar(value=base["cost"])
            cost_entry = ttk.Entry(base_frame, textvariable=cost_var, width=10)
            cost_entry.pack(side=tk.LEFT, padx=5)
            ttk.Label(base_frame, text="元").pack(side=tk.LEFT, padx=5)
            
            delete_btn = ttk.Button(base_frame, text="删除", command=lambda idx=i: self._delete_base(idx))
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
            attachment_frame = ttk.Frame(self.attachments_frame)
            attachment_frame.pack(fill=tk.X, pady=5)
            
            ttk.Label(attachment_frame, text="附件名称：").pack(side=tk.LEFT, padx=5)
            name_var = tk.StringVar(value=attachment["name"])
            name_entry = ttk.Entry(attachment_frame, textvariable=name_var, width=15)
            name_entry.pack(side=tk.LEFT, padx=5)
            
            ttk.Label(attachment_frame, text="成本：").pack(side=tk.LEFT, padx=5)
            cost_var = tk.DoubleVar(value=attachment["cost"])
            cost_entry = ttk.Entry(attachment_frame, textvariable=cost_var, width=10)
            cost_entry.pack(side=tk.LEFT, padx=5)
            ttk.Label(attachment_frame, text="元").pack(side=tk.LEFT, padx=5)
            
            stackable_var = tk.BooleanVar(value=attachment.get("stackable", False))
            ttk.Checkbutton(attachment_frame, text="累加", variable=stackable_var).pack(side=tk.LEFT, padx=5)
            
            delete_btn = ttk.Button(attachment_frame, text="删除", command=lambda idx=i: self._delete_attachment(idx))
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
    
    def _create_sku_config_tab(self, parent):
        ttk.Label(parent, text="SKU组合配置", style="Header.TLabel").pack(anchor=tk.W, pady=5)
        
        self.sku_listbox = tk.Listbox(parent, height=PRICING_CONF['listbox_height'], width=PRICING_CONF['listbox_width'])
        self.sku_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self._update_sku_list()
        
        sku_btn_frame = ttk.Frame(parent)
        sku_btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(sku_btn_frame, text="添加SKU", command=self._add_sku).pack(side=tk.LEFT, padx=5)
        ttk.Button(sku_btn_frame, text="自动生成SKU", command=self._auto_generate_sku).pack(side=tk.LEFT, padx=5)
        ttk.Button(sku_btn_frame, text="编辑SKU", command=self._edit_sku).pack(side=tk.LEFT, padx=5)
        ttk.Button(sku_btn_frame, text="删除SKU", command=self._delete_sku).pack(side=tk.LEFT, padx=5)
    
    def _create_strategy_result_tab(self, parent):
        strategy_frame = ttk.LabelFrame(parent, text="定价策略", padding="10")
        strategy_frame.pack(fill=tk.X, pady=5)
        
        row1 = ttk.Frame(strategy_frame)
        row1.pack(fill=tk.X, pady=5)
        
        self.strategy_var = tk.StringVar(value=self.pricing_strategy)
        ttk.Radiobutton(row1, text="统一倍率", variable=self.strategy_var, value="multiplier").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(row1, text="统一利润率", variable=self.strategy_var, value="margin").pack(side=tk.LEFT, padx=10)
        
        row2 = ttk.Frame(strategy_frame)
        row2.pack(fill=tk.X, pady=5)
        
        ttk.Label(row2, text="定价基准SKU：").pack(side=tk.LEFT, padx=5)
        self.target_sku_var = tk.StringVar(value=self.target_sku)
        self.target_sku_combobox = ttk.Combobox(row2, textvariable=self.target_sku_var, width=12, state="readonly")
        self.target_sku_combobox.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(row2, text="目标售价：").pack(side=tk.LEFT, padx=5)
        self.max_price_var = tk.DoubleVar(value=self.max_price)
        ttk.Entry(row2, textvariable=self.max_price_var, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(row2, text="元").pack(side=tk.LEFT, padx=2)
        
        ttk.Label(row2, text="小数位：").pack(side=tk.LEFT, padx=5)
        self.rounding_var = tk.StringVar(value=str(self.rounding))
        rounding_combo = ttk.Combobox(row2, textvariable=self.rounding_var, width=5, state="readonly")
        rounding_combo['values'] = ['0', '1', '2']
        rounding_combo.pack(side=tk.LEFT, padx=5)
        
        self._update_target_sku_combobox()
        
        result_frame = ttk.LabelFrame(parent, text="计算结果", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        columns = ("sku_name", "cost", "price", "profit", "profit_rate")
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show="headings")
        
        self.result_tree.heading("sku_name", text="SKU名称")
        self.result_tree.heading("cost", text="成本（元）")
        self.result_tree.heading("price", text="售价（元）")
        self.result_tree.heading("profit", text="利润（元）")
        self.result_tree.heading("profit_rate", text="利润率（%）")
        
        self.result_tree.column("sku_name", width=150)
        self.result_tree.column("cost", width=100, anchor=tk.CENTER)
        self.result_tree.column("price", width=100, anchor=tk.CENTER)
        self.result_tree.column("profit", width=100, anchor=tk.CENTER)
        self.result_tree.column("profit_rate", width=100, anchor=tk.CENTER)
        
        self.result_tree.pack(fill=tk.BOTH, expand=True, pady=5)
        
        stats_frame = ttk.Frame(result_frame)
        stats_frame.pack(fill=tk.X, pady=5)
        
        self.total_cost_var = tk.StringVar(value="总生产成本：0.00 元")
        ttk.Label(stats_frame, textvariable=self.total_cost_var, style="Result.TLabel").pack(side=tk.LEFT, padx=10)
        
        self.average_profit_rate_var = tk.StringVar(value="平均利润率：0.00%")
        ttk.Label(stats_frame, textvariable=self.average_profit_rate_var, style="Result.TLabel").pack(side=tk.LEFT, padx=10)
    
    def _update_target_sku_combobox(self):
        sku_names = [sku["name"] for sku in self.sku_configs]
        self.target_sku_combobox['values'] = sku_names
        if self.target_sku not in sku_names and sku_names:
            self.target_sku = sku_names[0]
            self.target_sku_var.set(self.target_sku)
    
    def _update_sku_list(self):
        self.sku_listbox.delete(0, tk.END)
        for sku in self.sku_configs:
            attachments = " + ".join(sku["attachments"]) if sku["attachments"] else "无附件"
            display_text = f"{sku['name']}: {sku['base_name']} + {attachments}"
            self.sku_listbox.insert(tk.END, display_text)
    
    def _add_sku(self):
        add_window = tk.Toplevel(self.root)
        add_window.title("添加SKU")
        add_window.geometry("400x450")
        add_window.resizable(False, False)
        
        ttk.Label(add_window, text="SKU名称：").pack(pady=5, padx=10, anchor=tk.W)
        sku_name_var = tk.StringVar()
        ttk.Entry(add_window, textvariable=sku_name_var, width=30).pack(pady=5, padx=10)
        
        ttk.Label(add_window, text="选择本体：").pack(pady=5, padx=10, anchor=tk.W)
        base_var = tk.StringVar(value=self.bases[0]["name"] if self.bases else "")
        base_combobox = ttk.Combobox(add_window, textvariable=base_var, width=28, state="readonly")
        base_combobox['values'] = [base["name"] for base in self.bases]
        base_combobox.pack(pady=5, padx=10)
        
        ttk.Label(add_window, text="选择附件：").pack(pady=5, padx=10, anchor=tk.W)
        
        attachment_vars = {}
        for attachment in self.attachments:
            var = tk.BooleanVar()
            cb = ttk.Checkbutton(add_window, text=f"{attachment['name']} ({attachment['cost']}元)", variable=var)
            cb.pack(anchor=tk.W, padx=20)
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
        
        ttk.Button(add_window, text="添加", command=do_add).pack(pady=20)
    
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
            
            if stackable:
                from itertools import combinations
                for r in range(1, len(stackable) + 1):
                    for combo in combinations(stackable, r):
                        self.sku_configs.append({
                            "name": f"SKU{sku_index}",
                            "base_name": base["name"],
                            "attachments": [a["name"] for a in combo]
                        })
                        sku_index += 1
                
                for attachment in non_stackable:
                    for r in range(1, len(stackable) + 1):
                        for combo in combinations(stackable, r):
                            self.sku_configs.append({
                                "name": f"SKU{sku_index}",
                                "base_name": base["name"],
                                "attachments": [attachment["name"]] + [a["name"] for a in combo]
                            })
                            sku_index += 1
        
        self._update_sku_list()
        self._update_target_sku_combobox()
        show_info(self.root, "成功", f"已自动生成 {len(self.sku_configs)} 个SKU")
    
    def _edit_sku(self):
        selection = self.sku_listbox.curselection()
        if not selection:
            show_warning(self.root, "警告", "请先选择要编辑的SKU")
            return
        
        index = selection[0]
        sku = self.sku_configs[index]
        
        edit_window = tk.Toplevel(self.root)
        edit_window.title("编辑SKU")
        edit_window.geometry("400x450")
        edit_window.resizable(False, False)
        
        ttk.Label(edit_window, text="SKU名称：").pack(pady=5, padx=10, anchor=tk.W)
        sku_name_var = tk.StringVar(value=sku["name"])
        ttk.Entry(edit_window, textvariable=sku_name_var, width=30).pack(pady=5, padx=10)
        
        ttk.Label(edit_window, text="选择本体：").pack(pady=5, padx=10, anchor=tk.W)
        base_var = tk.StringVar(value=sku["base_name"])
        base_combobox = ttk.Combobox(edit_window, textvariable=base_var, width=28, state="readonly")
        base_combobox['values'] = [base["name"] for base in self.bases]
        base_combobox.pack(pady=5, padx=10)
        
        ttk.Label(edit_window, text="选择附件：").pack(pady=5, padx=10, anchor=tk.W)
        
        attachment_vars = {}
        for attachment in self.attachments:
            var = tk.BooleanVar(value=attachment['name'] in sku['attachments'])
            cb = ttk.Checkbutton(edit_window, text=f"{attachment['name']} ({attachment['cost']}元)", variable=var)
            cb.pack(anchor=tk.W, padx=20)
            attachment_vars[attachment['name']] = var
        
        def do_edit():
            self.sku_configs[index] = {
                "name": sku_name_var.get(),
                "base_name": base_var.get(),
                "attachments": [name for name, var in attachment_vars.items() if var.get()]
            }
            self._update_sku_list()
            self._update_target_sku_combobox()
            edit_window.destroy()
        
        ttk.Button(edit_window, text="保存", command=do_edit).pack(pady=20)
    
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
        max_price = self.max_price_var.get()
        
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
            
            self.result_tree.insert("", "end", values=(
                sku["name"],
                f"{cost:.2f}",
                f"{price:.2f}",
                f"{profit:.2f}",
                f"{profit_rate:.2f}"
            ))
            
            total_cost += cost
            total_profit += profit
        
        avg_profit_rate = (total_profit / total_cost) * 100 if total_cost > 0 else 0
        self.total_cost_var.set(f"总生产成本：{total_cost:.2f} 元")
        self.average_profit_rate_var.set(f"平均利润率：{avg_profit_rate:.2f}%")
    
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
            from utils.database import db
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
            from utils.database import db
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
    root = tk.Tk()
    app = PricingToolGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
