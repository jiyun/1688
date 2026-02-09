import os
import sys
from PIL import Image
import glob

# 添加上级目录到路径，以便导入config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入配置
from config import FILE_NAMING, IMAGE_PROCESSING

# 获取配置参数
detail_image_prefix = FILE_NAMING.get('detail_image_prefix', 'C_')
new_image_prefix = FILE_NAMING.get('new_image_prefix', 'new_C_')
merged_image_name = FILE_NAMING.get('merged_image_name', '拼接结果.jpg')
min_width = IMAGE_PROCESSING.get('min_width', 750)



def process_single_image(image_path):
    """处理单张图片"""
    print(f"\n处理单张图片: {os.path.basename(image_path)}")
    
    # 打开图片
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            print(f"图片尺寸: {width}px × {height}px")
            
            # 检查宽度是否符合要求
            if width < min_width:
                print(f"图片宽度 {width}px < 最小宽度 {min_width}px，跳过处理")
                return
            
            # 检查是否需要切割
            max_single_height = width * 2
            if height <= max_single_height:
                print("图片高度未超过2倍宽度，不需要切割")
                return
            
            # 计算需要切割的份数
            切割份数 = (height + max_single_height - 1) // max_single_height
            print(f"需要切割为 {切割份数} 份")
            
            # 检查最后一份是否小于200px
            每份高度 = height // 切割份数
            最后一份高度 = height % 每份高度
            
            if 最后一份高度 < 200 and 切割份数 > 1:
                print(f"最后一份高度 {最后一份高度}px < 200px，将平均分配高度")
                # 平均分配高度，向上取整
                每份高度 = (height + 切割份数 - 1) // 切割份数
                print(f"平均每份高度: {每份高度}px")
            
            # 获取原始文件名和扩展名
            base_name = os.path.basename(image_path)
            name, ext = os.path.splitext(base_name)
            
            # 切割并保存
            当前高度 = 0
            for i in range(切割份数):
                # 计算当前份的高度
                if i == 切割份数 - 1:
                    # 最后一份
                    结束高度 = height
                else:
                    结束高度 = 当前高度 + 每份高度
                
                # 确保不超过总高度
                结束高度 = min(结束高度, height)
                
                # 切割
                切割图片 = img.crop((0, 当前高度, width, 结束高度))
                
                # 保存，维持原来的文件名后缀+[n]序号
                保存路径 = os.path.join(os.path.dirname(image_path), f"{name}[{i+1}]{ext}")
                切割图片.save(保存路径, quality=95)
                print(f"切割图片 {i+1} 保存到: {保存路径}")
                
                当前高度 = 结束高度
            
            print("\n单张图片处理完成！")
    except Exception as e:
        print(f"处理图片时出错: {e}")

def main():
    """主函数"""
    # 检查是否有命令行参数（拖放的图片文件）
    if len(sys.argv) > 1:
        # 获取命令行参数中的图片路径
        image_path = sys.argv[1]
        # 检查文件是否存在
        if os.path.exists(image_path) and os.path.isfile(image_path):
            # 处理单张图片
            process_single_image(image_path)
            return
    
    # 获取当前目录
    current_dir = os.getcwd()
    
    # 收集指定前缀开头的图片文件
    image_patterns = []
    for ext in ['jpg', 'png', 'jpeg']:
        image_patterns.append(os.path.join(current_dir, f'{detail_image_prefix}*.{ext}'))
    
    c_files = []
    for pattern in image_patterns:
        c_files.extend(glob.glob(pattern))
    
    # 实现自然排序，确保 C_11 不会排在 C_2 之前
    def natural_sort_key(filename):
        import re
        # 提取文件名中的数字部分
        parts = re.split(r'(\d+)', os.path.basename(filename))
        # 将数字部分转换为整数，非数字部分保持原样
        parts = [int(p) if p.isdigit() else p for p in parts]
        return parts
    
    # 使用自然排序对文件列表进行排序
    c_files = sorted(c_files, key=natural_sort_key)
    
    if not c_files:
        print(f"没有找到{detail_image_prefix}开头的图片文件")
        sys.exit(1)
    
    print(f"找到 {len(c_files)} 个{detail_image_prefix}开头的图片文件")
    
    # 收集图片宽度
    width_list = []
    for file in c_files:
        try:
            with Image.open(file) as img:
                width = img.width
                width_list.append((file, width))
        except Exception as e:
            print(f"无法读取图片 {file}: {e}")
    
    # 统计各宽度的数量
    width_counts = {}
    for file, width in width_list:
        if width not in width_counts:
            width_counts[width] = []
        width_counts[width].append(file)
    
    # 移除低于配置宽度的图片
    filtered_widths = {}
    removed_files = []
    for width, files in width_counts.items():
        if width >= min_width:
            filtered_widths[width] = files
        else:
            removed_files.extend(files)
    
    if removed_files:
        print(f"\n移除了 {len(removed_files)} 个低于{min_width}px的图片")
    
    if not filtered_widths:
        print(f"\n没有符合条件的图片（宽度>={min_width}px）")
        sys.exit(1)
    
    # 找到数量最多的宽度作为主队列
    main_width = max(filtered_widths, key=lambda w: len(filtered_widths[w]))
    main_files = filtered_widths[main_width]
    
    # 移除其他宽度的图片
    other_files = []
    for width, files in filtered_widths.items():
        if width != main_width:
            other_files.extend(files)
    
    if other_files:
        print(f"\n移除了 {len(other_files)} 个非主宽度的图片")
    
    print(f"\n主队列: {main_width}px, {len(main_files)}个文件")
    
    # 按顺序拼接图片
    if not main_files:
        print("\n主队列为空")
        sys.exit(1)
    
    # 获取主队列首张图片的宽度
    with Image.open(main_files[0]) as first_img:
        target_width = first_img.width
    
    # 计算总高度
    总高度 = 0
    images = []
    for file in main_files:
        try:
            img = Image.open(file)
            # 调整宽度为目标宽度
            if img.width != target_width:
                img = img.resize((target_width, int(img.height * target_width / img.width)), Image.LANCZOS)
            images.append(img)
            总高度 += img.height
        except Exception as e:
            print(f"无法处理图片 {file}: {e}")
    
    if not images:
        print("\n没有可处理的图片")
        sys.exit(1)
    
    # 创建拼接图片
    拼接图片 = Image.new('RGB', (target_width, 总高度), (255, 255, 255))
    
    # 粘贴图片
    当前高度 = 0
    for img in images:
        拼接图片.paste(img, (0, 当前高度))
        当前高度 += img.height
    
    # 保存拼接图片
    拼接图片路径 = os.path.join(current_dir, merged_image_name)
    拼接图片.save(拼接图片路径, quality=95)
    print(f"\n拼接图片保存到: {拼接图片路径}")
    
    # 计算切割份数
    # 宽高比小于1:2，即高度 > 2*宽度
    max_single_height = target_width * 2
    
    if 总高度 <= max_single_height:
        print("\n拼接图片高度未超过2倍宽度，不需要切割")
        return
    
    # 计算需要切割的份数
    切割份数 = (总高度 + max_single_height - 1) // max_single_height
    
    # 检查最后一份是否小于200px
    每份高度 = 总高度 // 切割份数
    最后一份高度 = 总高度 % 每份高度
    
    if 最后一份高度 < 200 and 切割份数 > 1:
        # 平均分配高度，向上取整
        每份高度 = (总高度 + 切割份数 - 1) // 切割份数
    
    # 切割并保存
    当前高度 = 0
    for i in range(切割份数):
        # 计算当前份的高度
        if i == 切割份数 - 1:
            # 最后一份
            结束高度 = 总高度
        else:
            结束高度 = 当前高度 + 每份高度
        
        # 确保不超过总高度
        结束高度 = min(结束高度, 总高度)
        
        # 切割
        切割图片 = 拼接图片.crop((0, 当前高度, target_width, 结束高度))
        
        # 保存
        保存路径 = os.path.join(current_dir, f"{new_image_prefix}{i+1}.jpg")
        切割图片.save(保存路径, quality=95)
        
        当前高度 = 结束高度

if __name__ == '__main__':
    main()
