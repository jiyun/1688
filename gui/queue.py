#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI队列管理模块
"""

import os
import re
import sys
import subprocess
import threading
import time
import datetime
from tkinter import filedialog
from config import GUI_CONF


class QueueManager:
    """队列管理器"""
    
    def __init__(self, parent):
        """初始化队列管理器
        
        Args:
            parent: 父窗口实例，用于访问UI控件和日志记录
        """
        self.parent = parent
        self.file_queue = []
        self.file_status = {}
        self.is_paused = False
        self.is_executing = False
        self.current_process = None
    
    def check_resource_completeness(self, folder_path, product_id):
        """检查资源完整性
        
        Args:
            folder_path: 输出目录路径
            product_id: 商品ID
            
        Returns:
            str: 状态 ('success', 'exists', 'none')
        """
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            return 'none'
        
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            resource_counts = db.count_resources(product_id)
            
            main_count = resource_counts['main_images']
            color_count = resource_counts['color_images']
            video_count = resource_counts['videos']
            
            main_pattern = re.compile(r'^(T_|E_T_)\d+\.(jpg|jpeg|png|webp|gif)$', re.IGNORECASE)
            color_pattern = re.compile(r'^(color_|new_color_).+\.(jpg|jpeg|png|webp|gif)$', re.IGNORECASE)
            video_pattern = re.compile(r'^video_\d+\.(mp4|avi|mov|wmv|flv|webm)$', re.IGNORECASE)
            
            actual_main = 0
            actual_color = 0
            actual_video = 0
            
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if os.path.isfile(item_path):
                    if main_pattern.match(item):
                        actual_main += 1
                    elif color_pattern.match(item):
                        actual_color += 1
                    elif video_pattern.match(item):
                        actual_video += 1
            
            if actual_main >= main_count and actual_color >= color_count and actual_video >= video_count:
                return 'success'
            else:
                return 'exists'
        except:
            return 'exists'
    
    def add_file(self):
        """添加多个 HTML 文件到队列"""
        file_paths = filedialog.askopenfilename(
            title=GUI_CONF['file_dialog']['title'],
            filetypes=GUI_CONF['file_dialog']['types'],
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
                    
                    # 检测同名子目录是否存在
                    file_name = os.path.basename(normalized_path)
                    folder_name = os.path.splitext(file_name)[0]
                    folder_path = os.path.join(os.path.dirname(normalized_path), folder_name)
                    
                    if os.path.exists(folder_path) and os.path.isdir(folder_path):
                        status = self.check_resource_completeness(folder_path, folder_name)
                        self.file_status[normalized_path] = status
                        if status == 'success':
                            self.parent.log(f"已添加文件: {file_name} (资源完整)")
                        else:
                            self.parent.log(f"已添加文件: {file_name} (检测到同名子目录)")
                    else:
                        # 同名子目录不存在，设置状态为none
                        self.file_status[normalized_path] = "none"
                        self.parent.log(f"已添加文件: {file_name}")
                    
                    added_count += 1
                else:
                    skipped_count += 1
                    self.parent.log(f"跳过文件（已在队列中）: {os.path.basename(normalized_path)}")
            
            if added_count > 0:
                self.update_queue_list()
                self.parent.log(f"共添加 {added_count} 个文件，跳过 {skipped_count} 个已在队列中的文件")
            elif skipped_count > 0:
                self.parent.show_info("提示", f"所有选择的文件都已在队列中")
            else:
                self.parent.show_info("提示", "未选择任何文件")
    
    def add_directory(self):
        """添加目录中所有 HTML 文件到队列"""
        dir_path = filedialog.askdirectory(title=GUI_CONF['directory_dialog']['title'])
        
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
                        
                        # 检测同名子目录是否存在
                        file_name = os.path.basename(normalized_path)
                        folder_name = os.path.splitext(file_name)[0]
                        folder_path = os.path.join(os.path.dirname(normalized_path), folder_name)
                        
                        if os.path.exists(folder_path) and os.path.isdir(folder_path):
                            status = self.check_resource_completeness(folder_path, folder_name)
                            self.file_status[normalized_path] = status
                            if status == 'success':
                                self.parent.log(f"已添加文件: {file_name} (资源完整)")
                            else:
                                self.parent.log(f"已添加文件: {file_name} (检测到同名子目录)")
                        else:
                            # 同名子目录不存在，设置状态为none
                            self.file_status[normalized_path] = "none"
                            self.parent.log(f"已添加文件: {file_name}")
                        
                        added_count += 1
                    else:
                        skipped_count += 1
                        self.parent.log(f"跳过文件（已在队列中）: {os.path.basename(normalized_path)}")
                
                self.update_queue_list()
                self.parent.log(f"已添加 {added_count} 个 HTML 文件，跳过 {skipped_count} 个已在队列中的文件")
            else:
                self.parent.show_info("提示", "目录中没有找到 HTML 文件")
    
    def remove_file(self):
        """从队列中移除选中的文件"""
        selected_items = self.parent.queue_tree.selection()
        if selected_items:
            removed_files = []
            for item in selected_items:
                values = self.parent.queue_tree.item(item, 'values')
                if values:
                    file_index = int(values[0]) - 1  # 序号从1开始
                    if 0 <= file_index < len(self.file_queue):
                        file_path = self.file_queue[file_index]
                        if file_path in self.file_queue:
                            self.file_queue.remove(file_path)
                            if file_path in self.file_status:
                                del self.file_status[file_path]
                            removed_files.append(file_path)
            
            if removed_files:
                self.update_queue_list()
                for file in removed_files:
                    self.parent.log(f"已移除文件: {os.path.basename(file)}")
                self.parent.log(f"共移除 {len(removed_files)} 个文件")
        else:
            self.parent.show_info("提示", "请先选择要移除的文件")
    
    def clear_queue(self):
        """清空队列"""
        if self.file_queue:
            # 弹出确认对话框
            confirm = self.parent.ask_yes_no("确认", "是否要清空全部队列？")
            if confirm:
                self.file_queue.clear()
                self.file_status.clear()  # 同时清空状态字典
                self.update_queue_list()
                self.parent.log("已清空队列")
        else:
            self.parent.show_info("提示", "队列为空")
    
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
                return GUI_CONF['status_order'].get(status, 0)
            items.sort(key=status_sort_key)
        elif column == "name":
            # 按文件名排序（按数字大小）
            def natural_sort_key(file_path):
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
        elif column == "output_path":
            # 按输出路径排序
            items.sort(key=lambda x: self.get_output_directory(x).lower() or x.lower())
        
        # 更新队列并刷新表格
        self.file_queue = items
        self.update_queue_list()
        
        # 记录排序操作
        column_names = {
            "index": "序号",
            "status": "状态",
            "name": "文件名",
            "date": "修改日期",
            "output_path": "输出路径"
        }
        self.parent.log(f"队列已按 {column_names.get(column, '未知列')} 排序")
    
    def update_queue_list(self):
        """更新队列表格"""
        for item in self.parent.queue_tree.get_children():
            self.parent.queue_tree.delete(item)
        
        for status, color in GUI_CONF['status_colors'].items():
            self.parent.queue_tree.tag_configure(status, foreground=color)
        
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
        except:
            db = None
        
        for i, file_path in enumerate(self.file_queue, 1):
            file_dir = os.path.dirname(file_path)
            file_name = os.path.basename(file_path)
            
            display_name = self._compress_path_display(file_dir, file_name)
            
            product_id = os.path.splitext(file_name)[0]
            shop_product_id = ""
            if db:
                try:
                    product_data = db.get_product(product_id)
                    if product_data:
                        shop_product_id = product_data.get('shop_product_id', '') or ''
                except:
                    pass
            
            try:
                mtime = os.path.getmtime(file_path)
                date_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            except:
                date_str = "未知"
            
            status = self.file_status.get(file_path, "none")
            status_icon = GUI_CONF['status_icons'].get(status, "")
            
            output_path = self.get_output_directory(file_path)
            display_output_path = self._compress_output_path(output_path) if output_path else ""
            
            if output_path:
                if self.check_duplicate_files(output_path):
                    status = "duplicate"
                    status_icon = GUI_CONF['status_icons'].get("duplicate", "")
                    self.file_status[file_path] = "duplicate"
                elif status == "none":
                    status = "exists"
                    status_icon = GUI_CONF['status_icons'].get("exists", "")
                    self.file_status[file_path] = "exists"
            
            item_id = self.parent.queue_tree.insert("", "end", values=(i, status_icon, display_name, shop_product_id, date_str, display_output_path), tags=(status,))
    
    def _compress_path_display(self, file_dir, file_name):
        """压缩文件路径显示
        
        Args:
            file_dir: 文件目录
            file_name: 文件名（包含扩展名）
            
        Returns:
            str: 压缩后的显示文本
        """
        max_dir_length = 30
        
        if file_dir:
            if len(file_dir) > max_dir_length:
                compressed_dir = file_dir[:max_dir_length//2] + "..." + file_dir[-max_dir_length//2:]
                return f"{compressed_dir}...{file_name}"
            else:
                return f"{file_dir}...{file_name}"
        else:
            return file_name
    
    def _compress_output_path(self, output_path):
        """压缩输出路径显示
        
        Args:
            output_path: 输出路径
            
        Returns:
            str: 压缩后的显示文本
        """
        if not output_path:
            return ""
        
        output_path = os.path.normpath(output_path)
        parts = output_path.split(os.sep)
        
        if len(parts) >= 2:
            product_id = parts[-1]
            parent_path = os.sep.join(parts[:-1])
            
            max_parent_length = 25
            if len(parent_path) > max_parent_length:
                compressed_parent = parent_path[:max_parent_length//2] + "..."
            else:
                compressed_parent = parent_path
            
            return f"{compressed_parent}...{product_id}{os.sep}"
        
        return output_path
    
    def check_output_directory_exists(self, file_path):
        """检查输出目录是否存在
        
        Args:
            file_path: HTML文件路径
            
        Returns:
            bool: 输出目录是否存在
        """
        output_dir = self.get_output_directory(file_path)
        return output_dir and os.path.exists(output_dir) and os.path.isdir(output_dir)
    
    def check_duplicate_files(self, output_dir):
        """检查输出目录中是否存在aria2c生成的重复文件
        
        Args:
            output_dir: 输出目录路径
            
        Returns:
            bool: 是否存在重复文件
        """
        if not output_dir or not os.path.exists(output_dir):
            return False
        
        has_duplicate = False
        
        for file in os.listdir(output_dir):
            if '.1.' in file or '.2.' in file:
                has_duplicate = True
                break
        
        return has_duplicate
    
    def get_output_directory(self, html_file_path, check_exists=True, include_product_id=True):
        """获取HTML文件对应的输出目录路径
        
        Args:
            html_file_path: HTML文件路径
            check_exists: 是否检查目录存在，默认True
            include_product_id: 是否包含商品ID子目录，默认True
            
        Returns:
            str: 输出目录路径
        """
        product_id = os.path.splitext(os.path.basename(html_file_path))[0]
        
        custom_output_path = self.parent.get_output_path()
        if custom_output_path:
            if include_product_id:
                output_dir = os.path.normpath(os.path.join(custom_output_path, product_id))
            else:
                output_dir = os.path.normpath(custom_output_path)
        else:
            html_dir = os.path.dirname(os.path.abspath(html_file_path))
            if include_product_id:
                output_dir = os.path.normpath(os.path.join(html_dir, product_id))
            else:
                output_dir = os.path.normpath(html_dir)
        
        if check_exists:
            if include_product_id:
                if os.path.exists(output_dir) and os.path.isdir(output_dir):
                    return output_dir
                return ""
            else:
                if os.path.exists(output_dir) and os.path.isdir(output_dir):
                    return output_dir
                return ""
        
        return output_dir
    
    def execute(self):
        """执行主程序处理队列中的文件"""
        if not self.file_queue:
            self.parent.show_info("提示", "队列为空，请先添加文件")
            return
        
        # 禁用执行按钮，启用暂停按钮
        self.parent.execute_btn.configure(state="disabled", text="执行中...")
        self.parent.pause_btn.configure(state="normal")
        
        # 设置执行状态
        self.is_executing = True
        self.is_paused = False
        
        # 在新线程中执行，避免阻塞 GUI
        def execute_thread():
            try:
                self.parent.log("开始执行处理...")
                
                # 统计需要处理的文件数量
                files_to_process = []
                skipped_files = []
                
                for file_path in self.file_queue:
                    status = self.file_status.get(file_path, "none")
                    if status in ["success", "error"]:
                        skipped_files.append(file_path)
                    else:
                        files_to_process.append(file_path)
                
                if skipped_files:
                    self.parent.log(f"跳过 {len(skipped_files)} 个已完成或失败的文件")
                
                if not files_to_process:
                    self.parent.log("没有需要处理的文件")
                    return
                
                self.parent.log(f"队列中有 {len(files_to_process)} 个文件需要处理")
                
                # 处理每个文件
                for i, file_path in enumerate(files_to_process, 1):
                    # 检查是否暂停
                    while self.is_paused:
                        time.sleep(0.1)
                    
                    # 检查是否已停止
                    if not self.is_executing:
                        break
                    
                    self.parent.log(f"\n处理文件 {i}/{len(files_to_process)}: {os.path.basename(file_path)}")
                    
                    # 构建命令，使用 main.py 的绝对路径，并添加 --no-rebuild 参数（GUI 模式下不创建重建脚本）
                    main_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "main.py")
                    cmd = ["python", main_py_path, file_path, "--no-rebuild"]
                    
                    # 获取输出路径
                    output_path = self.parent.get_output_path()
                    if output_path:
                        cmd.extend(["--output", output_path])
                    
                    # 执行命令并捕获输出
                    # 使用目标 HTML 文件所在的目录作为工作目录
                    file_dir = os.path.dirname(file_path)
                    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                    
                    env = os.environ.copy()
                    env['NO_COLOR'] = '1'
                    env['TERM'] = 'dumb'
                    
                    self.current_process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding='utf-8',
                        cwd=file_dir,
                        creationflags=creationflags,
                        env=env
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
                            self.parent.log(line, "error")
                        elif "成功" in line or "完成" in line:
                            self.parent.log(line, "success")
                        elif "警告" in line or "提示" in line:
                            self.parent.log(line, "warning")
                        else:
                            self.parent.log(line, "info")
                    
                    # 等待命令执行完成
                    self.current_process.wait()
                    
                    if self.current_process.returncode == 0 and not has_download_error:
                        self.parent.log(f"文件处理完成: {os.path.basename(file_path)}")
                        # 更新状态为成功
                        self.file_status[file_path] = "success"
                    else:
                        self.parent.log(f"文件处理失败: {os.path.basename(file_path)}", "error")
                        # 更新状态为失败
                        self.file_status[file_path] = "error"
                    # 更新表格显示
                    self.update_queue_list()
                
                if self.is_executing:
                    self.parent.log("\n所有文件处理完成！")
                    
                    # 批量导入临时数据到DuckDB
                    try:
                        from utils.database import import_pending_data
                        imported = import_pending_data()
                        if imported > 0:
                            self.parent.log(f"已批量导入 {imported} 条数据到数据库", "success")
                    except Exception as e:
                        self.parent.log(f"批量导入数据失败: {e}", "warning")
            except Exception as e:
                self.parent.log(f"执行过程中出错: {str(e)}")
            finally:
                # 恢复按钮状态
                self.parent.execute_btn.configure(state="normal", text="执行 (Enter)")
                self.parent.pause_btn.configure(state="disabled", text="暂停 (P)")
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
            self.parent.pause_btn.configure(text="暂停 (P)")
            self.parent.log("已恢复队列处理")
        else:
            # 暂停执行
            self.is_paused = True
            self.parent.pause_btn.configure(text="恢复")
            self.parent.log("已暂停队列处理")
