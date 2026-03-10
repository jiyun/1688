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
    'webp_quality': 80,                                # WebP保存质量（用于动图转换）
    'webp_method': 4,                                  # WebP压缩方法（0-6，越大压缩比越高但速度越慢）
    'parallel_workers': 4,                             # 并行处理线程数，默认为2
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

# GUI配置
GUI_CONF = {
    # 窗口配置
    'window_title': '1688详情页资源采集工具',
    'window_geometry': '1024x768',
    'window_resizable': True,
    
    # 字体配置（按优先级排序）
    'font_families': [
        # --- 大厂开源字体 (优先使用英文名) ---
        'Alibaba PuHuiTi',      # 阿里巴巴普惠体 (官方英文名，兼容性好)
        'HarmonyOS Sans',       # 华为鸿蒙字体 (官方英文名)
        'MiSans',               # 小米字体 (官方英文名，覆盖旧版"小米兰亭")
        'OPPO Sans',            # OPPO 字体 (官方英文名)
        
        # --- 经典开源字体 ---
        'Source Han Sans CN',   # 思源黑体 (CN 代表简体中文，最标准的调用名)
        'Smiley Sans',          # 得意黑 (官方英文名)
        'Sarasa Gothic SC',     # 更纱黑体 (修正：原名应为 Sarasa Gothic SC)
        
        # --- 系统自带字体 (作为兜底) ---
        'Microsoft YaHei',      # 微软雅黑 (Windows 标准英文名)
        'DengXian',             # 等线 (Windows 10+ 标准英文名)
        'SimHei',               # 黑体 (Windows 标准英文名)
        'Courier New',          # 默认等宽字体
    ],
    'font_size': 10,          # 字体大小
    
    # 日志配置
    'log_buffer_size': 1000,
    'log_colors': {
        'info': 'white',
        'success': 'green',
        'warning': 'yellow',
        'error': 'red',
        'input': 'green'
    },
    
    # 队列配置
    'queue_columns': (
        ('index', '序号', 30),
        ('status', '状态', 50),
        ('name', '文件名', 150),
        ('date', '修改日期', 120),
        ('path', '路径', 350)
    ),
    
    # 进度条配置
    'progress_colors': {
        'main': '#4CAF50',      # 主图 - 绿色
        'color': '#2196F3',     # 色卡图 - 蓝色
        'detail': '#FF9800',    # 详情图 - 橙色
    },
    'progress_bar_width': 20,    # 进度条宽度（字符数）
    
    # 状态配置
    'status_icons': {
        'success': '✓',
        'error': '✗',
        'exists': '❓',
        'duplicate': '❗',
        'none': '',
        'processing': '⏳'  # 处理中状态
    },
    'status_order': {'none': 1, 'exists': 1, 'duplicate': 2, 'error': 3, 'success': 4, 'processing': 5},
    'status_colors': {
        'success': 'green',
        'error': 'red',
        'exists': 'orange',
        'duplicate': 'purple',
        'none': 'black',
        'processing': 'blue'  # 处理中 - 蓝色
    },
    
    # 进度条配置
    'progress_colors': {
        'main': '#4CAF50',      # 主图 - 绿色
        'color': '#2196F3',     # 色卡图 - 蓝色
        'detail': '#FF9800'    # 详情图 - 橙色
    },
    'progress_bar_width': 20,    # 进度条宽度（字符数）
    'progress_bar_chars': ('█', '░'),  # 进度条字符（填充、空白）
    
    # 上下文菜单配置
    'context_menu_items': [
        ['图像优化', [
            ('默认优化', 'context_stitch_images'),
            ('WebP转换', 'context_stitch_images_webp'),
            ('WebP转换(仅主图)', 'context_stitch_images_webp_main'),
            ('WebP转换(仅色卡图)', 'context_stitch_images_webp_color'),
            ('WebP转换(全部)', 'context_stitch_images_webp_all'),
            ('separator', None),
            ('包含动图', 'context_stitch_images_with_animated'),
            ('包含动图 + WebP', 'context_stitch_images_webp_with_animated')
        ]],
        ('资源打包', 'context_pack_files'),
        ('separator', None),
        ('重新采集', 'context_recollect'),
        ('separator', None),
        ('访问原址', 'context_visit_url'),
        ('打开目录', 'context_open_folder'),
        ('删除项目', 'context_delete_item')
    ],
    
    # 文件选择配置
    'file_dialog': {
        'title': '选择 HTML 文件',
        'types': [('HTML 文件', '*.html'), ('所有文件', '*.*')]
    },
    'directory_dialog': {
        'title': '选择目录'
    },
    
    # 按钮配置
    'button_texts': {
        'add_file': '添加文件 (A)',
        'add_directory': '添加目录 (D)',
        'remove_file': '移除文件 (Del)',
        'clear_queue': '清空队列',
        'execute': '执行 (Enter)',
        'pause': '暂停 (P)',
        'execute_running': '执行中...',
        'resume': '恢复'
    },
    
    # 标签页配置
    'tab_names': {
        'queue': '处理队列',
        'help': '使用说明'
    },
    
    # 标签帧配置
    'label_frame_texts': {
        'queue': '处理队列',
        'log': '日志输出'
    }
}
