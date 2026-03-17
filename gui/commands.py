#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI上下文菜单命令模块
"""

import os
import sys
import subprocess
import shutil
import glob
import webbrowser
import threading
import multiprocessing
import traceback


def _run_optimization_process(shared_dict, folder_path, with_animated, webp_support, convert_main, convert_color):
    """在子进程中运行图像优化
    
    Args:
        shared_dict: 共享字典，包含所有进度信息
        folder_path: 文件夹路径
        with_animated: 是否包含动图
        webp_support: 是否支持WebP
        convert_main: 是否转换主图
        convert_color: 是否转换色卡图
    """
    import sys
    import time
    
    # 子进程启动信号
    shared_dict['status'] = 'started'
    shared_dict['start_time'] = time.time()
    
    try:
        # 添加项目路径
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        # 切换到目标目录
        os.chdir(folder_path)
        
        # 导入图像处理模块
        import utils.image_utils
        import utils.image_processor
        
        # 设置参数
        utils.image_utils.OUTPUT_WEBP = webp_support
        utils.image_utils.CONVERT_MAIN = convert_main
        utils.image_utils.CONVERT_COLOR = convert_color
        utils.image_utils.WITH_ANIMATED = with_animated  # 添加动图支持参数
        
        # 创建进度回调函数
        def progress_callback(name, current, total):
            percent = int((current / total) * 100) if total > 0 else 0
            shared_dict['status'] = 'processing'
            if '主图' in name:
                shared_dict['main_current'] = current
                shared_dict['main_total'] = total
                shared_dict['main_percent'] = percent
            elif '详情图' in name:
                shared_dict['detail_current'] = current
                shared_dict['detail_total'] = total
                shared_dict['detail_percent'] = percent
            elif '色卡' in name:
                shared_dict['color_current'] = current
                shared_dict['color_total'] = total
                shared_dict['color_percent'] = percent
        
        # 设置进度回调
        utils.image_processor.reporter.show_progress = progress_callback
        
        # 运行图像处理
        utils.image_processor.enlarge_main_images()
        
        # 处理详情图前，检查是否有文件需要处理
        detail_files = utils.image_utils.collect_image_files(folder_path, utils.image_processor.detail_image_prefix)
        if detail_files:
            shared_dict['detail_total'] = len(detail_files)
            utils.image_processor.process_regular_detail_images()
            # 处理完成后更新进度
            shared_dict['detail_current'] = shared_dict.get('detail_total', 0)
        
        # 处理色卡图前，检查是否有文件需要处理
        color_files = utils.image_utils.collect_image_files(folder_path, utils.image_processor.color_option_prefix)
        if color_files:
            shared_dict['color_total'] = len(color_files)
            utils.image_processor.enlarge_color_card_images()
            # 处理完成后更新进度
            shared_dict['color_current'] = shared_dict.get('color_total', 0)
        
        # 清理无用文件
        temp_files = ['down.txt', 'down_log.txt']
        for f in temp_files:
            file_path = os.path.join(folder_path, f)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # 删除拼接结果文件
        merged_path = os.path.join(folder_path, utils.image_utils.merged_image_name)
        if os.path.exists(merged_path):
            os.remove(merged_path)
        
        # 删除原采集文件
        patterns = ['C_*.jpg', 'C_*.png', 'T_*.jpg', 'T_*.png', 'color_*.jpg', 'color_*.png', 'C_*.avif', 'T_*.avif', 'color_*.avif']
        if with_animated:
            patterns.extend(['C_*.gif', 'T_*.gif', 'color_*.gif'])
        
        deleted_count = 0
        for pattern in patterns:
            for f in glob.glob(os.path.join(folder_path, pattern)):
                try:
                    os.remove(f)
                    deleted_count += 1
                except:
                    pass
        
        shared_dict['deleted_count'] = deleted_count
        shared_dict['end_time'] = time.time()
        shared_dict['status'] = 'completed'
        
    except Exception as e:
        shared_dict['error'] = str(e)
        shared_dict['status'] = 'error'


class ContextMenuCommands:
    """上下文菜单命令类"""
    
    def __init__(self, parent):
        """初始化上下文菜单命令
        
        Args:
            parent: 父窗口实例，用于访问UI控件和日志记录
        """
        self.parent = parent
        self.progress_manager = None  # 共享内存进度管理器
        self.progress_timer = None  # 进度更新定时器
    
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
            file_index = int(values[0]) - 1
            if 0 <= file_index < len(self.parent.queue_manager.file_queue):
                file_path = self.parent.queue_manager.file_queue[file_index]
                product_id = os.path.splitext(os.path.basename(file_path))[0]
                
                output_path = values[5]
                if output_path and os.path.exists(output_path):
                    return output_path
                
                from utils.database import db
                product_info = db.get_product(product_id)
                if product_info and product_info.get('output_path'):
                    db_output_path = product_info['output_path']
                    if os.path.exists(db_output_path):
                        return db_output_path
                
                return self.parent.queue_manager.get_output_directory(file_path, check_exists=False)
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
            
            # 显示参数设置
            params = []
            if with_animated:
                params.append("支持动图")
            if webp_support:
                params.append("WebP输出")
            if convert_main:
                params.append("主图WebP转换")
            if convert_color:
                params.append("色卡图WebP转换")
            
            if params:
                self.parent.log(f"参数: {', '.join(params)}")
            else:
                self.parent.log("参数: 默认设置")
            
            # 创建共享内存进度管理器
            from multiprocessing import Manager
            self.manager = Manager()
            self.shared_dict = self.manager.dict({
                'status': 'pending',
                'error': '',
                'deleted_count': 0,
                'start_time': 0,
                'end_time': 0,
                'main_current': 0,
                'main_total': 0,
                'main_percent': 0,
                'detail_current': 0,
                'detail_total': 0,
                'detail_percent': 0,
                'color_current': 0,
                'color_total': 0,
                'color_percent': 0
            })
            
            # 启动进度更新定时器
            self._start_progress_timer()
            
            # 启动子进程
            process = multiprocessing.Process(
                target=_run_optimization_process,
                args=(self.shared_dict, folder_path, with_animated, webp_support, convert_main, convert_color)
            )
            process.start()
            
            # 启动监控线程
            def monitor_thread():
                process.join()
                self._stop_progress_timer()
                
                # 获取最终结果
                status = self.shared_dict.get('status', 'unknown')
                error = self.shared_dict.get('error', '')
                
                # 显示最终报告
                self._show_final_report(dict(self.shared_dict))
                
                # 关闭管理器
                self.manager.shutdown()
                
                if status == 'completed':
                    self.parent.log("图像优化完成", "success")
                else:
                    self.parent.log(f"图像优化失败: {error or '未知错误'}", "error")
            
            thread = threading.Thread(target=monitor_thread)
            thread.daemon = True
            thread.start()
        else:
            self.parent.show_info("提示", "文件夹不存在")
    
    def _start_progress_timer(self):
        """启动进度更新定时器"""
        self._progress_stopped = False
        self._update_progress_display()
    
    def _stop_progress_timer(self):
        """停止进度更新定时器"""
        self._progress_stopped = True
    
    def _update_progress_display(self):
        """更新进度显示"""
        try:
            # 检查是否已停止
            if getattr(self, '_progress_stopped', False):
                return
            
            if not hasattr(self, 'shared_dict') or self.shared_dict is None:
                return
            
            status = self.shared_dict.get('status', 'pending')
            last_status = getattr(self, '_last_status', None)
            
            # 只在状态变化时输出日志
            if status != last_status:
                self._last_status = status
                if status == 'started':
                    self.parent.log("正在初始化...")
                elif status == 'processing':
                    self.parent.log("处理中...")
                elif status == 'completed':
                    self.parent.log("处理完成")
            
            # 更新进度显示
            if status == 'processing':
                main_current = self.shared_dict.get('main_current', 0)
                main_total = self.shared_dict.get('main_total', 0)
                detail_current = self.shared_dict.get('detail_current', 0)
                detail_total = self.shared_dict.get('detail_total', 0)
                color_current = self.shared_dict.get('color_current', 0)
                color_total = self.shared_dict.get('color_total', 0)
                
                last_main = getattr(self, '_last_main_current', 0)
                last_detail = getattr(self, '_last_detail_current', 0)
                last_color = getattr(self, '_last_color_current', 0)
                
                # 主图进度（每次变化都显示）
                if main_total > 0 and main_current != last_main:
                    self._last_main_current = main_current
                    percent = int((main_current / main_total) * 100) if main_total > 0 else 0
                    self.parent.log(f"主图进度: {main_current}/{main_total} ({percent}%)")
                
                # 详情图进度
                if detail_total > 0:
                    if detail_current > 0 and detail_current != last_detail:
                        self._last_detail_current = detail_current
                        percent = int((detail_current / detail_total) * 100) if detail_total > 0 else 0
                        self.parent.log(f"详情图进度: {detail_current}/{detail_total} ({percent}%)")
                    elif detail_current == 0:
                        # 队列存在但没有进度，显示处理中
                        self.parent.log("详情图进度: 处理中...")
                
                # 色卡图进度
                if color_total > 0:
                    if color_current > 0 and color_current != last_color:
                        self._last_color_current = color_current
                        percent = int((color_current / color_total) * 100) if color_total > 0 else 0
                        self.parent.log(f"色卡图进度: {color_current}/{color_total} ({percent}%)")
                    elif color_current == color_total and color_total > 0:
                        # 色卡图已完成，显示一次完成消息
                        if not getattr(self, '_color_completed_shown', False):
                            self._color_completed_shown = True
                            self.parent.log("色卡图进度: 已完成")
            
            # 如果还在处理中，继续定时更新
            if status in ('pending', 'started', 'processing'):
                self.parent.root.after(500, self._update_progress_display)
        except Exception as e:
            # 只在有实际错误时输出
            if str(e):
                self.parent.log(f"进度更新异常: {e}")
    
    def _show_final_report(self, shared_dict):
        """显示最终报告"""
        import time
        
        self.parent.log("\n" + "=" * 50)
        self.parent.log("图像优化处理报告")
        self.parent.log("=" * 50)
        
        # 计算耗时
        start_time = shared_dict.get('start_time', 0)
        end_time = shared_dict.get('end_time', 0)
        if start_time and end_time:
            elapsed = end_time - start_time
            self.parent.log(f"  耗时: {elapsed:.1f} 秒")
        
        # 显示各队列处理情况
        main_total = shared_dict.get('main_total', 0)
        detail_total = shared_dict.get('detail_total', 0)
        color_total = shared_dict.get('color_total', 0)
        
        if main_total > 0:
            self.parent.log(f"  主图: {shared_dict.get('main_current', 0)}/{main_total}")
        else:
            self.parent.log("  主图: 无需处理")
        
        if detail_total > 0:
            self.parent.log(f"  详情图: {shared_dict.get('detail_current', 0)}/{detail_total}")
        else:
            self.parent.log("  详情图: 无需处理")
        
        if color_total > 0:
            self.parent.log(f"  色卡图: {shared_dict.get('color_current', 0)}/{color_total}")
        else:
            self.parent.log("  色卡图: 无需处理")
        
        self.parent.log(f"  删除原采集文件: {shared_dict.get('deleted_count', 0)} 个")
        
        # 状态中文显示
        status = shared_dict.get('status', 'unknown')
        status_map = {
            'completed': '完成',
            'error': '错误',
            'pending': '等待',
            'started': '已启动',
            'processing': '处理中'
        }
        status_cn = status_map.get(status, status)
        self.parent.log(f"  状态: {status_cn}")
        
        if shared_dict.get('error'):
            self.parent.log(f"  错误: {shared_dict.get('error')}")
        self.parent.log("=" * 50)
    
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
        
        product_id = os.path.splitext(os.path.basename(file_path))[0]
        folder_path = self.get_selected_folder()
        
        if folder_path:
            folder_name = os.path.basename(os.path.normpath(folder_path))
            if folder_name != product_id:
                self.parent.log(f"安全检查: 输出目录名称 '{folder_name}' 与商品ID '{product_id}' 不匹配", "error")
                self.parent.show_info("错误", f"输出目录名称与商品ID不匹配\n目录: {folder_name}\n商品ID: {product_id}")
                return
        
        confirm = self.parent.ask_yes_no("确认", "是否重新采集该资源？\n这将删除现有文件并重新下载。")
        if not confirm:
            return
        
        self.parent.log(f"重新采集: {os.path.basename(file_path)}")
        
        import threading
        def recollect_thread():
            try:
                if folder_path and os.path.exists(folder_path):
                    self.parent.log(f"正在删除: {folder_path}")
                    for item in os.listdir(folder_path):
                        if item.startswith('.'):
                            continue
                        item_path = os.path.join(folder_path, item)
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                    
                    self.parent.log("正在重新采集...")
                    main_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "main.py")
                    
                    output_path = self.parent.get_output_path()
                    cmd = ["python", main_py_path, file_path, "--no-rebuild"]
                    if output_path:
                        cmd.extend(["--output", output_path])
                    
                    # 检查AVIF支持选项
                    if hasattr(self.parent, 'context_menu_manager') and self.parent.context_menu_manager.get_avif_support():
                        cmd.append("--keep-avif")
                    
                    env = os.environ.copy()
                    env['NO_COLOR'] = '1'
                    env['TERM'] = 'dumb'
                    
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding='utf-8',
                        bufsize=1,
                        universal_newlines=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
                        env=env
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
                    self.parent.log("文件夹不存在，执行新采集...")
                    main_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "main.py")
                    
                    output_path = self.parent.get_output_path()
                    cmd = ["python", main_py_path, file_path, "--no-rebuild"]
                    if output_path:
                        cmd.extend(["--output", output_path])
                    
                    # 检查AVIF支持选项
                    if hasattr(self.parent, 'context_menu_manager') and self.parent.context_menu_manager.get_avif_support():
                        cmd.append("--keep-avif")
                    
                    env = os.environ.copy()
                    env['NO_COLOR'] = '1'
                    env['TERM'] = 'dumb'
                    
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding='utf-8',
                        bufsize=1,
                        universal_newlines=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
                        env=env
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
                        self.parent.log("采集完成", "success")
                    else:
                        self.parent.queue_manager.file_status[file_path] = "error"
                        self.parent.log("采集失败", "error")
                    
                    self.parent.queue_manager.update_queue_list()
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
    
    def _get_product_id(self):
        """获取商品ID"""
        file_path = self.get_selected_file_path()
        if not file_path:
            return None
        
        file_name = os.path.basename(file_path)
        product_id = os.path.splitext(file_name)[0]
        return product_id
    
    def _copy_to_clipboard(self, text):
        """复制文本到剪贴板"""
        try:
            self.parent.root.clipboard_clear()
            self.parent.root.clipboard_append(text)
            self.parent.root.update()
            return True
        except Exception as e:
            self.parent.log(f"复制到剪贴板失败: {e}", "error")
            return False
    
    def context_consign_page(self):
        """右键菜单：铺货页面"""
        product_id = self._get_product_id()
        if not product_id:
            return
        
        url = f"https://detail.1688.com/offer/{product_id}.html?sk=consign&biz=qianniu&isNeedCloseWinport=y"
        
        if self._copy_to_clipboard(url):
            self.parent.log(f"已复制铺货页面链接: {url}")
    
    def context_shop_new(self):
        """右键菜单：店铺上新"""
        product_id = self._get_product_id()
        if not product_id:
            return
        
        url = f"https://item.upload.taobao.com/from1688/publish.htm?&sourceId={product_id}"
        
        if self._copy_to_clipboard(url):
            self.parent.log(f"已复制店铺上新链接: {url}")
    
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
    
    def context_edit_shop_id(self):
        """右键菜单：编辑DSID"""
        selected_items = self.parent.queue_tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        values = self.parent.queue_tree.item(item, 'values')
        if values:
            self.parent._edit_shop_id(item, values)
    
    def context_copy_item_url(self):
        """右键菜单：编辑商品 - 复制商品链接到剪切板"""
        selected_items = self.parent.queue_tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        values = self.parent.queue_tree.item(item, 'values')
        if values and len(values) > 3:
            dsid = values[3]
            if dsid and str(dsid).strip():
                url = f"https://item.upload.taobao.com/sell/v2/publish.htm?itemId={dsid}&fromAIPublish=true"                
                self.parent.root.clipboard_clear()
                self.parent.root.clipboard_append(url)
                self.parent.log(f"已复制商品链接: {url}")
            else:
                self.parent.show_info("提示", "该商品DSID为空，无法生成链接")
