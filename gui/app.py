#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主应用模块 - CustomTkinter 版本
"""

import os
import sys
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk
import multiprocessing

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
        
        self.pricing_btn = create_button(self.button_frame, "价格计算", self.open_pricing_tool, 'primary')
        self.pricing_btn.pack(side="left", padx=3)
        
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
        
        db_columns = ("product_id", "shop_product_id", "title", "shop_name", "ship_from", "resource_counts", "sku_prices", "output_path", "status", "created_at")
        self.db_tree = ttk.Treeview(self.db_tree_frame, columns=db_columns, show="headings", selectmode="browse")
        
        self.db_tree.heading("product_id", text="商品ID")
        self.db_tree.heading("shop_product_id", text="DSID")
        self.db_tree.heading("title", text="商品标题")
        self.db_tree.heading("shop_name", text="店铺")
        self.db_tree.heading("ship_from", text="发货地")
        self.db_tree.heading("resource_counts", text="资源")
        self.db_tree.heading("sku_prices", text="SKU")
        self.db_tree.heading("output_path", text="输出路径")
        self.db_tree.heading("status", text="状态")
        self.db_tree.heading("created_at", text="创建时间")
        
        self.db_tree.column("product_id", width=105, anchor="center")
        self.db_tree.column("shop_product_id", width=85, anchor="center")
        self.db_tree.column("title", width=180, anchor="w")
        self.db_tree.column("shop_name", width=90, anchor="w")
        self.db_tree.column("ship_from", width=70, anchor="center")
        self.db_tree.column("resource_counts", width=50, anchor="center")
        self.db_tree.column("sku_prices", width=40, anchor="center")
        self.db_tree.column("output_path", width=150, anchor="w")
        self.db_tree.column("status", width=50, anchor="center")
        self.db_tree.column("created_at", width=120, anchor="center")
        
        db_scrollbar = ttk.Scrollbar(self.db_tree_frame, orient="vertical", command=self.db_tree.yview)
        self.db_tree.configure(yscrollcommand=db_scrollbar.set)
        
        self.db_tree.pack(side="left", fill="both", expand=True)
        db_scrollbar.pack(side="right", fill="y")
        
        self.db_tree.bind('<Double-Button-1>', self._db_tree_double_click)
        
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
        
        self.db_refresh_btn = create_button(self.db_btn_frame, "刷新", self._refresh_db_data, 'secondary', width=60)
        self.db_refresh_btn.pack(side="left", padx=5)
        
        self.db_price_btn = create_button(self.db_btn_frame, "价格计算", self._open_pricing_for_selected, 'primary', width=70)
        self.db_price_btn.pack(side="left", padx=5)
        
        self.db_delete_btn = create_button(self.db_btn_frame, "删除选中", self._delete_db_record, 'danger', width=70)
        self.db_delete_btn.pack(side="left", padx=5)
        
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
        
        gitee_url = "https://gitee.com/jiyunui/1688/"
        self.gitee_label = ctk.CTkLabel(
            about_frame,
            text=f"Gitee: {gitee_url}",
            font=(self.available_font, self.font_size_subtitle),
            text_color="#1f6feb",
            cursor="hand2"
        )
        self.gitee_label.pack(pady=5)
        self.gitee_label.bind("<Button-1>", lambda e: self._open_url(gitee_url))
        self.gitee_label.bind("<Enter>", lambda e: self.gitee_label.configure(text_color="#1a5fb7"))
        self.gitee_label.bind("<Leave>", lambda e: self.gitee_label.configure(text_color="#1f6feb"))
        
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
                if len(title) > 18:
                    title = title[:18] + '...'
                
                product_id = product.get('product_id', '')
                
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
                        shop_name = shop.get('shop_name', '')[:10]
                
                ship_from = product.get('ship_from', '') or '-'
                
                status = product.get('status', '') or '-'
                if status == 'pending':
                    status = '待处理'
                elif status == 'completed':
                    status = '完成'
                
                self.db_tree.insert("", "end", values=(
                    product_id,
                    product.get('shop_product_id', ''),
                    title,
                    shop_name,
                    ship_from,
                    resource_counts_str,
                    sku_prices_str,
                    output_path,
                    status,
                    str(product.get('created_at', ''))[:16]
                ))
            
            self.db_status_label.configure(text=f"共 {len(products)} 条")
        except Exception as e:
            self.log(f"读取数据库失败: {e}", "error")
            self.db_status_label.configure(text="读取失败")
    
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
                if len(title) > 18:
                    title = title[:18] + '...'
                
                product_id = product.get('product_id', '')
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
                        shop_name = shop.get('shop_name', '')[:10]
                
                ship_from = product.get('ship_from', '') or '-'
                
                status = product.get('status', '') or '-'
                if status == 'pending':
                    status = '待处理'
                elif status == 'completed':
                    status = '完成'
                
                self.db_tree.insert("", "end", values=(
                    product_id,
                    product.get('shop_product_id', ''),
                    title,
                    shop_name,
                    ship_from,
                    resource_counts_str,
                    sku_prices_str,
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
        for item in self.db_tree.get_children():
            self.db_tree.delete(item)
        
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            
            if platform == "全部":
                products = db.get_all_products()
            else:
                products = db.search_products_full(platform=platform)
            
            for product in products:
                output_path = product.get('output_path', '') or ''
                if len(output_path) > 18:
                    output_path = '...' + output_path[-15:]
                
                title = product.get('title', '') or ''
                if len(title) > 18:
                    title = title[:18] + '...'
                
                product_id = product.get('product_id', '')
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
                        shop_name = shop.get('shop_name', '')[:10]
                
                ship_from = product.get('ship_from', '') or '-'
                
                status = product.get('status', '') or '-'
                if status == 'pending':
                    status = '待处理'
                elif status == 'completed':
                    status = '完成'
                
                self.db_tree.insert("", "end", values=(
                    product_id,
                    product.get('shop_product_id', ''),
                    title,
                    shop_name,
                    ship_from,
                    resource_counts_str,
                    sku_prices_str,
                    output_path,
                    status,
                    str(product.get('created_at', ''))[:16]
                ))
            
            self.db_status_label.configure(text=f"{platform}: {len(products)} 条")
            
        except Exception as e:
            self.log(f"过滤失败: {e}", "error")
    
    def _validate_search_input(self, *args):
        """验证搜索输入，只允许数字"""
        current = self.db_search_var.get()
        if current and not current.isdigit():
            self.db_search_var.set(''.join(filter(str.isdigit, current)))
    
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
    
    def _db_tree_double_click(self, event):
        """双击数据库记录"""
        region = self.db_tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        
        column = self.db_tree.identify_column(event.x)
        item = self.db_tree.identify_row(event.y)
        
        if not item:
            return
        
        values = self.db_tree.item(item, 'values')
        if not values:
            return
        
        product_id = values[0]
        
        if column == "#1":
            self._open_product_page(product_id)
        elif column == "#2":
            self._open_shop_page(product_id)
        elif column == "#6":
            self._show_resources_dialog(product_id)
    
    def _show_resources_dialog(self, product_id: str):
        """显示资源链接对话框"""
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            resources = db.get_resources_by_type(product_id)
            
            dialog = ctk.CTkToplevel(self.root)
            dialog.title(f"资源链接 - {product_id}")
            dialog.geometry("900x600")
            dialog.transient(self.root)
            dialog.grab_set()
            
            main_frame = ctk.CTkFrame(dialog)
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            notebook = ctk.CTkTabview(main_frame)
            notebook.pack(fill="both", expand=True)
            
            for res_type, res_list in resources.items():
                if not res_list:
                    continue
                
                # 资源类型中文映射
                type_names = {
                    'main_image': '主图',
                    'color_image': '色卡图',
                    'detail_image': '详情图',
                    'video': '视频'
                }
                tab_name = type_names.get(res_type, res_type.replace('_', ' ').title())
                tab = notebook.add(tab_name)
                
                columns = ("文件名", "URL", "状态", "大小", "下载时间")
                tree = ttk.Treeview(tab, columns=columns, show="headings", height=15)
                
                tree.heading("文件名", text="文件名")
                tree.heading("URL", text="URL")
                tree.heading("状态", text="状态")
                tree.heading("大小", text="大小")
                tree.heading("下载时间", text="下载时间")
                
                tree.column("文件名", width=150)
                tree.column("URL", width=400)
                tree.column("状态", width=80)
                tree.column("大小", width=100)
                tree.column("下载时间", width=150)
                
                for res in res_list:
                    status = "已下载" if res.get('downloaded') else "待下载"
                    file_size = res.get('file_size', 0) or 0
                    size_str = f"{file_size / 1024:.1f} KB" if file_size > 0 else "-"
                    download_time = str(res.get('download_time', ''))[:19] if res.get('download_time') else "-"
                    
                    tree.insert("", "end", values=(
                        res.get('output_filename', ''),
                        res.get('resource_url', '')[:80] + '...' if len(res.get('resource_url', '')) > 80 else res.get('resource_url', ''),
                        status,
                        size_str,
                        download_time
                    ))
                
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
            
            ctk.CTkButton(btn_frame, text="关闭", command=dialog.destroy).pack(side="right", padx=5)
            
        except Exception as e:
            self.log(f"获取资源链接失败: {e}", "error")
            self.show_info("错误", f"获取资源链接失败: {e}")
    
    def _open_pricing_for_selected(self):
        """为选中的数据库记录打开价格计算工具"""
        selected_items = self.db_tree.selection()
        if not selected_items:
            self.show_info("提示", "请先选择一条记录")
            return
        
        item = selected_items[0]
        values = self.db_tree.item(item, 'values')
        if values:
            product_id = values[0]
            self.open_pricing_tool(product_id)
    
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
        
        product_id = values[0]
        
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
        dialog.geometry("350x180")
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
        if hasattr(self, 'gitee_label'):
            self.gitee_label.configure(font=(self.available_font, self.font_size_subtitle))
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
