#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ctypes
import os
import sys

# 隐藏控制台窗口（仅在Windows系统中）
def hide_console():
    if os.name == 'nt':  # Windows系统
        try:
            # 获取当前进程句柄
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd != 0:
                # 隐藏窗口
                ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0
                # 更新窗口状态
                ctypes.windll.user32.UpdateWindow(hwnd)
        except:
            pass

# 在导入时执行隐藏控制台
hide_console()

"""
1688详情页资源采集工具 - GUI 版本

功能：
1. 支持添加单个 HTML 文件到处理队列
2. 支持添加目录中所有 HTML 文件到处理队列
3. 显示处理队列中的文件列表
4. 执行主程序处理队列中的文件
5. 显示执行过程中的日志输出

使用说明：
1. 点击 "添加文件" 按钮添加单个 HTML 文件
2. 点击 "添加目录" 按钮添加目录中所有 HTML 文件
3. 在列表中选择文件后点击 "移除文件" 按钮移除选中的文件
4. 点击 "清空队列" 按钮清空所有队列中的文件
5. 点击 "执行" 按钮开始处理队列中的文件
6. 点击 "暂停" 按钮暂停队列处理
7. 在下方日志窗口查看执行过程和结果
"""

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

# 尝试导入 scrolledtext，如果失败则使用替代方案
try:
    from tkinter import scrolledtext
except ImportError:
    # 如果 scrolledtext 不可用，创建一个简单的替代类
    class ScrolledText:
        def __init__(self, master=None, **kwargs):
            self.frame = tk.Frame(master)
            self.scrollbar = tk.Scrollbar(self.frame, orient=tk.VERTICAL)
            self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.text = tk.Text(self.frame, yscrollcommand=self.scrollbar.set, **kwargs)
            self.text.pack(fill=tk.BOTH, expand=True)
            self.scrollbar.config(command=self.text.yview)
        
        def pack(self, **kwargs):
            self.frame.pack(**kwargs)
        
        def config(self, **kwargs):
            self.text.config(**kwargs)
        
        def insert(self, *args, **kwargs):
            self.text.insert(*args, **kwargs)
        
        def see(self, *args, **kwargs):
            self.text.see(*args, **kwargs)
        
        def delete(self, *args, **kwargs):
            self.text.delete(*args, **kwargs)
        
        def tag_configure(self, *args, **kwargs):
            self.text.tag_configure(*args, **kwargs)
    
    # 创建 scrolledtext 命名空间
    class scrolledtext:
        ScrolledText = ScrolledText

import subprocess
import threading

class AlibabaScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("1688详情页资源采集工具")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 设置窗口图标（如果有）
        # if os.path.exists("icon.ico"):
        #     self.root.iconbitmap("icon.ico")
        
        # 队列列表
        self.file_queue = []
        # 状态管理：记录每个文件的执行状态 {file_path: status}
        # status: "none" (未执行), "success" (成功), "error" (失败)
        self.file_status = {}
        
        # 执行状态
        self.is_paused = False
        self.is_executing = False
        self.current_process = None
        
        # 创建主框架
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建标签页
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 创建处理队列标签页
        self.queue_tab = tk.Frame(self.notebook)
        self.notebook.add(self.queue_tab, text="处理队列")
        
        # 创建使用说明标签页
        self.help_tab = tk.Frame(self.notebook)
        self.notebook.add(self.help_tab, text="使用说明")
        
        # 处理队列标签页内容
        # 创建顶部按钮框架
        self.button_frame = tk.Frame(self.queue_tab)
        self.button_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 添加文件按钮
        self.add_file_btn = tk.Button(self.button_frame, text="添加文件 (A)", command=self.add_file, width=15)
        self.add_file_btn.pack(side=tk.LEFT, padx=5)
        
        # 添加目录按钮
        self.add_dir_btn = tk.Button(self.button_frame, text="添加目录 (D)", command=self.add_directory, width=15)
        self.add_dir_btn.pack(side=tk.LEFT, padx=5)
        
        # 移除文件按钮
        self.remove_file_btn = tk.Button(self.button_frame, text="移除文件 (Del)", command=self.remove_file, width=15)
        self.remove_file_btn.pack(side=tk.LEFT, padx=5)
        
        # 清空队列按钮
        self.clear_queue_btn = tk.Button(self.button_frame, text="清空队列", command=self.clear_queue, width=12)
        self.clear_queue_btn.pack(side=tk.LEFT, padx=5)
        
        # 执行按钮
        self.execute_btn = tk.Button(self.button_frame, text="执行 (Enter)", command=self.execute, width=15, bg="#4CAF50", fg="white")
        self.execute_btn.pack(side=tk.RIGHT, padx=5)
        
        # 暂停按钮
        self.pause_btn = tk.Button(self.button_frame, text="暂停 (P)", command=self.pause, width=15, bg="#FF9800", fg="white", state=tk.DISABLED)
        self.pause_btn.pack(side=tk.RIGHT, padx=5)
        
        # 添加快捷键绑定
        self.root.bind('<a>', lambda event: self.add_file())
        self.root.bind('<A>', lambda event: self.add_file())
        self.root.bind('<d>', lambda event: self.add_directory())
        self.root.bind('<D>', lambda event: self.add_directory())
        self.root.bind('<Delete>', lambda event: self.remove_file())
        self.root.bind('<p>', lambda event: self.pause())
        self.root.bind('<P>', lambda event: self.pause())
        self.root.bind('<Return>', lambda event: self.execute())
        self.root.bind('<Pause>', lambda event: self.pause())
        
        # 创建队列和日志框架
        self.content_frame = tk.Frame(self.queue_tab)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 队列表格
        self.queue_frame = tk.LabelFrame(self.content_frame, text="处理队列")
        self.queue_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP, pady=(0, 10))
        
        # 创建表格
        self.queue_tree = ttk.Treeview(self.queue_frame, columns=("index", "status", "name", "date", "path"), show="headings")
        
        # 设置列标题
        self.queue_tree.heading("index", text="序号")  # 序号列不用排序功能
        self.queue_tree.heading("status", text="状态", command=lambda: self.sort_treeview("status"))
        self.queue_tree.heading("name", text="文件名", command=lambda: self.sort_treeview("name"))
        self.queue_tree.heading("date", text="修改日期", command=lambda: self.sort_treeview("date"))
        self.queue_tree.heading("path", text="路径", command=lambda: self.sort_treeview("path"))
        
        # 设置列宽
        self.queue_tree.column("index", width=50, anchor=tk.CENTER)
        self.queue_tree.column("status", width=80, anchor=tk.CENTER)
        self.queue_tree.column("name", width=150, anchor=tk.W)
        self.queue_tree.column("date", width=120, anchor=tk.CENTER)
        self.queue_tree.column("path", width=350, anchor=tk.W)
        
        # 添加滚动条
        self.queue_scrollbar = ttk.Scrollbar(self.queue_frame, orient=tk.VERTICAL, command=self.queue_tree.yview)
        self.queue_tree.configure(yscroll=self.queue_scrollbar.set)
        
        # 布局
        self.queue_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.queue_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # 绑定双击事件
        self.queue_tree.bind('<Double-1>', self.on_treeview_double_click)
        
        # 绑定右键菜单
        self.queue_tree.bind('<Button-3>', self.show_context_menu)
        
        # 创建右键菜单
        self.create_context_menu()
        
        # 日志窗口
        self.log_frame = tk.LabelFrame(self.content_frame, text="日志输出")
        self.log_frame.pack(fill=tk.BOTH, expand=True, side=tk.BOTTOM)
        
        self.log_text = scrolledtext.ScrolledText(self.log_frame, width=100, height=15, state=tk.DISABLED, 
                                                 bg="black", fg="white", 
                                                 font=('Courier New', 10))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 初始化日志标签
        self.log_text.tag_configure("white", foreground="white")
        self.log_text.tag_configure("green", foreground="green")
        self.log_text.tag_configure("yellow", foreground="yellow")
        self.log_text.tag_configure("red", foreground="red")
        
        # 使用说明标签页内容
        self.help_text = scrolledtext.ScrolledText(self.help_tab, width=100, height=30, wrap=tk.WORD)
        self.help_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.load_help_content()
        
        # 初始化日志
        self.log("1688详情页资源采集工具 - GUI 版本")
        self.log("-----------------------------------")
        self.log("使用说明：")
        self.log("1. 点击 '添加文件' 按钮添加多个 HTML 文件（支持多选）")
        self.log("2. 点击 '添加目录' 按钮添加目录中所有 HTML 文件")
        self.log("3. 在列表中选择文件后点击 '移除文件' 按钮移除选中的文件")
        self.log("4. 点击 '清空队列' 按钮清空所有队列中的文件")
        self.log("5. 点击 '执行' 按钮开始处理队列中的文件")
        self.log("6. 点击 '暂停' 按钮暂停队列处理")
        self.log("7. 在下方日志窗口查看执行过程和结果")
        self.log("-----------------------------------")
    
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
    
    def log(self, message, message_type="info"):
        """添加日志信息到日志窗口
        
        Args:
            message: 日志消息
            message_type: 消息类型，可选值：info, success, warning, error, input
        """
        self.log_text.config(state=tk.NORMAL)
        
        # 根据消息类型设置不同的颜色
        color_map = {
            "info": "white",      # 普通信息 - 白色
            "success": "green",    # 成功信息 - 绿色
            "warning": "yellow",   # 警告信息 - 黄色
            "error": "red",       # 错误信息 - 红色
            "input": "green"       # 输入日志 - 绿色
        }
        
        # 获取消息类型对应的颜色
        color = color_map.get(message_type, "white")
        
        # 检查是否需要特殊处理
        if message_type == "info":
            # 检查是否包含特定提示词
            if "开始清理小文件..." in message or "没有需要删除的小文件" in message:
                # 整个句子标记为黄色
                self.log_text.tag_configure("yellow", foreground="yellow")
                self.log_text.insert(tk.END, message + "\n", "yellow")
            # 检查是否是复杂命令行参数（包含多个空格和特殊字符）
            elif "aria2c.exe" in message and ("--console-log-level" in message or "--dir=" in message):
                # 复杂命令行参数，不进行染色
                self.log_text.tag_configure(color, foreground=color)
                self.log_text.insert(tk.END, message + "\n", color)
            else:
                # 检查是否包含路径或文件信息
                import re
                # 匹配路径模式（改进版，支持更多路径格式）
                # 1. 完整路径（包含盘符）
                # 2. 相对路径（以 ./ 或 ../ 开头）
                # 3. 简单文件名（包含扩展名）
                path_pattern = r'([A-Za-z]:\\[\\\w\s#.-]+|[./][\\\w\s#.-]+|\\b[\w#.-]+\\.[\w]+\\b)'
                paths = re.findall(path_pattern, message)
                
                if paths:
                    # 分段插入文本，路径部分标记为黄色
                    current_pos = 0
                    for path in paths:
                        # 找到路径在消息中的位置
                        path_pos = message.find(path, current_pos)
                        if path_pos != -1:
                            # 插入路径前的文本
                            if path_pos > current_pos:
                                self.log_text.tag_configure(color, foreground=color)
                                self.log_text.insert(tk.END, message[current_pos:path_pos], color)
                            # 插入路径文本，标记为黄色
                            self.log_text.tag_configure("yellow", foreground="yellow")
                            self.log_text.insert(tk.END, path, "yellow")
                            # 更新当前位置
                            current_pos = path_pos + len(path)
                    # 插入剩余的文本
                    if current_pos < len(message):
                        self.log_text.tag_configure(color, foreground=color)
                        self.log_text.insert(tk.END, message[current_pos:] + "\n", color)
                    else:
                        self.log_text.insert(tk.END, "\n")
                else:
                    # 普通文本，使用默认颜色
                    self.log_text.tag_configure(color, foreground=color)
                    self.log_text.insert(tk.END, message + "\n", color)
        else:
            # 其他消息类型，使用默认颜色
            self.log_text.tag_configure(color, foreground=color)
            self.log_text.insert(tk.END, message + "\n", color)
        
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def load_help_content(self):
        """加载使用说明内容"""
        help_content = ""
        
        # 检查是否存在 README.md 文件
        readme_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md")
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
               "1. 启动 GUI 程序：双击 `main_gui.py` 文件\n" \
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
               "- 版本：0.2.0\n" \
               "- 作者：急云\n" \
               "- 项目地址：https://github.com/jiyun/1688/\n" \
               "- 日期：2026-02-01"
    
    def add_file(self):
        """添加多个 HTML 文件到队列"""
        file_paths = filedialog.askopenfilename(
            title="选择 HTML 文件",
            filetypes=[("HTML 文件", "*.html"), ("所有文件", "*")],
            multiple=True
        )
        
        if file_paths:
            added_count = 0
            skipped_count = 0
            # 获取规范化的队列文件路径列表
            normalized_queue = [os.path.normpath(p) for p in self.file_queue]
            
            for file_path in file_paths:
                # 规范化文件路径
                normalized_path = os.path.normpath(file_path)
                if normalized_path not in normalized_queue:
                    self.file_queue.append(normalized_path)
                    normalized_queue.append(normalized_path)
                    # 初始化状态为"none"
                    self.file_status[normalized_path] = "none"
                    added_count += 1
                    self.log(f"已添加文件: {os.path.basename(normalized_path)}")
                else:
                    skipped_count += 1
                    self.log(f"跳过文件（已在队列中）: {os.path.basename(normalized_path)}")
            
            if added_count > 0:
                self.update_queue_list()
                self.log(f"共添加 {added_count} 个文件，跳过 {skipped_count} 个已在队列中的文件")
            elif skipped_count > 0:
                self.show_info("提示", f"所有选择的文件都已在队列中")
            else:
                self.show_info("提示", "未选择任何文件")
    
    def add_directory(self):
        """添加目录中所有 HTML 文件到队列"""
        dir_path = filedialog.askdirectory(title="选择目录")
        
        if dir_path:
            html_files = []
            # 只处理当前目录，不递归处理子目录
            for file in os.listdir(dir_path):
                file_path = os.path.join(dir_path, file)
                if os.path.isfile(file_path) and file.lower().endswith(".html"):
                    html_files.append(file_path)
            
            if html_files:
                added_count = 0
                skipped_count = 0
                # 获取规范化的队列文件路径列表
                normalized_queue = [os.path.normpath(p) for p in self.file_queue]
                
                for file_path in html_files:
                    # 规范化文件路径
                    normalized_path = os.path.normpath(file_path)
                    if normalized_path not in normalized_queue:
                        self.file_queue.append(normalized_path)
                        normalized_queue.append(normalized_path)
                        # 初始化状态为"none"
                        self.file_status[normalized_path] = "none"
                        added_count += 1
                        self.log(f"已添加文件: {os.path.basename(normalized_path)}")
                    else:
                        skipped_count += 1
                        self.log(f"跳过文件（已在队列中）: {os.path.basename(normalized_path)}")
                
                self.update_queue_list()
                self.log(f"已添加 {added_count} 个 HTML 文件，跳过 {skipped_count} 个已在队列中的文件")
            else:
                self.show_info("提示", "目录中没有找到 HTML 文件")
    
    def remove_file(self):
        """从队列中移除选中的文件"""
        selected_items = self.queue_tree.selection()
        if selected_items:
            removed_files = []
            # 遍历所有选中的项目
            for item in selected_items:
                # 获取选中项的值
                values = self.queue_tree.item(item, 'values')
                if values:
                    # 找到对应的文件路径在队列中的索引
                    file_path = values[4]  # 路径在第5列
                    if file_path in self.file_queue:
                        index = self.file_queue.index(file_path)
                        removed_file = self.file_queue.pop(index)
                        # 从状态字典中删除对应的状态
                        if removed_file in self.file_status:
                            del self.file_status[removed_file]
                        removed_files.append(removed_file)
            
            # 更新队列列表
            if removed_files:
                self.update_queue_list()
                # 记录日志
                for file in removed_files:
                    self.log(f"已移除文件: {os.path.basename(file)}")
                self.log(f"共移除 {len(removed_files)} 个文件")
        else:
            self.show_info("提示", "请先选择要移除的文件")
    
    def clear_queue(self):
        """清空队列"""
        if self.file_queue:
            # 弹出确认对话框
            confirm = self.ask_yes_no("确认", "是否要清空全部队列？")
            if confirm:
                self.file_queue.clear()
                self.file_status.clear()  # 同时清空状态字典
                self.update_queue_list()
                self.log("已清空队列")
        else:
            self.show_info("提示", "队列为空")
    
    def sort_treeview(self, column):
        """按列排序表格
        
        Args:
            column: 排序的列名
        """
        # 获取当前队列中的文件路径
        items = self.file_queue.copy()
        
        # 根据列名排序
        if column == "index":
            # 按序号排序（添加顺序）
            pass  # 保持原始顺序
        elif column == "status":
            # 按状态排序
            def status_sort_key(file_path):
                status = self.file_status.get(file_path, "none")
                # 定义状态优先级：none < error < success
                status_order = {"none": 0, "error": 1, "success": 2}
                return status_order.get(status, 0)
            items.sort(key=status_sort_key)
        elif column == "name":
            # 按文件名排序（按数字大小）
            def natural_sort_key(file_path):
                import re
                file_name = os.path.basename(file_path)
                parts = re.split(r'(\d+)', file_name)
                # 将数字部分转换为整数，非数字部分保持原样
                key = []
                for part in parts:
                    if part.isdigit():
                        key.append(int(part))
                    else:
                        key.append(part.lower())
                return key
            items.sort(key=natural_sort_key)
        elif column == "date":
            # 按修改日期排序
            def get_file_mtime(file_path):
                try:
                    return os.path.getmtime(file_path)
                except:
                    return 0
            items.sort(key=get_file_mtime, reverse=True)
        elif column == "path":
            # 按路径排序
            items.sort(key=lambda x: x.lower())
        
        # 更新队列并刷新表格
        self.file_queue = items
        self.update_queue_list()
        
        # 记录排序操作
        column_names = {
            "index": "序号",
            "status": "状态",
            "name": "文件名",
            "date": "修改日期",
            "path": "路径"
        }
        self.log(f"队列已按 {column_names.get(column, '未知列')} 排序")
    
    def update_queue_list(self):
        """更新队列表格"""
        # 清空表格
        for item in self.queue_tree.get_children():
            self.queue_tree.delete(item)
        
        # 创建状态标签
        self.queue_tree.tag_configure('success', foreground='green')
        self.queue_tree.tag_configure('error', foreground='red')
        self.queue_tree.tag_configure('none', foreground='black')
        
        # 添加数据到表格
        for i, file_path in enumerate(self.file_queue, 1):
            # 获取文件名
            file_name = os.path.basename(file_path)
            
            # 获取文件修改日期
            try:
                mtime = os.path.getmtime(file_path)
                import datetime
                date_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            except:
                date_str = "未知"
            
            # 获取状态
            status = self.file_status.get(file_path, "none")
            
            # 根据状态显示不同的图标
            if status == "success":
                status_icon = "✓"  # 绿色打勾图标
            elif status == "error":
                status_icon = "✗"  # 红色错误图标
            else:
                status_icon = ""  # 空
            
            # 添加到表格，并根据状态设置标签
            self.queue_tree.insert("", tk.END, values=(i, status_icon, file_name, date_str, file_path), tags=(status,))
    
    def execute(self):
        """执行主程序处理队列中的文件"""
        if not self.file_queue:
            self.show_info("提示", "队列为空，请先添加文件")
            return
        
        # 禁用执行按钮，启用暂停按钮
        self.execute_btn.config(state=tk.DISABLED, text="执行中...")
        self.pause_btn.config(state=tk.NORMAL)
        
        # 设置执行状态
        self.is_executing = True
        self.is_paused = False
        
        # 在新线程中执行，避免阻塞 GUI
        def execute_thread():
            try:
                self.log("开始执行处理...")
                self.log(f"队列中有 {len(self.file_queue)} 个文件需要处理")
                
                # 处理每个文件
                for i, file_path in enumerate(self.file_queue):
                    # 检查是否暂停
                    while self.is_paused:
                        import time
                        time.sleep(0.1)
                    
                    # 检查是否已停止
                    if not self.is_executing:
                        break
                    
                    self.log(f"\n处理文件 {i+1}/{len(self.file_queue)}: {os.path.basename(file_path)}")
                    
                    # 构建命令，使用 main.py 的绝对路径，并添加 --no-rebuild 参数（GUI 模式下不创建重建脚本）
                    main_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
                    cmd = ["python", main_py_path, file_path, "--no-rebuild"]
                    
                    # 执行命令并捕获输出
                    # 使用目标 HTML 文件所在的目录作为工作目录
                    file_dir = os.path.dirname(file_path)
                    self.current_process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding='utf-8',
                        cwd=file_dir
                    )
                    
                    # 读取输出并显示到日志窗口
                    has_download_error = False
                    for line in self.current_process.stdout:
                        line = line.strip()
                        # 检测下载失败
                        if "[失败]" in line or "下载失败的项目" in line:
                            has_download_error = True
                        # 根据行内容判断消息类型
                        if "错误" in line or "失败" in line or "[失败]" in line:
                            self.log(line, "error")
                        elif "成功" in line or "完成" in line:
                            self.log(line, "success")
                        elif "警告" in line or "提示" in line:
                            self.log(line, "warning")
                        else:
                            self.log(line, "info")
                    
                    # 等待命令执行完成
                    self.current_process.wait()
                    
                    if self.current_process.returncode == 0 and not has_download_error:
                        self.log(f"文件处理完成: {os.path.basename(file_path)}")
                        # 更新状态为成功
                        self.file_status[file_path] = "success"
                    else:
                        self.log(f"文件处理失败: {os.path.basename(file_path)}", "error")
                        # 更新状态为失败
                        self.file_status[file_path] = "error"
                    # 更新表格显示
                    self.update_queue_list()
                
                if self.is_executing:
                    self.log("\n所有文件处理完成！")
            except Exception as e:
                self.log(f"执行过程中出错: {str(e)}")
            finally:
                # 恢复按钮状态
                self.execute_btn.config(state=tk.NORMAL, text="执行")
                self.pause_btn.config(state=tk.DISABLED, text="暂停")
                # 重置执行状态
                self.is_executing = False
                self.is_paused = False
                self.current_process = None
        
        # 启动执行线程
        thread = threading.Thread(target=execute_thread)
        thread.daemon = True
        thread.start()
    
    def pause(self):
        """暂停/恢复队列处理"""
        if not self.is_executing:
            return
        
        if self.is_paused:
            # 恢复执行
            self.is_paused = False
            self.pause_btn.config(text="暂停")
            self.log("已恢复队列处理")
        else:
            # 暂停执行
            self.is_paused = True
            self.pause_btn.config(text="恢复")
            self.log("已暂停队列处理")
    
    def on_treeview_double_click(self, event):
        """处理 treeview 双击事件"""
        # 获取双击的项目
        item = self.queue_tree.identify_row(event.y)
        if item:
            # 获取项目值
            values = self.queue_tree.item(item, 'values')
            if values:
                file_path = values[4]  # 路径在第5列
                status = self.file_status.get(file_path, "none")
                
                # 根据状态打开不同路径
                if status == "success":
                    # 执行完成状态：打开子文件夹路径
                    file_name = os.path.basename(file_path)
                    folder_name = os.path.splitext(file_name)[0]
                    folder_path = os.path.join(os.path.dirname(file_path), folder_name)
                    self.open_file_explorer(folder_path)
                else:
                    # 未完成或失败状态：打开文件所在路径
                    directory_path = os.path.dirname(file_path)
                    self.open_file_explorer(directory_path)
    
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
    
    def create_context_menu(self):
        """创建右键菜单"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="图像优化", command=self.context_stitch_images)
        self.context_menu.add_command(label="资源打包", command=self.context_pack_files)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="重新采集", command=self.context_recollect)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="访问原址", command=self.context_visit_url)
        self.context_menu.add_command(label="打开目录", command=self.context_open_folder)
        self.context_menu.add_command(label="删除项目", command=self.context_delete_item)
    
    def show_context_menu(self, event):
        """显示右键菜单"""
        # 获取鼠标点击位置的行
        item = self.queue_tree.identify_row(event.y)
        if item:
            # 选中该行
            self.queue_tree.selection_set(item)
            # 获取选中项的状态
            values = self.queue_tree.item(item, 'values')
            if values:
                file_path = values[4]
                status = self.file_status.get(file_path, "none")
                
                # 根据状态启用/禁用菜单项
                # 只有执行过采集（success或error）才启用前三项
                if status in ["success", "error"]:
                    self.context_menu.entryconfig("图像优化", state=tk.NORMAL)
                    self.context_menu.entryconfig("资源打包", state=tk.NORMAL)
                    self.context_menu.entryconfig("重新采集", state=tk.NORMAL)
                else:
                    self.context_menu.entryconfig("图像优化", state=tk.DISABLED)
                    self.context_menu.entryconfig("资源打包", state=tk.DISABLED)
                    self.context_menu.entryconfig("重新采集", state=tk.DISABLED)
                
                # 显示菜单
                self.context_menu.post(event.x_root, event.y_root)
    
    def get_selected_folder(self):
        """获取选中项目对应的文件夹路径"""
        selected_items = self.queue_tree.selection()
        if not selected_items:
            return None
        
        item = selected_items[0]
        values = self.queue_tree.item(item, 'values')
        if values:
            file_path = values[4]
            file_name = os.path.basename(file_path)
            folder_name = os.path.splitext(file_name)[0]
            folder_path = os.path.join(os.path.dirname(file_path), folder_name)
            return folder_path
        return None
    
    def context_stitch_images(self):
        """右键菜单：图像优化（拼接+清理）"""
        folder_path = self.get_selected_folder()
        if folder_path and os.path.exists(folder_path):
            self.log(f"执行图像优化: {folder_path}")
            try:
                main_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
                
                self.log("正在处理详情图拼接...")
                process = subprocess.Popen(
                    ["python", main_py_path, "--process-images"],
                    cwd=folder_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8'
                )
                for line in process.stdout:
                    self.log(line.strip())
                process.wait()
                
                self.log("正在清理无用文件...")
                temp_files = ['down.txt', 'down_log.txt']
                for f in temp_files:
                    file_path = os.path.join(folder_path, f)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                
                merged_path = os.path.join(folder_path, '拼接结果.jpg')
                if os.path.exists(merged_path):
                    import glob
                    for pattern in ['C_*.jpg', 'T_*.jpg']:
                        for f in glob.glob(os.path.join(folder_path, pattern)):
                            os.remove(f)
                    os.remove(merged_path)
                    self.log("已删除原采集文件", "success")
                
                self.log("图像优化完成", "success")
            except Exception as e:
                self.log(f"图像优化失败: {e}", "error")
        else:
            self.show_info("提示", "文件夹不存在")
    
    def context_pack_files(self):
        """右键菜单：资源打包"""
        selected_items = self.queue_tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        values = self.queue_tree.item(item, 'values')
        if values:
            file_path = values[4]
            folder_path = self.get_selected_folder()
            
            if folder_path and os.path.exists(folder_path):
                self.log(f"执行资源打包: {folder_path}")
                try:
                    import shutil
                    parent_dir = os.path.dirname(folder_path)
                    folder_name = os.path.basename(folder_path)
                    html_file = os.path.join(parent_dir, f"{folder_name}.html")
                    
                    zip_path = os.path.join(parent_dir, folder_name)
                    
                    temp_dir = os.path.join(parent_dir, f"_temp_pack_{folder_name}")
                    os.makedirs(temp_dir, exist_ok=True)
                    
                    target_subdir = os.path.join(temp_dir, folder_name)
                    shutil.copytree(folder_path, target_subdir)
                    
                    if os.path.exists(html_file):
                        shutil.copy2(html_file, temp_dir)
                    
                    shutil.make_archive(zip_path, 'zip', temp_dir)
                    shutil.rmtree(temp_dir)
                    
                    self.log(f"打包完成: {zip_path}.zip", "success")
                    
                    confirm = self.ask_yes_no("完成", "打包完成，是否删除原目录和文件并从队列中移除？")
                    if confirm:
                        if os.path.exists(folder_path):
                            shutil.rmtree(folder_path)
                        if os.path.exists(html_file):
                            os.remove(html_file)
                        self.log(f"已删除原目录和文件", "success")
                        
                        if file_path in self.file_queue:
                            self.file_queue.remove(file_path)
                        if file_path in self.file_status:
                            del self.file_status[file_path]
                        self.update_queue_list()
                        self.log(f"已移除: {os.path.basename(file_path)}")
                except Exception as e:
                    self.log(f"资源打包失败: {e}", "error")
            else:
                self.show_info("提示", "文件夹不存在")
    
    def context_recollect(self):
        """右键菜单：重新采集"""
        selected_items = self.queue_tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        values = self.queue_tree.item(item, 'values')
        if values:
            file_path = values[4]
            folder_path = self.get_selected_folder()
            
            confirm = self.ask_yes_no("确认", "是否重新采集该资源？\n这将删除现有文件并重新下载。")
            if not confirm:
                return
            
            self.log(f"重新采集: {os.path.basename(file_path)}")
            try:
                if folder_path and os.path.exists(folder_path):
                    self.log("正在删除现有文件...")
                    import glob
                    import shutil
                    for item in os.listdir(folder_path):
                        item_path = os.path.join(folder_path, item)
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                    
                    self.log("正在重新采集...")
                    main_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
                    file_dir = os.path.dirname(file_path)
                    
                    process = subprocess.Popen(
                        ["python", main_py_path, file_path, "--no-rebuild"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding='utf-8',
                        cwd=file_dir
                    )
                    
                    for line in process.stdout:
                        line = line.strip()
                        if "错误" in line or "失败" in line or "[失败]" in line:
                            self.log(line, "error")
                        elif "成功" in line or "完成" in line:
                            self.log(line, "success")
                        else:
                            self.log(line, "info")
                    
                    process.wait()
                    
                    if process.returncode == 0:
                        self.file_status[file_path] = "success"
                        self.log("重新采集完成", "success")
                    else:
                        self.file_status[file_path] = "error"
                        self.log("重新采集失败", "error")
                    
                    self.update_queue_list()
                else:
                    self.log("文件夹不存在", "error")
            except Exception as e:
                self.log(f"重新采集失败: {e}", "error")
    
    def context_visit_url(self):
        """右键菜单：访问原址"""
        selected_items = self.queue_tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        values = self.queue_tree.item(item, 'values')
        if values:
            file_path = values[4]
            folder_path = self.get_selected_folder()
            
            url = None
            
            # 首先检查目标目录内是否存在#url.url文件
            if folder_path and os.path.exists(folder_path):
                url_file = os.path.join(folder_path, '#url.url')
                if os.path.exists(url_file):
                    try:
                        with open(url_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # 解析URL文件格式
                            for line in content.split('\n'):
                                if line.startswith('URL='):
                                    url = line[4:].strip()
                                    break
                            if not url:
                                url = content.strip()
                    except Exception as e:
                        self.log(f"读取URL文件失败: {e}", "error")
            
            # 如果#url.url文件不存在，使用项目ID构造1688详情页地址
            if not url:
                file_name = os.path.basename(file_path)
                product_id = os.path.splitext(file_name)[0]
                url = f"https://detail.1688.com/offer/{product_id}.html"
            
            # 使用默认浏览器打开URL
            if url:
                try:
                    import webbrowser
                    webbrowser.open(url)
                    self.log(f"已打开: {url}")
                except Exception as e:
                    self.log(f"打开浏览器失败: {e}", "error")
                    self.show_info("错误", f"无法打开浏览器: {e}")
            else:
                self.show_info("提示", "无法获取有效的URL")
    
    def context_open_folder(self):
        """右键菜单：打开目录"""
        folder_path = self.get_selected_folder()
        if folder_path:
            if os.path.exists(folder_path):
                self.open_file_explorer(folder_path)
            else:
                # 如果文件夹不存在，打开HTML文件所在目录
                selected_items = self.queue_tree.selection()
                if selected_items:
                    item = selected_items[0]
                    values = self.queue_tree.item(item, 'values')
                    if values:
                        file_path = values[4]
                        self.open_file_explorer(os.path.dirname(file_path))
        else:
            self.show_info("提示", "请先选择一个项目")
    
    def context_delete_item(self):
        """右键菜单：删除项目"""
        selected_items = self.queue_tree.selection()
        if selected_items:
            item = selected_items[0]
            values = self.queue_tree.item(item, 'values')
            if values:
                file_path = values[4]
                file_name = os.path.basename(file_path)
                
                confirm = self.ask_yes_no("确认", f"是否从队列中移除 {file_name}？")
                if confirm:
                    if file_path in self.file_queue:
                        self.file_queue.remove(file_path)
                    if file_path in self.file_status:
                        del self.file_status[file_path]
                    self.update_queue_list()
                    self.log(f"已移除: {file_name}")

if __name__ == "__main__":
    root = tk.Tk()
    app = AlibabaScraperGUI(root)
    root.mainloop()
