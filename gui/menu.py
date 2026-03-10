#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI菜单模块
"""

import tkinter as tk
from config import GUI_CONF


class ContextMenuManager:
    """上下文菜单管理器"""
    
    def __init__(self, root, parent_widget):
        """初始化上下文菜单管理器
        
        Args:
            root: 主窗口实例
            parent_widget: 要绑定右键菜单的父控件
        """
        self.root = root
        self.parent_widget = parent_widget
        self.context_menu = None
        
        # 复选框状态管理
        self.checkbox_vars = {
            'with_animated': tk.BooleanVar(value=False),
            'webp_support': tk.BooleanVar(value=False),
            'webp_main': tk.BooleanVar(value=False),
            'webp_color': tk.BooleanVar(value=False)
        }
        
        self._create_context_menu()
    
    def _create_context_menu(self):
        """创建上下文菜单"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        
        # 创建图像优化子菜单
        image_menu = tk.Menu(self.context_menu, tearoff=0)
        
        # 添加支持动图选项（放在首行，与--with-animated参数等价）
        image_menu.add_checkbutton(
            label="支持动图",
            variable=self.checkbox_vars['with_animated']
        )
        
        # 创建WebP支持子菜单
        webp_menu = tk.Menu(image_menu, tearoff=0)
        webp_menu.add_checkbutton(
            label="支持主图",
            variable=self.checkbox_vars['webp_main'],
            state=tk.DISABLED  # 初始禁用，只有webp_support勾选时才启用
        )
        webp_menu.add_checkbutton(
            label="支持色卡图",
            variable=self.checkbox_vars['webp_color'],
            state=tk.DISABLED  # 初始禁用，只有webp_support勾选时才启用
        )
        
        # 添加WebP支持菜单项（带复选框）
        image_menu.add_checkbutton(
            label="WebP支持",
            variable=self.checkbox_vars['webp_support'],
            command=self._toggle_webp_options
        )
        image_menu.add_cascade(
            label="WebP选项",
            menu=webp_menu,
            state=tk.DISABLED  # 初始禁用，只有webp_support勾选时才启用
        )
        
        # 添加分隔线
        image_menu.add_separator()
        
        # 添加执行操作菜单项
        image_menu.add_command(
            label="执行操作",
            command=self._execute_image_optimization
        )
        
        # 将图像优化子菜单添加到主菜单
        self.context_menu.add_cascade(
            label="图像优化",
            menu=image_menu
        )
        
        # 添加其他原有菜单项
        self.context_menu.add_command(
            label="资源打包",
            command=lambda: self._call_command("context_pack_files")
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="重新采集",
            command=lambda: self._call_command("context_recollect")
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="访问原址",
            command=lambda: self._call_command("context_visit_url")
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="铺货页面",
            command=lambda: self._call_command("context_consign_page")
        )
        self.context_menu.add_command(
            label="店铺上新",
            command=lambda: self._call_command("context_shop_new")
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="打开目录",
            command=lambda: self._call_command("context_open_folder")
        )
        self.context_menu.add_command(
            label="删除项目",
            command=lambda: self._call_command("context_delete_item")
        )
    
    def _toggle_webp_options(self):
        """切换WebP选项的启用状态"""
        webp_enabled = self.checkbox_vars['webp_support'].get()
        state = tk.NORMAL if webp_enabled else tk.DISABLED
        
        # 获取WebP选项子菜单并设置状态
        webp_menu = self.context_menu.nametowidget(self.context_menu.entrycget("图像优化", "menu"))
        webp_menu.entryconfig("WebP选项", state=state)
        
        # 获取WebP选项子菜单的子菜单项并设置状态
        webp_submenu = webp_menu.nametowidget(webp_menu.entrycget("WebP选项", "menu"))
        webp_submenu.entryconfig("支持主图", state=state)
        webp_submenu.entryconfig("支持色卡图", state=state)
    
    def _execute_image_optimization(self):
        """执行图像优化操作"""
        # 收集复选框状态
        with_animated = self.checkbox_vars['with_animated'].get()
        webp_support = self.checkbox_vars['webp_support'].get()
        webp_main = self.checkbox_vars['webp_main'].get()
        webp_color = self.checkbox_vars['webp_color'].get()
        
        # 调用父控件的执行方法，传递复选框状态
        if hasattr(self.parent_widget, "context_stitch_images_with_options"):
            self.parent_widget.context_stitch_images_with_options(
                with_animated=with_animated,
                webp_support=webp_support,
                webp_main=webp_main,
                webp_color=webp_color
            )
    
    def _call_command(self, command_name):
        """调用父控件的命令方法
        
        Args:
            command_name: 要调用的方法名
        """
        if hasattr(self.parent_widget, command_name):
            command = getattr(self.parent_widget, command_name)
            command()
    
    def show_context_menu(self, event):
        """显示右键菜单
        
        Args:
            event: 右键点击事件
        """
        item = self.parent_widget.queue_tree.identify_row(event.y)
        if item:
            self.parent_widget.queue_tree.selection_set(item)
            values = self.parent_widget.queue_tree.item(item, 'values')
            if values:
                file_index = int(values[0]) - 1  # 序号从1开始
                if 0 <= file_index < len(self.parent_widget.queue_manager.file_queue):
                    file_path = self.parent_widget.queue_manager.file_queue[file_index]
                    status = self.parent_widget.file_status.get(file_path, "none")
                    
                    # 根据状态启用/禁用菜单项
                    # 只有执行过采集（success、error、exists或duplicate）才启用前三项
                    state = tk.NORMAL if status in ["success", "error", "exists", "duplicate"] else tk.DISABLED
                    
                    self.context_menu.entryconfig("图像优化", state=state)
                    self.context_menu.entryconfig("资源打包", state=state)
                    self.context_menu.entryconfig("重新采集", state=state)
                    
                    # 显示菜单
                    self.context_menu.post(event.x_root, event.y_root)
