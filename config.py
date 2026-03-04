# 项目配置文件

# 下载配置
DOWNLOAD_CONF = {
    'aria2c_args': '--console-log-level=warn',        # aria2c 命令参数
    'min_file_size': 5120,                             # 最小文件大小（字节），小于此值的文件将被删除
}

# 文件命名规则
FILE_NAMING = {
    'main_image_prefix': 'T_',                         # 主图前缀
    'detail_image_prefix': 'C_',                       # 详情图前缀
    'video_prefix': 'video_',                          # 视频前缀
    'color_option_prefix': 'color_',                   # 颜色选项前缀
    'new_image_prefix': 'new_C_',                      # 新生成图片前缀
    'merged_image_name': '拼接结果.jpg',               # 拼接结果图片文件名
}

# 图片处理配置
IMAGE_PROCESSING = {
    'min_width': 750,                                  # 最小图片宽度，低于此值的图片将被移除
    'detail_min_width': 1440,                          # 详情图最小宽度标准
    'detail_width_tolerance': 0.02,                    # 详情图宽度宽容度（2%）
    'enlarge_2x_width': 750,                           # 直接2倍放大的宽度值
    'enlarge_step1_width': 800,                        # 二次放大第一步目标宽度
    'enlarge_step2_width': 1600,                       # 二次放大第二步目标宽度
    'photo_min_width': 900,                            # 实拍照片最小宽度要求
    'photo_aspect_ratios': [(16, 9), (4, 3), (3, 2)],  # 实拍照片允许的宽高比
    'photo_aspect_tolerance': 0.10,                    # 宽高比容差（10%）
    'main_image_min_size': 800,                        # 主图最小尺寸
    'main_image_target_size': 1600,                    # 主图目标尺寸
    'min_split_height': 200,                           # 最小切割高度
    'jpeg_quality': 95,                                # JPEG保存质量
}

# 选择器配置
SELECTORS = {
    'main_images': 'div.img-list-wrapper img',         # 主图选择器
    'color_options': 'div.prop-item-wrapper div.prop-name',  # 颜色选项选择器
    'detail_images': 'div.content-detail img',         # 详情图选择器
    'videos': 'video',                                 # 视频选择器
    'attributes': 'div.od-pc-attribute div.offer-attr-item',  # 属性选择器
}

# 属性选择器
ATTRIBUTE_SELECTORS = {
    'name': 'span.offer-attr-item-name',               # 属性名选择器
    'value': 'span.offer-attr-item-value',             # 属性值选择器
}

# 排除文件配置
EXCLUDE_FILES = {
    'pack_exclude': ['down.txt', 'down_log.txt', 'rebuild.bat'],  # 打包时排除的文件
}
