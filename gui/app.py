#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主应用模块
"""

import os
import sys
import tkinter as tk
from tkinter import ttk
import multiprocessing

# 导入模块化组件
from gui.utils import hide_console, ScrolledText
from config import GUI_CONF
from gui.logging import GUILogger
from gui.queue import QueueManager
from gui.menu import ContextMenuManager
from gui.commands import ContextMenuCommands
from gui.dnd import DynamicDropOverlay, HAS_DND

# 尝试导入 tkinterweb 和 markdown
try:
    from tkinterweb import HtmlFrame
    HAS_TKINTERWEB = True
except ImportError:
    HAS_TKINTERWEB = False

try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False

try:
    from utils.updater import check_for_updates
    from utils.version import __version__
    HAS_UPDATER = True
except ImportError:
    HAS_UPDATER = False


class AlibabaScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(GUI_CONF['window_title'])
        self.root.geometry(GUI_CONF['window_geometry'])
        self.root.resizable(GUI_CONF['window_resizable'], GUI_CONF['window_resizable'])
        
        self.easter_egg_counter = 0
        self.alt_press_counter = 0
        self.easter_egg_activated = False
        self.db_tab_visible = False
        self._is_gui_mode = True
        self._queue_shortcuts_bound = False
        
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        self.queue_tab = tk.Frame(self.notebook)
        self.notebook.add(self.queue_tab, text="处理队列")
        
        self.help_tab = tk.Frame(self.notebook)
        self.notebook.add(self.help_tab, text="使用说明")
        
        self.db_tab = tk.Frame(self.notebook)
        
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self.last_tab_index = -1
        
        self._init_db_tab()
        
        self.button_frame = tk.Frame(self.queue_tab)
        self.button_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.add_file_btn = tk.Button(self.button_frame, text="添加文件 (A)", command=self.add_file, width=12)
        self.add_file_btn.pack(side=tk.LEFT, padx=3)
        
        self.add_dir_btn = tk.Button(self.button_frame, text="添加目录 (D)", command=self.add_directory, width=12)
        self.add_dir_btn.pack(side=tk.LEFT, padx=3)
        
        self.remove_file_btn = tk.Button(self.button_frame, text="移除文件 (Del)", command=self.remove_file, width=12)
        self.remove_file_btn.pack(side=tk.LEFT, padx=3)
        
        self.clear_queue_btn = tk.Button(self.button_frame, text="清空队列", command=self.clear_queue, width=12)
        self.clear_queue_btn.pack(side=tk.LEFT, padx=3)
        
        self.pricing_btn = tk.Button(self.button_frame, text="价格计算", command=self.open_pricing_tool, width=12)
        self.pricing_btn.pack(side=tk.LEFT, padx=3)
        
        self.pause_btn = tk.Button(self.button_frame, text="暂停 (P)", command=self.pause, width=12, bg="#FF9800", fg="white", state=tk.DISABLED)
        self.pause_btn.pack(side=tk.RIGHT, padx=3)
        
        self.execute_btn = tk.Button(self.button_frame, text="执行 (Enter)", command=self.execute, width=12, bg="#4CAF50", fg="white")
        self.execute_btn.pack(side=tk.RIGHT, padx=3)
        
        self.output_frame = tk.Frame(self.queue_tab)
        
        self.output_label = tk.Label(self.output_frame, text="输出路径:")
        self.output_label.pack(side=tk.LEFT, padx=5)
        
        self.output_path_var = tk.StringVar()
        self.output_path_entry = tk.Entry(self.output_frame, textvariable=self.output_path_var, width=60)
        self.output_path_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.browse_btn = tk.Button(self.output_frame, text="浏览...", command=self.browse_output_path, width=10)
        self.browse_btn.pack(side=tk.LEFT, padx=5)
        
        self.root.bind('<Alt_L>', self._on_alt_press)
        self.root.bind('<Alt_R>', self._on_alt_press)
        self.root.bind('<KeyRelease-Alt_L>', self._on_alt_release)
        self.root.bind('<KeyRelease-Alt_R>', self._on_alt_release)
        
        self._bind_queue_shortcuts()
        
        # 创建队列和日志框架
        self.content_frame = tk.Frame(self.queue_tab)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 队列表格
        self.queue_frame = tk.LabelFrame(self.content_frame, text="处理队列")
        self.queue_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP, pady=(0, 10))
        
        self.queue_tree = ttk.Treeview(self.queue_frame, columns=("index", "status", "name", "shop_id", "date", "output_path"), show="headings")
        
        self.queue_tree.heading("index", text="序号")
        self.queue_tree.heading("status", text="状态", command=lambda: self.sort_treeview("status"))
        self.queue_tree.heading("name", text="文件名", command=lambda: self.sort_treeview("name"))
        self.queue_tree.heading("shop_id", text="DSID", command=lambda: self.sort_treeview("shop_id"))
        self.queue_tree.heading("date", text="修改日期", command=lambda: self.sort_treeview("date"))
        self.queue_tree.heading("output_path", text="输出路径", command=lambda: self.sort_treeview("output_path"))
        
        self.queue_tree.column("index", width=30, anchor=tk.CENTER)
        self.queue_tree.column("status", width=50, anchor=tk.CENTER)
        self.queue_tree.column("name", width=250, anchor=tk.W)
        self.queue_tree.column("shop_id", width=80, anchor=tk.CENTER)
        self.queue_tree.column("date", width=120, anchor=tk.CENTER)
        self.queue_tree.column("output_path", width=250, anchor=tk.W)
        
        # 添加滚动条
        self.queue_scrollbar = ttk.Scrollbar(self.queue_frame, orient=tk.VERTICAL, command=self.queue_tree.yview)
        self.queue_tree.configure(yscroll=self.queue_scrollbar.set)
        
        # 布局
        self.queue_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.queue_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # 绑定事件
        self.queue_tree.bind('<Double-1>', self.on_treeview_double_click)
        
        # 日志窗口
        self.log_frame = tk.LabelFrame(self.content_frame, text="日志输出")
        self.log_frame.pack(fill=tk.BOTH, expand=True, side=tk.BOTTOM)
        
        # 获取可用字体
        available_font = self._get_available_font()
        
        self.log_text = ScrolledText(self.log_frame, width=100, height=15, state=tk.DISABLED, 
                                     bg="black", fg="white", 
                                     font=(available_font, GUI_CONF.get('font_size', 10)))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 初始化模块化组件
        self._init_modules()
        
        self._init_drop_zone()
        
        self.load_output_path()
        
        self.help_frame = None
        self.help_text = None
        
        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)
        
        self.log("1688详情页资源采集工具 - GUI 版本")
        self.log("-----------------------------------")
        self.log("使用说明：")
        self.log("1. 添加文件/目录 或 拖放HTML文件到窗口")
        self.log("2. 点击 '执行' 开始处理，'暂停' 暂停处理")
        self.log("3. 选中文件后可移除或清空队列")
        self.log("4. 日志窗口显示执行过程和结果")
        self.log("-----------------------------------")
    
    def _init_db_tab(self):
        """初始化数据库选项卡"""
        self.db_access_confirmed = False
        
        available_font = self._get_available_font()
        font_size = GUI_CONF.get('font_size', 10)
        
        self.db_welcome_frame = tk.Frame(self.db_tab)
        self.db_welcome_frame.pack(fill=tk.BOTH, expand=True)
        
        welcome_label = tk.Label(
            self.db_welcome_frame, 
            text="数据库管理\n\n此功能允许浏览和删除商品数据记录。\n\n点击下方按钮进入数据库管理界面。",
            justify=tk.CENTER,
            font=(available_font, font_size + 2)
        )
        welcome_label.pack(expand=True)
        
        enter_btn = tk.Button(
            self.db_welcome_frame, 
            text="进入数据库管理", 
            command=self._confirm_db_access,
            width=20,
            height=2
        )
        enter_btn.pack(pady=20)
        
        self.db_content_frame = tk.Frame(self.db_tab)
        
        self.db_tree_frame = tk.Frame(self.db_content_frame)
        self.db_tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        db_columns = ("product_id", "shop_product_id", "title", "cost_prices", "selling_prices", "resource_counts", "output_path", "status", "created_at")
        self.db_tree = ttk.Treeview(self.db_tree_frame, columns=db_columns, show="headings", selectmode="browse")
        
        self.db_tree.heading("product_id", text="商品ID")
        self.db_tree.heading("shop_product_id", text="DSID")
        self.db_tree.heading("title", text="标题")
        self.db_tree.heading("cost_prices", text="采集成本")
        self.db_tree.heading("selling_prices", text="价格设定")
        self.db_tree.heading("resource_counts", text="资源计数")
        self.db_tree.heading("output_path", text="输出路径")
        self.db_tree.heading("status", text="状态")
        self.db_tree.heading("created_at", text="创建时间")
        
        self.db_tree.column("product_id", width=100, anchor=tk.CENTER)
        self.db_tree.column("shop_product_id", width=80, anchor=tk.CENTER)
        self.db_tree.column("title", width=120, anchor=tk.W)
        self.db_tree.column("cost_prices", width=80, anchor=tk.CENTER)
        self.db_tree.column("selling_prices", width=80, anchor=tk.CENTER)
        self.db_tree.column("resource_counts", width=80, anchor=tk.CENTER)
        self.db_tree.column("output_path", width=150, anchor=tk.W)
        self.db_tree.column("status", width=60, anchor=tk.CENTER)
        self.db_tree.column("created_at", width=130, anchor=tk.CENTER)
        
        db_scrollbar = ttk.Scrollbar(self.db_tree_frame, orient=tk.VERTICAL, command=self.db_tree.yview)
        self.db_tree.configure(yscrollcommand=db_scrollbar.set)
        
        self.db_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        db_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.db_tree.bind('<Double-Button-1>', self._db_tree_double_click)
        
        self.db_btn_frame = tk.Frame(self.db_content_frame)
        self.db_btn_frame.pack(fill=tk.X, pady=5)
        
        self.db_search_frame = tk.Frame(self.db_btn_frame)
        self.db_search_frame.pack(side=tk.LEFT, padx=5)
        
        self.db_search_var = tk.StringVar()
        self.db_search_var.trace_add("write", self._validate_search_input)
        
        tk.Label(self.db_search_frame, text="搜索:").pack(side=tk.LEFT)
        
        self.db_search_entry = tk.Entry(self.db_search_frame, textvariable=self.db_search_var, width=15)
        self.db_search_entry.pack(side=tk.LEFT, padx=2)
        self.db_search_entry.bind('<Return>', lambda e: self._search_db_records())
        
        self.db_search_btn = tk.Button(self.db_search_frame, text="搜索", command=self._search_db_records, width=6)
        self.db_search_btn.pack(side=tk.LEFT, padx=2)
        
        self.db_refresh_btn = tk.Button(self.db_btn_frame, text="刷新", command=self._refresh_db_data, width=8)
        self.db_refresh_btn.pack(side=tk.LEFT, padx=5)
        
        self.db_price_btn = tk.Button(self.db_btn_frame, text="价格计算", command=self._open_pricing_for_selected, width=8)
        self.db_price_btn.pack(side=tk.LEFT, padx=5)
        
        self.db_delete_btn = tk.Button(self.db_btn_frame, text="删除选中", command=self._delete_db_record, width=8)
        self.db_delete_btn.pack(side=tk.LEFT, padx=5)
        
        self.db_close_btn = tk.Button(self.db_btn_frame, text="关闭数据库", command=self._close_db_tab, width=10)
        self.db_close_btn.pack(side=tk.RIGHT, padx=5)
        
        self.db_status_label = tk.Label(self.db_btn_frame, text="")
        self.db_status_label.pack(side=tk.RIGHT, padx=10)
    
    def _confirm_db_access(self):
        """确认数据库访问"""
        confirm = self.ask_yes_no("确认", "确定要进入数据库管理界面吗？\n\n请注意：删除操作不可撤销！")
        if confirm:
            self.db_access_confirmed = True
            self.db_welcome_frame.pack_forget()
            self.db_content_frame.pack(fill=tk.BOTH, expand=True)
            self._refresh_db_data()
    
    def _close_db_tab(self):
        """关闭数据库选项卡，返回处理队列"""
        self.db_content_frame.pack_forget()
        self.db_welcome_frame.pack(fill=tk.BOTH, expand=True)
        self.db_access_confirmed = False
        self.notebook.select(0)
    
    def _refresh_db_data(self):
        """刷新数据库数据"""
        for item in self.db_tree.get_children():
            self.db_tree.delete(item)
        
        try:
            from utils.database import db
            import json
            products = db.get_all_products()
            
            for product in products:
                output_path = product.get('output_path', '') or ''
                if len(output_path) > 30:
                    output_path = '...' + output_path[-27:]
                
                title = product.get('title', '') or ''
                if len(title) > 15:
                    title = title[:15] + '...'
                
                cost_prices_str = ''
                cost_prices = product.get('cost_prices')
                if cost_prices:
                    try:
                        cost_data = json.loads(cost_prices)
                        cost_prices_str = f"{len(cost_data)}条"
                    except:
                        pass
                
                selling_prices_str = ''
                selling_prices = product.get('selling_prices')
                if selling_prices:
                    try:
                        selling_data = json.loads(selling_prices)
                        selling_prices_str = f"{len(selling_data)}条"
                    except:
                        pass
                
                product_id = product.get('product_id', '')
                resource_counts = db.count_resources(product_id)
                resource_counts_str = f"主{resource_counts['main_images']}/色{resource_counts['color_images']}/详{resource_counts['detail_images']}/视{resource_counts['videos']}"
                
                self.db_tree.insert("", "end", values=(
                    product_id,
                    product.get('shop_product_id', ''),
                    title,
                    cost_prices_str,
                    selling_prices_str,
                    resource_counts_str,
                    output_path,
                    product.get('status', ''),
                    product.get('created_at', '')
                ))
            
            self.db_status_label.config(text=f"共 {len(products)} 条记录")
        except Exception as e:
            self.log(f"读取数据库失败: {e}", "error")
            self.db_status_label.config(text="读取失败")
    
    def _search_db_records(self):
        """搜索数据库记录 - 自动匹配商品ID和DSID"""
        search_term = self.db_search_var.get().strip()
        
        if not search_term:
            self._refresh_db_data()
            return
        
        for item in self.db_tree.get_children():
            self.db_tree.delete(item)
        
        try:
            from utils.database import db
            import json
            
            products = db.search_products_by_id(search_term)
            
            for product in products:
                output_path = product.get('output_path', '') or ''
                if len(output_path) > 30:
                    output_path = '...' + output_path[-27:]
                
                title = product.get('title', '') or ''
                if len(title) > 15:
                    title = title[:15] + '...'
                
                cost_prices_str = ''
                cost_prices = product.get('cost_prices')
                if cost_prices:
                    try:
                        cost_data = json.loads(cost_prices)
                        cost_prices_str = f"{len(cost_data)}条"
                    except:
                        pass
                
                selling_prices_str = ''
                selling_prices = product.get('selling_prices')
                if selling_prices:
                    try:
                        selling_data = json.loads(selling_prices)
                        selling_prices_str = f"{len(selling_data)}条"
                    except:
                        pass
                
                product_id = product.get('product_id', '')
                resource_counts = db.count_resources(product_id)
                resource_counts_str = f"主{resource_counts['main_images']}/色{resource_counts['color_images']}/详{resource_counts['detail_images']}/视{resource_counts['videos']}"
                
                self.db_tree.insert("", "end", values=(
                    product_id,
                    product.get('shop_product_id', ''),
                    title,
                    cost_prices_str,
                    selling_prices_str,
                    resource_counts_str,
                    output_path,
                    product.get('status', ''),
                    product.get('created_at', '')
                ))
            
            self.db_status_label.config(text=f"搜索结果: {len(products)} 条")
            
        except Exception as e:
            self.log(f"搜索失败: {e}", "error")
            self.db_status_label.config(text="搜索失败")
    
    def _validate_search_input(self, *args):
        """验证搜索输入，只允许数字"""
        current = self.db_search_var.get()
        if current and not current.isdigit():
            self.db_search_var.set(''.join(filter(str.isdigit, current)))
    
    def _open_product_page(self, product_id):
        """用浏览器打开商品页面"""
        import webbrowser
        from utils.database import db
        
        product = db.get_product(product_id)
        platform = product.get('platform', 'alibaba') if product else 'alibaba'
        
        if platform == 'jd':
            url = f"https://item.jd.com/{product_id}.html"
        else:
            url = f"https://detail.1688.com/offer/{product_id}.html"
        
        webbrowser.open(url)
        self.log(f"已打开商品页面: {url}")
    
    def _open_shop_page(self, product_id):
        """用浏览器打开店铺页面"""
        import webbrowser
        from utils.database import db
        
        product = db.get_product(product_id)
        platform = product.get('platform', 'alibaba') if product else 'alibaba'
        shop_product_id = product.get('shop_product_id', '') if product else ''
        
        if platform == 'jd':
            if shop_product_id:
                url = f"https://mall.jd.com/index-{shop_product_id}.html"
            else:
                self.show_info("提示", "该商品没有店铺ID信息")
                return
        else:
            if shop_product_id:
                url = f"https://{shop_product_id}.1688.com"
            else:
                self.show_info("提示", "该商品没有店铺ID信息")
                return
        
        webbrowser.open(url)
        self.log(f"已打开店铺页面: {url}")
    
    def _db_tree_double_click(self, event):
        """双击数据库记录"""
        region = self.db_tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        
        column = self.db_tree.identify_column(event.x)
        selected = self.db_tree.selection()
        if not selected:
            return
        
        item = selected[0]
        values = self.db_tree.item(item, 'values')
        product_id = values[0]
        
        if column == "#1":
            self._open_product_page(product_id)
        elif column == "#5":
            self._show_selling_prices(product_id)
        elif column == "#6":
            self._show_resources(product_id)
        else:
            self._open_pricing_for_product(product_id)
    
    def _show_selling_prices(self, product_id):
        """显示价格设定结果"""
        try:
            from utils.database import db
            import json
            
            product = db.get_product(product_id)
            if not product:
                self.show_info("提示", f"未找到商品：{product_id}")
                return
            
            selling_prices_str = product.get('selling_prices')
            if not selling_prices_str:
                self.show_info("提示", f"商品 {product_id} 没有价格设定数据")
                return
            
            selling_prices = json.loads(selling_prices_str)
            
            result_window = tk.Toplevel(self.root)
            result_window.title(f"价格设定 - {product_id}")
            result_window.geometry("500x400")
            
            tree_frame = ttk.Frame(result_window)
            tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            columns = ("sku_name", "price")
            tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
            tree.heading("sku_name", text="SKU名称")
            tree.heading("price", text="售价（元）")
            tree.column("sku_name", width=300)
            tree.column("price", width=100, anchor=tk.CENTER)
            
            scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            for item in selling_prices:
                if isinstance(item, dict):
                    sku_name = item.get("sku_name", "")
                    price = item.get("price", "")
                else:
                    sku_name = item[0] if len(item) > 0 else ""
                    price = item[1] if len(item) > 1 else ""
                tree.insert("", "end", values=(sku_name, price))
            
            def copy_price(event):
                selected = tree.selection()
                if selected:
                    item = selected[0]
                    values = tree.item(item, 'values')
                    if values and len(values) > 1:
                        price = values[1]
                        result_window.clipboard_clear()
                        result_window.clipboard_append(str(price))
                        self.log(f"已复制价格: {price}")
            
            def show_copy_menu(event):
                menu = tk.Menu(result_window, tearoff=0)
                menu.add_command(label="复制价格", command=lambda: copy_price(None))
                menu.add_command(label="复制SKU名称", command=lambda: copy_sku(None))
                menu.post(event.x_root, event.y_root)
            
            def copy_sku(event):
                selected = tree.selection()
                if selected:
                    item = selected[0]
                    values = tree.item(item, 'values')
                    if values and len(values) > 0:
                        sku_name = values[0]
                        result_window.clipboard_clear()
                        result_window.clipboard_append(str(sku_name))
                        self.log(f"已复制SKU名称: {sku_name}")
            
            def on_ctrl_c(event):
                """Ctrl+C快捷键复制价格"""
                copy_price(event)
                return "break"
            
            tree.bind('<Double-Button-1>', copy_price)
            tree.bind('<Button-3>', show_copy_menu)
            tree.bind('<Control-c>', on_ctrl_c)
            result_window.bind('<Control-c>', on_ctrl_c)
            
        except Exception as e:
            self.show_info("错误", f"读取价格设定失败: {e}")
    
    def _show_resources(self, product_id):
        """显示商品资源URL列表"""
        try:
            from utils.database import db
            
            resources = db.get_resources_by_type(product_id)
            
            if not any(resources.values()):
                self.show_info("提示", f"商品 {product_id} 没有资源数据")
                return
            
            result_window = tk.Toplevel(self.root)
            result_window.title(f"资源列表 - {product_id}")
            result_window.geometry("700x500")
            
            notebook = ttk.Notebook(result_window)
            notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            type_names = {
                'main_images': '主图',
                'color_images': '色卡图',
                'detail_images': '详情图',
                'videos': '视频'
            }
            
            for res_type, res_list in resources.items():
                if not res_list:
                    continue
                
                tab = ttk.Frame(notebook)
                notebook.add(tab, text=f"{type_names.get(res_type, res_type)} ({len(res_list)})")
                
                tree_frame = ttk.Frame(tab)
                tree_frame.pack(fill=tk.BOTH, expand=True)
                
                columns = ("name", "url", "downloaded")
                tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
                tree.heading("name", text="名称")
                tree.heading("url", text="URL")
                tree.heading("downloaded", text="已下载")
                tree.column("name", width=150)
                tree.column("url", width=450)
                tree.column("downloaded", width=60, anchor=tk.CENTER)
                
                scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
                tree.configure(yscrollcommand=scrollbar.set)
                
                tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                for res in res_list:
                    name = res.get('resource_name', '')
                    url = res.get('resource_url', '')
                    downloaded = "是" if res.get('downloaded') else "否"
                    tree.insert("", "end", values=(name, url, downloaded))
                
                def copy_url(event, tree_widget=tree, window=result_window):
                    selected = tree_widget.selection()
                    if selected:
                        item = selected[0]
                        values = tree_widget.item(item, 'values')
                        if values and len(values) > 1:
                            url = values[1]
                            window.clipboard_clear()
                            window.clipboard_append(str(url))
                            self.log(f"已复制URL: {url[:50]}...")
                
                tree.bind('<Double-Button-1>', copy_url)
            
        except Exception as e:
            self.show_info("错误", f"读取资源数据失败: {e}")
    
    def _open_pricing_for_product(self, product_id):
        """打开指定商品的价格计算工具"""
        try:
            from gui.pricing_gui import PricingToolGUI
            
            pricing_window = tk.Toplevel(self.root)
            pricing_window.title(f"商品定价计算工具 - {product_id}")
            pricing_window.geometry("1000x700")
            
            pricing_app = PricingToolGUI(pricing_window, product_id)
            
        except ImportError as e:
            self.show_info("错误", f"无法加载价格计算工具：{e}")
        except Exception as e:
            self.show_info("错误", f"打开价格计算工具失败：{e}")
    
    def _open_pricing_for_selected(self):
        """打开选中商品的价格计算工具"""
        selected = self.db_tree.selection()
        if not selected:
            self.show_info("提示", "请先选择要查看的商品")
            return
        
        item = selected[0]
        values = self.db_tree.item(item, 'values')
        product_id = values[0]
        self._open_pricing_for_product(product_id)
    
    def _delete_db_record(self):
        """删除选中的数据库记录"""
        selected = self.db_tree.selection()
        if not selected:
            self.show_info("提示", "请先选择要删除的记录")
            return
        
        item = selected[0]
        values = self.db_tree.item(item, 'values')
        product_id = values[0]
        
        confirm = self.ask_yes_no("确认删除", f"确定要删除商品ID为 {product_id} 的记录吗？\n\n此操作不可撤销！")
        if not confirm:
            return
        
        confirm2 = self.ask_yes_no("二次确认", f"再次确认：删除商品ID {product_id}？")
        if not confirm2:
            return
        
        try:
            from utils.database import db
            if db.delete_product(product_id):
                self.db_tree.delete(item)
                self.log(f"已删除商品记录: {product_id}")
                self._refresh_db_data()
            else:
                self.show_info("错误", "删除失败，记录可能不存在")
        except Exception as e:
            self.log(f"删除记录失败: {e}", "error")
    
    def _init_drop_zone(self):
        """初始化拖放覆盖层"""
        if HAS_DND:
            self.drop_overlay = DynamicDropOverlay(
                self.root,
                self.main_frame,
                on_drop_callback=self._on_files_dropped
            )
        else:
            self.drop_overlay = None
    
    def _on_files_dropped(self, files):
        """处理拖放的文件
        
        Args:
            files: 文件路径列表
        """
        added_count = 0
        for file_path in files:
            if file_path not in self.queue_manager.file_queue:
                self.queue_manager.file_queue.append(file_path)
                self.queue_manager.file_status[file_path] = "pending"
                added_count += 1
        
        if added_count > 0:
            self.queue_manager.update_queue_list()
            self.log(f"通过拖放添加了 {added_count} 个HTML文件", "success")
    
    def _init_modules(self):
        """初始化模块化组件"""
        # 初始化日志模块
        self.logger = GUILogger(self.log_text)
        
        # 初始化队列管理器
        self.queue_manager = QueueManager(self)
        
        # 初始化上下文菜单命令
        self.context_menu_commands = ContextMenuCommands(self)
        
        # 初始化上下文菜单管理器
        self.context_menu_manager = ContextMenuManager(self.root, self)
        
        # 绑定右键菜单
        self.queue_tree.bind('<Button-3>', self.context_menu_manager.show_context_menu)
        
        # 队列管理属性代理
        self.file_queue = self.queue_manager.file_queue
        self.file_status = self.queue_manager.file_status
    
    def log(self, message, message_type="info"):
        """添加日志信息到日志窗口
        
        Args:
            message: 日志消息
            message_type: 消息类型，可选值：info, success, warning, error, input
        """
        self.logger.log(message, message_type)
    
    def show_info(self, title, message):
        """显示信息提示框，在 GUI 界面居中弹出"""
        # 创建 Toplevel 窗口
        top = tk.Toplevel(self.root)
        top.title(title)
        top.transient(self.root)  # 设置为主窗口的临时窗口
        top.grab_set()  # 模态窗口，阻止与主窗口交互
        
        # 设置窗口大小
        width = 300
        height = 150
        
        # 获取主窗口的位置
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()
        
        # 计算提示框的位置，使其在主窗口居中
        x = root_x + (root_width - width) // 2
        y = root_y + (root_height - height) // 2
        
        # 设置窗口位置
        top.geometry(f"{width}x{height}+{x}+{y}")
        
        # 添加消息标签
        label = tk.Label(top, text=message, padx=20, pady=20)
        label.pack(fill=tk.BOTH, expand=True)
        
        # 添加确定按钮
        button = tk.Button(top, text="确定", command=top.destroy, width=10)
        button.pack(pady=10)
        
        # 设置按钮为默认焦点
        button.focus_set()
        top.bind('<Return>', lambda event: top.destroy())
    
    def ask_yes_no(self, title, message):
        """显示确认对话框，在 GUI 界面居中弹出，返回 True 或 False"""
        # 创建结果变量
        result = tk.BooleanVar()
        result.set(False)
        
        # 创建 Toplevel 窗口
        top = tk.Toplevel(self.root)
        top.title(title)
        top.transient(self.root)  # 设置为主窗口的临时窗口
        top.grab_set()  # 模态窗口，阻止与主窗口交互
        
        # 设置窗口大小
        width = 350
        height = 180
        
        # 获取主窗口的位置
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()
        
        # 计算提示框的位置，使其在主窗口居中
        x = root_x + (root_width - width) // 2
        y = root_y + (root_height - height) // 2
        
        # 设置窗口位置
        top.geometry(f"{width}x{height}+{x}+{y}")
        
        # 添加消息标签
        label = tk.Label(top, text=message, padx=20, pady=20)
        label.pack(fill=tk.BOTH, expand=True)
        
        # 创建按钮框架
        button_frame = tk.Frame(top)
        button_frame.pack(pady=10)
        
        # 添加是按钮
        yes_button = tk.Button(button_frame, text="是", command=lambda: [result.set(True), top.destroy()], width=10)
        yes_button.pack(side=tk.LEFT, padx=10)
        
        # 添加否按钮
        no_button = tk.Button(button_frame, text="否", command=lambda: [result.set(False), top.destroy()], width=10)
        no_button.pack(side=tk.RIGHT, padx=10)
        
        # 设置按钮为默认焦点
        no_button.focus_set()
        top.bind('<Return>', lambda event: [result.set(False), top.destroy()])
        top.bind('<Escape>', lambda event: [result.set(False), top.destroy()])
        
        # 等待窗口关闭
        self.root.wait_window(top)
        
        return result.get()
    
    def _on_alt_press(self, event):
        """Alt键按下事件处理"""
        if not self.easter_egg_activated:
            self.alt_press_counter += 1
            if self.alt_press_counter >= 8:
                self._activate_easter_egg()
    
    def _on_alt_release(self, event):
        """Alt键释放事件处理"""
        pass
    
    def _bind_queue_shortcuts(self):
        """绑定处理队列快捷键"""
        if not hasattr(self, '_queue_shortcuts_bound') or not self._queue_shortcuts_bound:
            self.root.bind('<a>', lambda event: self.add_file())
            self.root.bind('<A>', lambda event: self.add_file())
            self.root.bind('<d>', lambda event: self.add_directory())
            self.root.bind('<D>', lambda event: self.add_directory())
            self.root.bind('<Delete>', lambda event: self.remove_file())
            self.root.bind('<p>', lambda event: self.pause())
            self.root.bind('<P>', lambda event: self.pause())
            self.root.bind('<Return>', lambda event: self.execute())
            self.root.bind('<Pause>', lambda event: self.pause())
            self._queue_shortcuts_bound = True
    
    def _unbind_queue_shortcuts(self):
        """解绑处理队列快捷键"""
        if hasattr(self, '_queue_shortcuts_bound') and self._queue_shortcuts_bound:
            self.root.unbind('<a>')
            self.root.unbind('<A>')
            self.root.unbind('<d>')
            self.root.unbind('<D>')
            self.root.unbind('<Delete>')
            self.root.unbind('<p>')
            self.root.unbind('<P>')
            self.root.unbind('<Return>')
            self.root.unbind('<Pause>')
            self._queue_shortcuts_bound = False
    
    def _activate_easter_egg(self, show_message=True):
        """激活彩蛋 - 显示输出路径区域
        
        Args:
            show_message: 是否显示彩蛋激活消息
        """
        if not self.easter_egg_activated:
            self.easter_egg_activated = True
            self.output_frame.pack(fill=tk.X, pady=(0, 5), before=self.content_frame)
            if show_message:
                self.log("恭喜你发现了彩蛋！连续按8次Alt键激活了输出路径设置！", "success")
    
    def browse_output_path(self):
        """浏览并选择输出路径"""
        from tkinter import filedialog
        current_path = self.output_path_var.get()
        if not current_path or not os.path.exists(current_path):
            current_path = os.getcwd()
        
        selected_path = filedialog.askdirectory(
            title="选择输出路径",
            initialdir=current_path
        )
        
        if selected_path:
            # 验证路径有效性
            if self.validate_output_path(selected_path):
                self.output_path_var.set(selected_path)
                self.save_output_path(selected_path)
                self.log(f"输出路径已设置: {selected_path}")
            else:
                self.show_info("错误", "无效的输出路径或无写入权限")
    
    def validate_output_path(self, path):
        """验证输出路径有效性
        
        Args:
            path: 要验证的路径
            
        Returns:
            bool: 路径有效返回True，否则返回False
        """
        if not path:
            return False
        
        try:
            # 检查路径是否存在，不存在则尝试创建
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
            
            # 检查写入权限
            test_file = os.path.join(path, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            
            return True
        except Exception as e:
            self.log(f"路径验证失败: {e}", "error")
            return False
    
    def save_output_path(self, path):
        """保存输出路径到配置文件
        
        Args:
            path: 要保存的路径
        """
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.output_path')
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(path)
        except Exception as e:
            self.log(f"保存输出路径失败: {e}", "error")
    
    def load_output_path(self):
        """加载保存的输出路径"""
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.output_path')
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    saved_path = f.read().strip()
                    if saved_path and os.path.exists(saved_path):
                        self.output_path_var.set(saved_path)
                        self._activate_easter_egg(show_message=False)
                        self.log(f"已加载输出路径: {saved_path}")
        except Exception as e:
            self.log(f"加载输出路径失败: {e}", "error")
    
    def get_output_path(self):
        """获取当前设置的输出路径
        
        Returns:
            str: 输出路径，如果未设置或无效则返回None
        """
        path = self.output_path_var.get()
        if path and self.validate_output_path(path):
            return path
        return None
    
    def load_help_content(self):
        """加载使用说明内容"""
        help_content = ""
        
        # 检查是否存在 README.md 文件
        readme_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "README.md")
        if os.path.exists(readme_path):
            try:
                with open(readme_path, 'r', encoding='utf-8') as f:
                    help_content = f.read()
            except Exception as e:
                # 读取默认帮助内容
                default_content = self.get_default_help_content()
                help_content = f"读取 README.md 文件失败: {str(e)}\n\n" + default_content
        else:
            # 读取默认帮助内容
            help_content = self.get_default_help_content()
        
        # 显示使用说明内容
        self.help_text.config(state=tk.NORMAL)
        self.help_text.delete(1.0, tk.END)
        self.help_text.insert(tk.END, help_content)
        self.help_text.config(state=tk.DISABLED)
    
    def _load_help_frame(self):
        """加载帮助文档框架"""
        self._unload_help_frame()
        
        if not HAS_TKINTERWEB or not HAS_MARKDOWN:
            self.log("使用纯文本模式显示使用说明")
            self.help_text = ScrolledText(self.help_tab, width=100, height=30, wrap=tk.WORD)
            self.help_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            self.load_help_content()
            return
        
        try:
            self.help_frame = HtmlFrame(self.help_tab, messages_enabled=False)
            self.help_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            self.load_help_content_html()
            self.help_frame.bind('<Button-1>', self._on_link_click)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.log(f"HTML渲染加载失败: {e}", "warning")
            self._unload_help_frame()
            self.help_text = ScrolledText(self.help_tab, width=100, height=30, wrap=tk.WORD)
            self.help_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            self.load_help_content()
    
    def _unload_help_frame(self):
        """释放帮助文档框架"""
        for widget in self.help_tab.winfo_children():
            try:
                widget.destroy()
            except:
                pass
        self.help_frame = None
        self.help_text = None
    
    def _on_link_click(self, event):
        """处理链接点击事件"""
        import webbrowser
        try:
            element = self.help_frame.get_currently_hovered_element()
            if element is not None:
                if hasattr(element, 'tagName') and element.tagName.lower() == 'a':
                    href = element.getAttribute('href')
                    if href and (href.startswith('http://') or href.startswith('https://')):
                        webbrowser.open(href)
        except Exception:
            pass
    
    def load_help_content_html(self):
        """加载使用说明内容（HTML渲染）"""
        help_content = ""
        
        # 检查是否存在 README.md 文件
        readme_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "README.md")
        if os.path.exists(readme_path):
            try:
                with open(readme_path, 'r', encoding='utf-8') as f:
                    help_content = f.read()
            except Exception as e:
                help_content = f"# 错误\n\n读取 README.md 文件失败: {str(e)}"
        else:
            help_content = self.get_default_help_content()
        
        # 转换 Markdown 为 HTML
        html_content = markdown.markdown(
            help_content,
            extensions=['tables', 'fenced_code', 'toc', 'nl2br']
        )
        
        # 添加 CSS 样式
        full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: 'Microsoft YaHei', '微软雅黑', sans-serif;
            padding: 20px;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            border-bottom: 1px solid #bdc3c7;
            padding-bottom: 8px;
            margin-top: 25px;
        }}
        h3 {{
            color: #7f8c8d;
            margin-top: 20px;
        }}
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: Consolas, 'Courier New', monospace;
            font-size: 0.9em;
        }}
        pre {{
            background: #f8f8f8;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            border: 1px solid #e0e0e0;
        }}
        pre code {{
            background: none;
            padding: 0;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }}
        th {{
            background: #f5f5f5;
            font-weight: bold;
        }}
        tr:hover {{
            background: #f9f9f9;
        }}
        blockquote {{
            border-left: 4px solid #3498db;
            margin: 15px 0;
            padding: 10px 20px;
            background: #f9f9f9;
        }}
        ul, ol {{
            padding-left: 25px;
        }}
        li {{
            margin: 5px 0;
        }}
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        hr {{
            border: none;
            border-top: 1px solid #ddd;
            margin: 20px 0;
        }}
        img {{
            max-width: 100%;
            height: auto;
        }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""
        
        # 显示 HTML 内容
        self.help_frame.load_html(full_html)
    
    def get_default_help_content(self):
        """获取默认的使用说明内容"""
        return "# 1688详情页资源采集工具 - 使用说明\n\n" \
               "## 功能介绍\n\n" \
               "本工具用于从 1688 详情页 HTML 文件中提取资源，包括：\n\n" \
               "- 主图\n" \
               "- 颜色色卡图片\n" \
               "- 详情图\n" \
               "- 视频\n" \
               "- 商品属性\n\n" \
               "## 使用方法\n\n" \
               "### GUI 版本\n\n" \
               "1. 启动 GUI 程序：运行 `python main.py --gui`\n" \
               "2. 添加文件：点击 '添加文件' 按钮添加单个 HTML 文件\n" \
               "3. 添加目录：点击 '添加目录' 按钮添加目录中所有 HTML 文件\n" \
               "4. 移除文件：在列表中选择文件后点击 '移除文件' 按钮\n" \
               "5. 清空队列：点击 '清空队列' 按钮清空所有队列中的文件\n" \
               "6. 执行处理：点击 '执行' 按钮开始处理队列中的文件\n" \
               "7. 暂停处理：点击 '暂停' 按钮暂停队列处理\n" \
               "8. 查看日志：在下方日志窗口查看执行过程和结果\n\n" \
               "### 命令行版本\n\n" \
               "1. 单个文件处理：`python main.py <html_file>`\n" \
               "2. 批量处理：执行 `bp1688html.bat` 批处理文件\n" \
               "3. 拖放处理：将 HTML 文件拖放到 `start1688.bat` 文件上\n\n" \
               "## 注意事项\n\n" \
               "1. HTML 文件需要使用 singlefile 浏览器插件进行预处理\n" \
               "2. 需要安装 Python 以及相关库：requests、subprocess、splitext、BeautifulSoup、pandas\n" \
               "3. 需要安装 Aria2c 下载工具\n" \
               "4. 添加目录时，只会处理当前目录中的 HTML 文件，不会递归处理子目录\n" \
               "5. 工具会自动去重，避免添加重复的文件路径\n\n" \
               "## 输出结果\n\n" \
               "处理完成后，会在与 HTML 文件同名的目录中生成以下文件：\n\n" \
               "- 主图：`T_1.jpg`, `T_2.jpg`, ...\n" \
               "- 颜色色卡图片：`color_*.jpg`\n" \
               "- 详情图：`C_1.jpg`, `C_2.jpg`, ...\n" \
               "- 视频：`video_1.mp4`, ...\n" \
               "- 属性文件：`attribute.html`\n" \
               "- 重建脚本：`rebuild.bat`\n" \
               "- URL 快捷方式：`#URL.url`\n\n" \
               "## 故障排除\n\n" \
               "1. **无法找到 aria2c.exe**：确保 aria2c.exe 文件在项目根目录中\n" \
               "2. **缺少依赖库**：使用 `pip install requests beautifulsoup4 pandas` 安装依赖\n" \
               "3. **HTML 文件加载失败**：确保 HTML 文件存在且格式正确\n" \
               "4. **资源提取失败**：可能是 HTML 文件结构与预期不符，工具会尝试多种选择器策略\n\n" \
               "## 版本信息\n\n" \
               "- 版本：0.3.0\n" \
               "- 作者：急云\n" \
               "- 项目地址：https://github.com/jiyun/1688/\n" \
               "- 日期：2026-02-01"
    
    # 队列管理代理方法
    def add_file(self):
        """添加多个 HTML 文件到队列"""
        self.queue_manager.add_file()
    
    def add_directory(self):
        """添加目录中所有 HTML 文件到队列"""
        self.queue_manager.add_directory()
    
    def remove_file(self):
        """从队列中移除选中的文件"""
        self.queue_manager.remove_file()
    
    def clear_queue(self):
        """清空队列"""
        self.queue_manager.clear_queue()
    
    def sort_treeview(self, column):
        """按列排序表格"""
        self.queue_manager.sort_treeview(column)
    
    def update_queue_list(self):
        """更新队列表格"""
        self.queue_manager.update_queue_list()
    
    def execute(self):
        """执行主程序处理队列中的文件"""
        self.queue_manager.execute()
    
    def _on_tab_changed(self, event):
        """标签页切换事件（含彩蛋和帮助文档加载）"""
        try:
            current_index = self.notebook.index(self.notebook.select())
            
            if current_index == 0:
                self._bind_queue_shortcuts()
            else:
                self._unbind_queue_shortcuts()
            
            if current_index == 1:
                self._load_help_frame()
            else:
                self._unload_help_frame()
            
            if not self.db_tab_visible:
                if self.last_tab_index != -1 and current_index != self.last_tab_index:
                    if (current_index == 0 and self.last_tab_index == 1) or (current_index == 1 and self.last_tab_index == 0):
                        self.easter_egg_counter += 1
                        if self.easter_egg_counter >= 15:
                            self._show_db_tab()
                            self.easter_egg_counter = 0
                            return
            
            self.last_tab_index = current_index
        except Exception as e:
            self.log(f"标签页切换错误: {e}", "error")
    
    def _show_db_tab(self):
        """显示数据库选项卡"""
        self.notebook.add(self.db_tab, text="数据库")
        self.db_tab_visible = True
        self.show_info("恭喜！", "你发现了隐藏的数据库选项卡！")
    
    def pause(self):
        """暂停/恢复队列处理"""
        self.queue_manager.pause()
    
    def on_treeview_double_click(self, event):
        """处理 treeview 双击事件"""
        region = self.queue_tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        
        column = self.queue_tree.identify_column(event.x)
        item = self.queue_tree.identify_row(event.y)
        
        if item:
            values = self.queue_tree.item(item, 'values')
            if values:
                if column == "#4":
                    self._edit_shop_id(item, values)
                    return
                
                file_path = self.queue_manager.file_queue[int(values[0]) - 1]
                html_dir = os.path.dirname(file_path)
                
                output_path = self.queue_manager.get_output_directory(file_path)
                
                if column == "#6":
                    if output_path and os.path.exists(output_path):
                        self.open_file_explorer(output_path)
                    else:
                        self.open_file_explorer(html_dir)
                else:
                    self.open_file_explorer(html_dir)
    
    def _edit_shop_id(self, item, values):
        """编辑DSID"""
        current_shop_id = values[3] if len(values) > 3 else ""
        
        file_index = int(values[0]) - 1
        if 0 <= file_index < len(self.queue_manager.file_queue):
            file_path = self.queue_manager.file_queue[file_index]
            product_id = os.path.splitext(os.path.basename(file_path))[0]
        else:
            product_id = ""
        
        dialog = tk.Toplevel(self.root)
        dialog.title("编辑DSID")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("350x150")
        dialog.resizable(False, False)
        
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        main_frame = tk.Frame(dialog, padx=20, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        label_frame = tk.Frame(main_frame)
        label_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(label_frame, text="商品ID:").pack(side=tk.LEFT)
        tk.Label(label_frame, text=product_id, fg="gray").pack(side=tk.LEFT, padx=(5, 0))
        
        entry_frame = tk.Frame(main_frame)
        entry_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(entry_frame, text="DSID:").pack(side=tk.LEFT)
        
        def validate_number(new_value):
            if new_value == "":
                return True
            if new_value.isdigit() and not new_value.startswith('0'):
                return True
            if new_value == '0':
                return True
            return False
        
        vcmd = (dialog.register(validate_number), '%P')
        entry = tk.Entry(entry_frame, width=25, validate='key', validatecommand=vcmd)
        entry.pack(side=tk.LEFT, padx=(5, 0))
        entry.insert(0, current_shop_id)
        entry.focus_set()
        entry.select_range(0, tk.END)
        
        error_label = tk.Label(main_frame, text="", fg="red")
        error_label.pack(fill=tk.X)
        
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        def save_shop_id():
            new_shop_id = entry.get().strip()
            
            if not new_shop_id:
                error_label.config(text="DSID不能为空")
                return
            
            if not new_shop_id.isdigit():
                error_label.config(text="DSID必须为纯数字")
                return
            
            if new_shop_id.startswith('0') and len(new_shop_id) > 1:
                error_label.config(text="DSID不能以0开头")
                return
            
            try:
                int(new_shop_id)
            except ValueError:
                error_label.config(text="DSID格式无效")
                return
            
            self.queue_tree.set(item, column="shop_id", value=new_shop_id)
            try:
                from utils.database import db
                db.update_shop_product_id(product_id, new_shop_id)
                self.log(f"已保存DSID: {product_id} -> {new_shop_id}")
            except Exception as e:
                self.log(f"保存DSID失败: {e}", "warning")
            dialog.destroy()
        
        tk.Button(btn_frame, text="保存", command=save_shop_id, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="取消", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)
        
        dialog.bind('<Return>', lambda e: save_shop_id())
        dialog.bind('<Escape>', lambda e: dialog.destroy())
    
    def open_file_explorer(self, path):
        """打开资源管理器到指定路径"""
        try:
            # 确保路径存在
            if not os.path.exists(path):
                # 如果路径不存在，尝试创建
                os.makedirs(path, exist_ok=True)
            
            # 使用 subprocess 打开资源管理器
            import subprocess
            if sys.platform == 'win32':
                # Windows 系统
                subprocess.run(['explorer', path])
            elif sys.platform == 'darwin':
                # macOS 系统
                subprocess.run(['open', path])
            else:
                # Linux 系统
                subprocess.run(['xdg-open', path])
            
            self.log(f"已打开资源管理器: {path}")
        except Exception as e:
            self.log(f"打开资源管理器失败: {str(e)}", "error")
    
    def _get_available_font(self):
        """获取可用的字体
        
        按优先级检测系统中可用的字体，返回第一个可用的字体
        
        Returns:
            str: 可用的字体名称
        """
        import tkinter.font as tkfont
        
        available_fonts = tkfont.families()
        
        font_families = GUI_CONF.get('font_families', [])
        
        for font_name in font_families:
            if font_name in available_fonts:
                return font_name
            
            if f'@{font_name}' in available_fonts:
                return f'@{font_name}'
        
        for fallback in ['微软雅黑', '黑体', '宋体']:
            if fallback in available_fonts:
                return fallback
            if f'@{fallback}' in available_fonts:
                return f'@{fallback}'
        
        return 'TkDefaultFont'
    
    # 上下文菜单命令代理方法
    def context_stitch_images(self):
        """右键菜单：图像优化（拼接+清理）"""
        self.context_menu_commands.context_stitch_images()
    
    def context_stitch_images_with_options(self, with_animated=False, webp_support=False, webp_main=False, webp_color=False):
        """右键菜单：带选项的图像优化"""
        self.context_menu_commands.context_stitch_images_with_options(with_animated, webp_support, webp_main, webp_color)
    
    def context_pack_files(self):
        """右键菜单：资源打包"""
        self.context_menu_commands.context_pack_files()
    
    def context_recollect(self):
        """右键菜单：重新采集"""
        self.context_menu_commands.context_recollect()
    
    def context_visit_url(self):
        """右键菜单：访问原址"""
        self.context_menu_commands.context_visit_url()
    
    def context_consign_page(self):
        """右键菜单：铺货页面"""
        self.context_menu_commands.context_consign_page()
    
    def context_shop_new(self):
        """右键菜单：店铺上新"""
        self.context_menu_commands.context_shop_new()
    
    def context_open_folder(self):
        """右键菜单：打开目录"""
        self.context_menu_commands.context_open_folder()
    
    def context_delete_item(self):
        """右键菜单：删除项目"""
        self.context_menu_commands.context_delete_item()
    
    def context_edit_shop_id(self):
        """右键菜单：编辑DSID"""
        self.context_menu_commands.context_edit_shop_id()
    
    def context_copy_item_url(self):
        """右键菜单：编辑商品 - 复制商品链接"""
        self.context_menu_commands.context_copy_item_url()
    
    def open_pricing_tool(self):
        """打开价格计算工具"""
        try:
            from gui.pricing_gui import PricingToolGUI
            import re
            
            selected_product_id = None
            selected_items = self.queue_tree.selection()
            
            if selected_items:
                item = selected_items[0]
                values = self.queue_tree.item(item, 'values')
                
                if values and len(values) > 2:
                    display_name = values[2]
                    match = re.search(r'(\d{10,12})\.html$', display_name)
                    if match:
                        selected_product_id = match.group(1)
            
            pricing_window = tk.Toplevel(self.root)
            if selected_product_id:
                pricing_window.title(f"商品定价计算工具 - {selected_product_id}")
            else:
                pricing_window.title("商品定价计算工具")
            pricing_window.geometry("1000x700")
            
            pricing_app = PricingToolGUI(pricing_window, selected_product_id)
            
        except ImportError as e:
            self.show_info("错误", f"无法加载价格计算工具：{e}")
        except Exception as e:
            self.show_info("错误", f"打开价格计算工具失败：{e}")
    
    def run(self):
        """运行GUI应用"""
        if self._is_gui_mode and HAS_UPDATER:
            self.root.after(1000, self._check_updates_on_startup)
        self.root.mainloop()
    
    def _check_updates_on_startup(self):
        """启动后检测更新（仅在GUI模式）"""
        try:
            from config import UPDATE_CONF
            if not UPDATE_CONF.get('check_on_startup', True):
                return
            
            import threading
            
            def check_in_thread():
                version_info = check_for_updates(silent=True)
                if version_info:
                    self.root.after(0, lambda: self._show_update_dialog(version_info))
            
            thread = threading.Thread(target=check_in_thread, daemon=True)
            thread.start()
        except Exception:
            pass
    
    def _show_update_dialog(self, version_info):
        """显示更新提示对话框"""
        message = f"发现新版本: v{version_info.version}\n"
        message += f"发布日期: {version_info.release_date}\n\n"
        
        if version_info.breaking_changes:
            message += "⚠️ 此版本包含重大变更\n\n"
        
        if version_info.mandatory:
            message += "此更新为强制更新"
        else:
            message += "是否立即下载更新？"
        
        if version_info.mandatory:
            self.show_info("发现新版本", message)
        else:
            result = self.ask_yes_no("发现新版本", message)
            if result:
                self._download_update(version_info)
    
    def _download_update(self, version_info):
        """下载更新包"""
        from utils.updater import UpdateDownloader
        
        self._current_version_info = version_info
        
        def download_in_thread():
            try:
                downloader = UpdateDownloader(use_mirror=True)
                
                def progress_callback(downloaded, total):
                    if total > 0:
                        percent = int(downloaded / total * 100)
                        self.root.after(0, lambda: self._update_download_progress(percent))
                
                filepath = downloader.download_update(version_info, progress_callback)
                
                if filepath:
                    self.root.after(0, lambda: self._on_download_complete(filepath, version_info))
                else:
                    self.root.after(0, lambda: self._on_download_failed())
            except Exception as e:
                self.root.after(0, lambda: self._on_download_error(str(e)))
        
        self._show_download_progress()
        
        import threading
        thread = threading.Thread(target=download_in_thread, daemon=True)
        thread.start()
    
    def _show_download_progress(self):
        """显示下载进度窗口"""
        self.download_window = tk.Toplevel(self.root)
        self.download_window.title("下载更新")
        self.download_window.geometry("400x120")
        self.download_window.resizable(False, False)
        self.download_window.transient(self.root)
        self.download_window.grab_set()
        
        tk.Label(self.download_window, text="正在下载更新包...", font=('Arial', 10)).pack(pady=10)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.download_window, 
            variable=self.progress_var, 
            maximum=100,
            length=350
        )
        self.progress_bar.pack(pady=5)
        
        self.progress_label = tk.Label(self.download_window, text="0%", font=('Arial', 9))
        self.progress_label.pack()
        
        self.cancel_download_btn = tk.Button(
            self.download_window, 
            text="取消", 
            command=self._cancel_download,
            width=10
        )
        self.cancel_download_btn.pack(pady=10)
        
        self.download_window.protocol("WM_DELETE_WINDOW", self._cancel_download)
    
    def _update_download_progress(self, percent):
        """更新下载进度"""
        if hasattr(self, 'progress_var') and hasattr(self, 'progress_label'):
            self.progress_var.set(percent)
            self.progress_label.config(text=f"{percent}%")
    
    def _on_download_complete(self, filepath, version_info):
        """下载完成"""
        if hasattr(self, 'download_window'):
            self.download_window.destroy()
        
        message = f"更新包下载完成！\n\n"
        message += f"版本: v{version_info.version}\n"
        message += f"文件: {filepath}\n\n"
        message += "请手动解压并替换文件。"
        
        self.show_info("下载完成", message)
    
    def _on_download_failed(self):
        """下载失败"""
        if hasattr(self, 'download_window'):
            self.download_window.destroy()
        
        result = self.ask_yes_no("下载失败", "下载失败，是否在浏览器中打开下载页面？")
        if result and hasattr(self, '_current_version_info'):
            self._open_download_page(self._current_version_info)
    
    def _on_download_error(self, error):
        """下载出错"""
        if hasattr(self, 'download_window'):
            self.download_window.destroy()
        
        self.show_info("下载出错", f"下载出错：{error}")
    
    def _cancel_download(self):
        """取消下载"""
        if hasattr(self, 'download_window'):
            self.download_window.destroy()
    
    def _open_download_page(self, version_info):
        """打开下载页面"""
        import webbrowser
        
        url = version_info.download_urls.get('gitee') or version_info.download_urls.get('github')
        if url:
            webbrowser.open(url)
            self.show_info("下载更新", f"已在浏览器中打开下载页面\n版本: v{version_info.version}")


def main():
    """主函数"""
    multiprocessing.freeze_support()
    
    if HAS_DND:
        from gui.dnd import create_dnd_root
        root = create_dnd_root()
    else:
        root = tk.Tk()
    
    app = AlibabaScraperGUI(root)
    
    hide_console()
    
    app.run()


if __name__ == "__main__":
    main()
