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


class AlibabaScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(GUI_CONF['window_title'])
        self.root.geometry(GUI_CONF['window_geometry'])
        self.root.resizable(GUI_CONF['window_resizable'], GUI_CONF['window_resizable'])
        
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
        
        # 创建输出路径配置框架
        self.output_frame = tk.Frame(self.queue_tab)
        self.output_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 输出路径标签
        self.output_label = tk.Label(self.output_frame, text="输出路径:")
        self.output_label.pack(side=tk.LEFT, padx=5)
        
        # 输出路径输入框
        self.output_path_var = tk.StringVar()
        self.output_path_entry = tk.Entry(self.output_frame, textvariable=self.output_path_var, width=60)
        self.output_path_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 浏览按钮
        self.browse_btn = tk.Button(self.output_frame, text="浏览...", command=self.browse_output_path, width=10)
        self.browse_btn.pack(side=tk.LEFT, padx=5)
        
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
        self.queue_tree = ttk.Treeview(self.queue_frame, columns=("index", "status", "name", "date", "output_path"), show="headings")
        
        # 设置列标题
        self.queue_tree.heading("index", text="序号")
        self.queue_tree.heading("status", text="状态", command=lambda: self.sort_treeview("status"))
        self.queue_tree.heading("name", text="文件名", command=lambda: self.sort_treeview("name"))
        self.queue_tree.heading("date", text="修改日期", command=lambda: self.sort_treeview("date"))
        self.queue_tree.heading("output_path", text="输出路径", command=lambda: self.sort_treeview("output_path"))
        
        # 设置列宽
        self.queue_tree.column("index", width=30, anchor=tk.CENTER)
        self.queue_tree.column("status", width=50, anchor=tk.CENTER)
        self.queue_tree.column("name", width=300, anchor=tk.W)
        self.queue_tree.column("date", width=120, anchor=tk.CENTER)
        self.queue_tree.column("output_path", width=300, anchor=tk.W)
        
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
        
        # 加载保存的输出路径
        self.load_output_path()
        
        # 使用说明标签页内容
        if HAS_TKINTERWEB and HAS_MARKDOWN:
            # 使用 tkinterweb 渲染 Markdown（禁用调试消息）
            self.help_frame = HtmlFrame(self.help_tab, messages_enabled=False)
            self.help_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            self.load_help_content_html()
        else:
            # 回退到纯文本显示
            self.help_text = ScrolledText(self.help_tab, width=100, height=30, wrap=tk.WORD)
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
                file_path = self.queue_manager.file_queue[int(values[0]) - 1]  # 通过序号获取文件路径
                html_dir = os.path.dirname(file_path)
                
                # 获取完整的输出路径
                output_path = self.queue_manager.get_output_directory(file_path)
                
                # 根据点击的列执行不同操作
                if column == "#5":  # 输出路径列
                    if output_path and os.path.exists(output_path):
                        self.open_file_explorer(output_path)
                    else:
                        self.open_file_explorer(html_dir)
                else:  # 其他列（包括文件名列）
                    self.open_file_explorer(html_dir)
    
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
        
        # 获取系统所有可用字体
        available_fonts = tkfont.families()
        
        # 按优先级检测字体
        font_families = GUI_CONF.get('font_families', ['Courier New'])
        
        for font_name in font_families:
            # 检查字体是否可用（支持中文名称、英文名称和带@前缀的名称）
            if font_name in available_fonts:
                return font_name
            
            # 检查带@前缀的字体
            if f'@{font_name}' in available_fonts:
                return f'@{font_name}'
        
        # 如果没有找到任何优先字体，返回默认字体
        return 'Courier New'
    
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
    
    def run(self):
        """运行GUI应用"""
        self.root.mainloop()


def main():
    """主函数"""
    # Windows上使用multiprocessing需要调用freeze_support
    multiprocessing.freeze_support()
    
    root = tk.Tk()
    app = AlibabaScraperGUI(root)
    
    # 隐藏控制台窗口（在GUI窗口创建后）
    hide_console()
    
    app.run()


if __name__ == "__main__":
    main()
