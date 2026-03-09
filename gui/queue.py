#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI队列管理模块
"""

import os
import re
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
                        # 同名子目录存在，设置状态为exists
                        self.file_status[normalized_path] = "exists"
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
                            # 同名子目录存在，设置状态为exists
                            self.file_status[normalized_path] = "exists"
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
            # 遍历所有选中的项目
            for item in selected_items:
                # 获取选中项的值
                values = self.parent.queue_tree.item(item, 'values')
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
        
        for i, file_path in enumerate(self.file_queue, 1):
            file_dir = os.path.dirname(file_path)
            file_name = os.path.basename(file_path)
            name_without_ext = os.path.splitext(file_name)[0]
            
            if file_dir:
                display_name = f"{file_dir}...{name_without_ext}"
            else:
                display_name = name_without_ext
            
            try:
                mtime = os.path.getmtime(file_path)
                date_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            except:
                date_str = "未知"
            
            status = self.file_status.get(file_path, "none")
            status_icon = GUI_CONF['status_icons'].get(status, "")
            
            output_path = self.get_output_directory(file_path)
            
            if output_path:
                if self.check_duplicate_files(output_path):
                    status = "duplicate"
                    status_icon = GUI_CONF['status_icons'].get("duplicate", "")
                elif status == "none":
                    status = "exists"
                    status_icon = GUI_CONF['status_icons'].get("exists", "")
            
            self.parent.queue_tree.insert("", "end", values=(i, status_icon, display_name, date_str, output_path), tags=(status,))
    
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
    
    def get_output_directory(self, html_file_path):
        """获取HTML文件对应的输出目录路径
        
        Args:
            html_file_path: HTML文件路径
            
        Returns:
            str: 输出目录路径，如果目录不存在则返回空字符串
        """
        product_id = os.path.splitext(os.path.basename(html_file_path))[0]
        
        custom_output_path = self.parent.get_output_path()
        if custom_output_path:
            output_dir = os.path.normpath(os.path.join(custom_output_path, product_id))
        else:
            html_dir = os.path.dirname(os.path.abspath(html_file_path))
            output_dir = os.path.normpath(os.path.join(html_dir, product_id))
        
        if os.path.exists(output_dir) and os.path.isdir(output_dir):
            return output_dir
        return ""
    
    def execute(self):
        """执行主程序处理队列中的文件"""
        if not self.file_queue:
            self.parent.show_info("提示", "队列为空，请先添加文件")
            return
        
        # 禁用执行按钮，启用暂停按钮
        self.parent.execute_btn.config(state="disabled", text="执行中...")
        self.parent.pause_btn.config(state="normal")
        
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
            except Exception as e:
                self.parent.log(f"执行过程中出错: {str(e)}")
            finally:
                # 恢复按钮状态
                self.parent.execute_btn.config(state="normal", text="执行 (Enter)")
                self.parent.pause_btn.config(state="disabled", text="暂停 (P)")
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
            self.parent.pause_btn.config(text="暂停 (P)")
            self.parent.log("已恢复队列处理")
        else:
            # 暂停执行
            self.is_paused = True
            self.parent.pause_btn.config(text="恢复")
            self.parent.log("已暂停队列处理")
