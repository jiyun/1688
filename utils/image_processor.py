"""
图像处理模块

提供图像处理的完整功能，包括：
- 图片放大
- 图片切割
- 动图转换
- 主图处理
- 详情图处理
- 色卡图处理
"""

import os
import sys
import re
import threading
import multiprocessing
import time
import glob
from multiprocessing import Pool, Manager
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from typing import List, Tuple, Optional

if sys.stdout:
    sys.stdout.reconfigure(line_buffering=True)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FILE_NAMING, IMAGE_PROCESSING

WITH_ANIMATED = False
OUTPUT_WEBP = False
CONVERT_MAIN = False
CONVERT_COLOR = False

detail_image_prefix = FILE_NAMING.get('detail_image_prefix', 'C_')
new_image_prefix = FILE_NAMING.get('new_image_prefix', 'new_C_')
merged_image_name = FILE_NAMING.get('merged_image_name', '拼接结果.jpg')
main_image_prefix = FILE_NAMING.get('main_image_prefix', 'T_')
color_option_prefix = FILE_NAMING.get('color_option_prefix', 'color_')

min_width = IMAGE_PROCESSING.get('min_width', 750)
detail_min_width = IMAGE_PROCESSING.get('detail_min_width', 1440)
detail_width_tolerance = IMAGE_PROCESSING.get('detail_width_tolerance', 0.02)
enlarge_2x_width = IMAGE_PROCESSING.get('enlarge_2x_width', 750)
enlarge_step1_width = IMAGE_PROCESSING.get('enlarge_step1_width', 800)
enlarge_step2_width = IMAGE_PROCESSING.get('enlarge_step2_width', 1600)
photo_min_width = IMAGE_PROCESSING.get('photo_min_width', 900)
photo_aspect_ratios = IMAGE_PROCESSING.get('photo_aspect_ratios', [(16, 9), (4, 3), (3, 2)])
photo_aspect_tolerance = IMAGE_PROCESSING.get('photo_aspect_tolerance', 0.10)
main_image_min_size = IMAGE_PROCESSING.get('main_image_min_size', 800)
main_image_target_size = IMAGE_PROCESSING.get('main_image_target_size', 1600)
min_split_height = IMAGE_PROCESSING.get('min_split_height', 200)
jpeg_quality = IMAGE_PROCESSING.get('jpeg_quality', 95)
webp_quality = IMAGE_PROCESSING.get('webp_quality', 80)
webp_method = IMAGE_PROCESSING.get('webp_method', 4)
parallel_workers = IMAGE_PROCESSING.get('parallel_workers', 2)


def natural_sort_key(filename):
    """自然排序键函数"""
    parts = re.split(r'(\d+)', os.path.basename(filename) if isinstance(filename, str) else os.path.basename(filename[0]))
    parts = [int(p) if p.isdigit() else p for p in parts]
    return parts


def enlarge_image(img):
    """统一的图片放大函数"""
    width, height = img.size
    
    if width >= detail_min_width:
        return img, (width, height, "保持不变")
    
    if width == enlarge_2x_width:
        new_width = width * 2
        new_height = height * 2
        img_resized = img.resize((new_width, new_height), Image.LANCZOS)
        return img_resized, (new_width, new_height, f"2倍放大: {width}px -> {new_width}px")
    
    if width <= enlarge_step1_width:
        scale1 = enlarge_step1_width / width
        temp_width = enlarge_step1_width
        temp_height = int(height * scale1)
        img_temp = img.resize((temp_width, temp_height), Image.LANCZOS)
        
        new_width = enlarge_step2_width
        new_height = int(temp_height * enlarge_step2_width / temp_width)
        img_resized = img_temp.resize((new_width, new_height), Image.LANCZOS)
        
        return img_resized, (new_width, new_height, f"二次放大: {width}px -> {temp_width}px -> {new_width}px")
    
    new_width = width * 2
    new_height = height * 2
    img_resized = img.resize((new_width, new_height), Image.LANCZOS)
    return img_resized, (new_width, new_height, f"2倍放大: {width}px -> {new_width}px")


def get_enlarge_target_width(width):
    """获取放大后的目标宽度（不实际放大图片）"""
    if width >= detail_min_width:
        return width
    if width == enlarge_2x_width:
        return width * 2
    if width <= enlarge_step1_width:
        return enlarge_step2_width
    return enlarge_step2_width


def check_aspect_ratio(width, height):
    """检查图片是否符合实拍照片的宽高比要求"""
    actual_ratio = width / height
    
    best_match = None
    best_diff = float('inf')
    
    for w_ratio, h_ratio in photo_aspect_ratios:
        target_ratio = w_ratio / h_ratio
        diff = abs(actual_ratio - target_ratio)
        if diff < best_diff:
            best_diff = diff
            best_match = (w_ratio, h_ratio)
    
    if best_match and best_diff <= photo_aspect_tolerance:
        return True, best_match
    return False, None


def split_merged_image(merged_image, target_width, total_height, output_dir, output_prefix):
    """切割拼接后的图片"""
    max_single_height = target_width * 2
    
    if total_height <= max_single_height:
        if OUTPUT_WEBP:
            save_path = os.path.join(output_dir, f"{output_prefix}1.webp")
            merged_image.save(save_path, format="WebP", quality=jpeg_quality)
        else:
            save_path = os.path.join(output_dir, f"{output_prefix}1.jpg")
            merged_image.save(save_path, quality=jpeg_quality)
        
        return 1
    
    切割份数 = (total_height + max_single_height - 1) // max_single_height
    
    每份高度 = total_height // 切割份数
    最后一份高度 = total_height % 每份高度
    
    if 最后一份高度 < min_split_height and 切割份数 > 1:
        每份高度 = (total_height + 切割份数 - 1) // 切割份数
    
    当前高度 = 0
    for i in range(切割份数):
        if i == 切割份数 - 1:
            结束高度 = total_height
        else:
            结束高度 = 当前高度 + 每份高度
        
        结束高度 = min(结束高度, total_height)
        
        切割图片 = merged_image.crop((0, 当前高度, target_width, 结束高度))
        
        if OUTPUT_WEBP:
            保存路径 = os.path.join(output_dir, f"{output_prefix}{i+1}.webp")
            切割图片.save(保存路径, format="WebP", quality=jpeg_quality)
        else:
            保存路径 = os.path.join(output_dir, f"{output_prefix}{i+1}.jpg")
            切割图片.save(保存路径, quality=jpeg_quality)
        
        当前高度 = 结束高度
    
    return 切割份数


def convert_animated_image(file_path, output_path, target_width=None):
    """将动图转换为WebP格式的动图文件"""
    try:
        with Image.open(file_path) as img:
            if img.is_animated:
                total_frames = img.n_frames
                
                if target_width and img.width != target_width:
                    scale = target_width / img.width
                    new_width = target_width
                    new_height = int(img.height * scale)
                    
                    frames = []
                    for frame_idx in range(total_frames):
                        img.seek(frame_idx)
                        resized_frame = img.resize((new_width, new_height), Image.LANCZOS)
                        frames.append(resized_frame.copy())
                    
                    if frames:
                        frames[0].save(
                            output_path, 
                            format="WebP", 
                            save_all=True, 
                            append_images=frames[1:], 
                            loop=0, 
                            quality=webp_quality,
                            method=webp_method
                        )
                        print(f"动图转换: {os.path.basename(file_path)} ({total_frames}帧) -> {os.path.basename(output_path)}", flush=True)
                        return True
                else:
                    img.save(
                        output_path, 
                        format="WebP", 
                        save_all=True, 
                        loop=0, 
                        quality=webp_quality,
                        method=webp_method
                    )
                    print(f"动图转换: {os.path.basename(file_path)} ({total_frames}帧) -> {os.path.basename(output_path)}", flush=True)
                    return True
        return False
    except Exception as e:
        print(f"转换动图失败 {file_path}: {e}", flush=True)
        return False


def collect_image_files(directory, prefix):
    """收集指定前缀的图片文件"""
    image_patterns = []
    base_exts = ['jpg', 'png', 'jpeg', 'avif']
    animated_exts = ['gif', 'webp'] if WITH_ANIMATED else []
    
    all_exts = base_exts + animated_exts
    
    for ext in all_exts:
        image_patterns.append(os.path.join(directory, f'{prefix}*.{ext}'))
    
    files = []
    for pattern in image_patterns:
        files.extend(glob.glob(pattern))
    
    return sorted(files, key=natural_sort_key)


def process_images_parallel(image_paths, process_func, max_workers=None):
    """并行处理图片"""
    if max_workers is None:
        max_workers = parallel_workers
    
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_func, path) for path in image_paths]
        for future in futures:
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"处理图片失败: {e}", flush=True)
    
    return results


class ProgressReporter:
    """统一的进度报告器"""
    
    def __init__(self):
        self.main_start_time = None
        self.detail_start_time = None
        self.color_start_time = None
        self.main_stats = {'total': 0, 'processed': 0, 'skipped': 0, 'errors': 0, 'generated': 0}
        self.detail_stats = {'total': 0, 'processed': 0, 'skipped': 0, 'errors': 0, 'generated': 0}
        self.color_stats = {'total': 0, 'processed': 0, 'skipped': 0, 'errors': 0, 'generated': 0}
        self.progress_callback = None  # 进度回调函数
        self.current_file = None  # 当前处理的文件
        self.progress_manager = None  # 共享内存进度管理器
    
    def set_progress_callback(self, callback):
        """设置进度回调函数
        
        Args:
            callback: 回调函数，接受 (file_path, progress_text, progress_type) 参数
        """
        self.progress_callback = callback
    
    def set_current_file(self, file_path):
        """设置当前处理的文件
        
        Args:
            file_path: 文件路径
        """
        self.current_file = file_path
    
    def set_progress_manager(self, manager):
        """设置共享内存进度管理器
        
        Args:
            manager: SharedProgressManager实例
        """
        self.progress_manager = manager
    
    def start_main(self):
        """开始主图处理"""
        self.main_start_time = time.time()
        if self.progress_manager:
            self.progress_manager.start_main()
    
    def start_detail(self):
        """开始详情图处理"""
        self.detail_start_time = time.time()
        if self.progress_manager:
            self.progress_manager.start_detail()
    
    def start_color(self):
        """开始色卡图处理"""
        self.color_start_time = time.time()
        if self.progress_manager:
            self.progress_manager.start_color()
    
    def show_progress(self, name, current, total):
        """显示进度条"""
        bar_length = GUI_CONF.get('progress_bar_width', 20) if 'GUI_CONF' in dir() else 20
        percent = int((current / total) * 100) if total > 0 else 0
        filled = int(bar_length * current / total) if total > 0 else 0
        bar = '█' * filled + '░' * (bar_length - filled)
        progress_text = f"[{bar}] {percent}%"
        
        # 通知GUI更新进度
        if self.progress_callback and self.current_file:
            progress_type = 'detail'
            if '主图' in name:
                progress_type = 'main'
            elif '色卡' in name:
                progress_type = 'color'
            self.progress_callback(self.current_file, progress_text, progress_type)
        
        # 更新共享内存进度
        if self.progress_manager:
            if '主图' in name:
                self.progress_manager.update_main(current=current, total=total)
            elif '详情图' in name:
                self.progress_manager.update_detail(current=current, total=total)
            elif '色卡' in name:
                self.progress_manager.update_color(current=current, total=total)
    
    def complete_progress(self, name):
        """完成进度显示"""
        # 通知GUI清除进度
        if self.progress_callback and self.current_file:
            self.progress_callback(self.current_file, "", "")
        
        # 更新共享内存状态
        if self.progress_manager:
            if '主图' in name:
                self.progress_manager.complete_main()
            elif '详情图' in name:
                self.progress_manager.complete_detail()
            elif '色卡' in name:
                self.progress_manager.complete_color()
    
    def show_section_header(self, name, count):
        """显示章节标题"""
        print(f"\n{'='*50}")
        print(f"  {name} ({count} 张)")
        print(f"{'='*50}")
    
    def show_section_summary(self, name, stats):
        """显示章节小结"""
        # 根据队列类型计算耗时
        if '主图' in name and self.main_start_time:
            elapsed = time.time() - self.main_start_time
        elif '详情图' in name and self.detail_start_time:
            elapsed = time.time() - self.detail_start_time
        elif '色卡' in name and self.color_start_time:
            elapsed = time.time() - self.color_start_time
        else:
            elapsed = 0
        
        print(f"\n{name}")
        # 对于详情图，显示生成图片数量
        if '详情图' in name and stats.get('generated', 0) > 0:
            print(f"  处理完成: {stats['processed']} 张  生成图片: {stats['generated']} 张")
        else:
            print(f"  处理完成: {stats['processed']} 张")
        print(f"  跳过文件: {stats['skipped']} 张")
        if stats['errors'] > 0:
            print(f"  处理失败: {stats['errors']} 张")
        print(f"  耗时: {elapsed:.1f} 秒")
    
    def show_final_summary(self):
        """显示最终汇总报告"""
        # 计算总耗时
        if self.main_start_time and self.color_start_time:
            total_elapsed = time.time() - self.main_start_time
        else:
            total_elapsed = 0
        
        total_processed = self.main_stats['processed'] + self.detail_stats['processed'] + self.color_stats['processed']
        total_skipped = self.main_stats['skipped'] + self.detail_stats['skipped'] + self.color_stats['skipped']
        total_errors = self.main_stats['errors'] + self.detail_stats['errors'] + self.color_stats['errors']
        
        print(f"\n{'='*50}")
        print(f"图像优化处理报告")
        print(f"{'='*50}")
        print(f"  主图:   处理 {self.main_stats['processed']} 张, 跳过 {self.main_stats['skipped']} 张")
        print(f"  详情图: 处理 {self.detail_stats['processed']} 张, 跳过 {self.detail_stats['skipped']} 张")
        print(f"  色卡图: 处理 {self.color_stats['processed']} 张, 跳过 {self.color_stats['skipped']} 张")
        print(f"  总计:   处理 {total_processed} 张, 跳过 {total_skipped} 张")
        if total_errors > 0:
            print(f"          失败 {total_errors} 张")
        print(f"  耗时:   {total_elapsed:.1f} 秒")
        print(f"{'='*50}\n")


reporter = ProgressReporter()


# 线程安全的进度计数器
class ProgressCounter:
    def __init__(self, total):
        self.total = total
        self.count = 0
        self.lock = threading.Lock()
    
    def increment(self):
        with self.lock:
            self.count += 1
            return self.count


# 多进程处理详情图的全局变量
_process_detail_current_dir = None
_process_detail_counter = None


def _init_process_detail(current_dir, counter):
    """初始化多进程处理详情图的全局变量"""
    global _process_detail_current_dir, _process_detail_counter
    _process_detail_current_dir = current_dir
    _process_detail_counter = counter


def _process_single_detail_worker(args):
    """处理单张详情图的工作函数（模块级别，用于多进程）"""
    file_path, width, height, total_count = args
    try:
        with Image.open(file_path) as img:
            if utils.image_utils.OUTPUT_WEBP:
                base_name = os.path.basename(file_path)
                name, ext = os.path.splitext(base_name)
                webp_path = os.path.join(_process_detail_current_dir, f"{name}.webp")
                if width >= detail_min_width:
                    img.save(webp_path, format="WebP", quality=jpeg_quality)
                    return ('skipped', True)
                else:
                    result = enlarge_image(img)
                    img_resized = result[0]
                    img_resized.save(webp_path, format="WebP", quality=jpeg_quality)
                    return ('processed', True)
            else:
                if width >= detail_min_width:
                    return ('skipped', False)
                else:
                    result = enlarge_image(img)
                    img_resized = result[0]
                    img_resized.save(file_path, quality=jpeg_quality)
                    return ('processed', False)
    except Exception as e:
        return ('error', str(e))


def _split_with_custom_index(merged_image, target_width, total_height, output_dir, output_prefix, start_index):
    """切割拼接图片，使用自定义的起始文件索引
    
    Args:
        merged_image: 拼接后的图片
        target_width: 目标宽度
        total_height: 总高度
        output_dir: 输出目录
        output_prefix: 输出文件前缀
        start_index: 起始文件索引
        
    Returns:
        int: 切割生成的文件数量
    """
    max_single_height = target_width * 2
    
    if total_height <= max_single_height:
        if utils.image_utils.OUTPUT_WEBP:
            save_path = os.path.join(output_dir, f"{output_prefix}{start_index}.webp")
            merged_image.save(save_path, format="WebP", quality=jpeg_quality)
        else:
            save_path = os.path.join(output_dir, f"{output_prefix}{start_index}.jpg")
            merged_image.save(save_path, quality=jpeg_quality)
        
        return 1
    
    切割份数 = (total_height + max_single_height - 1) // max_single_height
    
    每份高度 = total_height // 切割份数
    最后一份高度 = total_height % 每份高度
    
    if 最后一份高度 < 200 and 切割份数 > 1:
        每份高度 = (total_height + 切割份数 - 1) // 切割份数
    
    当前高度 = 0
    file_count = 0
    
    for i in range(切割份数):
        if i == 切割份数 - 1:
            结束高度 = total_height
        else:
            结束高度 = 当前高度 + 每份高度
        
        结束高度 = min(结束高度, total_height)
        
        切割图片 = merged_image.crop((0, 当前高度, target_width, 结束高度))
        
        current_index = start_index + i
        
        if utils.image_utils.OUTPUT_WEBP:
            保存路径 = os.path.join(output_dir, f"{output_prefix}{current_index}.webp")
            切割图片.save(保存路径, format="WebP", quality=jpeg_quality)
        else:
            保存路径 = os.path.join(output_dir, f"{output_prefix}{current_index}.jpg")
            切割图片.save(保存路径, quality=jpeg_quality)
        
        当前高度 = 结束高度
        file_count += 1
    
    print(f"\n拼接图切割完成，共 {file_count} 份")
    return file_count


def _process_static_batch(static_batch, current_dir, base_output_name, file_index, target_width, is_small):
    """处理静态图片批次
    
    Args:
        static_batch: 静态图片批次
        current_dir: 当前工作目录
        base_output_name: 输出文件的基础名称
        file_index: 起始文件索引
        target_width: 目标宽度
        is_small: 是否为小图流程
        
    Returns:
        int: 处理后下一个可用的文件索引
    """
    images = []
    total_height = 0
    
    sorted_batch = sorted(static_batch, key=lambda x: natural_sort_key(x[0]))
    
    for file_path, width, height in sorted_batch:
        try:
            with Image.open(file_path) as img:
                if is_small:
                    img_resized, (new_width, new_height, desc) = enlarge_image(img)
                    if new_width != target_width:
                        img_resized = img_resized.resize((target_width, int(new_height * target_width / new_width)), Image.LANCZOS)
                    img_copy = img_resized.copy()
                else:
                    if img.width < detail_min_width:
                        img_resized, (new_width, new_height, desc) = enlarge_image(img)
                        if new_width != target_width:
                            img_resized = img_resized.resize((target_width, int(new_height * target_width / new_width)), Image.LANCZOS)
                        img_copy = img_resized.copy()
                    elif img.width != target_width:
                        img_resized = img.resize((target_width, int(img.height * target_width / img.width)), Image.LANCZOS)
                        img_copy = img_resized.copy()
                    else:
                        img_copy = img.copy()
                
                images.append(img_copy)
                total_height += img_copy.height
        except Exception as e:
            print(f"无法处理图片 {file_path}: {e}", flush=True)
    
    if not images:
        return file_index
    
    merged_image = Image.new('RGB', (target_width, total_height), (255, 255, 255))
    current_height = 0
    for img in images:
        merged_image.paste(img, (0, current_height))
        current_height += img.height
    
    cut_count = _split_with_custom_index(merged_image, target_width, total_height, current_dir, base_output_name, file_index)
    
    return file_index + cut_count


def process_mixed_images(images_info, current_dir, base_output_name):
    """处理混合图片序列（静态图和动图）
    
    Args:
        images_info: 图片信息列表，每个元素为(file_path, width, height, is_animated)
        current_dir: 当前工作目录
        base_output_name: 输出文件的基础名称
        
    Returns:
        int: 处理后生成的文件总数
    """
    static_batch = []
    file_index = 1
    target_width = None
    
    total_images = len(images_info)
    animated_count = sum(1 for _, _, _, is_animated in images_info if is_animated)
    static_count = total_images - animated_count
    
    print(f"混合图片处理: 共 {total_images} 张 (静态图: {static_count}, 动图: {animated_count})", flush=True)
    
    all_static_widths = []
    for file_path, width, height, is_animated in images_info:
        if not is_animated:
            all_static_widths.append(width)
    
    if all_static_widths:
        max_width = max(all_static_widths)
        
        if max_width <= enlarge_step1_width:
            target_width = enlarge_step2_width
        else:
            width_counts = {}
            for w in all_static_widths:
                width_counts[w] = width_counts.get(w, 0) + 1
            main_width = max(width_counts.keys(), key=lambda w: width_counts[w])
            target_width = get_enlarge_target_width(main_width)
    
    processed_count = 0
    
    for i, (file_path, width, height, is_animated) in enumerate(images_info):
        if not is_animated:
            static_batch.append((file_path, width, height))
        else:
            if static_batch:
                if max(w for _, w, _ in static_batch) <= enlarge_step1_width:
                    file_index = _process_static_batch(static_batch, current_dir, base_output_name, file_index, target_width, is_small=True)
                else:
                    file_index = _process_static_batch(static_batch, current_dir, base_output_name, file_index, target_width, is_small=False)
                
                processed_count += len(static_batch)
                percent = int((processed_count / total_images) * 100)
                print(f'混合图片处理进度: {processed_count}/{total_images} ({percent}%)', flush=True)
                reporter.show_progress("详情图", processed_count, total_images)
                
                static_batch = []
            
            output_path = os.path.join(current_dir, f"{base_output_name}{file_index}.webp")
            
            if convert_animated_image(file_path, output_path, target_width):
                file_index += 1
            
            processed_count += 1
            percent = int((processed_count / total_images) * 100)
            print(f'混合图片处理进度: {processed_count}/{total_images} ({percent}%)', flush=True)
            reporter.show_progress("详情图", processed_count, total_images)
    
    if static_batch:
        if max(w for _, w, _ in static_batch) <= enlarge_step1_width:
            file_index = _process_static_batch(static_batch, current_dir, base_output_name, file_index, target_width, is_small=True)
        else:
            file_index = _process_static_batch(static_batch, current_dir, base_output_name, file_index, target_width, is_small=False)
        
        processed_count += len(static_batch)
        percent = int((processed_count / total_images) * 100)
        print(f'混合图片处理进度: {processed_count}/{total_images} ({percent}%)', flush=True)
        reporter.show_progress("详情图", processed_count, total_images)
    
    return file_index - 1


def enlarge_main_images():
    """放大主图功能：两步处理主图"""
    reporter.start_main()  # 记录主图开始时间
    current_dir = os.getcwd()
    main_files = collect_image_files(current_dir, main_image_prefix)

    if not main_files:
        reporter.main_stats = {'total': 0, 'processed': 0, 'skipped': 0, 'errors': 0}
        return

    total_files = len(main_files)
    reporter.main_stats['total'] = total_files
    reporter.show_section_header("主图处理", total_files)
    
    step1_queue = []
    step1_processed = 0
    need_step1 = False

    for file_path in main_files:
        try:
            with Image.open(file_path) as img:
                width, height = img.size

                base_name = os.path.basename(file_path)
                name, ext = os.path.splitext(base_name)

                if name.startswith('E_'):
                    step1_queue.append(file_path)
                    continue

                if width < main_image_min_size or height < main_image_min_size:
                    need_step1 = True
                
                step1_queue.append(file_path)
        except Exception as e:
            reporter.main_stats['errors'] += 1
    
    processed_count = 0
    
    if need_step1:
        for i, file_path in enumerate(step1_queue, 1):
            try:
                with Image.open(file_path) as img:
                    width, height = img.size

                    base_name = os.path.basename(file_path)
                    name, ext = os.path.splitext(base_name)

                    if name.startswith('E_'):
                        continue

                    if width < main_image_min_size or height < main_image_min_size:
                        scale = max(main_image_min_size / width, main_image_min_size / height)
                        new_width = int(width * scale)
                        new_height = int(height * scale)

                        img_resized = img.resize((new_width, new_height), Image.LANCZOS)
                        img_resized.save(file_path, quality=jpeg_quality)
                        step1_processed += 1
                        reporter.main_stats['processed'] += 1
                    else:
                        reporter.main_stats['skipped'] += 1

            except Exception as e:
                reporter.main_stats['errors'] += 1
            
            processed_count += 1
            reporter.show_progress("主图", processed_count, len(step1_queue))
        
        reporter.complete_progress("主图")
    
    for i, file_path in enumerate(step1_queue, 1):
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                base_name = os.path.basename(file_path)
                name, ext = os.path.splitext(base_name)
                if name.startswith('E_'):
                    continue
                new_name = f"E_{name}{ext}"
                output_path = os.path.join(current_dir, new_name)
                if utils.image_utils.OUTPUT_WEBP and utils.image_utils.CONVERT_MAIN:
                    webp_path = os.path.join(current_dir, f"E_{name}.webp")
                    if width < main_image_target_size or height < main_image_target_size:
                        img_resized = img.resize((main_image_target_size, main_image_target_size), Image.LANCZOS)
                        img_resized.save(webp_path, format="WebP", quality=jpeg_quality)
                        reporter.main_stats['processed'] += 1
                    else:
                        img.save(webp_path, format="WebP", quality=jpeg_quality)
                        reporter.main_stats['skipped'] += 1
                else:
                    if width < main_image_target_size or height < main_image_target_size:
                        img_resized = img.resize((main_image_target_size, main_image_target_size), Image.LANCZOS)
                        img_resized.save(output_path, quality=jpeg_quality)
                        reporter.main_stats['processed'] += 1
                    else:
                        img.save(output_path, quality=jpeg_quality)
                        reporter.main_stats['skipped'] += 1

        except Exception as e:
            reporter.main_stats['errors'] += 1
        
        reporter.show_progress("主图", i, len(step1_queue))
    
    reporter.complete_progress("主图")
    reporter.show_section_summary("主图处理完成", reporter.main_stats)


def enlarge_detail_images():
    """详情图放大处理功能（多进程版本）"""
    current_dir = os.getcwd()
    detail_files = collect_image_files(current_dir, detail_image_prefix)
    
    if not detail_files:
        reporter.detail_stats = {'total': 0, 'processed': 0, 'skipped': 0, 'errors': 0}
        return
    
    total_files = len(detail_files)
    reporter.detail_stats['total'] = total_files
    reporter.show_section_header("详情图处理", total_files)
    
    process_queue = []
    skip_queue = []
    
    for file_path in detail_files:
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                base_name = os.path.basename(file_path)
                
                if width >= min_width:
                    process_queue.append((file_path, width, height))
                else:
                    skip_queue.append((file_path, width, height))
        except Exception as e:
            reporter.detail_stats['errors'] += 1
    
    if skip_queue:
        reporter.detail_stats['skipped'] += len(skip_queue)
    
    if not process_queue:
        reporter.show_section_summary("详情图处理完成", reporter.detail_stats)
        return
    
    # 使用全局变量传递参数
    global _process_detail_current_dir
    _process_detail_current_dir = current_dir
    
    # 准备参数
    total_count = len(process_queue)
    args_list = [(f, w, h, total_count) for f, w, h in process_queue]
    
    with multiprocessing.Pool(processes=parallel_workers) as pool:
        results = pool.map(_process_single_detail_worker, args_list)
    
    # 统计结果
    for result in results:
        if result[0] == 'processed':
            reporter.detail_stats['processed'] += 1
        elif result[0] == 'skipped':
            reporter.detail_stats['skipped'] += 1
        if result[1] == True:
            pass
    
    reporter.show_section_summary("详情图处理完成", reporter.detail_stats)


def enlarge_color_card_images():
    """色卡图放大处理功能
    
    处理后的文件使用 new_ 前缀命名，避免与原始文件冲突
    """
    reporter.start_color()  # 记录色卡图开始时间
    current_dir = os.getcwd()
    color_files = collect_image_files(current_dir, color_option_prefix)
    
    if not color_files:
        reporter.color_stats = {'total': 0, 'processed': 0, 'skipped': 0, 'errors': 0}
        return
    
    total_files = len(color_files)
    reporter.color_stats['total'] = total_files
    reporter.show_section_header("色卡图处理", total_files)
    
    for i, file_path in enumerate(color_files, 1):
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                
                base_name = os.path.basename(file_path)
                name, ext = os.path.splitext(base_name)
                
                if utils.image_utils.OUTPUT_WEBP and utils.image_utils.CONVERT_COLOR:
                    new_file_name = f"new_{name}.webp"
                    new_file_path = os.path.join(current_dir, new_file_name)
                    if width >= detail_min_width:
                        img.save(new_file_path, format="WebP", quality=jpeg_quality)
                        reporter.color_stats['skipped'] += 1
                    else:
                        result = enlarge_image(img)
                        img_resized = result[0]
                        img_resized.save(new_file_path, format="WebP", quality=jpeg_quality)
                        reporter.color_stats['processed'] += 1
                else:
                    new_file_name = f"new_{name}{ext}"
                    new_file_path = os.path.join(current_dir, new_file_name)
                    if width >= detail_min_width:
                        img.save(new_file_path, quality=jpeg_quality)
                        reporter.color_stats['skipped'] += 1
                    else:
                        result = enlarge_image(img)
                        img_resized = result[0]
                        img_resized.save(new_file_path, quality=jpeg_quality)
                        reporter.color_stats['processed'] += 1
        except Exception as e:
            reporter.color_stats['errors'] += 1
        
        reporter.show_progress("色卡图", i, total_files)
    
    reporter.complete_progress("色卡图")
    reporter.show_section_summary("色卡图处理完成", reporter.color_stats)


def process_regular_detail_images():
    """常规详情图拼接处理"""
    reporter.start_detail()  # 记录详情图开始时间
    current_dir = os.getcwd()
    c_files = collect_image_files(current_dir, detail_image_prefix)
    
    if not c_files:
        reporter.detail_stats = {'total': 0, 'processed': 0, 'skipped': 0, 'errors': 0}
        return
    
    original_count = len(c_files)
    reporter.detail_stats['total'] = original_count
    reporter.show_section_header("详情图处理", original_count)
    
    all_images_info = []
    has_animated = False
    for file_path in c_files:
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                is_animated = getattr(img, 'is_animated', False)
                all_images_info.append((file_path, width, height, is_animated))
                if is_animated:
                    has_animated = True
        except Exception as e:
            reporter.detail_stats['errors'] += 1
    
    filtered_images = [(file_path, width, height, is_animated) for file_path, width, height, is_animated in all_images_info if width >= min_width]
    
    removed_small = len(all_images_info) - len(filtered_images)
    if removed_small > 0:
        reporter.detail_stats['skipped'] += removed_small
    
    if not filtered_images:
        reporter.show_section_summary("详情图处理完成", reporter.detail_stats)
        return
    
    animated_count = sum(1 for _, _, _, is_animated in filtered_images if is_animated)
    static_count = len(filtered_images) - animated_count
    
    if has_animated:
        total_files = process_mixed_images(filtered_images, current_dir, new_image_prefix)
        reporter.detail_stats['processed'] += total_files
        reporter.detail_stats['generated'] += total_files
    else:
        small_images = [(f, w, h) for f, w, h, _ in filtered_images if w <= enlarge_step1_width]
        large_images = [(f, w, h) for f, w, h, _ in filtered_images if w > enlarge_step1_width]
        
        if small_images and not large_images:
            generated = _process_small_images(small_images, current_dir)
            reporter.detail_stats['processed'] += len(small_images)
            reporter.detail_stats['generated'] += generated
        elif large_images and not small_images:
            generated = _process_large_images(large_images, current_dir)
            reporter.detail_stats['processed'] += len(large_images)
            reporter.detail_stats['generated'] += generated
        elif small_images and large_images:
            small_count = len(small_images)
            large_count = len(large_images)
            ratio = small_count / large_count if large_count > 0 else float('inf')
            
            if ratio >= 10:
                generated = _process_small_images(small_images, current_dir)
                reporter.detail_stats['processed'] += len(small_images)
                reporter.detail_stats['generated'] += generated
            elif ratio <= 0.1:
                generated = _process_large_images(large_images, current_dir)
                reporter.detail_stats['processed'] += len(large_images)
                reporter.detail_stats['generated'] += generated
            else:
                generated = _process_mixed_size_images(small_images, large_images, current_dir)
                reporter.detail_stats['processed'] += len(small_images) + len(large_images)
                reporter.detail_stats['generated'] += generated
    
    reporter.show_section_summary("详情图处理完成", reporter.detail_stats)


def _process_small_images(small_images, current_dir):
    """处理小图放大拼接流程
    
    Returns:
        int: 生成的图片数量
    """
    images = []
    
    small_images_sorted = sorted(small_images, key=lambda x: natural_sort_key(x[0]))
    total_files = len(small_images_sorted)
    
    target_width = enlarge_step2_width
    
    for i, (file_path, width, height) in enumerate(small_images_sorted, 1):
        try:
            with Image.open(file_path) as img:
                img_resized, (new_width, new_height, desc) = enlarge_image(img)
                if img_resized.width != target_width:
                    img_resized = img_resized.resize((target_width, int(img_resized.height * target_width / img_resized.width)), Image.LANCZOS)
                images.append(img_resized.copy())
        except Exception as e:
            reporter.detail_stats['errors'] += 1
        
        reporter.show_progress("详情图", i, total_files)
    
    reporter.complete_progress("详情图")
    
    if not images:
        return 0
    
    总高度 = sum(img.height for img in images)
    拼接图片 = Image.new('RGB', (target_width, 总高度), (255, 255, 255))
    
    当前高度 = 0
    for img in images:
        拼接图片.paste(img, (0, 当前高度))
        当前高度 += img.height
    
    return split_merged_image(拼接图片, target_width, 总高度, current_dir, new_image_prefix)


def _process_large_images(large_images, current_dir):
    """处理大图拼接流程
    
    Returns:
        int: 生成的图片数量
    """
    总高度 = 0
    images = []
    
    main_files_sorted = sorted(large_images, key=natural_sort_key)
    total_files = len(main_files_sorted)
    
    target_width = None
    
    for i, (file_path, width, height) in enumerate(main_files_sorted, 1):
        try:
            with Image.open(file_path) as img:
                if target_width is None:
                    target_width = img.width if img.width >= detail_min_width else enlarge_step2_width
                
                if img.width < detail_min_width:
                    img_resized, (new_width, new_height, desc) = enlarge_image(img)
                    if new_width != target_width:
                        img_resized = img_resized.resize((target_width, int(new_height * target_width / new_width)), Image.LANCZOS)
                    img_copy = img_resized.copy()
                elif img.width != target_width:
                    img_resized = img.resize((target_width, int(img.height * target_width / img.width)), Image.LANCZOS)
                    img_copy = img_resized.copy()
                else:
                    img_copy = img.copy()
                images.append(img_copy)
                总高度 += img_copy.height
        except Exception as e:
            reporter.detail_stats['errors'] += 1
        
        reporter.show_progress("详情图", i, total_files)
    
    reporter.complete_progress("详情图")
    
    if not images:
        return 0
    
    拼接图片 = Image.new('RGB', (target_width, 总高度), (255, 255, 255))
    
    当前高度 = 0
    for img in images:
        拼接图片.paste(img, (0, 当前高度))
        当前高度 += img.height
    
    return split_merged_image(拼接图片, target_width, 总高度, current_dir, new_image_prefix)


def _process_mixed_size_images(small_images, large_images, current_dir):
    """处理混合尺寸图片拼接流程
    
    将小图放大后与大图合并处理
    
    Args:
        small_images: 小图列表 [(file_path, width, height), ...]
        large_images: 大图列表 [(file_path, width, height), ...]
        current_dir: 当前目录
    
    Returns:
        int: 生成的图片数量
    """
    总高度 = 0
    images = []
    
    # 使用 enlarge_step2_width 作为目标宽度，而不是大图的平均宽度
    target_width = enlarge_step2_width
    
    # 合并并排序所有图片
    all_images = small_images + large_images
    all_images_sorted = sorted(all_images, key=lambda x: natural_sort_key(x[0]))
    total_files = len(all_images_sorted)
    
    for i, (file_path, width, height) in enumerate(all_images_sorted, 1):
        try:
            with Image.open(file_path) as img:
                if width < enlarge_step1_width:
                    # 小图：放大到目标宽度
                    img_resized, (new_width, new_height, desc) = enlarge_image(img)
                    if new_width != target_width:
                        img_resized = img_resized.resize((target_width, int(new_height * target_width / new_width)), Image.LANCZOS)
                    img_copy = img_resized.copy()
                elif width < target_width:
                    # 中等尺寸：调整到目标宽度
                    img_resized = img.resize((target_width, int(img.height * target_width / img.width)), Image.LANCZOS)
                    img_copy = img_resized.copy()
                elif width > target_width:
                    # 大图：缩小到目标宽度
                    img_resized = img.resize((target_width, int(img.height * target_width / img.width)), Image.LANCZOS)
                    img_copy = img_resized.copy()
                else:
                    img_copy = img.copy()
                images.append(img_copy)
                总高度 += img_copy.height
        except Exception as e:
            reporter.detail_stats['errors'] += 1
        
        reporter.show_progress("详情图", i, total_files)
    
    reporter.complete_progress("详情图")
    
    if not images:
        return 0
    
    拼接图片 = Image.new('RGB', (target_width, 总高度), (255, 255, 255))
    
    当前高度 = 0
    for img in images:
        拼接图片.paste(img, (0, 当前高度))
        当前高度 += img.height
    
    return split_merged_image(拼接图片, target_width, 总高度, current_dir, new_image_prefix)


def process_single_image(image_path):
    """处理单张图片"""
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            
            if width < min_width:
                return None
            
            if width >= detail_min_width:
                return img
            
            img_resized, (new_width, new_height, desc) = enlarge_image(img)
            return img_resized
    except Exception as e:
        print(f"处理图片失败 {image_path}: {e}")
        return None
