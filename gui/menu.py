#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI菜单模块
包含上下文菜单管理和命令处理
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
import tkinter as tk
from config import GUI_CONF


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
    import time
    
    shared_dict['status'] = 'started'
    shared_dict['start_time'] = time.time()
    
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        os.chdir(folder_path)
        
        import utils.image_processor
        
        utils.image_processor.OUTPUT_WEBP = webp_support
        utils.image_processor.CONVERT_MAIN = convert_main
        utils.image_processor.CONVERT_COLOR = convert_color
        utils.image_processor.WITH_ANIMATED = with_animated
        
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
        
        utils.image_processor.reporter.show_progress = progress_callback
        
        utils.image_processor.enlarge_main_images()
        
        detail_files = utils.image_processor.collect_image_files(folder_path, utils.image_processor.detail_image_prefix)
        if detail_files:
            shared_dict['detail_total'] = len(detail_files)
            utils.image_processor.process_regular_detail_images()
            shared_dict['detail_current'] = shared_dict.get('detail_total', 0)
        
        color_files = utils.image_processor.collect_image_files(folder_path, utils.image_processor.color_option_prefix)
        if color_files:
            shared_dict['color_total'] = len(color_files)
            utils.image_processor.enlarge_color_card_images()
            shared_dict['color_current'] = shared_dict.get('color_total', 0)
        
        temp_files = ['.download_list.txt']
        for f in temp_files:
            file_path = os.path.join(folder_path, f)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        merged_path = os.path.join(folder_path, utils.image_processor.merged_image_name)
        if os.path.exists(merged_path):
            os.remove(merged_path)
        
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
        self.parent = parent
        self.progress_manager = None
        self.progress_timer = None
    
    def get_selected_folder(self):
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
                
                from utils.database import get_shared_db
                db = get_shared_db()
                product_info = db.get_product(product_id)
                if product_info and product_info.get('output_path'):
                    db_output_path = product_info['output_path']
                    if os.path.exists(db_output_path):
                        return db_output_path
                
                return self.parent.queue_manager.get_output_directory(file_path, check_exists=False)
        return None
    
    def get_selected_file_path(self):
        selected_items = self.parent.queue_tree.selection()
        if not selected_items:
            return None
        
        item = selected_items[0]
        values = self.parent.queue_tree.item(item, 'values')
        if values:
            file_index = int(values[0]) - 1
            if 0 <= file_index < len(self.parent.queue_manager.file_queue):
                return self.parent.queue_manager.file_queue[file_index]
        return None
    
    def context_stitch_images_with_options(self, with_animated=False, webp_support=False, webp_main=False, webp_color=False):
        args = ["--process-images"]
        
        if with_animated:
            args.append("--with-animated")
        
        if webp_support:
            args.append("--webp")
            if webp_main:
                args.append("--t")
            if webp_color:
                args.append("--color")
        
        self._run_image_optimization(*args)
    
    def _run_image_optimization(self, *args):
        folder_path = self.get_selected_folder()
        
        if folder_path and os.path.exists(folder_path):
            self.parent.log(f"执行图像优化: {folder_path}")
            
            with_animated = '--with-animated' in args
            webp_support = '--webp' in args
            convert_main = '--t' in args
            convert_color = '--color' in args
            
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
            
            self._start_progress_timer()
            
            process = multiprocessing.Process(
                target=_run_optimization_process,
                args=(self.shared_dict, folder_path, with_animated, webp_support, convert_main, convert_color)
            )
            process.start()
            
            def monitor_thread():
                process.join()
                self._stop_progress_timer()
                
                status = self.shared_dict.get('status', 'unknown')
                error = self.shared_dict.get('error', '')
                
                self._show_final_report(dict(self.shared_dict))
                
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
        self._progress_stopped = False
        self._update_progress_display()
    
    def _stop_progress_timer(self):
        self._progress_stopped = True
    
    def _update_progress_display(self):
        try:
            if getattr(self, '_progress_stopped', False):
                return
            
            if not hasattr(self, 'shared_dict') or self.shared_dict is None:
                return
            
            status = self.shared_dict.get('status', 'pending')
            last_status = getattr(self, '_last_status', None)
            
            if status != last_status:
                self._last_status = status
                if status == 'started':
                    self.parent.log("正在初始化...")
                elif status == 'processing':
                    self.parent.log("处理中...")
                elif status == 'completed':
                    self.parent.log("处理完成")
            
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
                
                if main_total > 0 and main_current != last_main:
                    self._last_main_current = main_current
                    percent = int((main_current / main_total) * 100) if main_total > 0 else 0
                    self.parent.log(f"主图进度: {main_current}/{main_total} ({percent}%)")
                
                if detail_total > 0:
                    if detail_current > 0 and detail_current != last_detail:
                        self._last_detail_current = detail_current
                        percent = int((detail_current / detail_total) * 100) if detail_total > 0 else 0
                        self.parent.log(f"详情图进度: {detail_current}/{detail_total} ({percent}%)")
                    elif detail_current == 0:
                        self.parent.log("详情图进度: 处理中...")
                
                if color_total > 0:
                    if color_current > 0 and color_current != last_color:
                        self._last_color_current = color_current
                        percent = int((color_current / color_total) * 100) if color_total > 0 else 0
                        self.parent.log(f"色卡图进度: {color_current}/{color_total} ({percent}%)")
                    elif color_current == color_total and color_total > 0:
                        if not getattr(self, '_color_completed_shown', False):
                            self._color_completed_shown = True
                            self.parent.log("色卡图进度: 已完成")
            
            if status in ('pending', 'started', 'processing'):
                self.parent.root.after(500, self._update_progress_display)
        except Exception as e:
            if str(e):
                self.parent.log(f"进度更新异常: {e}")
    
    def _show_final_report(self, shared_dict):
        import time
        
        self.parent.log("\n" + "=" * 50)
        self.parent.log("图像优化处理报告")
        self.parent.log("=" * 50)
        
        start_time = shared_dict.get('start_time', 0)
        end_time = shared_dict.get('end_time', 0)
        if start_time and end_time:
            elapsed = end_time - start_time
            self.parent.log(f"  耗时: {elapsed:.1f} 秒")
        
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
    
    def context_pack_files(self):
        file_path = self.get_selected_file_path()
        if not file_path:
            return
        
        folder_path = self.get_selected_folder()
        
        if folder_path and os.path.exists(folder_path):
            self.parent.log(f"执行资源打包: {folder_path}")
            try:
                parent_dir = os.path.dirname(folder_path)
                folder_name = os.path.basename(folder_path)
                html_file = file_path
                
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
    
    def context_recollect_data(self):
        """重采数据：只采集HTML里的标题、价格等数据导入数据库"""
        self._context_recollect_internal(mode='data')
    
    def context_recollect_resources(self):
        """重采资源：只采集HTML里的资源链接"""
        self._context_recollect_internal(mode='resources')
    
    def context_recollect(self):
        """执行重采：同时执行数据与资源采集"""
        self._context_recollect_internal(mode='all')
    
    def context_redownload_resources(self):
        """重新下载资源：重新下载该商品的所有资源文件"""
        file_path = self.get_selected_file_path()
        if not file_path:
            self.parent.log("请先选择一个文件", "warning")
            return
        
        product_id = os.path.splitext(os.path.basename(file_path))[0]
        self.parent.log(f"准备重新下载资源: {product_id}", "info")
        
        if hasattr(self.parent, '_download_product_resources'):
            self.parent._download_product_resources(product_id, force=True)
        else:
            self.parent.log("下载功能不可用", "error")
    
    def context_online_collect(self):
        """在线采集：直接从浏览器采集数据并保存到数据库"""
        file_path = self.get_selected_file_path()
        if not file_path:
            self.parent.log("请先选择一个文件", "warning")
            return
        
        product_id = os.path.splitext(os.path.basename(file_path))[0]
        url = f"https://detail.1688.com/offer/{product_id}.html"
        
        self.parent.log(f"准备在线采集: {url}", "info")
        
        def collect_thread():
            try:
                from gui.online_collector_gui import get_collector
                
                collector = get_collector(self.parent.log)
                
                if not collector.browser_started:
                    self.parent.log("正在启动浏览器...")
                    if not collector.start_browser():
                        self.parent.log("浏览器启动失败", "error")
                        return
                
                self.parent.log("正在采集数据...")
                data = collector.collect_data_direct(product_id)
                
                if data:
                    self.parent.log("数据采集成功，正在保存到数据库...")
                    self._save_collected_data_to_db(data)
                    self.parent.log("数据已保存到数据库", "success")
                else:
                    self.parent.log("数据采集失败", "error")
                    
            except Exception as e:
                self.parent.log(f"在线采集异常: {e}", "error")
                import traceback
                traceback.print_exc()
        
        thread = threading.Thread(target=collect_thread, daemon=True)
        thread.start()
    
    def _save_collected_data_to_db(self, data):
        """将采集的数据保存到数据库"""
        from utils.database import get_shared_db
        
        db = get_shared_db()
        
        product_id = data.get('product_id', '')
        
        product_info = data.get('product_info', {})
        sku_prices = data.get('sku_prices', [])
        color_images = data.get('color_images', [])
        
        try:
            db.update_product(product_id, {
                'title': product_info.get('subject', ''),
            })
        except Exception:
            pass
        
        saved_sku_count = 0
        if sku_prices:
            for sku_data in sku_prices:
                try:
                    if sku_data is None:
                        continue
                    
                    # 检查数据类型
                    if not isinstance(sku_data, dict):
                        self.parent.log(f"SKU数据格式错误: 期望dict, 实际{type(sku_data)}, 值={sku_data}", "warning")
                        continue
                    
                    color = sku_data.get('color', '') or ''
                    size = sku_data.get('size', '') or ''
                    
                    sku_id = sku_data.get('skuId')
                    if not sku_id:
                        continue
                    
                    # 安全获取价格，处理空字符串情况
                    price_str = sku_data.get('price', '')
                    price = float(price_str) if price_str and price_str.strip() else None
                    
                    discount_price_str = sku_data.get('discountPrice', '')
                    discount_price = float(discount_price_str) if discount_price_str and discount_price_str.strip() else None
                    # 安全获取库存和销量
                    can_book_count_str = str(sku_data.get('canBookCount', ''))
                    can_book_count = int(can_book_count_str) if can_book_count_str and can_book_count_str.strip() else 0
                    
                    sale_count_str = str(sku_data.get('saleCount', ''))
                    sale_count = int(sale_count_str) if sale_count_str and sale_count_str.strip() else 0
                    spec_id = sku_data.get('specId')
                    
                    db.insert_sku_price(product_id, sku_id, color, size, price, discount_price, can_book_count, sale_count, spec_id)
                    saved_sku_count += 1
                except Exception as e:
                    self.parent.log(f"保存SKU价格失败: {e}, sku_data类型={type(sku_data)}, 内容={sku_data}", "warning")
        
        saved_color_count = 0
        if color_images:
            for color_data in color_images:
                try:
                    from config import sanitize_filename
                    safe_name = sanitize_filename(color_data['name'])
                    db.insert_resource(
                        product_id=product_id,
                        resource_type='color_card',
                        resource_url=color_data['imageUrl'],
                        resource_name=safe_name
                    )
                    saved_color_count += 1
                except Exception as e:
                    self.parent.log(f"保存色卡图失败: {e}", "warning")
        
        self.parent.log(f"已保存 {saved_sku_count} 条SKU价格")
        self.parent.log(f"已保存 {saved_color_count} 条色卡图")
    
    def _context_recollect_internal(self, mode='all'):
        """内部重采方法
        
        Args:
            mode: 采集模式
                - 'data': 只采集数据（标题、价格等）
                - 'resources': 只采集资源链接
                - 'all': 同时采集数据和资源
        """
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
        
        mode_names = {
            'data': '重采数据',
            'resources': '重采资源',
            'all': '执行重采'
        }
        mode_name = mode_names.get(mode, '重新采集')
        
        confirm = self.parent.ask_yes_no("确认", f"是否{mode_name}？\n这将更新数据库和/或资源文件。")
        if not confirm:
            return
        
        self.parent.log(f"{mode_name}: {os.path.basename(file_path)}")
        
        def recollect_thread():
            try:
                main_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "main.py")
                
                output_path = self.parent.get_output_path()
                cmd = ["python", main_py_path, file_path, "--no-rebuild"]
                
                if output_path:
                    cmd.extend(["--output", output_path])
                
                # 添加采集模式参数
                if mode == 'data':
                    cmd.append("--data-only")
                elif mode == 'resources':
                    cmd.append("--resources-only")
                
                if hasattr(self.parent, 'context_menu_manager'):
                    if self.parent.context_menu_manager.get_avif_support():
                        cmd.append("--keep-avif")
                    if self.parent.context_menu_manager.get_webp_support():
                        cmd.append("--webp-support")
                
                env = os.environ.copy()
                env['NO_COLOR'] = '1'
                env['TERM'] = 'dumb'
                
                self.parent.log(f"正在{mode_name}...")
                
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
                    self.parent.log(f"========== {mode_name}完成 ==========", "success")
                    
                    try:
                        from utils.database import import_pending_data
                        imported = import_pending_data()
                        if imported > 0:
                            self.parent.log(f"已导入 {imported} 条数据到数据库", "success")
                    except Exception as e:
                        self.parent.log(f"导入数据失败: {e}", "warning")
                    
                    if hasattr(self.parent, '_refresh_db_data'):
                        self.parent.root.after(100, self.parent._refresh_db_data)
                else:
                    self.parent.queue_manager.file_status[file_path] = "error"
                    self.parent.log(f"========== {mode_name}失败 ==========", "error")
                
                self.parent.queue_manager.update_queue_list()
            except Exception as e:
                self.parent.log(f"========== {mode_name}异常: {e} ==========", "error")
        
        thread = threading.Thread(target=recollect_thread, daemon=True)
        thread.start()
    
    def context_visit_url(self, event=None):
        """访问原址 - 使用内嵌浏览器或外部浏览器
        
        Args:
            event: 鼠标事件，用于检测Shift键状态
        """
        file_path = self.get_selected_file_path()
        if not file_path:
            return
        
        folder_path = self.get_selected_folder()
        
        url = None
        
        if folder_path and os.path.exists(folder_path):
            url_file = os.path.join(folder_path, '#url.url')
            if os.path.exists(url_file):
                try:
                    with open(url_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        for line in content.split('\n'):
                            if line.startswith('URL='):
                                url = line[4:].strip()
                                break
                        if not url:
                            url = content.strip()
                except Exception as e:
                    self.parent.log(f"读取URL文件失败: {e}", "error")
        
        if not url:
            file_name = os.path.basename(file_path)
            product_id = os.path.splitext(file_name)[0]
            url = f"https://detail.1688.com/offer/{product_id}.html"
        
        if url:
            use_external = False
            
            if event and hasattr(event, 'state'):
                if event.state & 0x1:
                    use_external = True
            
            if use_external:
                try:
                    webbrowser.open(url)
                    self.parent.log(f"已在外部浏览器打开: {url}")
                except Exception as e:
                    self.parent.log(f"打开浏览器失败: {e}", "error")
            else:
                self._open_in_embedded_browser(url)
        else:
            self.parent.show_info("提示", "无法获取有效的URL")
    
    def _open_in_embedded_browser(self, url):
        """使用内嵌浏览器打开URL"""
        try:
            from gui.online_collector_gui import get_collector
            
            collector = get_collector(self.parent.log)
            
            if not collector.browser_started:
                self.parent.log("正在启动内嵌浏览器...")
                if not collector.start_browser():
                    self.parent.log("内嵌浏览器启动失败，使用外部浏览器", "warning")
                    import webbrowser
                    webbrowser.open(url)
                    return
            
            collector.collector.driver.get(url)
            self.parent.log(f"已在内嵌浏览器打开: {url}")
            
        except ImportError:
            self.parent.log("内嵌浏览器模块不可用，使用外部浏览器", "warning")
            import webbrowser
            webbrowser.open(url)
        except Exception as e:
            self.parent.log(f"内嵌浏览器打开失败: {e}，使用外部浏览器", "warning")
            import webbrowser
            webbrowser.open(url)
    
    def _get_product_id(self):
        file_path = self.get_selected_file_path()
        if not file_path:
            return None
        
        file_name = os.path.basename(file_path)
        product_id = os.path.splitext(file_name)[0]
        return product_id
    
    def _copy_to_clipboard(self, text):
        try:
            self.parent.root.clipboard_clear()
            self.parent.root.clipboard_append(text)
            self.parent.root.update()
            return True
        except Exception as e:
            self.parent.log(f"复制到剪贴板失败: {e}", "error")
            return False
    
    def context_consign_page(self):
        product_id = self._get_product_id()
        if not product_id:
            return
        
        url = f"https://detail.1688.com/offer/{product_id}.html?sk=consign&biz=qianniu&isNeedCloseWinport=y"
        
        if self._copy_to_clipboard(url):
            self.parent.log(f"已复制铺货页面链接: {url}")
    
    def context_shop_new(self):
        product_id = self._get_product_id()
        if not product_id:
            return
        
        url = f"https://item.upload.taobao.com/from1688/publish.htm?&sourceId={product_id}"
        
        if self._copy_to_clipboard(url):
            self.parent.log(f"已复制店铺上新链接: {url}")
    
    def context_open_folder(self):
        folder_path = self.get_selected_folder()
        if folder_path and os.path.exists(folder_path):
            self.parent.open_file_explorer(folder_path)
        else:
            file_path = self.get_selected_file_path()
            if file_path:
                self.parent.open_file_explorer(os.path.dirname(file_path))
            else:
                self.parent.show_info("提示", "请先选择一个项目")
    
    def context_delete_item(self):
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
        selected_items = self.parent.queue_tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        values = self.parent.queue_tree.item(item, 'values')
        if values:
            self.parent._edit_shop_id(item, values)
    
    def context_copy_item_url(self):
        selected_items = self.parent.queue_tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        values = self.parent.queue_tree.item(item, 'values')
        if values and len(values) > 3:
            dsid = values[3]
            if dsid and str(dsid).strip():
                url = f"https://item.upload.taobao.com/sell/v2/publish.htm?itemId={dsid}&fromAIPublish=true&newRouter=1&fromAICategory=true"
                self.parent.root.clipboard_clear()
                self.parent.root.clipboard_append(url)
                self.parent.log(f"已复制商品链接: {url}")


class ContextMenuManager(ContextMenuCommands):
    """上下文菜单管理器"""
    
    def __init__(self, root, parent_widget):
        self.root = root
        self.parent_widget = parent_widget
        self.context_menu = None
        
        self.checkbox_vars = {
            'with_animated': tk.BooleanVar(value=False),
            'webp_support': tk.BooleanVar(value=False),
            'webp_main': tk.BooleanVar(value=False),
            'webp_color': tk.BooleanVar(value=False),
            'avif_support': tk.BooleanVar(value=False)
        }
        
        self._create_context_menu()
    
    def _create_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)
        
        # 图像优化菜单
        image_menu = tk.Menu(self.context_menu, tearoff=0)
        
        image_menu.add_checkbutton(
            label="支持动图",
            variable=self.checkbox_vars['with_animated']
        )
        
        # WebP选项作为支持动图的子菜单
        webp_submenu = tk.Menu(image_menu, tearoff=0)
        webp_submenu.add_checkbutton(
            label="支持主图",
            variable=self.checkbox_vars['webp_main']
        )
        webp_submenu.add_checkbutton(
            label="支持色卡图",
            variable=self.checkbox_vars['webp_color']
        )
        
        image_menu.add_cascade(
            label="WebP选项",
            menu=webp_submenu
        )
        
        image_menu.add_separator()
        
        image_menu.add_command(
            label="执行操作",
            command=self._execute_image_optimization
        )
        
        self.context_menu.add_cascade(
            label="图像优化",
            menu=image_menu
        )
        
        self.context_menu.add_command(
            label="资源打包",
            command=lambda: self._call_command("context_pack_files")
        )
        
        self.context_menu.add_separator()
        
        # 重新采集菜单（改为目录）
        recollect_menu = tk.Menu(self.context_menu, tearoff=0)
        
        recollect_menu.add_command(
            label="重采数据",
            command=lambda: self._call_command("context_recollect_data")
        )
        
        recollect_menu.add_separator()
        
        recollect_menu.add_command(
            label="重采资源",
            command=lambda: self._call_command("context_recollect")
        )
        
        recollect_menu.add_checkbutton(
            label="AVIF支持",
            variable=self.checkbox_vars['avif_support']
        )
        
        recollect_menu.add_checkbutton(
            label="WebP支持",
            variable=self.checkbox_vars['webp_support']
        )
        
        recollect_menu.add_separator()
        
        recollect_menu.add_command(
            label="执行重采",
            command=lambda: self._call_command("context_recollect")
        )
        
        self.context_menu.add_cascade(
            label="重新采集",
            menu=recollect_menu
        )
        
        self.context_menu.add_command(
            label="在线采集",
            command=self.context_online_collect
        )
        
        self.context_menu.add_command(
            label="重新下载资源",
            command=self.context_redownload_resources
        )
        
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="访问原址 ©",
            command=lambda: self._call_command("context_visit_url")
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="铺货页面 ©",
            command=lambda: self._call_command("context_consign_page")
        )
        self.context_menu.add_command(
            label="店铺上新 ©",
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
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="编辑DSID",
            command=lambda: self._call_command("context_edit_shop_id")
        )
        self.context_menu.add_command(
            label="编辑商品 ©",
            command=lambda: self._call_command("context_copy_item_url")
        )
    
    def _toggle_webp_options(self):
        webp_enabled = self.checkbox_vars['webp_support'].get()
        state = tk.NORMAL if webp_enabled else tk.DISABLED
        
        webp_menu = self.context_menu.nametowidget(self.context_menu.entrycget("图像优化", "menu"))
        webp_menu.entryconfig("WebP选项", state=state)
        
        webp_submenu = webp_menu.nametowidget(webp_menu.entrycget("WebP选项", "menu"))
        webp_submenu.entryconfig("支持主图", state=state)
        webp_submenu.entryconfig("支持色卡图", state=state)
    
    def _execute_image_optimization(self):
        with_animated = self.checkbox_vars['with_animated'].get()
        webp_support = self.checkbox_vars['webp_support'].get()
        webp_main = self.checkbox_vars['webp_main'].get()
        webp_color = self.checkbox_vars['webp_color'].get()
        
        if hasattr(self.parent_widget, "context_stitch_images_with_options"):
            self.parent_widget.context_stitch_images_with_options(
                with_animated=with_animated,
                webp_support=webp_support,
                webp_main=webp_main,
                webp_color=webp_color
            )
    
    def get_avif_support(self) -> bool:
        return self.checkbox_vars['avif_support'].get()
    
    def get_webp_support(self) -> bool:
        return self.checkbox_vars['webp_support'].get()
    
    def _call_command(self, command_name):
        if hasattr(self.parent_widget, command_name):
            command = getattr(self.parent_widget, command_name)
            command()
    
    def show_context_menu(self, event):
        item = self.parent_widget.queue_tree.identify_row(event.y)
        if item:
            self.parent_widget.queue_tree.selection_set(item)
            values = self.parent_widget.queue_tree.item(item, 'values')
            if values:
                file_index = int(values[0]) - 1
                if 0 <= file_index < len(self.parent_widget.queue_manager.file_queue):
                    file_path = self.parent_widget.queue_manager.file_queue[file_index]
                    status = self.parent_widget.file_status.get(file_path, "none")
                    
                    state = tk.NORMAL if status in ["success", "error", "exists", "duplicate"] else tk.DISABLED
                    
                    self.context_menu.entryconfig("图像优化", state=state)
                    self.context_menu.entryconfig("资源打包", state=state)
                    self.context_menu.entryconfig("重新采集", state=state)
                    self.context_menu.entryconfig("重新下载资源", state=state)
                    
                    dsid = values[3] if len(values) > 3 else ""
                    edit_product_state = tk.NORMAL if dsid and str(dsid).strip() else tk.DISABLED
                    self.context_menu.entryconfig("编辑商品 ©", state=edit_product_state)
                    
                    try:
                        self.context_menu.tk_popup(event.x_root, event.y_root)
                    finally:
                        self.context_menu.grab_release()
