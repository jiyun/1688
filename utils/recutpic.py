import os
import sys
import re
from PIL import Image
import glob

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FILE_NAMING, IMAGE_PROCESSING

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
    return width * 2


def check_aspect_ratio(width, height):
    """检查图片是否符合实拍照片的宽高比要求"""
    actual_ratio = width / height
    
    best_match = None
    best_diff = float('inf')
    
    for w_ratio, h_ratio in photo_aspect_ratios:
        target_ratio = w_ratio / h_ratio
        
        diff1 = abs(actual_ratio - target_ratio)
        diff2 = abs(actual_ratio - 1/target_ratio)
        
        if diff1 <= photo_aspect_tolerance and diff1 < best_diff:
            best_diff = diff1
            best_match = (w_ratio, h_ratio)
        
        if diff2 <= photo_aspect_tolerance and diff2 < best_diff:
            best_diff = diff2
            best_match = (w_ratio, h_ratio)
    
    if best_match:
        return True, best_match
    
    return False, None


def split_merged_image(merged_image, target_width, total_height, output_dir, output_prefix):
    """统一的切割函数"""
    max_single_height = target_width * 2
    
    if total_height <= max_single_height:
        print("\n拼接图片高度未超过2倍宽度，不需要切割")
        return 0
    
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
        
        保存路径 = os.path.join(output_dir, f"{output_prefix}{i+1}.jpg")
        切割图片.save(保存路径, quality=jpeg_quality)
        
        当前高度 = 结束高度
    
    print(f"\n拼接图切割完成，共 {切割份数} 份")
    return 切割份数


def collect_image_files(directory, prefix):
    """收集指定前缀的图片文件"""
    image_patterns = []
    for ext in ['jpg', 'png', 'jpeg']:
        image_patterns.append(os.path.join(directory, f'{prefix}*.{ext}'))
    
    files = []
    for pattern in image_patterns:
        files.extend(glob.glob(pattern))
    
    return sorted(files, key=natural_sort_key)


def enlarge_main_images():
    """放大主图功能：两步处理主图"""
    print("\n开始处理主图放大...")

    current_dir = os.getcwd()
    main_files = collect_image_files(current_dir, main_image_prefix)

    if not main_files:
        print(f"没有找到{main_image_prefix}开头的图片文件")
        return

    print(f"找到 {len(main_files)} 个{main_image_prefix}开头的图片文件")

    print(f"\n=== 第一步处理：将小于{main_image_min_size}px的图片放大到{main_image_min_size}px ===")
    step1_queue = []

    for file_path in main_files:
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                print(f"\n处理图片: {os.path.basename(file_path)}, 尺寸: {width}px × {height}px")

                base_name = os.path.basename(file_path)
                name, ext = os.path.splitext(base_name)

                if name.startswith('E_'):
                    print(f"图片已处理过，跳过")
                    step1_queue.append(file_path)
                    continue

                if width < main_image_min_size or height < main_image_min_size:
                    scale = max(main_image_min_size / width, main_image_min_size / height)
                    new_width = int(width * scale)
                    new_height = int(height * scale)

                    img_resized = img.resize((new_width, new_height), Image.LANCZOS)
                    img_resized.save(file_path, quality=jpeg_quality)
                    print(f"第一步：放大图片到 {new_width}px × {new_height}px，覆盖原文件")

                    step1_queue.append(file_path)
                else:
                    step1_queue.append(file_path)
                    print(f"图片尺寸已满足要求，直接进入第二步处理队列")

        except Exception as e:
            print(f"处理图片 {file_path} 时出错: {e}")

    print(f"\n=== 第二步处理：将{main_image_min_size}px到{detail_min_width}px之间的图片放大到{main_image_target_size}px ===")

    processed_count = 0
    skipped_count = 0

    for file_path in step1_queue:
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                print(f"\n处理图片: {os.path.basename(file_path)}, 尺寸: {width}px × {height}px")

                base_name = os.path.basename(file_path)
                name, ext = os.path.splitext(base_name)

                new_name = f"E_{name}{ext}"
                output_path = os.path.join(current_dir, new_name)

                if main_image_min_size <= width <= detail_min_width and main_image_min_size <= height <= detail_min_width:
                    img_resized = img.resize((main_image_target_size, main_image_target_size), Image.LANCZOS)
                    print(f"第二步：放大图片到 {main_image_target_size}px × {main_image_target_size}px")

                    img_resized.save(output_path, quality=jpeg_quality)
                    print(f"放大后的图片已保存到: {output_path}")

                    processed_count += 1
                else:
                    img.save(output_path, quality=jpeg_quality)
                    print(f"图片尺寸大于{detail_min_width}px，保持原尺寸，添加E_前缀保存")
                    print(f"图片已保存到: {output_path}")

                    processed_count += 1

        except Exception as e:
            print(f"处理图片 {file_path} 时出错: {e}")
            skipped_count += 1

    print(f"\n主图放大完成！共处理 {processed_count} 张图片，跳过 {skipped_count} 张图片")


def enlarge_detail_images():
    """详情图放大处理功能"""
    print("\n开始处理详情图放大...")

    current_dir = os.getcwd()
    detail_files = collect_image_files(current_dir, detail_image_prefix)
    
    if not detail_files:
        print(f"没有找到{detail_image_prefix}开头的图片文件")
        return
    
    print(f"找到 {len(detail_files)} 个{detail_image_prefix}开头的图片文件")
    
    tolerance_min_width = int(detail_min_width * (1 - detail_width_tolerance))
    print(f"详情图筛选标准：宽度 >= {tolerance_min_width}px 或宽度 < {enlarge_step1_width}px（需要放大）")
    
    process_queue = []
    skip_queue = []
    
    for file_path in detail_files:
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                base_name = os.path.basename(file_path)
                
                if width >= tolerance_min_width or width < enlarge_step1_width:
                    process_queue.append((file_path, width, height))
                    if width < enlarge_step1_width:
                        print(f"纳入处理队列（需要放大）: {base_name}, 尺寸: {width}px × {height}px")
                    else:
                        print(f"纳入处理队列: {base_name}, 尺寸: {width}px × {height}px")
                else:
                    skip_queue.append((file_path, width, height))
                    print(f"排除（宽度在{enlarge_step1_width}px到{tolerance_min_width}px之间）: {base_name}")
        except Exception as e:
            print(f"无法读取图片 {file_path}: {e}")
    
    if skip_queue:
        print(f"\n排除了 {len(skip_queue)} 个宽度在{enlarge_step1_width}px到{tolerance_min_width}px之间的图片")
    
    if not process_queue:
        print(f"\n没有符合条件的详情图")
        return
    
    print(f"\n处理队列: {len(process_queue)} 个文件")
    
    processed_count = 0
    skipped_count = 0
    
    for file_path, width, height in process_queue:
        try:
            with Image.open(file_path) as img:
                base_name = os.path.basename(file_path)
                
                if width >= detail_min_width:
                    print(f"\n跳过放大: {base_name}, 尺寸: {width}px × {height}px（已符合标准）")
                    skipped_count += 1
                    continue
                
                img_resized, (new_width, new_height, desc) = enlarge_image(img)
                img_resized.save(file_path, quality=jpeg_quality)
                print(f"\n{desc}: {base_name}, {width}px × {height}px -> {new_width}px × {new_height}px")
                processed_count += 1
                    
        except Exception as e:
            print(f"处理图片 {file_path} 时出错: {e}")
    
    print(f"\n详情图放大完成！共处理 {processed_count} 张图片，跳过 {skipped_count} 张图片")


def enlarge_color_card_images():
    """色卡图放大处理功能"""
    print("\n开始处理色卡图放大...")

    current_dir = os.getcwd()
    color_files = collect_image_files(current_dir, color_option_prefix)
    
    if not color_files:
        print(f"没有找到{color_option_prefix}开头的色卡图文件")
        return
    
    print(f"找到 {len(color_files)} 个{color_option_prefix}开头的色卡图文件")
    
    processed_count = 0
    skipped_count = 0
    
    for file_path in color_files:
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                base_name = os.path.basename(file_path)
                
                print(f"\n处理色卡图: {base_name}, 尺寸: {width}px × {height}px")
                
                if width >= detail_min_width:
                    print(f"跳过放大: 宽度 {width}px >= {detail_min_width}px，已符合标准")
                    skipped_count += 1
                    continue
                
                img_resized, (new_width, new_height, desc) = enlarge_image(img)
                img_resized.save(file_path, quality=jpeg_quality)
                print(f"{desc}: {width}px × {height}px -> {new_width}px × {new_height}px")
                processed_count += 1
                    
        except Exception as e:
            print(f"处理图片 {file_path} 时出错: {e}")
    
    print(f"\n色卡图放大完成！共处理 {processed_count} 张图片，跳过 {skipped_count} 张图片")


def process_photo_detail_images(original_files):
    """实拍照片类详情图处理功能
    
    Args:
        original_files: 原始C_开头的文件列表
    
    Returns:
        bool: 是否成功处理
    """
    print("\n=== 启用照片拼接流程 ===")
    
    current_dir = os.getcwd()
    
    photo_queue = []
    
    for file_path in original_files:
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                base_name = os.path.basename(file_path)
                
                if width < min_width:
                    print(f"排除（宽度低于{min_width}px）: {base_name}, 尺寸: {width}px × {height}px")
                    continue
                
                is_photo, matched_ratio = check_aspect_ratio(width, height)
                
                if is_photo and width >= photo_min_width:
                    photo_queue.append((file_path, width, height, matched_ratio))
                    print(f"纳入实拍照片队列: {base_name}, 尺寸: {width}px × {height}px, 比例: {matched_ratio[0]}:{matched_ratio[1]}")
                else:
                    if not is_photo:
                        print(f"排除（比例不符合）: {base_name}, 尺寸: {width}px × {height}px")
                    else:
                        print(f"排除（宽度低于{photo_min_width}px）: {base_name}, 尺寸: {width}px × {height}px")
        except Exception as e:
            print(f"无法读取图片 {file_path}: {e}")
    
    if not photo_queue:
        print(f"\n没有符合条件的实拍照片类详情图")
        return False
    
    print(f"\n实拍照片队列: {len(photo_queue)} 个文件")
    
    max_width = max(item[1] for item in photo_queue)
    print(f"最大宽度: {max_width}px")
    
    need_enlarge = [item for item in photo_queue if item[1] < max_width]
    if need_enlarge:
        print(f"需要放大的图片: {len(need_enlarge)} 张")
    
    总高度 = 0
    images = []
    
    photo_queue_sorted = sorted(photo_queue, key=natural_sort_key)
    
    for file_path, width, height, matched_ratio in photo_queue_sorted:
        try:
            with Image.open(file_path) as img:
                if width < max_width:
                    scale = max_width / width
                    new_width = max_width
                    new_height = int(height * scale)
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                    print(f"放大: {os.path.basename(file_path)}, {width}px × {height}px -> {new_width}px × {new_height}px")
                    img_copy = img.copy()
                else:
                    img_copy = img.copy()
                
                images.append(img_copy)
                总高度 += img_copy.height
        except Exception as e:
            print(f"无法处理图片 {file_path}: {e}")
    
    if not images:
        print("\n没有可处理的图片")
        return False
    
    拼接图片 = Image.new('RGB', (max_width, 总高度), (255, 255, 255))
    
    当前高度 = 0
    for img in images:
        拼接图片.paste(img, (0, 当前高度))
        当前高度 += img.height
    
    拼接图片路径 = os.path.join(current_dir, merged_image_name)
    拼接图片.save(拼接图片路径, quality=jpeg_quality)
    print(f"\n拼接图片保存到: {拼接图片路径}")
    print(f"拼接图片尺寸: {max_width}px × {总高度}px")
    
    split_merged_image(拼接图片, max_width, 总高度, current_dir, new_image_prefix)
    
    return True


def process_regular_detail_images():
    """常规详情图拼接处理
    
    新流程：
    1. 读取目标目录C_开头的所有文件
    2. 读取所有图片的宽度，对于小于750px的直接抛弃
    3. 分析进入队列的图片：
       - 低于等于800px走默认流程拼接放大
       - 如果进入队列的图片大于800px，检测是否存在横屏图片
       - 如果存在横屏图片，启动照片拼图检测流程
       - 如果队列中超过一半是照片比例的图片，启动照片拼接流程
       - 否则进入常规流程
    """
    current_dir = os.getcwd()
    c_files = collect_image_files(current_dir, detail_image_prefix)
    
    if not c_files:
        print(f"没有找到{detail_image_prefix}开头的图片文件")
        return
    
    original_count = len(c_files)
    print(f"\n=== 详情图拼接处理 ===")
    print(f"找到 {original_count} 个{detail_image_prefix}开头的图片文件")
    
    all_images_info = []
    for file in c_files:
        try:
            with Image.open(file) as img:
                width, height = img.size
                all_images_info.append((file, width, height))
        except Exception as e:
            print(f"无法读取图片 {file}: {e}")
    
    filtered_images = [(f, w, h) for f, w, h in all_images_info if w >= min_width]
    
    removed_small = len(all_images_info) - len(filtered_images)
    if removed_small > 0:
        print(f"\n移除了 {removed_small} 个宽度低于{min_width}px的图片")
    
    if not filtered_images:
        print(f"\n没有符合条件的图片")
        return
    
    small_images = [(f, w, h) for f, w, h in filtered_images if w <= enlarge_step1_width]
    large_images = [(f, w, h) for f, w, h in filtered_images if w > enlarge_step1_width]
    
    print(f"\n图片分析结果:")
    print(f"  - 宽度 <= {enlarge_step1_width}px: {len(small_images)} 张")
    print(f"  - 宽度 > {enlarge_step1_width}px: {len(large_images)} 张")
    
    if small_images and not large_images:
        print(f"\n=== 执行小图放大拼接流程 ===")
        _process_small_images(small_images, current_dir)
        return
    
    if large_images:
        landscape_images = [(f, w, h) for f, w, h in large_images if w > h]
        
        print(f"\n队列分析:")
        print(f"  - 大于{enlarge_step1_width}px的图片数量: {len(large_images)}")
        print(f"  - 其中横屏图片数量: {len(landscape_images)}")
        
        if landscape_images:
            print(f"\n检测到横屏图片，启动照片拼图检测流程...")
            
            photo_images = []
            for f, w, h in large_images:
                is_photo, matched_ratio = check_aspect_ratio(w, h)
                if is_photo:
                    photo_images.append((f, w, h, matched_ratio))
            
            print(f"  - 符合照片比例的图片数量: {len(photo_images)}")
            
            threshold = len(large_images) / 2
            if len(photo_images) > threshold:
                print(f"\n照片比例图片({len(photo_images)}) > 队列半数({threshold})，启用照片拼接流程")
                if process_photo_detail_images(c_files):
                    return
            else:
                print(f"\n照片比例图片({len(photo_images)}) <= 队列半数({threshold})，进入常规流程")
        else:
            print(f"\n未检测到横屏图片，进入常规流程")
    
    print(f"\n=== 执行常规拼接流程 ===")
    _process_large_images(large_images, current_dir)


def _process_small_images(small_images, current_dir):
    """处理小图放大拼接"""
    target_width = enlarge_step2_width
    print(f"目标宽度: {target_width}px")
    
    总高度 = 0
    images = []
    
    small_images_sorted = sorted(small_images, key=natural_sort_key)
    
    for file_path, width, height in small_images_sorted:
        try:
            with Image.open(file_path) as img:
                img_resized, (new_width, new_height, desc) = enlarge_image(img)
                if new_width != target_width:
                    img_resized = img_resized.resize((target_width, int(new_height * target_width / new_width)), Image.LANCZOS)
                img_copy = img_resized.copy()
                images.append(img_copy)
                总高度 += img_copy.height
                print(f"处理: {os.path.basename(file_path)}, {width}px × {height}px -> {target_width}px")
        except Exception as e:
            print(f"无法处理图片 {file_path}: {e}")
    
    if not images:
        print("\n没有可处理的图片")
        return
    
    拼接图片 = Image.new('RGB', (target_width, 总高度), (255, 255, 255))
    
    当前高度 = 0
    for img in images:
        拼接图片.paste(img, (0, 当前高度))
        当前高度 += img.height
    
    拼接图片路径 = os.path.join(current_dir, merged_image_name)
    拼接图片.save(拼接图片路径, quality=jpeg_quality)
    print(f"\n拼接图片保存到: {拼接图片路径}")
    print(f"拼接图片尺寸: {target_width}px × {总高度}px")
    
    split_merged_image(拼接图片, target_width, 总高度, current_dir, new_image_prefix)


def _process_large_images(large_images, current_dir):
    """处理大图拼接"""
    width_counts = {}
    for f, w, h in large_images:
        if w not in width_counts:
            width_counts[w] = []
        width_counts[w].append((f, w, h))
    
    main_width = max(width_counts.keys(), key=lambda w: len(width_counts[w]))
    main_files = width_counts[main_width]
    
    other_count = sum(len(files) for w, files in width_counts.items() if w != main_width)
    if other_count > 0:
        print(f"\n移除了 {other_count} 个非主宽度的图片")
    
    print(f"\n主队列: {main_width}px, {len(main_files)}个文件")
    
    if not main_files:
        print("\n主队列为空")
        return
    
    target_width = get_enlarge_target_width(main_width)
    
    if target_width != main_width:
        print(f"\n主队列宽度 {main_width}px，需要放大到 {target_width}px")
    
    总高度 = 0
    images = []
    
    main_files_sorted = sorted(main_files, key=natural_sort_key)
    
    for file_path, width, height in main_files_sorted:
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
    
    if not images:
        print("\n没有可处理的图片")
        return
    
    拼接图片 = Image.new('RGB', (target_width, 总高度), (255, 255, 255))
    
    当前高度 = 0
    for img in images:
        拼接图片.paste(img, (0, 当前高度))
        当前高度 += img.height
    
    拼接图片路径 = os.path.join(current_dir, merged_image_name)
    拼接图片.save(拼接图片路径, quality=jpeg_quality)
    print(f"\n拼接图片保存到: {拼接图片路径}")
    
    split_merged_image(拼接图片, target_width, 总高度, current_dir, new_image_prefix)


def process_single_image(image_path):
    """处理单张图片"""
    print(f"\n处理单张图片: {os.path.basename(image_path)}")
    
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            print(f"图片尺寸: {width}px × {height}px")
            
            if width < min_width:
                print(f"图片宽度 {width}px < 最小宽度 {min_width}px，跳过处理")
                return
            
            max_single_height = width * 2
            if height <= max_single_height:
                print("图片高度未超过2倍宽度，不需要切割")
                return
            
            切割份数 = (height + max_single_height - 1) // max_single_height
            print(f"需要切割为 {切割份数} 份")
            
            每份高度 = height // 切割份数
            最后一份高度 = height % 每份高度
            
            if 最后一份高度 < min_split_height and 切割份数 > 1:
                print(f"最后一份高度 {最后一份高度}px < {min_split_height}px，将平均分配高度")
                每份高度 = (height + 切割份数 - 1) // 切割份数
                print(f"平均每份高度: {每份高度}px")
            
            base_name = os.path.basename(image_path)
            name, ext = os.path.splitext(base_name)
            
            当前高度 = 0
            for i in range(切割份数):
                if i == 切割份数 - 1:
                    结束高度 = height
                else:
                    结束高度 = 当前高度 + 每份高度
                
                结束高度 = min(结束高度, height)
                
                切割图片 = img.crop((0, 当前高度, width, 结束高度))
                
                保存路径 = os.path.join(os.path.dirname(image_path), f"{name}[{i+1}]{ext}")
                切割图片.save(保存路径, quality=jpeg_quality)
                print(f"切割图片 {i+1} 保存到: {保存路径}")
                
                当前高度 = 结束高度
            
            print("\n单张图片处理完成！")
    except Exception as e:
        print(f"处理图片时出错: {e}")


def main():
    """主函数"""
    print("=== 图片处理工具 ====")
    
    enlarge_main_images()
    
    enlarge_color_card_images()
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        if os.path.exists(image_path) and os.path.isfile(image_path):
            process_single_image(image_path)
            return
    
    process_regular_detail_images()


if __name__ == '__main__':
    main()
