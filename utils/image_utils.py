"""
图像处理基础工具模块

提供图像处理的基础功能，包括：
- 图片放大
- 图片切割
- 动图转换
- 文件收集
- 并行处理
"""

import os
import sys
import re
from PIL import Image
import glob
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple, Optional

if sys.stdout:
    sys.stdout.reconfigure(line_buffering=True)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FILE_NAMING, IMAGE_PROCESSING

# 全局变量定义
WITH_ANIMATED = False
OUTPUT_WEBP = False
CONVERT_MAIN = False
CONVERT_COLOR = False

# 配置参数
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
    # 对于宽度在 enlarge_step1_width 和 detail_min_width 之间的图片
    # 统一放大到 enlarge_step2_width
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
    """切割拼接后的图片
    
    Args:
        merged_image: 拼接后的图片
        target_width: 目标宽度
        total_height: 总高度
        output_dir: 输出目录
        output_prefix: 输出文件前缀
    
    Returns:
        int: 生成的图片数量
      """
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
    """将动图转换为WebP格式的动图文件
    
    Args:
        file_path: 输入动图文件路径
        output_path: 输出WebP动图文件路径
        target_width: 目标宽度，如果指定则将动图放大到该宽度
        
    Returns:
        bool: True如果转换成功，False否则
    """
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
    """并行处理图片
    
    Args:
        image_paths: 图片路径列表
        process_func: 处理函数
        max_workers: 最大并行数，默认使用配置值
        
    Returns:
        处理结果列表
    """
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
