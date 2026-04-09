#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主应用模块 - CustomTkinter 版本
"""

import os
import sys

sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

import tkinter as tk
import customtkinter as ctk
from tkinter import ttk
import multiprocessing
import threading

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

from gui.utils import hide_console, ScrolledText, create_button
from config import GUI_CONF
from gui.logging import GUILogger
from gui.queue import QueueManager
from gui.menu import ContextMenuManager, ContextMenuCommands
from gui.dnd import DynamicDropOverlay, HAS_DND

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
        
        # 初始化共享内存
        try:
            from utils.shared_cache import init_shared_cache, HAS_SHARED_MEMORY
            if HAS_SHARED_MEMORY:
                init_shared_cache()
        except Exception as e:
            print(f"共享内存初始化异常: {e}")
        
        # 统一字体设置
        self._init_font_settings()
        
        # 配置 ttk 样式
        self._configure_ttk_styles()
        
        self._version = __version__ if HAS_UPDATER else "未知"
        self.easter_egg_counter = 0
        self.alt_press_counter = 0
        self.easter_egg_activated = False
        self.db_tab_visible = False
        self._is_gui_mode = True
        self._queue_shortcuts_bound = False
        
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill="both", expand=True)
        
        self.queue_tab = ctk.CTkFrame(self.notebook)
        self.notebook.add(self.queue_tab, text="处理队列")
        
        self.help_tab = ctk.CTkFrame(self.notebook)
        self.notebook.add(self.help_tab, text="使用说明")
        
        self.db_tab = ctk.CTkFrame(self.notebook)
        
        self.about_tab = ctk.CTkFrame(self.notebook)
        self.notebook.add(self.about_tab, text="关于")
        
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        
        # 绑定Shift键事件
        self.root.bind("<KeyPress-Shift_L>", self._on_shift_press)
        self.root.bind("<KeyPress-Shift_R>", self._on_shift_press)
        self.root.bind("<KeyRelease-Shift_L>", self._on_shift_release)
        self.root.bind("<KeyRelease-Shift_R>", self._on_shift_release)
        
        # 绑定鼠标中键点击事件
        self.root.bind_all("<Button-2>", self._on_middle_click)
        
        self._shift_pressed = False  # Shift键状态
        
        self.last_tab_index = -1
        
        self._init_db_tab()
        self._init_about_tab()
        
        self.button_frame = ctk.CTkFrame(self.queue_tab, fg_color="transparent")
        self.button_frame.pack(fill="x", pady=(0, 10))
        
        self.add_file_btn = create_button(self.button_frame, "添加文件 (A)", self.add_file, 'primary')
        self.add_file_btn.pack(side="left", padx=3)
        
        self.add_dir_btn = create_button(self.button_frame, "添加目录 (D)", self.add_directory, 'primary')
        self.add_dir_btn.pack(side="left", padx=3)
        
        self.remove_file_btn = create_button(self.button_frame, "移除文件 (Del)", self.remove_file, 'secondary')
        self.remove_file_btn.pack(side="left", padx=3)
        
        self.clear_queue_btn = create_button(self.button_frame, "清空队列", self.clear_queue, 'danger')
        self.clear_queue_btn.pack(side="left", padx=3)
        
        self.pause_btn = create_button(self.button_frame, "暂停 (P)", self.pause, 'warning', state="disabled")
        self.pause_btn.pack(side="right", padx=3)
        
        self.execute_btn = create_button(self.button_frame, "执行 (Enter)", self.execute, 'success')
        self.execute_btn.pack(side="right", padx=3)
        
        self.output_frame = ctk.CTkFrame(self.queue_tab, fg_color="transparent")
        
        self.output_label = ctk.CTkLabel(self.output_frame, text="输出路径:")
        self.output_label.pack(side="left", padx=5)
        
        self.output_path_var = ctk.StringVar()
        self.output_path_entry = ctk.CTkEntry(self.output_frame, textvariable=self.output_path_var, width=400)
        self.output_path_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        self.browse_btn = create_button(self.output_frame, "浏览...", self.browse_output_path, 'secondary')
        self.browse_btn.pack(side="left", padx=5)
        
        self.root.bind('<Alt_L>', self._on_alt_press)
        self.root.bind('<Alt_R>', self._on_alt_press)
        self.root.bind('<KeyRelease-Alt_L>', self._on_alt_release)
        self.root.bind('<KeyRelease-Alt_R>', self._on_alt_release)
        
        self._bind_queue_shortcuts()
        
        self.content_frame = ctk.CTkFrame(self.queue_tab, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True)
        
        self.queue_frame = ctk.CTkFrame(self.content_frame)
        self.queue_frame.pack(fill="both", expand=True, side="top", pady=(0, 10))
        
        self.queue_label = ctk.CTkLabel(self.queue_frame, text="处理队列", font=(self.available_font, self.font_size_large, "bold"))
        self.queue_label.pack(anchor="w", padx=10, pady=5)
        
        tree_frame = ctk.CTkFrame(self.queue_frame, fg_color="transparent")
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.queue_tree = ttk.Treeview(tree_frame, columns=("index", "status", "name", "shop_id", "date", "output_path"), show="headings")
        
        self.queue_tree.heading("index", text="序号")
        self.queue_tree.heading("status", text="状态", command=lambda: self.sort_treeview("status"))
        self.queue_tree.heading("name", text="文件名", command=lambda: self.sort_treeview("name"))
        self.queue_tree.heading("shop_id", text="DSID", command=lambda: self.sort_treeview("shop_id"))
        self.queue_tree.heading("date", text="修改日期", command=lambda: self.sort_treeview("date"))
        self.queue_tree.heading("output_path", text="输出路径", command=lambda: self.sort_treeview("output_path"))
        
        self.queue_tree.column("index", width=30, anchor="center")
        self.queue_tree.column("status", width=50, anchor="center")
        self.queue_tree.column("name", width=250, anchor="w")
        self.queue_tree.column("shop_id", width=80, anchor="center")
        self.queue_tree.column("date", width=120, anchor="center")
        self.queue_tree.column("output_path", width=250, anchor="w")
        
        self.queue_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.queue_tree.yview)
        self.queue_tree.configure(yscroll=self.queue_scrollbar.set)
        
        self.queue_tree.pack(side="left", fill="both", expand=True)
        self.queue_scrollbar.pack(side="right", fill="y")
        
        self.queue_tree.bind('<Double-1>', self.on_treeview_double_click)
        
        self.log_frame = ctk.CTkFrame(self.content_frame)
        self.log_frame.pack(fill="both", expand=True, side="bottom")
        
        self.log_label = ctk.CTkLabel(self.log_frame, text="日志输出", font=(self.available_font, self.font_size_large, "bold"))
        self.log_label.pack(anchor="w", padx=10, pady=5)
        
        self.log_text = ScrolledText(self.log_frame, width=100, height=15, state="disabled", 
                                     bg="#1a1a2e", fg="#eaeaea", 
                                     font=(self.available_font, self.font_size))
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        
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
        
        self._check_extensions()
    
    def _check_extensions(self):
        """检查扩展依赖"""
        try:
            from utils.extension_manager import ExtensionManager, check_dependencies
            manager = ExtensionManager()
            status = manager.get_status()
            
            missing = []
            for name, installed in status.items():
                if not installed:
                    missing.append(name)
            
            if missing:
                self.log(f"扩展检查: 缺少 {len(missing)} 个组件")
                for name in missing:
                    self.log(f"  - {name}: 未安装")
            else:
                self.log("扩展检查: 所有依赖已就绪")
            
            try:
                from utils.database import get_shared_db, HAS_DUCKDB
                if not HAS_DUCKDB:
                    self.log("数据库: DuckDB未安装，跳过迁移检查")
                else:
                    db = get_shared_db()
                    if db is None:
                        self.log("数据库: 无法获取数据库连接")
                    else:
                        columns = db.conn.execute("DESCRIBE sku_prices").fetchall()
                        existing_columns = {col[0] for col in columns}
                        required_columns = {'sku_id', 'color', 'size', 'price', 'discount_price', 
                                          'can_book_count', 'sale_count', 'spec_id'}
                        
                        if not required_columns.issubset(existing_columns):
                            self.log("数据库: 检测到旧版 sku_prices 表结构")
                            db._migrate_sku_prices_table()
                            self.log("数据库: sku_prices 表结构已更新")
                        db.close()
            except Exception as e:
                self.log(f"数据库迁移检查: {e}")
                
        except ImportError as e:
            self.log(f"扩展管理器不可用: {e}")
        except Exception as e:
            self.log(f"扩展检查失败: {e}")
    
    def _init_db_tab(self):
        """初始化数据库选项卡"""
        self.db_access_confirmed = False
        
        self.db_welcome_frame = ctk.CTkFrame(self.db_tab)
        self.db_welcome_frame.pack(fill="both", expand=True)
        
        self.welcome_label = ctk.CTkLabel(
            self.db_welcome_frame, 
            text="数据库管理\n\n此功能允许浏览和删除商品数据记录。\n\n点击下方按钮进入数据库管理界面。",
            justify="center",
            font=(self.available_font, self.font_size_large)
        )
        self.welcome_label.pack(expand=True)
        
        self.enter_btn = create_button(
            self.db_welcome_frame, 
            "进入数据库管理", 
            self._confirm_db_access,
            'success',
            width=160,
            height=40
        )
        self.enter_btn.pack(pady=20)
        
        self.db_content_frame = ctk.CTkFrame(self.db_tab, fg_color="transparent")
        
        self.db_stats_frame = ctk.CTkFrame(self.db_content_frame, fg_color="transparent")
        self.db_stats_frame.pack(fill="x", padx=5, pady=5)
        
        self.db_stats_labels = {}
        stats_items = [
            ('total', '商品总数'),
            ('resources', '资源总数'),
            ('downloaded', '已下载'),
            ('shops', '店铺数'),
            ('platform', '平台')
        ]
        for key, label in stats_items:
            frame = ctk.CTkFrame(self.db_stats_frame)
            frame.pack(side="left", padx=5, pady=2)
            ctk.CTkLabel(frame, text=label, font=(self.available_font, self.font_size_small)).pack(side="left", padx=2)
            self.db_stats_labels[key] = ctk.CTkLabel(frame, text="0", font=(self.available_font, self.font_size_small, "bold"))
            self.db_stats_labels[key].pack(side="left", padx=2)
        
        self.db_tree_frame = ctk.CTkFrame(self.db_content_frame, fg_color="transparent")
        self.db_tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        db_columns = ("platform", "product_id", "title", "ship_from", "resource_counts", "sku_prices", "shop_name", "shop_product_id", "price_matrix", "output_path", "status", "created_at")
        self.db_tree = ttk.Treeview(self.db_tree_frame, columns=db_columns, show="headings", selectmode="browse")
        
        self.db_tree.heading("platform", text="平台", command=lambda: self._sort_db_column("platform"))
        self.db_tree.heading("product_id", text="商品ID", command=lambda: self._sort_db_column("product_id"))
        self.db_tree.heading("title", text="商品标题", command=lambda: self._sort_db_column("title"))
        self.db_tree.heading("ship_from", text="发货地", command=lambda: self._sort_db_column("ship_from"))
        self.db_tree.heading("resource_counts", text="资源", command=lambda: self._sort_db_column("resource_counts"))
        self.db_tree.heading("sku_prices", text="SKU", command=lambda: self._sort_db_column("sku_prices"))
        self.db_tree.heading("shop_name", text="DS店铺", command=lambda: self._sort_db_column("shop_name"))
        self.db_tree.heading("shop_product_id", text="DSID", command=lambda: self._sort_db_column("shop_product_id"))
        self.db_tree.heading("price_matrix", text="DS价格矩阵", command=lambda: self._sort_db_column("price_matrix"))
        self.db_tree.heading("output_path", text="输出路径")
        self.db_tree.heading("status", text="状态", command=lambda: self._sort_db_column("status"))
        self.db_tree.heading("created_at", text="创建时间", command=lambda: self._sort_db_column("created_at"))
        
        self.db_tree.column("platform", width=60, anchor="center")
        self.db_tree.column("product_id", width=105, anchor="center")
        self.db_tree.column("title", width=200, anchor="w")
        self.db_tree.column("ship_from", width=60, anchor="center")
        self.db_tree.column("resource_counts", width=45, anchor="center")
        self.db_tree.column("sku_prices", width=40, anchor="center")
        self.db_tree.column("shop_name", width=80, anchor="w")
        self.db_tree.column("shop_product_id", width=85, anchor="center")
        self.db_tree.column("price_matrix", width=80, anchor="center")
        self.db_tree.column("output_path", width=150, anchor="w")
        self.db_tree.column("status", width=50, anchor="center")
        self.db_tree.column("created_at", width=120, anchor="center")
        
        db_scrollbar = ttk.Scrollbar(self.db_tree_frame, orient="vertical", command=self.db_tree.yview)
        self.db_tree.configure(yscrollcommand=db_scrollbar.set)
        
        self.db_tree.pack(side="left", fill="both", expand=True)
        db_scrollbar.pack(side="right", fill="y")
        
        self.db_tree.bind('<Button-3>', self._show_db_context_menu)
        self.db_tree.bind('<Double-1>', self._on_db_tree_double_click)
        
        self._db_sort_column = None
        self._db_sort_reverse = False
        
        self.db_btn_frame = ctk.CTkFrame(self.db_content_frame, fg_color="transparent")
        self.db_btn_frame.pack(fill="x", pady=5)
        
        self.db_search_frame = ctk.CTkFrame(self.db_btn_frame, fg_color="transparent")
        self.db_search_frame.pack(side="left", padx=5)
        
        self.db_search_var = ctk.StringVar()
        self.db_search_var.trace_add("write", self._validate_search_input)
        
        ctk.CTkLabel(self.db_search_frame, text="搜索:").pack(side="left")
        
        self.db_search_entry = ctk.CTkEntry(self.db_search_frame, textvariable=self.db_search_var, width=150)
        self.db_search_entry.pack(side="left", padx=2)
        self.db_search_entry.bind('<Return>', lambda e: self._search_db_records())
        
        self.db_search_btn = create_button(self.db_search_frame, "搜索", self._search_db_records, 'primary', width=60)
        self.db_search_btn.pack(side="left", padx=2)
        
        self.db_filter_frame = ctk.CTkFrame(self.db_btn_frame, fg_color="transparent")
        self.db_filter_frame.pack(side="left", padx=10)
        
        ctk.CTkLabel(self.db_filter_frame, text="平台:").pack(side="left")
        self.db_platform_var = ctk.StringVar(value="全部")
        self.db_platform_menu = ctk.CTkOptionMenu(self.db_filter_frame, variable=self.db_platform_var, 
            values=["全部", "alibaba", "jd"], width=80, command=self._filter_by_platform)
        self.db_platform_menu.pack(side="left", padx=2)
        
        ctk.CTkLabel(self.db_filter_frame, text="发货地:").pack(side="left", padx=(10, 0))
        self.db_ship_from_var = ctk.StringVar(value="全部")
        self.db_ship_from_menu = ctk.CTkOptionMenu(self.db_filter_frame, variable=self.db_ship_from_var,
            values=["全部"], width=80, command=self._filter_by_ship_from)
        self.db_ship_from_menu.pack(side="left", padx=2)
        
        ctk.CTkLabel(self.db_filter_frame, text="状态:").pack(side="left", padx=(10, 0))
        self.db_status_var = ctk.StringVar(value="全部")
        self.db_status_menu = ctk.CTkOptionMenu(self.db_filter_frame, variable=self.db_status_var,
            values=["全部", "完成", "待处理"], width=80, command=self._filter_by_status)
        self.db_status_menu.pack(side="left", padx=2)
        
        self.db_refresh_btn = create_button(self.db_btn_frame, "刷新", self._refresh_db_data, 'secondary', width=60)
        self.db_refresh_btn.pack(side="left", padx=5)
        
        self.db_import_btn = create_button(self.db_btn_frame, "导入", self._show_import_dialog, 'success', width=60)
        self.db_import_btn.pack(side="left", padx=5)
        
        self.db_close_btn = create_button(self.db_btn_frame, "关闭数据库", self._close_db_tab, 'secondary', width=80)
        self.db_close_btn.pack(side="right", padx=5)
        
        self.db_status_label = ctk.CTkLabel(self.db_btn_frame, text="")
        self.db_status_label.pack(side="right", padx=10)
    
    def _init_about_tab(self):
        """初始化关于选项卡"""
        about_frame = ctk.CTkFrame(self.about_tab, fg_color="transparent")
        about_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.title_label = ctk.CTkLabel(
            about_frame,
            text="1688详情页资源采集工具",
            font=(self.available_font, self.font_size_title, "bold")
        )
        self.title_label.pack(pady=(20, 10))
        
        self.version_label = ctk.CTkLabel(
            about_frame,
            text=f"版本: {self._version}",
            font=(self.available_font, self.font_size_subtitle)
        )
        self.version_label.pack(pady=5)
        
        self.author_label = ctk.CTkLabel(
            about_frame,
            text="作者: 急云",
            font=(self.available_font, self.font_size_subtitle)
        )
        self.author_label.pack(pady=5)
        
        github_url = "https://github.com/jiyun/1688/"
        self.github_label = ctk.CTkLabel(
            about_frame,
            text=f"GitHub: {github_url}",
            font=(self.available_font, self.font_size_subtitle),
            text_color="#1f6feb",
            cursor="hand2"
        )
        self.github_label.pack(pady=5)
        self.github_label.bind("<Button-1>", lambda e: self._open_url(github_url))
        self.github_label.bind("<Enter>", lambda e: self.github_label.configure(text_color="#1a5fb7"))
        self.github_label.bind("<Leave>", lambda e: self.github_label.configure(text_color="#1f6feb"))
        
        self.desc_label = ctk.CTkLabel(
            about_frame,
            text="用于采集1688商品详情页资源的工具。",
            font=(self.available_font, self.font_size_large),
            wraplength=400
        )
        self.desc_label.pack(pady=(20, 10))
        
        btn_frame = ctk.CTkFrame(about_frame, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        self.check_update_btn = create_button(
            btn_frame,
            "检查更新",
            self._check_update,
            'primary',
            width=120,
            height=35
        )
        self.check_update_btn.pack(side="left", padx=10)
        
        self.reinstall_btn = create_button(
            btn_frame,
            "重新安装",
            self._reinstall_current_version,
            'secondary',
            width=120,
            height=35
        )
        self.reinstall_btn.pack(side="left", padx=10)
        
        online_collect_frame = ctk.CTkFrame(about_frame, fg_color="transparent")
        online_collect_frame.pack(pady=15)
        
        self.online_collect_btn = create_button(
            online_collect_frame,
            "在线采集",
            self._show_online_collect_dialog,
            'success',
            width=150,
            height=40
        )
        self.online_collect_btn.pack(side="left", padx=5)
        
        login_frame = ctk.CTkFrame(online_collect_frame, fg_color="transparent")
        login_frame.pack(side="left", padx=10)
        
        ctk.CTkLabel(login_frame, text="登陆平台:", font=(self.available_font, self.font_size)).pack(side="left", padx=(0, 5))
        
        login_1688_btn = create_button(
            login_frame,
            "1688",
            lambda: self._open_platform_login("1688"),
            'primary',
            width=60,
            height=32
        )
        login_1688_btn.pack(side="left", padx=2)
        
        login_jd_btn = create_button(
            login_frame,
            "京东",
            lambda: self._open_platform_login("jd"),
            'primary',
            width=60,
            height=32
        )
        login_jd_btn.pack(side="left", padx=2)
        
        self.update_status_frame = ctk.CTkFrame(about_frame, fg_color="transparent")
        
        self.update_status_label = ctk.CTkLabel(
            self.update_status_frame,
            text="",
            font=(self.available_font, self.font_size_large)
        )
        self.update_status_label.pack(pady=5)
        
        self.update_progress_bar = ctk.CTkProgressBar(
            self.update_status_frame,
            width=300,
            height=15
        )
        self.update_progress_bar.set(0)
        
        self.update_progress_label = ctk.CTkLabel(
            self.update_status_frame,
            text="",
            font=("", 11)
        )
        
        self.update_action_frame = ctk.CTkFrame(self.update_status_frame, fg_color="transparent")
        
        self.install_update_btn = ctk.CTkButton(
            self.update_action_frame,
            text="安装更新",
            command=self._install_downloaded_update,
            width=100,
            fg_color="#28a745"
        )
        
        self.cancel_update_btn = ctk.CTkButton(
            self.update_action_frame,
            text="取消",
            command=self._cancel_update,
            width=80,
            fg_color="gray"
        )
        
        self._update_download_filepath = None
        self._update_version_info = None
    
    def _open_url(self, url):
        """打开URL"""
        import webbrowser
        webbrowser.open(url)
    
    def _show_online_collect_dialog(self):
        """显示在线采集对话框"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("在线采集")
        dialog.geometry("900x250")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=15)
        
        platform_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        platform_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(platform_frame, text="平台:", font=(self.available_font, self.font_size)).pack(side="left")
        
        platform_var = ctk.StringVar(value="1688")
        
        platform_1688 = ctk.CTkRadioButton(platform_frame, text="1688", variable=platform_var, value="1688")
        platform_1688.pack(side="left", padx=15)
        
        platform_jd = ctk.CTkRadioButton(platform_frame, text="京东", variable=platform_var, value="jd")
        platform_jd.pack(side="left", padx=5)
        
        input_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        input_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(input_frame, text="URL或商品ID:", font=(self.available_font, self.font_size)).pack(anchor="w")
        
        input_var = ctk.StringVar()
        input_entry = ctk.CTkEntry(input_frame, textvariable=input_var, width=400, height=35)
        input_entry.pack(fill="x", pady=5)
        input_entry.focus_set()
        
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=15)
        
        def do_collect():
            input_text = input_var.get().strip()
            if not input_text:
                return
            
            platform = platform_var.get()
            
            product_id = None
            if input_text.isdigit():
                product_id = input_text
            else:
                import re
                if platform == "1688":
                    match = re.search(r'offer/(\d+)\.html', input_text)
                    if match:
                        product_id = match.group(1)
                elif platform == "jd":
                    match = re.search(r'item/(\d+)\.html', input_text)
                    if match:
                        product_id = match.group(1)
                    if not match:
                        match = re.search(r'jd\.com/(\d+)', input_text)
                        if match:
                            product_id = match.group(1)
            
            if not product_id:
                self.show_warning("提示", "无法识别商品ID，请检查输入")
                return
            
            dialog.destroy()
            
            if platform == "1688":
                url = f"https://detail.1688.com/offer/{product_id}.html"
            else:
                url = f"https://item.jd.com/{product_id}.html"
            
            self._start_online_collect(product_id, url, platform)
        
        def on_enter(event):
            do_collect()
        
        input_entry.bind('<Return>', on_enter)
        
        cancel_btn = create_button(btn_frame, "取消", dialog.destroy, 'secondary', width=100)
        cancel_btn.pack(side="right", padx=5)
        
        collect_btn = create_button(btn_frame, "开始采集", do_collect, 'success', width=100)
        collect_btn.pack(side="right", padx=5)
    
    def _start_online_collect(self, product_id: str, url: str, platform: str):
        """开始在线采集"""
        import time
        self.log(f"准备在线采集: {url}", "info")
        
        self._collect_start_time = time.time()
        self._collect_product_id = product_id
        
        if hasattr(self, 'online_collect_btn') and self.online_collect_btn:
            self.online_collect_btn.configure(state='disabled')
        
        def collect_thread():
            try:
                from gui.online_collector_gui import get_collector
                
                collector = get_collector(self.log)
                
                if not collector.browser_started:
                    self.log("正在启动浏览器...")
                    if not collector.start_browser():
                        self.log("浏览器启动失败", "error")
                        return
                
                self.log("正在采集数据...")
                data = collector.collect_data_direct(product_id)
                
                if data:
                    self.log("数据采集成功，正在保存到数据库...")
                    self._save_online_collect_data(data)
                    self.log("数据已保存到数据库", "success")
                    
                    self.root.after(0, self._refresh_db_data)
                else:
                    self.log("数据采集失败", "error")
                    
            except Exception as e:
                self.log(f"在线采集异常: {e}", "error")
                import traceback
                traceback.print_exc()
            finally:
                self.root.after(0, self._on_online_collect_complete)
        
        thread = threading.Thread(target=collect_thread, daemon=True)
        thread.start()
    
    def _on_online_collect_complete(self):
        """在线采集完成后的回调"""
        if hasattr(self, 'online_collect_btn') and self.online_collect_btn:
            self.online_collect_btn.configure(state='normal')
        
        import time
        elapsed_time = 0
        product_id = getattr(self, '_collect_product_id', '')
        
        if hasattr(self, '_collect_start_time'):
            elapsed_time = time.time() - self._collect_start_time
        
        result = self._show_continue_dialog(product_id, elapsed_time)
        if result:
            self._show_online_collect_dialog()
    
    def _show_continue_dialog(self, product_id: str = '', elapsed_time: float = 0) -> bool:
        """显示是否继续采集的对话框"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("采集完成")
        dialog.geometry("350x200")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        result = [False]
        
        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=15)
        
        if product_id:
            info_text = f"商品 {product_id} 采集完成"
            info_label = ctk.CTkLabel(main_frame, text=info_text, font=(self.available_font, self.font_size_large))
            info_label.pack(pady=(5, 0))
        
        time_text = f"共耗时 {elapsed_time:.1f} 秒"
        time_label = ctk.CTkLabel(main_frame, text=time_text, font=(self.available_font, self.font_size_large), text_color="gray")
        time_label.pack(pady=(2, 5))
        
        question_label = ctk.CTkLabel(main_frame, text="是否继续采集？", font=(self.available_font, self.font_size_large))
        question_label.pack(pady=5)
        
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=5)
        
        def on_yes():
            result[0] = True
            dialog.destroy()
        
        def on_no():
            result[0] = False
            dialog.destroy()
        
        yes_btn = create_button(btn_frame, "是", on_yes, 'success', width=80)
        yes_btn.pack(side="left", padx=20, expand=True)
        
        no_btn = create_button(btn_frame, "否", on_no, 'secondary', width=80)
        no_btn.pack(side="right", padx=20, expand=True)
        
        dialog.wait_window()
        return result[0]
    
    def _open_platform_login(self, platform: str):
        """打开平台登录页面（正常模式，非无头模式）"""
        try:
            from utils.auto_collector import AutoCollector
            
            if platform == "1688":
                url = "https://www.1688.com"
                self.log("正在打开1688登录页面...")
            else:
                url = "https://www.jd.com"
                self.log("正在打开京东登录页面...")
            
            def open_login_thread():
                try:
                    need_start = False
                    if not hasattr(self, '_login_collector') or self._login_collector is None:
                        need_start = True
                    elif self._login_collector.driver is None:
                        need_start = True
                    else:
                        try:
                            self._login_collector.driver.current_url
                        except:
                            need_start = True
                    
                    if need_start:
                        self._login_collector = AutoCollector(headless=False)
                        self._login_collector.start_browser()
                    
                    self._login_collector.driver.get(url)
                    self.log(f"已打开 {platform} 登录页面，请在浏览器中完成登录")
                    
                except Exception as e:
                    self.log(f"打开登录页面失败: {e}", "error")
                    self._login_collector = None
            
            thread = threading.Thread(target=open_login_thread, daemon=True)
            thread.start()
            
        except Exception as e:
            self.log(f"启动登录浏览器失败: {e}", "error")
    
    def _check_update(self):
        """检查更新"""
        if HAS_UPDATER:
            self.log("正在检查更新...")
            self._show_update_status("正在检查更新...", False)
            try:
                version_info = check_for_updates(silent=False, force=True)
                if version_info:
                    self.log(f"发现新版本: {version_info.version}", "success")
                    self._update_version_info = version_info
                    self._show_update_status(f"发现新版本: {version_info.version}", False)
                    self._start_download_update(version_info)
                else:
                    self.log("当前已是最新版本", "success")
                    self._show_update_status("当前已是最新版本", False)
            except Exception as e:
                self.log(f"检查更新失败: {str(e)}", "error")
                self._show_update_status(f"检查更新失败: {str(e)}", False)
        else:
            self.log("更新功能不可用", "warning")
    
    def _show_update_status(self, message: str, show_progress: bool):
        """显示更新状态"""
        self.update_status_label.configure(text=message)
        if show_progress:
            self.update_status_frame.pack(pady=10, fill="x")
            self.update_progress_bar.pack(pady=5)
            self.update_progress_label.pack()
        else:
            self.update_progress_bar.pack_forget()
            self.update_progress_label.pack_forget()
            self.update_action_frame.pack_forget()
    
    def _start_download_update(self, version_info):
        """开始下载更新"""
        import threading
        
        self._show_update_status("正在下载更新包...", True)
        self.update_progress_label.configure(text="0%")
        
        def download_thread():
            try:
                import os
                self.log("下载线程启动...")
                from utils.updater import UpdateDownloader, HAS_ARIA2C
                
                self.log(f"HAS_ARIA2C: {HAS_ARIA2C}")
                
                def progress_callback(downloaded, total):
                    percent = int(downloaded / total * 100) if total > 0 else 0
                    self.root.after(0, lambda p=percent: self._update_download_progress(p))
                
                downloader = UpdateDownloader()
                self.log(f"开始下载: {version_info.download_urls}")
                filepath = downloader.download_update(version_info, progress_callback)
                
                self.log(f"下载结果: {filepath}")
                
                if filepath and os.path.exists(filepath):
                    self._update_download_filepath = filepath
                    fp = filepath
                    vi = version_info
                    self.root.after(0, lambda: self._on_download_complete(fp, vi))
                else:
                    self.root.after(0, lambda: self._on_download_failed())
            except Exception as e:
                import traceback
                self.log(f"下载异常: {e}")
                traceback.print_exc()
                err = str(e)
                self.root.after(0, lambda: self._on_download_error(err))
        
        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()
    
    def _update_download_progress(self, percent: int):
        """更新下载进度"""
        self.update_progress_bar.set(percent / 100)
        self.update_progress_label.configure(text=f"{percent}%")
    
    def _on_download_complete(self, filepath, version_info):
        """下载完成"""
        self._show_update_status(f"下载完成: v{version_info.version}", False)
        self.update_status_label.configure(text=f"下载完成: v{version_info.version}")
        
        self.update_action_frame.pack(pady=10)
        self.install_update_btn.pack(side="left", padx=10)
        self.cancel_update_btn.pack(side="left", padx=10)
        
        self.log(f"更新包已下载: {filepath}", "success")
    
    def _on_download_failed(self):
        """下载失败"""
        self._show_update_status("下载失败", False)
        self.log("下载更新包失败", "error")
    
    def _on_download_error(self, error: str):
        """下载错误"""
        self._show_update_status(f"下载错误: {error}", False)
        self.log(f"下载更新包错误: {error}", "error")
    
    def _install_downloaded_update(self):
        """安装已下载的更新"""
        if self._update_download_filepath:
            try:
                from utils.updater import UpdateDownloader
                downloader = UpdateDownloader()
                if downloader.apply_update(self._update_download_filepath, restart=True):
                    self.log("正在安装更新...", "success")
                    import sys
                    sys.exit(0)
                else:
                    self.log("启动更新失败", "error")
            except Exception as e:
                self.log(f"安装更新失败: {e}", "error")
    
    def _cancel_update(self):
        """取消更新"""
        self._update_download_filepath = None
        self._update_version_info = None
        self.update_status_frame.pack_forget()
        self.log("已取消更新")
    
    def _reinstall_current_version(self):
        """重新安装当前版本"""
        from utils.version import __version__
        from utils.updater import VersionInfo
        
        version_info = VersionInfo(
            version=__version__,
            release_date="",
            download_urls={
                'github': f'https://github.com/jiyun/1688/archive/refs/tags/v{__version__}.zip'
            }
        )
        
        self._update_version_info = version_info
        self.log(f"正在下载 v{__version__} 安装包...")
        self._start_download_update(version_info)
    
    def _confirm_db_access(self):
        """确认数据库访问"""
        confirm = self.ask_yes_no("确认", "确定要进入数据库管理界面吗？\n\n请注意：删除操作不可撤销！")
        if confirm:
            self.db_access_confirmed = True
            self.db_welcome_frame.pack_forget()
            self.db_content_frame.pack(fill="both", expand=True)
            self._refresh_db_data()
            self.root.state("zoomed")
    
    def _close_db_tab(self):
        """关闭数据库选项卡，返回处理队列"""
        self.db_content_frame.pack_forget()
        self.db_welcome_frame.pack(fill="both", expand=True)
        self.db_access_confirmed = False
        self.notebook.select(0)
    
    def _refresh_db_data(self):
        """刷新数据库数据"""
        for item in self.db_tree.get_children():
            self.db_tree.delete(item)
        
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            
            try:
                stats = db.get_statistics()
                self.db_stats_labels['total'].configure(text=str(stats['total_products']))
                self.db_stats_labels['resources'].configure(text=str(stats['total_resources']))
                self.db_stats_labels['downloaded'].configure(text=str(stats['downloaded_resources']))
                self.db_stats_labels['shops'].configure(text=str(stats['total_shops']))
                platform_str = '/'.join([f"{k}:{v}" for k, v in stats['by_platform'].items()])
                self.db_stats_labels['platform'].configure(text=platform_str if platform_str else '-')
                
                products = db.get_all_products()
                
                for product in products:
                    output_path = product.get('output_path', '') or ''
                    if len(output_path) > 18:
                        output_path = '...' + output_path[-15:]
                    
                    title = product.get('title', '') or ''
                    if len(title) > 20:
                        title = title[:20] + '...'
                    
                    product_id = product.get('product_id', '')
                    
                    platform = product.get('platform', 'alibaba')
                    if platform == 'alibaba':
                        platform = '1688'
                    elif platform == 'jd':
                        platform = '京东'
                    
                    sku_prices_count = db.count_sku_prices(product_id)
                    sku_prices_str = f"{sku_prices_count}" if sku_prices_count > 0 else "-"
                    
                    resource_counts = db.count_resources(product_id)
                    total_resources = resource_counts['main_images'] + resource_counts['color_images'] + resource_counts['detail_images'] + resource_counts['videos']
                    resource_counts_str = f"{total_resources}" if total_resources > 0 else "-"
                    
                    shop_id = product.get('shop_id', '')
                    shop_name = ''
                    if shop_id:
                        shop = db.get_shop(shop_id)
                        if shop:
                            shop_name = shop.get('shop_name', '')[:8]
                    
                    ship_from = product.get('ship_from', '') or '-'
                    
                    shop_product_id = product.get('shop_product_id', '') or '-'
                    
                    price_matrix = product.get('selling_prices', '')
                    if price_matrix:
                        try:
                            import json
                            prices_data = json.loads(price_matrix)
                            if isinstance(prices_data, list) and len(prices_data) > 0:
                                price_matrix = f"{len(prices_data)}条"
                            else:
                                price_matrix = '-'
                        except:
                            price_matrix = '-'
                    else:
                        price_matrix = '-'
                    
                    status = product.get('status', '') or '-'
                    if status == 'pending':
                        status = '待处理'
                    elif status == 'completed':
                        status = '完成'
                    
                    self.db_tree.insert("", "end", values=(
                        platform,
                        product_id,
                        title,
                        ship_from,
                        resource_counts_str,
                        sku_prices_str,
                        shop_name,
                        shop_product_id,
                        price_matrix,
                        output_path,
                        status,
                        str(product.get('created_at', ''))[:16]
                    ))
                
                self.db_status_label.configure(text=f"共 {len(products)} 条")
                
                self._update_ship_from_options(db, stats)
            finally:
                db.close()
        except Exception as e:
            self.log(f"读取数据库失败: {e}", "error")
            self.db_status_label.configure(text="读取失败")
    
    def _update_ship_from_options(self, db, stats):
        """更新发货地筛选选项"""
        try:
            ship_from_list = ["全部"]
            for ship_from, count in stats.get('by_ship_from', {}).items():
                if ship_from and ship_from.strip():
                    ship_from_list.append(ship_from)
            
            current_selection = self.db_ship_from_var.get()
            self.db_ship_from_menu.configure(values=ship_from_list)
            
            if current_selection not in ship_from_list:
                self.db_ship_from_var.set("全部")
        except Exception:
            pass
    
    def _search_db_records(self):
        """搜索数据库记录 - 自动匹配商品ID和DSID"""
        search_term = self.db_search_var.get().strip()
        
        if not search_term:
            self._refresh_db_data()
            return
        
        for item in self.db_tree.get_children():
            self.db_tree.delete(item)
        
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            
            products = db.search_products_by_id(search_term)
            
            for product in products:
                output_path = product.get('output_path', '') or ''
                if len(output_path) > 18:
                    output_path = '...' + output_path[-15:]
                
                title = product.get('title', '') or ''
                if len(title) > 20:
                    title = title[:20] + '...'
                
                product_id = product.get('product_id', '')
                
                platform = product.get('platform', 'alibaba')
                if platform == 'alibaba':
                    platform = '1688'
                elif platform == 'jd':
                    platform = '京东'
                
                sku_prices_count = db.count_sku_prices(product_id)
                sku_prices_str = f"{sku_prices_count}" if sku_prices_count > 0 else "-"
                
                resource_counts = db.count_resources(product_id)
                total_resources = resource_counts['main_images'] + resource_counts['color_images'] + resource_counts['detail_images'] + resource_counts['videos']
                resource_counts_str = f"{total_resources}" if total_resources > 0 else "-"
                
                shop_id = product.get('shop_id', '')
                shop_name = ''
                if shop_id:
                    shop = db.get_shop(shop_id)
                    if shop:
                        shop_name = shop.get('shop_name', '')[:8]
                
                ship_from = product.get('ship_from', '') or '-'
                
                shop_product_id = product.get('shop_product_id', '') or '-'
                
                price_matrix = product.get('selling_prices', '')
                if price_matrix:
                    try:
                        import json
                        prices_data = json.loads(price_matrix)
                        if isinstance(prices_data, list) and len(prices_data) > 0:
                            price_matrix = f"{len(prices_data)}条"
                        else:
                            price_matrix = '-'
                    except:
                        price_matrix = '-'
                else:
                    price_matrix = '-'
                
                status = product.get('status', '') or '-'
                if status == 'pending':
                    status = '待处理'
                elif status == 'completed':
                    status = '完成'
                
                self.db_tree.insert("", "end", values=(
                    platform,
                    product_id,
                    title,
                    ship_from,
                    resource_counts_str,
                    sku_prices_str,
                    shop_name,
                    shop_product_id,
                    price_matrix,
                    output_path,
                    status,
                    str(product.get('created_at', ''))[:16]
                ))
            
            self.db_status_label.configure(text=f"搜索结果: {len(products)} 条")
            
        except Exception as e:
            self.log(f"搜索失败: {e}", "error")
            self.db_status_label.configure(text="搜索失败")
    
    def _filter_by_platform(self, platform: str):
        """按平台过滤"""
        self._apply_db_filters()
    
    def _filter_by_ship_from(self, ship_from: str):
        """按发货地过滤"""
        self._apply_db_filters()
    
    def _filter_by_status(self, status: str):
        """按状态过滤"""
        self._apply_db_filters()
    
    def _apply_db_filters(self):
        """应用所有筛选条件"""
        for item in self.db_tree.get_children():
            self.db_tree.delete(item)
        
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            
            platform = self.db_platform_var.get()
            ship_from = self.db_ship_from_var.get()
            status = self.db_status_var.get()
            
            if platform == "全部" and ship_from == "全部" and status == "全部":
                products = db.get_all_products()
            else:
                products = db.search_products_full(
                    platform=platform if platform != "全部" else None,
                    ship_from=ship_from if ship_from != "全部" else None
                )
                if status != "全部":
                    status_map = {"完成": "completed", "待处理": "pending"}
                    products = [p for p in products if p.get('status') == status_map.get(status, status)]
            
            for product in products:
                output_path = product.get('output_path', '') or ''
                if len(output_path) > 18:
                    output_path = '...' + output_path[-15:]
                
                title = product.get('title', '') or ''
                if len(title) > 20:
                    title = title[:20] + '...'
                
                product_id = product.get('product_id', '')
                
                product_platform = product.get('platform', 'alibaba')
                if product_platform == 'alibaba':
                    product_platform = '1688'
                elif product_platform == 'jd':
                    product_platform = '京东'
                
                sku_prices_count = db.count_sku_prices(product_id)
                sku_prices_str = f"{sku_prices_count}" if sku_prices_count > 0 else "-"
                
                resource_counts = db.count_resources(product_id)
                total_resources = resource_counts['main_images'] + resource_counts['color_images'] + resource_counts['detail_images'] + resource_counts['videos']
                resource_counts_str = f"{total_resources}" if total_resources > 0 else "-"
                
                shop_id = product.get('shop_id', '')
                shop_name = ''
                if shop_id:
                    shop = db.get_shop(shop_id)
                    if shop:
                        shop_name = shop.get('shop_name', '')[:8]
                
                ship_from_val = product.get('ship_from', '') or '-'
                
                shop_product_id = product.get('shop_product_id', '') or '-'
                
                price_matrix = product.get('selling_prices', '')
                if price_matrix:
                    try:
                        import json
                        prices_data = json.loads(price_matrix)
                        if isinstance(prices_data, list) and len(prices_data) > 0:
                            price_matrix = f"{len(prices_data)}条"
                        else:
                            price_matrix = '-'
                    except:
                        price_matrix = '-'
                else:
                    price_matrix = '-'
                
                status_val = product.get('status', '') or '-'
                if status_val == 'pending':
                    status_val = '待处理'
                elif status_val == 'completed':
                    status_val = '完成'
                
                self.db_tree.insert("", "end", values=(
                    product_platform,
                    product_id,
                    title,
                    ship_from_val,
                    resource_counts_str,
                    sku_prices_str,
                    shop_name,
                    shop_product_id,
                    price_matrix,
                    output_path,
                    status_val,
                    str(product.get('created_at', ''))[:16]
                ))
            
            filter_desc = []
            if platform != "全部":
                filter_desc.append(f"平台:{platform}")
            if ship_from != "全部":
                filter_desc.append(f"发货地:{ship_from}")
            if status != "全部":
                filter_desc.append(f"状态:{status}")
            
            filter_str = " | ".join(filter_desc) if filter_desc else "全部"
            self.db_status_label.configure(text=f"{filter_str}: {len(products)} 条")
            
        except Exception as e:
            self.log(f"过滤失败: {e}", "error")
    
    def _validate_search_input(self, *args):
        """验证搜索输入"""
        pass
    
    def _open_product_page(self, product_id):
        """用浏览器打开商品页面"""
        import webbrowser
        from utils.database import get_shared_db
        
        db = get_shared_db()
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
        from utils.database import get_shared_db
        
        db = get_shared_db()
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
    
    def _on_db_tree_double_click(self, event):
        """数据库树双击事件"""
        item = self.db_tree.identify_row(event.y)
        column = self.db_tree.identify_column(event.x)
        if not item:
            return
        
        self.db_tree.selection_set(item)
        values = self.db_tree.item(item, 'values')
        if not values:
            return
        
        product_id = values[1]
        
        # 检查是否双击了可编辑列
        col_index = int(column.replace('#', '')) - 1
        if col_index == 6:  # shop_name (DS店铺)
            self._inline_edit_cell(item, product_id, 'ds_shop', 'shop_name', values[6], column)
            return
        elif col_index == 7:  # shop_product_id (DSID)
            self._inline_edit_cell(item, product_id, 'shop_product_id', 'shop_product_id', values[7], column, is_dsid=True)
            return
        
        self._show_product_detail(product_id)
    
    def _inline_edit_cell(self, item, product_id: str, db_field: str, tree_column: str, current_value: str, column, is_dsid: bool = False):
        """内联编辑单元格"""
        import tkinter as tk
        from utils.database import get_shared_db
        
        if current_value == '-':
            current_value = ''
        
        # 获取单元格位置
        x, y, width, height = self.db_tree.bbox(item, column)
        
        # 创建编辑框
        entry = tk.Entry(self.db_tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, current_value)
        entry.focus_set()
        entry.select_range(0, tk.END)
        
        db = get_shared_db()
        
        def save(event=None):
            new_value = entry.get().strip()
            
            if is_dsid and new_value and not new_value.isdigit():
                self.log("DSID必须为纯数字", "error")
                return
            
            try:
                db.update_product(product_id, {db_field: new_value if new_value else None})
                self.db_tree.set(item, column=tree_column, value=new_value if new_value else '-')
                self.log(f"已保存: {product_id} -> {db_field}: {new_value}")
            except Exception as e:
                self.log(f"保存失败: {e}", "error")
            
            entry.destroy()
        
        def cancel(event=None):
            entry.destroy()
        
        entry.bind('<Return>', save)
        entry.bind('<Escape>', cancel)
        entry.bind('<FocusOut>', save)
    
    def _show_db_context_menu(self, event):
        """显示数据库右键菜单"""
        item = self.db_tree.identify_row(event.y)
        if not item:
            return
        
        self.db_tree.selection_set(item)
        
        values = self.db_tree.item(item, 'values')
        if not values:
            return
        
        platform = values[0]
        product_id = values[1]
        shop_product_id = values[7]
        output_path = values[9] if len(values) > 9 else None
        
        context_menu = tk.Menu(self.root, tearoff=0)
        
        context_menu.add_command(label="查看商品详情", command=lambda: self._show_product_detail(product_id))
        context_menu.add_command(label="查看店铺信息", command=lambda: self._show_shop_info(product_id))
        context_menu.add_separator()
        
        if platform == '1688':
            context_menu.add_command(label="访问原址", command=lambda: self._open_product_page(product_id))
        elif platform == '京东':
            context_menu.add_command(label="访问原址", command=lambda: webbrowser.open(f"https://item.jd.com/{product_id}.html"))
        
        context_menu.add_command(label="显示资源", command=lambda: self._show_resources_dialog(product_id))
        context_menu.add_command(label="打开输出路径", command=lambda: self._open_output_directory(output_path))
        
        if shop_product_id and shop_product_id != '-':
            context_menu.add_command(label="访问店铺商品页", command=lambda: webbrowser.open(f"https://detail.1688.com/offer/{shop_product_id}.html"))
        
        context_menu.add_separator()
        
        consign_url = f"https://detail.1688.com/offer/{product_id}.html?sk=consign&biz=qianniu&isNeedCloseWinport=y"
        context_menu.add_command(label="铺货页面", command=lambda: self._copy_url_to_clipboard(consign_url, "铺货页面"))
        
        shop_new_url = f"https://item.upload.taobao.com/from1688/publish.htm?&sourceId={product_id}"
        context_menu.add_command(label="店铺上新", command=lambda: self._copy_url_to_clipboard(shop_new_url, "店铺上新"))
        
        if shop_product_id and shop_product_id != '-':
            edit_url = f"https://item.upload.taobao.com/sell/v2/publish.htm?itemId={shop_product_id}&fromAIPublish=true&newRouter=1&fromAICategory=true"
            context_menu.add_command(label="编辑商品", command=lambda: self._copy_url_to_clipboard(edit_url, "编辑商品"))
        
        context_menu.add_separator()
        context_menu.add_command(label="价格计算", command=lambda: self.open_pricing_tool(product_id))
        context_menu.add_command(label="在线采集", command=lambda: self._db_online_collect_for_item(product_id))
        context_menu.add_separator()
        context_menu.add_command(label="删除记录", command=self._delete_db_record)
        
        context_menu.post(event.x_root, event.y_root)
    
    def _copy_url_to_clipboard(self, url: str, name: str):
        """复制URL到剪贴板"""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.log(f"已复制{name}链接: {url}")
        except Exception as e:
            self.log(f"复制失败: {e}", "error")
    
    def _open_output_directory(self, output_path: str):
        """打开输出目录"""
        if output_path and output_path != '-' and os.path.exists(output_path):
            import subprocess
            subprocess.run(['explorer', output_path])
        else:
            # 尝试默认路径
            default_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'products', 'upload')
            if os.path.exists(default_path):
                import subprocess
                subprocess.run(['explorer', default_path])
            else:
                self.show_info("提示", "输出目录不存在")
    
    def _show_product_detail(self, product_id: str):
        """显示商品详情（products表完整记录）"""
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            product = db.get_product(product_id)
            
            if not product:
                self.show_info("提示", "未找到商品记录")
                return
            
            dialog = ctk.CTkToplevel(self.root)
            dialog.title(f"商品详情 - {product_id}")
            dialog.geometry("900x500")
            dialog.transient(self.root)
            dialog.grab_set()
            
            main_frame = ctk.CTkFrame(dialog)
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            columns = ("字段", "值")
            tree = ttk.Treeview(main_frame, columns=columns, show="headings", height=20)
            
            tree.heading("字段", text="字段")
            tree.heading("值", text="值")
            
            tree.column("字段", width=150)
            tree.column("值", width=700)
            
            field_names = {
                'product_id': '商品ID',
                'shop_product_id': 'DSID',
                'title': '标题',
                'description': '描述',
                'product_url': '商品链接',
                'product_code': '商品编码',
                'shop_id': '店铺ID',
                'status': '状态',
                'platform': '平台',
                'ship_from': '发货地',
                'sales_count': '销量',
                'min_order': '最小起订量',
                'shipping_cost': '运费',
                'unit_price': '一口价',
                'output_path': '输出路径',
                'resource_counts': '资源统计',
                'cost_prices': '成本价格',
                'selling_prices': '销售价格',
                'created_at': '创建时间',
                'updated_at': '更新时间'
            }
            
            for key, label in field_names.items():
                value = product.get(key, '')
                if value is None:
                    value = ''
                if isinstance(value, str) and len(value) > 100:
                    value = value[:100] + '...'
                tree.insert("", "end", iid=key, values=(label, str(value)))
            
            for key, value in product.items():
                if key not in field_names:
                    if isinstance(value, str) and len(value) > 100:
                        value = value[:100] + '...'
                    tree.insert("", "end", iid=key, values=(key, str(value)))
            
            rate_info = db.get_rate_info(product_id)
            if rate_info:
                tree.insert("", "end", iid="_rate_sep", values=("─── 评价信息 ───", ""))
                tree.insert("", "end", iid="good_rates", values=("好评数", rate_info.get('good_rates', 0)))
                tree.insert("", "end", iid="goods_grade", values=("商品评分", rate_info.get('goods_grade', '-')))
                
                impression_tags = rate_info.get('impression_tags', [])
                if impression_tags:
                    tags_str = ', '.join([f"{t.get('name', '')}({t.get('count', 0)})" for t in impression_tags[:5]])
                    tree.insert("", "end", iid="impression_tags", values=("印象标签", tags_str))
                
                common_tags = rate_info.get('common_tags', [])
                if common_tags:
                    tags_str = ', '.join([f"{t.get('name', '')}({t.get('count', 0)})" for t in common_tags[:5]])
                    tree.insert("", "end", iid="common_tags", values=("常见标签", tags_str))
            
            def on_double_click(event):
                selected = tree.selection()
                if not selected:
                    return
                
                item_id = selected[0]
                item = tree.item(item_id)
                field_label = item['values'][0]
                value = item['values'][1]
                
                if item_id == 'description' or field_label == '描述':
                    self._show_description_dialog(product_id, value)
                else:
                    dialog.clipboard_clear()
                    dialog.clipboard_append(value)
                    self.log(f"已复制: {value[:50]}...")
            
            tree.bind("<Double-1>", on_double_click)
            
            scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            tree.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            btn_frame = ctk.CTkFrame(dialog)
            btn_frame.pack(fill="x", pady=10)
            
            ctk.CTkLabel(btn_frame, text="双击行可复制值，描述字段双击查看属性", font=(self.available_font, self.font_size_small)).pack(side="left", padx=10)
            ctk.CTkButton(btn_frame, text="关闭", command=dialog.destroy, width=80).pack(side="right", padx=5)
            
        except Exception as e:
            self.log(f"获取商品详情失败: {e}", "error")
            self.show_info("错误", f"获取商品详情失败: {e}")
    
    def _show_description_dialog(self, product_id: str, description: str):
        """显示描述属性对话框"""
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            
            attributes = db.get_attributes(product_id)
            
            dialog = ctk.CTkToplevel(self.root)
            dialog.title(f"商品属性 - {product_id}")
            dialog.geometry("600x400")
            dialog.transient(self.root)
            dialog.grab_set()
            
            main_frame = ctk.CTkFrame(dialog)
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            columns = ("属性名", "属性值")
            tree = ttk.Treeview(main_frame, columns=columns, show="headings", height=15)
            
            tree.heading("属性名", text="属性名")
            tree.heading("属性值", text="属性值")
            
            tree.column("属性名", width=200)
            tree.column("属性值", width=350)
            
            if attributes:
                for attr in attributes:
                    attr_name = attr.get('attr_name', '') or attr.get('name', '')
                    attr_value = attr.get('attr_value', '') or attr.get('value', '')
                    tree.insert("", "end", values=(attr_name, attr_value))
            else:
                if description:
                    lines = description.split('\n')
                    for line in lines:
                        if ':' in line or '：' in line:
                            sep = '：' if '：' in line else ':'
                            parts = line.split(sep, 1)
                            if len(parts) == 2:
                                tree.insert("", "end", values=(parts[0].strip(), parts[1].strip()))
                        elif line.strip():
                            tree.insert("", "end", values=("", line.strip()))
                
                if not tree.get_children():
                    tree.insert("", "end", values=("-", "无属性数据"))
            
            def copy_value(event):
                selected = tree.selection()
                if selected:
                    item = tree.item(selected[0])
                    value = f"{item['values'][0]}: {item['values'][1]}"
                    dialog.clipboard_clear()
                    dialog.clipboard_append(value)
                    self.log(f"已复制: {value[:50]}...")
            
            tree.bind("<Double-1>", copy_value)
            
            scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            tree.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            btn_frame = ctk.CTkFrame(dialog)
            btn_frame.pack(fill="x", pady=10)
            
            ctk.CTkLabel(btn_frame, text="双击行可复制", font=(self.available_font, self.font_size_small)).pack(side="left", padx=10)
            ctk.CTkButton(btn_frame, text="关闭", command=dialog.destroy, width=80).pack(side="right", padx=5)
            
        except Exception as e:
            self.log(f"获取商品属性失败: {e}", "error")
            self.show_info("错误", f"获取商品属性失败: {e}")
    
    def _show_shop_info(self, product_id: str):
        """显示店铺信息（shops表记录）"""
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            product = db.get_product(product_id)
            
            if not product:
                self.show_info("提示", "未找到商品记录")
                return
            
            shop_id = product.get('shop_id', '')
            if not shop_id:
                self.show_info("提示", "该商品没有关联店铺信息")
                return
            
            shop = db.get_shop(shop_id)
            if not shop:
                self.show_info("提示", "未找到店铺记录")
                return
            
            dialog = ctk.CTkToplevel(self.root)
            dialog.title(f"店铺信息 - {shop_id}")
            dialog.geometry("800x400")
            dialog.transient(self.root)
            dialog.grab_set()
            
            main_frame = ctk.CTkFrame(dialog)
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            columns = ("字段", "值")
            tree = ttk.Treeview(main_frame, columns=columns, show="headings", height=15)
            
            tree.heading("字段", text="字段")
            tree.heading("值", text="值")
            
            tree.column("字段", width=150)
            tree.column("值", width=600)
            
            field_names = {
                'shop_id': '店铺ID',
                'shop_name': '店铺名称',
                'shop_url': '店铺链接',
                'platform': '平台',
                'rating': '评分',
                'sales': '销量',
                'location': '地址',
                'created_at': '创建时间',
                'updated_at': '更新时间'
            }
            
            for key, label in field_names.items():
                value = shop.get(key, '')
                if value is None:
                    value = ''
                if isinstance(value, str) and len(value) > 100:
                    value = value[:100] + '...'
                tree.insert("", "end", values=(label, str(value)))
            
            for key, value in shop.items():
                if key not in field_names:
                    if isinstance(value, str) and len(value) > 100:
                        value = value[:100] + '...'
                    tree.insert("", "end", values=(key, str(value)))
            
            def copy_value(event):
                selected = tree.selection()
                if selected:
                    item = tree.item(selected[0])
                    value = item['values'][1]
                    dialog.clipboard_clear()
                    dialog.clipboard_append(value)
                    self.log(f"已复制: {value[:50]}...")
            
            tree.bind("<Double-1>", copy_value)
            
            scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            tree.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            btn_frame = ctk.CTkFrame(dialog)
            btn_frame.pack(fill="x", pady=10)
            
            ctk.CTkLabel(btn_frame, text="双击行可复制值", font=(self.available_font, self.font_size_small)).pack(side="left", padx=10)
            ctk.CTkButton(btn_frame, text="关闭", command=dialog.destroy, width=80).pack(side="right", padx=5)
            
        except Exception as e:
            self.log(f"获取店铺信息失败: {e}", "error")
            self.show_info("错误", f"获取店铺信息失败: {e}")
    
    def _sort_db_column(self, col):
        """按列排序"""
        items = [(self.db_tree.set(item, col), item) for item in self.db_tree.get_children('')]
        
        if self._db_sort_column == col:
            self._db_sort_reverse = not self._db_sort_reverse
        else:
            self._db_sort_column = col
            self._db_sort_reverse = False
        
        try:
            items.sort(key=lambda x: float(x[0].replace('-', '0').replace('条', '')), reverse=self._db_sort_reverse)
        except ValueError:
            items.sort(key=lambda x: x[0], reverse=self._db_sort_reverse)
        
        for index, (val, item) in enumerate(items):
            self.db_tree.move(item, '', index)
    
    def _db_online_collect_for_item(self, product_id: str):
        """对指定商品进行在线采集"""
        url = f"https://detail.1688.com/offer/{product_id}.html"
        
        self.log(f"准备在线采集: {url}", "info")
        
        def collect_thread():
            try:
                from gui.online_collector_gui import get_collector
                
                collector = get_collector(self.log)
                
                if not collector.browser_started:
                    self.log("正在启动浏览器...")
                    if not collector.start_browser():
                        self.log("浏览器启动失败", "error")
                        return
                
                self.log("正在采集数据...")
                data = collector.collect_data_direct(product_id)
                
                if data:
                    self.log("数据采集成功，正在保存到数据库...")
                    self._save_online_collect_data(data)
                    self.log("数据已保存到数据库", "success")
                    
                    self.root.after(0, self._refresh_db_data)
                else:
                    self.log("数据采集失败", "error")
                    
            except Exception as e:
                self.log(f"在线采集异常: {e}", "error")
                import traceback
                traceback.print_exc()
        
        thread = threading.Thread(target=collect_thread, daemon=True)
        thread.start()
    
    def _show_resources_dialog(self, product_id: str):
        """显示资源链接对话框"""
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            resources = db.get_resources_by_type(product_id)
            
            product = db.get_product(product_id)
            output_path = product.get('output_path', '') if product else ''
            
            dialog = ctk.CTkToplevel(self.root)
            dialog.title(f"资源链接 - {product_id}")
            dialog.geometry("1100x650")
            dialog.transient(self.root)
            dialog.grab_set()
            
            main_frame = ctk.CTkFrame(dialog)
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            notebook = ctk.CTkTabview(main_frame)
            notebook.pack(fill="both", expand=True)
            
            type_order = [
                ('main_image', '主图'),
                ('color_image', '色卡图'),
                ('detail_image', '详情图'),
                ('video', '视频')
            ]
            
            for res_type, tab_name in type_order:
                res_list = resources.get(res_type, [])
                
                tab = notebook.add(tab_name)
                
                columns = ("文件名", "URL", "状态", "分辨率", "大小", "下载时间")
                tree = ttk.Treeview(tab, columns=columns, show="headings", height=15)
                
                tree.heading("文件名", text="文件名")
                tree.heading("URL", text="URL")
                tree.heading("状态", text="状态")
                tree.heading("分辨率", text="分辨率")
                tree.heading("大小", text="大小")
                tree.heading("下载时间", text="下载时间")
                
                tree.column("文件名", width=150)
                tree.column("URL", width=400)
                tree.column("状态", width=80)
                tree.column("分辨率", width=80)
                tree.column("大小", width=100)
                tree.column("下载时间", width=150)
                
                for res in res_list:
                    status = "已下载" if res.get('downloaded') else "待下载"
                    file_size = res.get('file_size', 0) or 0
                    size_str = f"{file_size / 1024:.1f} KB" if file_size > 0 else "-"
                    download_time = str(res.get('download_time', ''))[:19] if res.get('download_time') else "-"
                    
                    resolution = "-"
                    local_path = None
                    if output_path and res.get('output_filename'):
                        local_path = os.path.join(output_path, res.get('output_filename'))
                    
                    if local_path and os.path.exists(local_path):
                        try:
                            if res_type == 'video':
                                try:
                                    import cv2
                                    cap = cv2.VideoCapture(local_path)
                                    if cap.isOpened():
                                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                                        resolution = f"{width}x{height}"
                                        cap.release()
                                except ImportError:
                                    pass
                            else:
                                from PIL import Image
                                with Image.open(local_path) as img:
                                    resolution = f"{img.width}x{img.height}"
                        except Exception:
                            resolution = "-"
                    
                    tree.insert("", "end", values=(
                        res.get('output_filename', ''),
                        res.get('resource_url', '')[:80] + '...' if len(res.get('resource_url', '')) > 80 else res.get('resource_url', ''),
                        status,
                        resolution,
                        size_str,
                        download_time
                    ))
                
                if not res_list:
                    tree.insert("", "end", values=("-", "无数据", "-", "-", "-", "-"))
                
                scrollbar = ttk.Scrollbar(tab, orient="vertical", command=tree.yview)
                tree.configure(yscrollcommand=scrollbar.set)
                tree.pack(side="left", fill="both", expand=True)
                scrollbar.pack(side="right", fill="y")
                
                def copy_url(event, tree=tree):
                    selected = tree.selection()
                    if selected:
                        item = tree.item(selected[0])
                        url = item['values'][1]
                        if url.endswith('...'):
                            self.show_info("提示", "URL过长，请从数据库中查看完整URL")
                        else:
                            dialog.clipboard_clear()
                            dialog.clipboard_append(url)
                            self.log(f"已复制URL: {url[:50]}...")
                
                tree.bind("<Double-1>", copy_url)
            
            btn_frame = ctk.CTkFrame(main_frame)
            btn_frame.pack(fill="x", pady=10)
            
            def check_resources():
                self._check_resources_status(product_id, output_path)
                self._show_resources_dialog(product_id)
                dialog.destroy()
            
            def redownload_resources():
                dialog.destroy()
                self._download_product_resources(product_id, force=True)
            
            ctk.CTkButton(btn_frame, text="检查", command=check_resources, width=80).pack(side="left", padx=5)
            ctk.CTkButton(btn_frame, text="重新下载", command=redownload_resources, width=80).pack(side="left", padx=5)
            ctk.CTkButton(btn_frame, text="关闭", command=dialog.destroy, width=80).pack(side="right", padx=5)
            
        except Exception as e:
            self.log(f"获取资源链接失败: {e}", "error")
            self.show_info("错误", f"获取资源链接失败: {e}")
    
    def _check_resources_status(self, product_id: str, output_path: str):
        """检查资源状态并更新分辨率"""
        try:
            if not output_path or not os.path.exists(output_path):
                self.log("输出路径不存在", "warning")
                return
            
            from utils.database import get_shared_db
            db = get_shared_db()
            resources = db.get_resources_by_type(product_id)
            
            has_cv2 = False
            try:
                import cv2
                has_cv2 = True
            except ImportError:
                pass
            
            checked_count = 0
            for res_type in ['main_image', 'color_image', 'detail_image', 'video']:
                res_list = resources.get(res_type, [])
                
                for res in res_list:
                    local_path = None
                    if output_path and res.get('output_filename'):
                        local_path = os.path.join(output_path, res.get('output_filename'))
                    
                    if local_path and os.path.exists(local_path):
                        try:
                            resolution = "-"
                            file_size = os.path.getsize(local_path)
                            
                            if res_type == 'video':
                                if has_cv2:
                                    import cv2
                                    cap = cv2.VideoCapture(local_path)
                                    if cap.isOpened():
                                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                                        resolution = f"{width}x{height}"
                                        cap.release()
                            else:
                                from PIL import Image
                                with Image.open(local_path) as img:
                                    resolution = f"{img.width}x{img.height}"
                            
                            db.update('resources', {
                                'file_size': file_size,
                                'downloaded': True
                            }, 'id = ?', [res['id']])
                            
                            checked_count += 1
                        except Exception as e:
                            self.log(f"检查资源失败 {res.get('output_filename')}: {e}", "warning")
            
            self.log(f"已检查 {checked_count} 个资源", "success")
            
        except Exception as e:
            self.log(f"检查资源失败: {e}", "error")
    
    def _show_import_dialog(self):
        """显示导入对话框"""
        import_dialog = ctk.CTkToplevel(self.root)
        import_dialog.title("导入数据")
        import_dialog.geometry("950x850")
        import_dialog.transient(self.root)
        import_dialog.grab_set()
        
        main_frame = ctk.CTkFrame(import_dialog)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        # 格式说明
        format_frame = ctk.CTkFrame(main_frame)
        format_frame.pack(fill="x", pady=8)
        
        ctk.CTkLabel(
            format_frame, 
            text="导入格式说明",
            font=(self.available_font, self.font_size_large, "bold")
        ).pack(anchor="w", padx=8)
        
        ctk.CTkLabel(
            format_frame, 
            text="• 格式：URL [中间内容] DSID（空格分隔）\n• URL：商品链接，从中解析商品ID\n• 中间内容：可选，包含价格数字的文本\n• DSID：店铺商品ID（主要目的）",
            font=(self.available_font, self.font_size),
            justify="left"
        ).pack(anchor="w", padx=20)
        
        ctk.CTkLabel(
            format_frame, 
            text="示例：\n  https://detail.1688.com/offer/123456789.html ABC123\n  https://detail.1688.com/offer/123456789.html 【¥25.00】 ABC123",
            font=(self.available_font, self.font_size),
            text_color="gray"
        ).pack(anchor="w", padx=20, pady=5)
        
        # 文本输入区
        input_frame = ctk.CTkFrame(main_frame)
        input_frame.pack(fill="both", expand=True, pady=8)
        
        ctk.CTkLabel(input_frame, text="请粘贴数据（每行一条）：", font=(self.available_font, self.font_size)).pack(anchor="w", padx=8)
        
        text_input = ctk.CTkTextbox(input_frame, height=200, font=(self.available_font, self.font_size))
        text_input.pack(fill="both", expand=True, padx=8, pady=8)
        
        # 预览区
        preview_frame = ctk.CTkFrame(main_frame)
        preview_frame.pack(fill="both", expand=True, pady=8)
        
        ctk.CTkLabel(preview_frame, text="解析预览：", font=(self.available_font, self.font_size)).pack(anchor="w", padx=8)
        
        preview_columns = ("行号", "商品ID", "目标售价", "DSID", "状态")
        preview_tree = ttk.Treeview(preview_frame, columns=preview_columns, show="headings", height=8)
        
        preview_tree.heading("行号", text="行号")
        preview_tree.heading("商品ID", text="商品ID")
        preview_tree.heading("目标售价", text="目标售价")
        preview_tree.heading("DSID", text="DSID")
        preview_tree.heading("状态", text="状态")
        
        preview_tree.column("行号", width=50, anchor="center")
        preview_tree.column("商品ID", width=120, anchor="center")
        preview_tree.column("目标售价", width=100, anchor="center")
        preview_tree.column("DSID", width=120, anchor="center")
        preview_tree.column("状态", width=100, anchor="center")
        
        preview_scrollbar = ttk.Scrollbar(preview_frame, orient="vertical", command=preview_tree.yview)
        preview_tree.configure(yscrollcommand=preview_scrollbar.set)
        preview_tree.pack(side="left", fill="both", expand=True, padx=5)
        preview_scrollbar.pack(side="right", fill="y")
        
        # 存储解析结果
        parsed_data = []
        
        def parse_input():
            """解析输入数据"""
            nonlocal parsed_data
            parsed_data = []
            
            for item in preview_tree.get_children():
                preview_tree.delete(item)
            
            text = text_input.get("1.0", "end-1c")
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            for idx, line in enumerate(lines, 1):
                result = self._parse_import_line(line)
                parsed_data.append(result)
                
                status = "✓ 有效" if result['valid'] else f"✗ {result['error']}"
                status_color = "有效" if result['valid'] else "无效"
                
                preview_tree.insert("", "end", values=(
                    idx,
                    result.get('product_id', '-'),
                    result.get('target_price', '-'),
                    result.get('dsid', '-'),
                    status
                ))
            
            valid_count = sum(1 for d in parsed_data if d['valid'])
            count_label.configure(text=f"共 {len(lines)} 行，有效 {valid_count} 行")
        
        def confirm_import():
            """确认导入"""
            valid_data = [d for d in parsed_data if d['valid']]
            
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
                            update_data = {'updated_at': datetime.now()}
                            if target_price is not None:
                                update_data['target_price'] = target_price
                            if dsid:
                                update_data['shop_product_id'] = dsid
                            
                            db.update('products', update_data, 'product_id = ?', [product_id])
                        else:
                            insert_data = {
                                'product_id': product_id,
                                'status': 'pending',
                                'created_at': datetime.now()
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
            
            # 显示导入报告
            report = f"导入完成！\n\n成功: {success_count} 条\n失败: {fail_count} 条"
            if errors:
                report += f"\n\n失败原因:\n" + "\n".join(errors[:10])
                if len(errors) > 10:
                    report += f"\n... 还有 {len(errors) - 10} 条错误"
            
            self.show_info("导入报告", report)
            self._refresh_db_data()
            import_dialog.destroy()
        
        # 按钮区
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x", pady=10)
        
        count_label = ctk.CTkLabel(btn_frame, text="共 0 行", font=(self.available_font, self.font_size_small))
        count_label.pack(side="left", padx=10)
        
        ctk.CTkButton(btn_frame, text="解析预览", command=parse_input).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="确认导入", command=confirm_import).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="取消", command=import_dialog.destroy).pack(side="right", padx=5)
    
    def _parse_import_line(self, line: str) -> dict:
        """解析单行导入数据
        
        格式：URL [中间内容] DSID
        - URL开头
        - DSID在结尾（主要目的）
        - 中间内容可选，可能包含价格
        """
        import re
        
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
            
            # 提取URL（开头部分）
            url_match = re.match(r'(https?://[^\s]+)', line)
            if not url_match:
                result['error'] = '行首未找到URL'
                return result
            
            url = url_match.group(1)
            
            # 从URL中提取商品ID
            id_match = re.search(r'offer/(\d+)\.html', url)
            if not id_match:
                id_match = re.search(r'/(\d{10,})', url)
            
            if not id_match:
                result['error'] = 'URL中未找到商品ID'
                return result
            
            result['product_id'] = id_match.group(1)
            
            # 获取URL后的剩余部分
            remaining = line[len(url):].strip()
            
            if remaining:
                parts = remaining.split()
                
                if len(parts) >= 1:
                    # 最后一个字段作为DSID（必须是纯数字）
                    last_part = parts[-1]
                    if last_part.isdigit():
                        result['dsid'] = last_part
                    
                    # 如果有多个字段，中间部分可能包含价格
                    if len(parts) >= 2:
                        middle_parts = parts[:-1]  # 排除最后一个（DSID）
                        middle_text = ' '.join(middle_parts)
                        
                        # 1. 先尝试匹配【】中的价格
                        price_match = re.search(r'【[^】]*?(\d+\.?\d*)[^】]*?】', middle_text)
                        if price_match:
                            try:
                                result['target_price'] = float(price_match.group(1))
                            except ValueError:
                                pass
                        else:
                            # 2. 尝试从中间文本提取价格数字
                            # 匹配 "价格99.0" 或 "99.0" 这样的格式
                            price_patterns = [
                                r'价格\s*(\d+\.?\d*)',      # 价格99.0
                                r'售价\s*(\d+\.?\d*)',      # 售价99.0
                                r'[¥￥]\s*(\d+\.?\d*)',     # ¥99.0
                                r'(\d+\.?\d*)\s*元',        # 99.0元
                            ]
                            
                            for pattern in price_patterns:
                                match = re.search(pattern, middle_text)
                                if match:
                                    try:
                                        result['target_price'] = float(match.group(1))
                                        break
                                    except ValueError:
                                        pass
                            
                            # 3. 如果还是没有找到，尝试提取独立的数字
                            if result['target_price'] is None:
                                # 查找独立的数字（前后有空格或边界）
                                numbers = re.findall(r'(?<![a-zA-Z0-9.])(\d+\.?\d*)(?![a-zA-Z0-9.])', middle_text)
                                for num_str in numbers:
                                    try:
                                        num = float(num_str)
                                        # 假设价格在合理范围内（1-10000）
                                        if 1 <= num <= 10000:
                                            result['target_price'] = num
                                            break
                                    except ValueError:
                                        pass
            
            result['valid'] = True
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _save_online_collect_data(self, data):
        """保存在线采集的数据到数据库"""
        from utils.database import get_shared_db
        
        db = get_shared_db()
        
        try:
            columns = db.conn.execute("DESCRIBE sku_prices").fetchall()
            existing_columns = {col[0] for col in columns}
            required_columns = {'sku_id', 'color', 'size', 'price', 'discount_price', 
                              'can_book_count', 'sale_count', 'spec_id'}
            old_columns = {'sku_name', 'cost_price', 'original_price'}
            has_old_columns = bool(existing_columns & old_columns)
            
            if not required_columns.issubset(existing_columns) or has_old_columns:
                self.log("数据库: 开始迁移 sku_prices 表...")
                
                try:
                    db.conn.execute('DROP INDEX IF EXISTS idx_sku_prices_product_id')
                    db.conn.execute('DROP INDEX IF EXISTS idx_sku_prices_sku_id')
                except Exception:
                    pass
                
                db.conn.execute('DROP TABLE IF EXISTS sku_prices')
                
                db.conn.execute('''
                    CREATE TABLE sku_prices (
                        id INTEGER PRIMARY KEY,
                        product_id VARCHAR NOT NULL,
                        sku_id VARCHAR,
                        color VARCHAR,
                        size VARCHAR,
                        price DOUBLE,
                        discount_price DOUBLE,
                        can_book_count INTEGER,
                        sale_count INTEGER,
                        spec_id VARCHAR,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                db.conn.execute('CREATE INDEX IF NOT EXISTS idx_sku_prices_product_id ON sku_prices(product_id)')
                db.conn.execute('CREATE INDEX IF NOT EXISTS idx_sku_prices_sku_id ON sku_prices(sku_id)')
                
                self.log("数据库: sku_prices 表结构已更新")
        except Exception as e:
            self.log(f"数据库迁移失败: {e}")
        
        product_id = data.get('product_id', '')
        
        product_info = data.get('product_info', {})
        sku_prices = data.get('sku_prices', [])
        color_images = data.get('color_images', [])
        main_images = data.get('main_images', [])
        detail_images = data.get('detail_images', [])
        video_info = data.get('video_info', {})
        shop_info = data.get('shop_info', {})
        attributes = data.get('attributes', [])
        rate_info = data.get('rate_info', {})
        
        try:
            db.update_product(product_id, {
                'title': product_info.get('subject', ''),
            })
        except Exception:
            pass
        
        saved_shop = False
        if shop_info and shop_info.get('shop_id'):
            try:
                db.save_shop(
                    shop_id=shop_info.get('shop_id'),
                    shop_name=shop_info.get('shop_name'),
                    shop_url=shop_info.get('shop_url'),
                    shop_rating=shop_info.get('shop_rating'),
                    shop_address=shop_info.get('shop_address'),
                    platform='alibaba'
                )
                db.update_product(product_id, {'shop_id': shop_info.get('shop_id')})
                saved_shop = True
                self.log(f"已保存店铺信息: {shop_info.get('shop_name', shop_info.get('shop_id'))}")
            except Exception as e:
                self.log(f"保存店铺信息失败: {e}", "warning")
        
        saved_attr_count = 0
        if attributes:
            try:
                db.clear_attributes(product_id)
                for attr in attributes:
                    try:
                        db.insert_attribute(
                            product_id=product_id,
                            fid=attr.get('fid', ''),
                            attr_name=attr.get('name', ''),
                            attr_value=attr.get('value', '')
                        )
                        saved_attr_count += 1
                    except Exception as e:
                        self.log(f"保存属性失败: {e}", "warning")
            except Exception as e:
                self.log(f"保存属性失败: {e}", "warning")
        
        saved_rate = False
        if rate_info:
            try:
                db.save_rate_info(
                    product_id=product_id,
                    good_rates=rate_info.get('goodRates', 0),
                    goods_grade=rate_info.get('goodsGrade'),
                    impression_tags=rate_info.get('impressionTags', []),
                    common_tags=rate_info.get('commonTags', [])
                )
                saved_rate = True
                self.log(f"已保存评价信息")
            except Exception as e:
                self.log(f"保存评价信息失败: {e}", "warning")
        
        saved_sku_count = 0
        if sku_prices:
            for sku_data in sku_prices:
                try:
                    color = sku_data.get('color', '')
                    size = sku_data.get('size', '')
                    
                    if '代发' in color or '代发' in size:
                        continue
                    
                    sku_id = sku_data['skuId']
                    price = float(sku_data['price']) if sku_data['price'] else None
                    discount_price = float(sku_data['discountPrice']) if sku_data['discountPrice'] else None
                    can_book_count = int(sku_data['canBookCount']) if sku_data['canBookCount'] else None
                    sale_count = int(sku_data['saleCount']) if sku_data['saleCount'] else None
                    spec_id = sku_data['specId']
                    
                    db.insert_sku_price(product_id, sku_id, color, size, price, discount_price, can_book_count, sale_count, spec_id)
                    saved_sku_count += 1
                except Exception as e:
                    self.log(f"保存SKU价格失败: {e}", "warning")
        
        saved_main_count = 0
        if main_images:
            for idx, img_url in enumerate(main_images):
                try:
                    from config import FILE_NAMING
                    db.insert_resource(
                        product_id=product_id,
                        resource_type='main_image',
                        resource_url=img_url,
                        resource_name=f'main_{idx+1}',
                        output_filename=f'{FILE_NAMING["main_image_prefix"]}{idx+1}.jpg'
                    )
                    saved_main_count += 1
                except Exception as e:
                    self.log(f"保存主图失败: {e}", "warning")
        
        saved_color_count = 0
        if color_images:
            for color_data in color_images:
                try:
                    from config import FILE_NAMING, sanitize_filename
                    safe_name = sanitize_filename(color_data['name'])
                    db.insert_resource(
                        product_id=product_id,
                        resource_type='color_image',
                        resource_url=color_data['imageUrl'],
                        resource_name=color_data['name'],
                        output_filename=f'{FILE_NAMING["color_option_prefix"]}{safe_name}.jpg'
                    )
                    saved_color_count += 1
                except Exception as e:
                    self.log(f"保存色卡图失败: {e}", "warning")
        
        saved_detail_count = 0
        if detail_images:
            for idx, img_url in enumerate(detail_images):
                try:
                    from config import FILE_NAMING
                    filename = f'{FILE_NAMING["detail_image_prefix"]}{idx+1}.jpg'
                    result = db.insert_resource(
                        product_id=product_id,
                        resource_type='detail_image',
                        resource_url=img_url,
                        resource_name=f'detail_{idx+1}',
                        output_filename=filename
                    )
                    if result:
                        saved_detail_count += 1
                except Exception as e:
                    self.log(f"保存详情图失败: {e}", "warning")
        
        saved_video_count = 0
        if video_info and video_info.get('videoUrl'):
            try:
                db.insert_resource(
                    product_id=product_id,
                    resource_type='video',
                    resource_url=video_info['videoUrl'],
                    resource_name=video_info.get('title', 'video_1'),
                    output_filename='video_1.mp4'
                )
                saved_video_count += 1
            except Exception as e:
                self.log(f"保存视频失败: {e}", "warning")
        
        self.log(f"已保存 {saved_sku_count} 条SKU价格")
        self.log(f"已保存 {saved_main_count} 条主图")
        self.log(f"已保存 {saved_color_count} 条色卡图")
        self.log(f"已保存 {saved_detail_count} 条详情图")
        self.log(f"已保存 {saved_video_count} 条视频")
        self.log(f"已保存 {saved_attr_count} 条属性")
        
        db.close()
        
        total_resources = saved_main_count + saved_color_count + saved_detail_count + saved_video_count
        if total_resources > 0:
            self.log("开始下载资源...")
            self._download_product_resources(product_id)
    
    def _download_product_resources(self, product_id: str, force: bool = False):
        """下载商品资源
        
        Args:
            product_id: 商品ID
            force: 是否强制重新下载（忽略已存在的文件）
        """
        try:
            from utils.resource_downloader import ResourceDownloader, get_aria2c_path
            from utils.database import get_shared_db
            
            aria2c_path = get_aria2c_path()
            if not aria2c_path:
                self.log("aria2c 未找到，尝试自动下载...")
                try:
                    from utils.tool_downloader import ensure_aria2c
                    aria2c_path = ensure_aria2c()
                    if not aria2c_path:
                        self.log("aria2c 下载失败，请手动下载 aria2c.exe 放到 tools 目录", "error")
                        return
                    self.log(f"aria2c 已下载: {aria2c_path}", "success")
                except Exception as e:
                    self.log(f"aria2c 下载失败: {e}", "error")
                    return
            
            db = get_shared_db()
            product = db.get_product(product_id)
            
            if not product:
                self.log("未找到商品记录", "error")
                db.close()
                return
            
            output_path = product.get('output_path')
            if not output_path:
                project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                output_path = os.path.join(project_dir, 'products', 'upload', product_id)
                db.update_product(product_id, {'output_path': output_path})
            
            if not os.path.exists(output_path):
                os.makedirs(output_path, exist_ok=True)
            
            db.close()
            
            downloader = ResourceDownloader()
            
            if force:
                self.log(f"强制重新下载资源到: {output_path}")
            else:
                self.log(f"正在下载资源到: {output_path}")
            
            result = downloader.download_product_resources(product_id, output_path, force=force)
            
            if result.get('success'):
                downloaded = result.get('count', 0)
                self.log(f"资源下载完成: {downloaded} 个文件", "success")
            else:
                self.log(f"资源下载完成，部分文件可能失败", "warning")
            
        except ImportError as e:
            self.log(f"资源下载器不可用: {e}", "warning")
        except Exception as e:
            self.log(f"下载资源失败: {e}", "error")
            import traceback
            traceback.print_exc()
    
    def _delete_db_record(self):
        """删除选中的数据库记录"""
        selected_items = self.db_tree.selection()
        if not selected_items:
            self.show_info("提示", "请先选择要删除的记录")
            return
        
        item = selected_items[0]
        values = self.db_tree.item(item, 'values')
        if not values:
            return
        
        product_id = values[1]
        
        confirm = self.ask_yes_no("确认删除", f"确定要删除商品 {product_id} 的记录吗？\n\n此操作不可撤销！")
        if not confirm:
            return
        
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
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
        self.logger = GUILogger(self.log_text)
        
        # 设置全局 GUI 日志实例
        from utils.logger import set_gui_logger
        set_gui_logger(self.logger)
        
        self.queue_manager = QueueManager(self)
        
        self.context_menu_commands = ContextMenuCommands(self)
        
        self.context_menu_manager = ContextMenuManager(self.root, self)
        
        self.queue_tree.bind('<Button-3>', self.context_menu_manager.show_context_menu)
        
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
        top = ctk.CTkToplevel(self.root)
        top.title(title)
        top.transient(self.root)
        top.grab_set()
        
        width = 300
        height = 160
        
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()
        
        x = root_x + (root_width - width) // 2
        y = root_y + (root_height - height) // 2
        
        top.geometry(f"{width}x{height}+{x}+{y}")
        
        main_frame = ctk.CTkFrame(top, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=15)
        
        label = ctk.CTkLabel(main_frame, text=message, wraplength=250)
        label.pack(fill="both", expand=True)
        
        button = create_button(main_frame, "确定", top.destroy, 'primary')
        button.pack(pady=(10, 0))
        
        button.focus_set()
        top.bind('<Return>', lambda event: top.destroy())
    
    def ask_yes_no(self, title, message):
        """显示确认对话框，在 GUI 界面居中弹出，返回 True 或 False"""
        result = ctk.BooleanVar()
        result.set(False)
        
        top = ctk.CTkToplevel(self.root)
        top.title(title)
        top.transient(self.root)
        top.grab_set()
        
        width = 350
        height = 180
        
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()
        
        x = root_x + (root_width - width) // 2
        y = root_y + (root_height - height) // 2
        
        top.geometry(f"{width}x{height}+{x}+{y}")
        
        label = ctk.CTkLabel(top, text=message, padx=20, pady=20, wraplength=300)
        label.pack(fill="both", expand=True)
        
        button_frame = ctk.CTkFrame(top, fg_color="transparent")
        button_frame.pack(pady=10)
        
        yes_button = create_button(button_frame, "是", lambda: [result.set(True), top.destroy()], 'success')
        yes_button.pack(side="left", padx=10)
        
        no_button = create_button(button_frame, "否", lambda: [result.set(False), top.destroy()], 'secondary')
        no_button.pack(side="right", padx=10)
        
        no_button.focus_set()
        top.bind('<Return>', lambda event: [result.set(False), top.destroy()])
        top.bind('<Escape>', lambda event: [result.set(False), top.destroy()])
        
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
            self.output_frame.pack(fill="x", pady=(0, 5), before=self.content_frame)
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
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
            
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
        
        readme_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "README.md")
        if os.path.exists(readme_path):
            try:
                with open(readme_path, 'r', encoding='utf-8') as f:
                    help_content = f.read()
            except Exception as e:
                default_content = self.get_default_help_content()
                help_content = f"读取 README.md 文件失败: {str(e)}\n\n" + default_content
        else:
            help_content = self.get_default_help_content()
        
        self.help_text.config(state="normal")
        self.help_text.delete(1.0, "end")
        self.help_text.insert("end", help_content)
        self.help_text.config(state="disabled")
    
    def _load_help_frame(self):
        """加载帮助文档框架"""
        self._unload_help_frame()
        
        if not HAS_TKINTERWEB or not HAS_MARKDOWN:
            self.log("使用纯文本模式显示使用说明")
            self.help_text = ScrolledText(self.help_tab, width=100, height=30, wrap="word")
            self.help_text.pack(fill="both", expand=True, padx=10, pady=10)
            self.load_help_content()
            return
        
        try:
            self.help_frame = HtmlFrame(self.help_tab, messages_enabled=False)
            self.help_frame.pack(fill="both", expand=True, padx=10, pady=10)
            self.load_help_content_html()
            self.help_frame.bind('<Button-1>', self._on_link_click)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.log(f"HTML渲染加载失败: {e}", "warning")
            self._unload_help_frame()
            self.help_text = ScrolledText(self.help_tab, width=100, height=30, wrap="word")
            self.help_text.pack(fill="both", expand=True, padx=10, pady=10)
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
        
        readme_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "README.md")
        if os.path.exists(readme_path):
            try:
                with open(readme_path, 'r', encoding='utf-8') as f:
                    help_content = f.read()
            except Exception as e:
                help_content = f"# 错误\n\n读取 README.md 文件失败: {str(e)}"
        else:
            help_content = self.get_default_help_content()
        
        html_content = markdown.markdown(
            help_content,
            extensions=['tables', 'fenced_code', 'toc', 'nl2br']
        )
        
        full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: '{self.available_font}', 'Microsoft YaHei', '微软雅黑', sans-serif;
            font-size: {self.font_size + 2}px;
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
            font-size: {self.font_size + 8}px;
        }}
        h2 {{
            color: #34495e;
            border-bottom: 1px solid #bdc3c7;
            padding-bottom: 8px;
            margin-top: 25px;
            font-size: {self.font_size + 6}px;
        }}
        h3 {{
            color: #7f8c8d;
            margin-top: 20px;
            font-size: {self.font_size + 4}px;
        }}
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: Consolas, 'Courier New', monospace;
            font-size: {self.font_size}px;
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
        
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("编辑DSID")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("350x220")
        dialog.resizable(False, False)
        
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=15)
        
        label_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        label_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(label_frame, text="商品ID:").pack(side="left")
        ctk.CTkLabel(label_frame, text=product_id, text_color="gray").pack(side="left", padx=(5, 0))
        
        entry_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        entry_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(entry_frame, text="DSID:").pack(side="left")
        
        def validate_number(new_value):
            if new_value == "":
                return True
            if new_value.isdigit() and not new_value.startswith('0'):
                return True
            if new_value == '0':
                return True
            return False
        
        entry = ctk.CTkEntry(entry_frame, width=200)
        entry.pack(side="left", padx=(5, 0))
        entry.insert(0, current_shop_id)
        entry.focus_set()
        
        error_label = ctk.CTkLabel(main_frame, text="", text_color="red")
        error_label.pack(fill="x", pady=(0, 5))
        
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(5, 0))
        
        def save_shop_id():
            new_shop_id = entry.get().strip()
            
            if not new_shop_id:
                error_label.configure(text="DSID不能为空")
                return
            
            if not new_shop_id.isdigit():
                error_label.configure(text="DSID必须为纯数字")
                return
            
            if new_shop_id.startswith('0') and len(new_shop_id) > 1:
                error_label.configure(text="DSID不能以0开头")
                return
            
            try:
                int(new_shop_id)
            except ValueError:
                error_label.configure(text="DSID格式无效")
                return
            
            self.queue_tree.set(item, column="shop_id", value=new_shop_id)
            try:
                from utils.database import get_shared_db
                db = get_shared_db()
                db.update_shop_product_id(product_id, new_shop_id)
                self.log(f"已保存DSID: {product_id} -> {new_shop_id}")
            except Exception as e:
                self.log(f"保存DSID失败: {e}", "warning")
            dialog.destroy()
        
        create_button(btn_frame, "保存", save_shop_id, 'success').pack(side="left", padx=5)
        create_button(btn_frame, "取消", dialog.destroy, 'secondary').pack(side="left", padx=5)
        
        dialog.bind('<Return>', lambda e: save_shop_id())
        dialog.bind('<Escape>', lambda e: dialog.destroy())
    
    def open_file_explorer(self, path):
        """打开资源管理器到指定路径"""
        try:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
            
            import subprocess
            if sys.platform == 'win32':
                subprocess.run(['explorer', path])
            elif sys.platform == 'darwin':
                subprocess.run(['open', path])
            else:
                subprocess.run(['xdg-open', path])
            
            self.log(f"已打开资源管理器: {path}")
        except Exception as e:
            self.log(f"打开资源管理器失败: {str(e)}", "error")
    
    def _init_font_settings(self):
        """初始化字体设置"""
        # 默认值
        self.base_font_size = GUI_CONF.get('font_size', 10)
        self.font_scale = 0  # 字体缩放：-3 到 +5
        self.available_font = self._get_available_font()
        
        # 从数据库加载保存的设置
        self._load_font_settings()
        
        # 计算实际字体大小
        self._update_font_sizes()
    
    def _load_font_settings(self):
        """从数据库加载字体设置"""
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            if db:
                settings = db.get_setting('font_settings')
                if settings:
                    saved_font = settings.get('font', None)
                    self.font_scale = settings.get('scale', 0)
                    
                    # 验证保存的字体是否仍然可用
                    if saved_font:
                        import tkinter.font as tkfont
                        available_fonts = tkfont.families()
                        if saved_font in available_fonts or f'@{saved_font}' in available_fonts:
                            self.available_font = saved_font
        except Exception as e:
            print(f"加载字体设置失败: {e}")
    
    def _save_font_settings(self):
        """保存字体设置到数据库"""
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            if db:
                settings = {
                    'font': self.available_font,
                    'scale': self.font_scale
                }
                db.save_setting('font_settings', settings)
        except Exception as e:
            print(f"保存字体设置失败: {e}")
        """保存字体设置"""
        import json
        
        try:
            settings = {
                'font': self.available_font,
                'scale': self.font_scale
            }
            with open(self.font_settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存字体设置失败: {e}")
    
    def _update_font_sizes(self):
        """更新字体大小变量"""
        # 根据缩放计算实际字体大小
        scale_map = {
            -3: -4, -2: -3, -1: -2, 0: 0,
            1: 2, 2: 4, 3: 6, 4: 8, 5: 10
        }
        size_offset = scale_map.get(self.font_scale, 0)
        
        self.font_size = self.base_font_size + size_offset
        self.font_size_small = self.font_size - 2
        self.font_size_large = self.font_size + 2
        self.font_size_title = self.font_size + 10
        self.font_size_subtitle = self.font_size + 4
    
    def _apply_font_to_all(self):
        """应用字体设置到所有控件"""
        # 更新 ttk 样式
        self._configure_ttk_styles()
        
        # 更新所有 ctk 控件需要重新创建或更新
        # 这里我们通过刷新界面来实现
        self._refresh_ui_fonts()
    
    def _refresh_ui_fonts(self):
        """刷新界面字体"""
        # 更新队列标签
        if hasattr(self, 'queue_label'):
            self.queue_label.configure(font=(self.available_font, self.font_size_large, "bold"))
        
        # 更新日志标签
        if hasattr(self, 'log_label'):
            self.log_label.configure(font=(self.available_font, self.font_size_large, "bold"))
        
        # 更新日志文本框
        if hasattr(self, 'log_text'):
            self.log_text.configure(font=(self.available_font, self.font_size))
        
        # 更新按钮字体
        button_font = (self.available_font, self.font_size + 1)
        for btn_name in ['add_file_btn', 'add_dir_btn', 'remove_file_btn', 'clear_queue_btn', 
                         'pricing_btn', 'pause_btn', 'execute_btn', 'browse_btn',
                         'db_search_btn', 'db_refresh_btn', 'db_price_btn', 'db_delete_btn', 'db_close_btn',
                         'check_update_btn', 'reinstall_btn', 'enter_btn']:
            if hasattr(self, btn_name):
                getattr(self, btn_name).configure(font=button_font)
        
        # 更新关于选项卡
        if hasattr(self, 'title_label'):
            self.title_label.configure(font=(self.available_font, self.font_size_title, "bold"))
        if hasattr(self, 'version_label'):
            self.version_label.configure(font=(self.available_font, self.font_size_subtitle))
        if hasattr(self, 'author_label'):
            self.author_label.configure(font=(self.available_font, self.font_size_subtitle))
        if hasattr(self, 'github_label'):
            self.github_label.configure(font=(self.available_font, self.font_size_subtitle))
        if hasattr(self, 'desc_label'):
            self.desc_label.configure(font=(self.available_font, self.font_size_large))
        if hasattr(self, 'update_status_label'):
            self.update_status_label.configure(font=(self.available_font, self.font_size_large))
        
        # 更新数据库选项卡
        if hasattr(self, 'welcome_label'):
            self.welcome_label.configure(font=(self.available_font, self.font_size_large))
        
        # 刷新帮助文档
        if hasattr(self, 'help_frame') and self.help_frame:
            self.load_help_content_html()
    
    def _on_shift_press(self, event):
        """Shift键按下"""
        self._shift_pressed = True
    
    def _on_shift_release(self, event):
        """Shift键释放"""
        self._shift_pressed = False
    
    def _on_middle_click(self, event):
        """鼠标中键点击事件"""
        # 实时检测Shift键状态（通过event.state）
        # event.state 的第0位表示Shift键是否按下
        shift_pressed = bool(event.state & 0x1)
        if shift_pressed:
            self._show_font_menu(event)
    
    def _show_font_menu(self, event):
        """显示字体选择菜单（带漂亮样式）"""
        import tkinter.font as tkfont
        
        # 使用与GUI统一的颜色（Light模式）
        menu_bg = "#dbdbdb"  # gray86 - customtkinter Light模式背景色
        menu_fg = "#1a1a1a"  # 深色文字
        menu_active_bg = "#3B8ED0"  # customtkinter 按钮色
        menu_active_fg = "#ffffff"
        
        # 创建菜单并设置样式
        menu = tk.Menu(self.root, tearoff=0, 
                       bg=menu_bg, fg=menu_fg,
                       activebackground=menu_active_bg, activeforeground=menu_active_fg,
                       font=(self.available_font, 10),
                       relief="flat", borderwidth=0)
        
        # 获取配置中的字体列表
        font_families = GUI_CONF.get('font_families', [])
        available_fonts = tkfont.families()
        
        # 筛选可用的字体
        usable_fonts = []
        for font_name in font_families:
            if font_name in available_fonts or f'@{font_name}' in available_fonts:
                usable_fonts.append(font_name)
        
        # 添加标题
        menu.add_command(label="🎨 字体设置", state="disabled")
        menu.add_separator()
        
        # 添加字体选项
        font_menu = tk.Menu(menu, tearoff=0,
                           bg=menu_bg, fg=menu_fg,
                           activebackground=menu_active_bg, activeforeground=menu_active_fg,
                           font=(self.available_font, 10),
                           relief="flat", borderwidth=0)
        for font_name in usable_fonts:
            is_current = (font_name == self.available_font)
            label = f"✓ {font_name}" if is_current else f"   {font_name}"
            font_menu.add_command(
                label=label,
                command=lambda f=font_name: self._apply_font(f)
            )
        
        menu.add_cascade(label="📝 选择字体", menu=font_menu)
        
 # 添加字体缩放选项
        scale_menu = tk.Menu(menu, tearoff=0,
                            bg=menu_bg, fg=menu_fg,
                            activebackground=menu_active_bg, activeforeground=menu_active_fg,
                            font=(self.available_font, 10),
                            relief="flat", borderwidth=0)
        scale_options = [
            ("🔍 -3 (最小)", -3), ("🔍 -2", -2), ("🔍 -1", -1),
            ("✓ 0 (默认)", 0),
            ("🔍 +1", 1), ("🔍 +2", 2), ("🔍 +3", 3), ("🔍 +4", 4), ("🔍 +5 (最大)", 5)
        ]
        
        for label, scale in scale_options:
            is_current = (scale == self.font_scale)
            display_label = label if is_current else label.replace("✓", " ")
            scale_menu.add_command(
                label=display_label,
                command=lambda s=scale: self._apply_font_scale(s)
            )
        
        menu.add_cascade(label="🔤 字体缩放", menu=scale_menu)
        
        # 添加分隔线
        menu.add_separator()
        
        # 显示当前设置
        menu.add_command(label=f"📍 当前字体: {self.available_font}", state="disabled")
        scale_text = f"{self.font_scale:+d}" if self.font_scale != 0 else "0 (默认)"
        menu.add_command(label=f"📍 当前缩放: {scale_text}", state="disabled")
        menu.add_command(label=f"📍 实际大小: {self.font_size}px", state="disabled")
        
        # 显示菜单
        menu.post(event.x_root, event.y_root)
    
    def _apply_font(self, font_name):
        """应用选中的字体"""
        self.available_font = font_name
        self._update_font_sizes()
        self._apply_font_to_all()
        self._save_font_settings()
        self.log(f"字体已切换为: {font_name}")
    
    def _apply_font_scale(self, scale):
        """应用字体缩放"""
        self.font_scale = scale
        self._update_font_sizes()
        self._apply_font_to_all()
        self._save_font_settings()
        self.log(f"字体缩放已设置为: {scale:+d} (实际大小: {self.font_size}px)")
    
    def _on_shift_press(self, event):
        """Shift键按下"""
        self._shift_pressed = True
    
    def _on_shift_release(self, event):
        """Shift键释放"""
        self._shift_pressed = False
    
    def _on_right_click(self, event):
        """右键点击事件"""
        if self._shift_pressed:
            self._show_font_menu(event)
    
    def _configure_ttk_styles(self):
        """配置 ttk 控件的统一样式"""
        style = ttk.Style()
        
        # 配置 Treeview 样式
        style.configure(
            "Treeview",
            font=(self.available_font, self.font_size),
            rowheight=25
        )
        style.configure(
            "Treeview.Heading",
            font=(self.available_font, self.font_size_large, "bold")
        )
        
        # 配置 Notebook 样式（选项卡文字减小一号）
        style.configure(
            "TNotebook.Tab",
            font=(self.available_font, self.font_size - 1)
        )
    
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
    
    def context_redownload_resources(self):
        """右键菜单：重新下载资源"""
        self.context_menu_commands.context_redownload_resources()
    
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
    
    def open_pricing_tool(self, selected_product_id=None):
        """打开价格计算工具"""
        try:
            from gui.pricing_gui import PricingToolGUI
            import re
            
            if selected_product_id is None:
                selected_items = self.queue_tree.selection()
                
                if selected_items:
                    item = selected_items[0]
                    values = self.queue_tree.item(item, 'values')
                    
                    if values and len(values) > 2:
                        display_name = values[2]
                        match = re.search(r'(\d{10,12})\.html$', display_name)
                        if match:
                            selected_product_id = match.group(1)
            
            pricing_window = ctk.CTkToplevel(self.root)
            if selected_product_id:
                pricing_window.title(f"商品定价计算工具 - {selected_product_id}")
            else:
                pricing_window.title("商品定价计算工具")
            pricing_window.geometry("1000x780")
            pricing_window.transient(self.root)
            pricing_window.grab_set()
            pricing_window.focus_force()
            pricing_window.lift()
            
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
            self._start_download_update(version_info)
        else:
            result = self.ask_yes_no("发现新版本", message)
            if result:
                self._start_download_update(version_info)
    
    def open_online_collector(self):
        """在线采集 - 直接打开选中商品的原始页面"""
        try:
            from gui.online_collector_gui import start_online_collect, get_product_id_from_filename
            import re
            
            selected_items = self.queue_tree.selection()
            
            if not selected_items:
                self.show_info("提示", "请先选择一个商品文件")
                return
            
            item = selected_items[0]
            values = self.queue_tree.item(item, 'values')
            
            product_id = None
            if values and len(values) > 2:
                display_name = values[2]
                product_id = get_product_id_from_filename(display_name)
            
            if not product_id:
                self.show_info("提示", "无法从选中文件获取商品ID")
                return
            
            self.log(f"在线采集: 商品ID {product_id}")
            start_online_collect(self.log, product_id=product_id)
            
        except ImportError as e:
            self.log(f"无法加载在线采集模块: {e}")
        except Exception as e:
            self.log(f"在线采集失败: {e}")


def main():
    """主函数"""
    if HAS_DND:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk()
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")
    else:
        root = ctk.CTk()
    app = AlibabaScraperGUI(root)
    app.run()


if __name__ == "__main__":
    main()
