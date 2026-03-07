"""
图像处理流程模块

提供图像处理的完整流程，包括：
- 主图处理
- 详情图处理
- 色卡图处理
- 混合图片处理
"""

import os
import sys
from PIL import Image

if sys.stdout:
    sys.stdout.reconfigure(line_buffering=True)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.image_utils import (
    natural_sort_key, enlarge_image, get_enlarge_target_width,
    check_aspect_ratio, split_merged_image, convert_animated_image,
    collect_image_files, process_images_parallel,
    detail_image_prefix, new_image_prefix, main_image_prefix, color_option_prefix,
    min_width, detail_min_width, detail_width_tolerance,
    enlarge_step1_width, enlarge_step2_width, photo_min_width,
    main_image_min_size, main_image_target_size, jpeg_quality,
    OUTPUT_WEBP, CONVERT_MAIN, CONVERT_COLOR, parallel_workers
)


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
        if OUTPUT_WEBP:
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
        
        if OUTPUT_WEBP:
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
        if max(all_static_widths) <= enlarge_step1_width:
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
                
                static_batch = []
            
            output_path = os.path.join(current_dir, f"{base_output_name}{file_index}.webp")
            
            if convert_animated_image(file_path, output_path, target_width):
                file_index += 1
            
            processed_count += 1
            percent = int((processed_count / total_images) * 100)
            print(f'混合图片处理进度: {processed_count}/{total_images} ({percent}%)', flush=True)
    
    if static_batch:
        if max(w for _, w, _ in static_batch) <= enlarge_step1_width:
            file_index = _process_static_batch(static_batch, current_dir, base_output_name, file_index, target_width, is_small=True)
        else:
            file_index = _process_static_batch(static_batch, current_dir, base_output_name, file_index, target_width, is_small=False)
        
        processed_count += len(static_batch)
        percent = int((processed_count / total_images) * 100)
        print(f'混合图片处理进度: {processed_count}/{total_images} ({percent}%)', flush=True)
    
    return file_index - 1


def enlarge_main_images():
    """放大主图功能：两步处理主图"""
    print("\n开始处理主图放大...", flush=True)

    current_dir = os.getcwd()
    main_files = collect_image_files(current_dir, main_image_prefix)

    if not main_files:
        print(f"没有找到{main_image_prefix}开头的图片文件", flush=True)
        return

    total_files = len(main_files)
    print(f"找到 {total_files} 张主图文件", flush=True)
    
    bar_length = 40
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
            print(f"\n处理图片 {file_path} 时出错: {e}", flush=True)
    
    if need_step1:
        print(f"\n=== 第一步处理：将小于{main_image_min_size}px的图片放大到{main_image_min_size}px ===", flush=True)
        
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

            except Exception as e:
                print(f"\n处理图片 {file_path} 时出错: {e}", flush=True)
            
            percent = (i / len(step1_queue)) * 100
            filled = int(bar_length * i / len(step1_queue))
            bar = '█' * filled + '-' * (bar_length - filled)
            print(f'主图处理进度: [{bar}] {i}/{len(step1_queue)} ({percent:.1f}%)', flush=True)
        
        print(f'\n第一步完成：放大 {step1_processed} 张图片', flush=True)
    
    need_step2 = False
    for file_path in step1_queue:
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                if main_image_min_size <= width <= detail_min_width and main_image_min_size <= height <= detail_min_width:
                    need_step2 = True
                    break
        except:
            pass
    
    if not need_step2:
        if OUTPUT_WEBP and CONVERT_MAIN:
            print(f"\n=== 主图WebP转换 ===", flush=True)
            for i, file_path in enumerate(step1_queue, 1):
                try:
                    with Image.open(file_path) as img:
                        base_name = os.path.basename(file_path)
                        name, ext = os.path.splitext(base_name)
                        webp_path = os.path.join(current_dir, f"{name}.webp")
                        img.save(webp_path, format="WebP", quality=jpeg_quality)
                except Exception as e:
                    print(f"\n转换WebP失败 {file_path}: {e}", flush=True)
                
                percent = (i / len(step1_queue)) * 100
                filled = int(bar_length * i / len(step1_queue))
                bar = '█' * filled + '-' * (bar_length - filled)
                print(f'主图WebP转换进度: [{bar}] {i}/{len(step1_queue)} ({percent:.1f}%)', flush=True)
        
        print(f"主图处理完成！无需放大处理", flush=True)
        return

    print(f"\n=== 第二步处理：将{main_image_min_size}px到{detail_min_width}px之间的图片放大到{main_image_target_size}px ===", flush=True)

    processed_count = 0
    skipped_count = 0

    for i, file_path in enumerate(step1_queue, 1):
        try:
            with Image.open(file_path) as img:
                width, height = img.size

                base_name = os.path.basename(file_path)
                name, ext = os.path.splitext(base_name)

                new_name = f"E_{name}{ext}"
                output_path = os.path.join(current_dir, new_name)

                if OUTPUT_WEBP and CONVERT_MAIN:
                    webp_path = os.path.join(current_dir, f"E_{name}.webp")
                    if main_image_min_size <= width <= detail_min_width and main_image_min_size <= height <= detail_min_width:
                        img_resized = img.resize((main_image_target_size, main_image_target_size), Image.LANCZOS)
                        img_resized.save(webp_path, format="WebP", quality=jpeg_quality)
                    else:
                        img.save(webp_path, format="WebP", quality=jpeg_quality)
                    processed_count += 1
                else:
                    if main_image_min_size <= width <= detail_min_width and main_image_min_size <= height <= detail_min_width:
                        img_resized = img.resize((main_image_target_size, main_image_target_size), Image.LANCZOS)
                        img_resized.save(output_path, quality=jpeg_quality)
                    else:
                        img.save(output_path, quality=jpeg_quality)
                    processed_count += 1

        except Exception as e:
            skipped_count += 1
        
        percent = (i / len(step1_queue)) * 100
        filled = int(bar_length * i / len(step1_queue))
        bar = '█' * filled + '-' * (bar_length - filled)
        print(f'主图处理进度: [{bar}] {i}/{len(step1_queue)} ({percent:.1f}%)', flush=True)
    
    print(f'\n第二步完成：生成 {processed_count} 张图片', flush=True)
    if OUTPUT_WEBP and CONVERT_MAIN:
        print(f"已将主图转换为WebP格式", flush=True)
    print(f"主图放大完成！共处理 {processed_count} 张图片，跳过 {skipped_count} 张图片", flush=True)


def enlarge_detail_images():
    """详情图放大处理功能"""
    print("\n开始处理详情图放大...", flush=True)

    current_dir = os.getcwd()
    detail_files = collect_image_files(current_dir, detail_image_prefix)
    
    if not detail_files:
        print(f"没有找到{detail_image_prefix}开头的图片文件", flush=True)
        return
    
    total_files = len(detail_files)
    print(f"找到 {total_files} 张详情图文件", flush=True)
    
    tolerance_min_width = int(detail_min_width * (1 - detail_width_tolerance))
    print(f"详情图筛选标准：宽度 >= {tolerance_min_width}px 或宽度 < {enlarge_step1_width}px（需要放大）", flush=True)
    
    process_queue = []
    skip_queue = []
    
    for file_path in detail_files:
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                base_name = os.path.basename(file_path)
                
                if width >= tolerance_min_width or width < enlarge_step1_width:
                    process_queue.append((file_path, width, height))
                else:
                    skip_queue.append((file_path, width, height))
        except Exception as e:
            print(f"无法读取图片 {file_path}: {e}", flush=True)
    
    if skip_queue:
        print(f"排除了 {len(skip_queue)} 个宽度在{enlarge_step1_width}px到{tolerance_min_width}px之间的图片", flush=True)
    
    if not process_queue:
        print(f"没有符合条件的详情图", flush=True)
        return
    
    print(f"处理队列: {len(process_queue)} 个文件", flush=True)
    
    bar_length = 40
    processed_count = 0
    skipped_count = 0
    webp_converted = 0
    
    for i, (file_path, width, height) in enumerate(process_queue, 1):
        try:
            with Image.open(file_path) as img:
                if OUTPUT_WEBP:
                    base_name = os.path.basename(file_path)
                    name, ext = os.path.splitext(base_name)
                    webp_path = os.path.join(current_dir, f"{name}.webp")
                    if width >= detail_min_width:
                        skipped_count += 1
                        img.save(webp_path, format="WebP", quality=jpeg_quality)
                    else:
                        result = enlarge_image(img)
                        img_resized = result[0]
                        img_resized.save(webp_path, format="WebP", quality=jpeg_quality)
                        processed_count += 1
                    webp_converted += 1
                else:
                    if width >= detail_min_width:
                        skipped_count += 1
                    else:
                        result = enlarge_image(img)
                        img_resized = result[0]
                        img_resized.save(file_path, quality=jpeg_quality)
                        processed_count += 1
        except Exception as e:
            pass
        
        percent = (i / len(process_queue)) * 100
        filled = int(bar_length * i / len(process_queue))
        bar = '█' * filled + '-' * (bar_length - filled)
        print(f'详情图处理进度: [{bar}] {i}/{len(process_queue)} ({percent:.1f}%)', flush=True)
    
    print(f'\n详情图放大完成！共处理 {processed_count} 张图片，跳过 {skipped_count} 张图片', flush=True)
    if OUTPUT_WEBP:
        print(f"已将 {webp_converted} 张详情图转换为WebP格式", flush=True)


def enlarge_color_card_images():
    """色卡图放大处理功能"""
    current_dir = os.getcwd()
    color_files = collect_image_files(current_dir, color_option_prefix)
    
    if not color_files:
        return
    
    total_files = len(color_files)
    
    need_process = False
    for file_path in color_files:
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                if width < detail_min_width:
                    need_process = True
                    break
        except:
            pass
    
    print(f"\n开始处理色卡图放大...", flush=True)
    print(f"找到 {total_files} 张色卡图文件", flush=True)
    
    bar_length = 40
    processed_count = 0
    skipped_count = 0
    webp_converted = 0
    
    for i, file_path in enumerate(color_files, 1):
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                
                if OUTPUT_WEBP and CONVERT_COLOR:
                    base_name = os.path.basename(file_path)
                    name, ext = os.path.splitext(base_name)
                    webp_path = os.path.join(current_dir, f"{name}.webp")
                    if width >= detail_min_width:
                        skipped_count += 1
                        img.save(webp_path, format="WebP", quality=jpeg_quality)
                    else:
                        result = enlarge_image(img)
                        img_resized = result[0]
                        img_resized.save(webp_path, format="WebP", quality=jpeg_quality)
                        processed_count += 1
                    webp_converted += 1
                else:
                    if width >= detail_min_width:
                        skipped_count += 1
                    else:
                        result = enlarge_image(img)
                        img_resized = result[0]
                        img_resized.save(file_path, quality=jpeg_quality)
                        processed_count += 1
        except Exception as e:
            pass
        
        percent = (i / total_files) * 100
        filled = int(bar_length * i / total_files)
        bar = '█' * filled + '-' * (bar_length - filled)
        print(f'色卡图处理进度: [{bar}] {i}/{total_files} ({percent:.1f}%)', flush=True)
    
    print(f'\n色卡图放大完成！共处理 {processed_count} 张图片，跳过 {skipped_count} 张图片', flush=True)
    if OUTPUT_WEBP and CONVERT_COLOR:
        print(f"已将 {webp_converted} 张色卡图转换为WebP格式", flush=True)


def process_regular_detail_images():
    """常规详情图拼接处理"""
    current_dir = os.getcwd()
    c_files = collect_image_files(current_dir, detail_image_prefix)
    
    if not c_files:
        print(f"没有找到{detail_image_prefix}开头的图片文件")
        return
    
    original_count = len(c_files)
    print(f"\n=== 详情图拼接处理 ===")
    print(f"找到 {original_count} 张详情图文件")
    
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
            print(f"无法读取图片 {file_path}: {e}")
    
    filtered_images = [(file_path, width, height, is_animated) for file_path, width, height, is_animated in all_images_info if width >= min_width]
    
    removed_small = len(all_images_info) - len(filtered_images)
    if removed_small > 0:
        print(f"\n移除了 {removed_small} 个宽度低于{min_width}px的图片")
    
    if not filtered_images:
        print(f"\n没有符合条件的详情图")
        return
    
    animated_count = sum(1 for _, _, _, is_animated in filtered_images if is_animated)
    static_count = len(filtered_images) - animated_count
    
    print(f"\n图片分析结果:")
    print(f"  - 静态图片数量: {static_count} 张")
    print(f"  - 动图数量: {animated_count} 张")
    
    if has_animated:
        print(f"\n检测到动图，执行混合图片处理流程")
        total_files = process_mixed_images(filtered_images, current_dir, new_image_prefix)
        print(f"\n混合图片处理完成，共生成 {total_files} 个文件")
    else:
        print(f"\n没有检测到动图，执行原有静态图片处理流程")
        
        small_images = [(f, w, h) for f, w, h, _ in filtered_images if w <= enlarge_step1_width]
        large_images = [(f, w, h) for f, w, h, _ in filtered_images if w > enlarge_step1_width]
        
        print(f"  - 宽度 <= {enlarge_step1_width}px: {len(small_images)} 张")
        print(f"  - 宽度 > {enlarge_step1_width}px: {len(large_images)} 张")
        
        if small_images and not large_images:
            print(f"\n=== 执行小图放大拼接流程 ===")
            _process_small_images(small_images, current_dir)
            return
        
        if large_images:
            landscape_images = [(f, w, h) for f, w, h, _ in filtered_images if w > h]
            
            print(f"\n队列分析:")
            print(f"  - 大于{enlarge_step1_width}px的图片数量: {len(large_images)}")
            print(f"  - 其中横屏图片数量: {len(landscape_images)}")
            
            if landscape_images:
                print(f"\n检测到横屏图片，启动照片拼图检测流程...")
                
                photo_images = []
                for f, w, h, _ in filtered_images:
                    is_photo, matched_ratio = check_aspect_ratio(w, h)
                    if is_photo:
                        photo_images.append((f, w, h, matched_ratio))
                
                print(f"  - 符合照片比例的图片数量: {len(photo_images)}")
                
                threshold = len(large_images) / 2
                if len(photo_images) > threshold:
                    print(f"\n照片比例图片({len(photo_images)}) > 队列半数({threshold})，启用照片拼接流程")
                else:
                    print(f"\n照片比例图片({len(photo_images)}) <= 队列半数({threshold})，进入常规流程")
            else:
                print(f"\n未检测到横屏图片，进入常规流程")
        
        print(f"\n=== 执行常规拼接流程 ===")
        _process_large_images(large_images, current_dir)


def _process_small_images(small_images, current_dir):
    """处理小图放大拼接流程"""
    images = []
    总高度 = 0
    
    small_images_sorted = sorted(small_images, key=lambda x: natural_sort_key(x[0]))
    total_files = len(small_images_sorted)
    bar_length = 40
    
    for i, (file_path, width, height) in enumerate(small_images_sorted, 1):
        try:
            with Image.open(file_path) as img:
                img_resized, (new_width, new_height, desc) = enlarge_image(img)
                images.append(img_resized.copy())
                总高度 += new_height
        except Exception as e:
            print(f"无法处理图片 {file_path}: {e}")
        
        percent = (i / total_files) * 100
        filled = int(bar_length * i / total_files)
        bar = '█' * filled + '-' * (bar_length - filled)
        print(f'详情图处理进度: [{bar}] {i}/{total_files} ({percent:.1f}%)', flush=True)
    
    print()  # 换行，结束进度条
    
    if not images:
        print("\n没有可处理的图片")
        return
    
    target_width = enlarge_step2_width
    拼接图片 = Image.new('RGB', (target_width, 总高度), (255, 255, 255))
    
    当前高度 = 0
    for img in images:
        if img.width != target_width:
            img = img.resize((target_width, int(img.height * target_width / img.width)), Image.LANCZOS)
        拼接图片.paste(img, (0, 当前高度))
        当前高度 += img.height
    
    split_merged_image(拼接图片, target_width, 总高度, current_dir, new_image_prefix)


def _process_large_images(large_images, current_dir):
    """处理大图拼接流程"""
    总高度 = 0
    images = []
    
    main_files_sorted = sorted(large_images, key=natural_sort_key)
    total_files = len(main_files_sorted)
    bar_length = 40
    
    target_width = None
    
    for i, (file_path, width, height) in enumerate(main_files_sorted, 1):
        try:
            with Image.open(file_path) as img:
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
            print(f"无法处理图片 {file_path}: {e}")
        
        percent = (i / total_files) * 100
        filled = int(bar_length * i / total_files)
        bar = '█' * filled + '-' * (bar_length - filled)
        print(f'详情图处理进度: [{bar}] {i}/{total_files} ({percent:.1f}%)', flush=True)
    
    print()  # 换行，结束进度条
    
    if not images:
        print("\n没有可处理的图片")
        return
    
    拼接图片 = Image.new('RGB', (target_width, 总高度), (255, 255, 255))
    
    当前高度 = 0
    for img in images:
        拼接图片.paste(img, (0, 当前高度))
        当前高度 += img.height
    
    split_merged_image(拼接图片, target_width, 总高度, current_dir, new_image_prefix)


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
