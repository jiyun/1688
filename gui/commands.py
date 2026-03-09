#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI上下文菜单命令模块
"""

import os
import subprocess
import shutil
import glob
import webbrowser


class ContextMenuCommands:
    """上下文菜单命令类"""
    
    def __init__(self, parent):
        """初始化上下文菜单命令
        
        Args:
            parent: 父窗口实例，用于访问UI控件和日志记录
        """
        self.parent = parent
    
    def get_selected_folder(self):
        """获取选中项目对应的文件夹路径
        
        Returns:
            str: 选中项目的文件夹路径
        """
        selected_items = self.parent.queue_tree.selection()
        if not selected_items:
            return None
        
        item = selected_items[0]
        values = self.parent.queue_tree.item(item, 'values')
        if values:
            output_path = values[4]  # 输出路径在第5列
            if output_path and os.path.exists(output_path):
                return output_path
            # 如果输出路径不存在，返回HTML文件所在目录
            file_index = int(values[0]) - 1  # 序号从1开始
            if 0 <= file_index < len(self.parent.queue_manager.file_queue):
                file_path = self.parent.queue_manager.file_queue[file_index]
                return os.path.dirname(file_path)
        return None
    
    def get_selected_file_path(self):
        """获取选中项目对应的HTML文件路径
        
        Returns:
            str: HTML文件路径
        """
        selected_items = self.parent.queue_tree.selection()
        if not selected_items:
            return None
        
        item = selected_items[0]
        values = self.parent.queue_tree.item(item, 'values')
        if values:
            file_index = int(values[0]) - 1  # 序号从1开始
            if 0 <= file_index < len(self.parent.queue_manager.file_queue):
                return self.parent.queue_manager.file_queue[file_index]
        return None
    
    def context_stitch_images(self):
        """右键菜单：图像优化（默认）"""
        self._run_image_optimization("--process-images")
    
    def context_stitch_images_webp(self):
        """右键菜单：图像优化 + WebP转换"""
        self._run_image_optimization("--process-images", "--webp")
    
    def context_stitch_images_webp_main(self):
        """右键菜单：图像优化 + 主图WebP转换"""
        self._run_image_optimization("--process-images", "--webp", "--t")
    
    def context_stitch_images_webp_color(self):
        """右键菜单：图像优化 + 色卡图WebP转换"""
        self._run_image_optimization("--process-images", "--webp", "--color")
    
    def context_stitch_images_webp_all(self):
        """右键菜单：图像优化 + 全部WebP转换"""
        self._run_image_optimization("--process-images", "--webp", "--t", "--color")
    
    def context_stitch_images_with_animated(self):
        """右键菜单：图像优化 + 包含动图"""
        self._run_image_optimization("--process-images", "--with-animated")
    
    def context_stitch_images_webp_with_animated(self):
        """右键菜单：图像优化 + WebP转换 + 包含动图"""
        self._run_image_optimization("--process-images", "--webp", "--t", "--color", "--with-animated")
    
    def _run_image_optimization(self, *args):
        """执行图像优化的通用方法
        
        Args:
            *args: 命令行参数
        """
        folder_path = self.get_selected_folder()
        if folder_path and os.path.exists(folder_path):
            self.parent.log(f"执行图像优化: {folder_path}")
            
            # 检查命令行参数
            with_animated = '--with-animated' in args
            webp_support = '--webp' in args
            convert_main = '--t' in args
            convert_color = '--color' in args
            
            # 创建并启动线程，避免阻塞GUI主线程
            import threading
            def optimization_thread():
                try:
                    main_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "main.py")
                    
                    self.parent.log("正在处理详情图...")
                    command = ["python", main_py_path] + list(args)
                    process = subprocess.Popen(
                        command,
                        cwd=folder_path,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding='utf-8',
                        bufsize=1,  # 行缓冲，确保实时输出
                        universal_newlines=True
                    )
                    
                    # 实时读取输出并更新进度条
                    total_files = 0
                    processed_files = 0
                    import re
                    while True:
                        line = process.stdout.readline()
                        if not line and process.poll() is not None:
                            break
                        if line:
                            line = line.strip()
                            if line:
                                # 只显示关键信息，压缩详细日志
                                if "找到" in line and ("张详情图文件" in line or "张主图文件" in line or "张色卡图文件" in line):
                                    self.parent.log(line)
                                    # 提取文件数量
                                    match = re.search(r'找到 (\d+) 张', line)
                                    if match:
                                        total_files = int(match.group(1))
                                elif "开始处理主图放大" in line or "开始处理色卡图放大" in line:
                                    self.parent.log(line)
                                elif "主图放大完成" in line or "色卡图放大完成" in line:
                                    self.parent.log(line)
                                elif "混合图片处理完成" in line:
                                    self.parent.log(line)
                                # 捕获详情图处理进度（格式：详情图处理进度: [████████████] 5/9 (55.6%)）
                                elif "详情图处理进度:" in line and "[" in line:
                                    match = re.search(r'详情图处理进度:.*?(\d+)/(\d+)', line)
                                    if match:
                                        current = int(match.group(1))
                                        total = int(match.group(2))
                                        percent = int((current / total) * 100)
                                        self.parent.log(f"详情图处理进度: {current}/{total} ({percent}%)")
                                # 捕获主图处理进度
                                elif "主图处理进度:" in line and "[" in line:
                                    match = re.search(r'主图处理进度:.*?(\d+)/(\d+)', line)
                                    if match:
                                        current = int(match.group(1))
                                        total = int(match.group(2))
                                        percent = int((current / total) * 100)
                                        self.parent.log(f"主图处理进度: {current}/{total} ({percent}%)")
                                # 捕获主图WebP转换进度
                                elif "主图WebP转换进度:" in line and "[" in line:
                                    match = re.search(r'主图WebP转换进度:.*?(\d+)/(\d+)', line)
                                    if match:
                                        current = int(match.group(1))
                                        total = int(match.group(2))
                                        percent = int((current / total) * 100)
                                        self.parent.log(f"主图WebP转换进度: {current}/{total} ({percent}%)")
                                # 捕获色卡图处理进度
                                elif "色卡图处理进度:" in line and "[" in line:
                                    match = re.search(r'色卡图处理进度:.*?(\d+)/(\d+)', line)
                                    if match:
                                        current = int(match.group(1))
                                        total = int(match.group(2))
                                        percent = int((current / total) * 100)
                                        self.parent.log(f"色卡图处理进度: {current}/{total} ({percent}%)")
                                # 捕获混合图片处理进度
                                elif "混合图片处理进度:" in line:
                                    self.parent.log(line)
                                # 捕获混合图片处理开始
                                elif "混合图片处理:" in line:
                                    self.parent.log(line)
                                # 捕获动图转换
                                elif "动图转换:" in line:
                                    self.parent.log(line)
                    
                    process.wait()
                    
                    # 清理无用文件
                    self.parent.log("\n正在清理无用文件...")
                    temp_files = ['down.txt', 'down_log.txt']
                    for f in temp_files:
                        file_path = os.path.join(folder_path, f)
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    
                    # 删除拼接结果文件（如果存在)
                    merged_path = os.path.join(folder_path, '拼接结果.jpg')
                    if os.path.exists(merged_path):
                        os.remove(merged_path)
                    
                    # 删除原采集文件
                    # 注意：新生成的文件使用 new_ 前缀或 E_ 前缀，原始文件使用 C_ 和 T_ 前缀
                    # 所以删除原始文件不会影响新生成的文件
                    patterns = ['C_*.jpg', 'C_*.png', 'T_*.jpg', 'T_*.png', 'color_*.jpg', 'color_*.png']
                    if with_animated:
                        patterns.extend(['C_*.gif', 'T_*.gif', 'color_*.gif'])
                    
                    deleted_count = 0
                    for pattern in patterns:
                        for f in glob.glob(os.path.join(folder_path, pattern)):
                            try:
                                os.remove(f)
                                deleted_count += 1
                            except Exception as e:
                                self.parent.log(f"删除文件失败 {f}: {e}")
                    
                    if deleted_count > 0:
                        self.parent.log(f"已删除 {deleted_count} 个原采集文件", "success")
                    
                    self.parent.log("图像优化完成", "success")
                except Exception as e:
                    self.parent.log(f"图像优化失败: {e}", "error")
            
            # 启动优化线程
            thread = threading.Thread(target=optimization_thread)
            thread.daemon = True
            thread.start()
        else:
            self.parent.show_info("提示", "文件夹不存在")
    
    def context_stitch_images_with_options(self, with_animated=False, webp_support=False, webp_main=False, webp_color=False):
        """右键菜单：带选项的图像优化
        
        Args:
            with_animated: 是否包含动画
            webp_support: 是否支持WebP
            webp_main: 是否支持主图WebP转换
            webp_color: 是否支持色卡图WebP转换
        """
        args = ["--process-images"]
        
        # 添加命令行参数：--with-animated参数不再依赖--webp参数
        if with_animated:
            args.append("--with-animated")
        
        if webp_support:
            args.append("--webp")
            if webp_main:
                args.append("--t")
            if webp_color:
                args.append("--color")
        
        # 执行图像优化
        self._run_image_optimization(*args)
    
    def context_pack_files(self):
        """右键菜单：资源打包"""
        file_path = self.get_selected_file_path()
        if not file_path:
            return
        
        folder_path = self.get_selected_folder()
        
        if folder_path and os.path.exists(folder_path):
            self.parent.log(f"执行资源打包: {folder_path}")
            try:
                parent_dir = os.path.dirname(folder_path)
                folder_name = os.path.basename(folder_path)
                html_file = file_path  # 使用原始HTML文件路径
                
                zip_path = os.path.join(parent_dir, folder_name)
                
                temp_dir = os.path.join(parent_dir, f"_temp_pack_{folder_name}")
                os.makedirs(temp_dir, exist_ok=True)
                
                target_subdir = os.path.join(temp_dir, folder_name)
                shutil.copytree(folder_path, target_subdir)
                
                if os.path.exists(html_file):
                    shutil.copy2(html_file, temp_dir)
                
                shutil.make_archive(zip_path, 'zip', temp_dir)
                shutil.rmtree(temp_dir)
                
                self.parent.log(f"打包完成: {zip_path}.zip", "success")
                
                confirm = self.parent.ask_yes_no("完成", "打包完成，是否删除原目录和文件并从队列中移除？")
                if confirm:
                    if os.path.exists(folder_path):
                        shutil.rmtree(folder_path)
                    if os.path.exists(html_file):
                        os.remove(html_file)
                    self.parent.log(f"已删除原目录和文件", "success")
                    
                    if file_path in self.parent.queue_manager.file_queue:
                        self.parent.queue_manager.file_queue.remove(file_path)
                    if file_path in self.parent.queue_manager.file_status:
                        del self.parent.queue_manager.file_status[file_path]
                    self.parent.queue_manager.update_queue_list()
                    self.parent.log(f"已移除: {os.path.basename(file_path)}")
            except Exception as e:
                self.parent.log(f"资源打包失败: {e}", "error")
        else:
            self.parent.show_info("提示", "文件夹不存在")
    
    def context_recollect(self):
        """右键菜单：重新采集"""
        file_path = self.get_selected_file_path()
        if not file_path:
            return
        
        folder_path = self.get_selected_folder()
        
        confirm = self.parent.ask_yes_no("确认", "是否重新采集该资源？\n这将删除现有文件并重新下载。")
        if not confirm:
            return
        
        self.parent.log(f"重新采集: {os.path.basename(file_path)}")
        
        import threading
        def recollect_thread():
            try:
                if folder_path and os.path.exists(folder_path):
                    self.parent.log("正在删除现有文件...")
                    for item in os.listdir(folder_path):
                        item_path = os.path.join(folder_path, item)
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                    
                    self.parent.log("正在重新采集...")
                    main_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "main.py")
                    file_dir = os.path.dirname(file_path)
                    
                    output_path = self.parent.get_output_path()
                    cmd = ["python", main_py_path, file_path, "--no-rebuild"]
                    if output_path:
                        cmd.extend(["--output", output_path])
                    
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding='utf-8',
                        bufsize=1,
                        universal_newlines=True,
                        cwd=file_dir
                    )
                    
                    while True:
                        line = process.stdout.readline()
                        if not line and process.poll() is not None:
                            break
                        if line:
                            line = line.strip()
                            if line:
                                if "错误" in line or "失败" in line or "[失败]" in line:
                                    self.parent.log(line, "error")
                                elif "成功" in line or "完成" in line:
                                    self.parent.log(line, "success")
                                else:
                                    self.parent.log(line, "info")
                    
                    process.wait()
                    
                    if process.returncode == 0:
                        self.parent.queue_manager.file_status[file_path] = "success"
                        self.parent.log("重新采集完成", "success")
                    else:
                        self.parent.queue_manager.file_status[file_path] = "error"
                        self.parent.log("重新采集失败", "error")
                    
                    self.parent.queue_manager.update_queue_list()
                else:
                    self.parent.log("文件夹不存在", "error")
            except Exception as e:
                self.parent.log(f"重新采集失败: {e}", "error")
        
        thread = threading.Thread(target=recollect_thread)
        thread.daemon = True
        thread.start()
    
    def context_visit_url(self):
        """右键菜单：访问原址"""
        file_path = self.get_selected_file_path()
        if not file_path:
            return
        
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
                    self.parent.log(f"读取URL文件失败: {e}", "error")
        
        # 如果#url.url文件不存在，使用项目ID构造1688详情页地址
        if not url:
            file_name = os.path.basename(file_path)
            product_id = os.path.splitext(file_name)[0]
            url = f"https://detail.1688.com/offer/{product_id}.html"
        
        # 使用默认浏览器打开URL
        if url:
            try:
                webbrowser.open(url)
                self.parent.log(f"已打开: {url}")
            except Exception as e:
                self.parent.log(f"打开浏览器失败: {e}", "error")
                self.parent.show_info("错误", f"无法打开浏览器: {e}")
        else:
            self.parent.show_info("提示", "无法获取有效的URL")
    
    def context_open_folder(self):
        """右键菜单：打开目录"""
        folder_path = self.get_selected_folder()
        if folder_path and os.path.exists(folder_path):
            self.parent.open_file_explorer(folder_path)
        else:
            # 如果文件夹不存在，打开HTML文件所在目录
            file_path = self.get_selected_file_path()
            if file_path:
                self.parent.open_file_explorer(os.path.dirname(file_path))
            else:
                self.parent.show_info("提示", "请先选择一个项目")
    
    def context_delete_item(self):
        """右键菜单：删除项目"""
        file_path = self.get_selected_file_path()
        if not file_path:
            return
        
        file_name = os.path.basename(file_path)
        
        confirm = self.parent.ask_yes_no("确认", f"是否从队列中移除 {file_name}？")
        if confirm:
            if file_path in self.parent.queue_manager.file_queue:
                self.parent.queue_manager.file_queue.remove(file_path)
            if file_path in self.parent.queue_manager.file_status:
                del self.parent.queue_manager.file_status[file_path]
            self.parent.queue_manager.update_queue_list()
            self.parent.log(f"已移除: {file_name}")
