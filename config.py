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
    'enlarge_step2_width': 1500,                       # 二次放大第二步目标宽度
    'photo_min_width': 900,                            # 实拍照片最小宽度要求
    'photo_aspect_ratios': [(16, 9), (4, 3), (3, 2)],  # 实拍照片允许的宽高比
    'photo_aspect_tolerance': 0.10,                    # 宽高比容差（10%）
    'main_image_min_size': 800,                        # 主图最小尺寸
    'main_image_target_size': 1500,                    # 主图目标尺寸
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
    'pack_exclude': ['rebuild.bat', '.download_list.txt'],  # 打包时排除的文件
}

# GUI配置
GUI_CONF = {
    # 窗口配置
    'window_title': '1688详情页资源采集工具',
    'window_geometry': '1024x768',
    'window_resizable': True,
    
    # 字体配置（按优先级排序，数字越小优先级越高）
    'font_families': [
        # 优先级 1-4: 大厂开源字体
        'Alibaba PuHuiTi',      # 1. 阿里巴巴普惠体
        'HarmonyOS Sans',       # 2. 华为鸿蒙字体
        'MiSans',               # 3. 小米字体
        'OPPO Sans',            # 4. OPPO 字体
        
        # 优先级 5-7: 经典开源字体
        'Source Han Sans CN',   # 5. 思源黑体
        'Smiley Sans',          # 6. 得意黑
        'Sarasa Gothic SC',     # 7. 更纱黑体
        
        # 优先级 8-13: 系统自带字体（使用实际注册名称）
        'Microsoft YaHei UI',   # 8. 微软雅黑 UI
        '微软雅黑',              # 9. 微软雅黑（中文名）
        '等线',                  # 10. 等线（中文名）
        '黑体',                  # 11. 黑体（中文名）
        '宋体',                  # 12. 宋体（中文名）
        '仿宋',                  # 13. 仿宋（中文名）
    ],
    'font_size': 10,          # 字体大小
    
    # 日志配置
    'log_colors': {
        'info': 'white',
        'success': 'green',
        'warning': 'yellow',
        'error': 'red',
        'input': 'green'
    },
    
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
    }
}

PRICING_CONF = {
    'default_base_name': '本体1',
    'default_base_cost': 0.0,
    'default_pricing_strategy': 'multiplier',
    'default_rounding': 0,
    'default_max_price': 0.0,
    'window_geometry': '1000x850',
    'window_resizable': True,
    'canvas_height': 150,
    'listbox_height': 10,
    'listbox_width': 70,
}

UPDATE_CONF = {
    'check_on_startup': True,
    'check_interval': 86400,
    'timeout': 10,
    'github_api': 'https://api.github.com/repos/jiyun/1688',
    'github_raw': 'https://raw.githubusercontent.com/jiyun/1688',
    'gitee_api': 'https://gitee.com/api/v5/repos/jiyunui/1688',
    'gitee_raw': 'https://gitee.com/jiyunui/1688/raw',
    'version_file': 'version.json',
    'changelog_file': 'CHANGELOG.md',
    'download_dir': 'updates',
}

BUTTON_CONF = {
    'width': 120,
    'height': 40,
    'corner_radius': 8,
    'border_width': 0,
    
    'themes': {
        'default': {
            'primary': {'fg_color': '#1F6AA5', 'hover_color': '#144870', 'text_color': 'white'},
            'success': {'fg_color': '#4CAF50', 'hover_color': '#388E3C', 'text_color': 'white'},
            'danger': {'fg_color': '#D32F2F', 'hover_color': '#B71C1C', 'text_color': 'white'},
            'warning': {'fg_color': '#FF9800', 'hover_color': '#F57C00', 'text_color': 'white'},
            'secondary': {'fg_color': '#607D8B', 'hover_color': '#455A64', 'text_color': 'white'},
        },
        'dark': {
            'primary': {'fg_color': '#2196F3', 'hover_color': '#1976D2', 'text_color': 'white'},
            'success': {'fg_color': '#66BB6A', 'hover_color': '#43A047', 'text_color': 'white'},
            'danger': {'fg_color': '#EF5350', 'hover_color': '#E53935', 'text_color': 'white'},
            'warning': {'fg_color': '#FFA726', 'hover_color': '#FB8C00', 'text_color': 'white'},
            'secondary': {'fg_color': '#78909C', 'hover_color': '#546E7A', 'text_color': 'white'},
        },
        'light': {
            'primary': {'fg_color': '#3F51B5', 'hover_color': '#303F9F', 'text_color': 'white'},
            'success': {'fg_color': '#43A047', 'hover_color': '#2E7D32', 'text_color': 'white'},
            'danger': {'fg_color': '#E53935', 'hover_color': '#C62828', 'text_color': 'white'},
            'warning': {'fg_color': '#FB8C00', 'hover_color': '#EF6C00', 'text_color': 'white'},
            'secondary': {'fg_color': '#546E7A', 'hover_color': '#37474F', 'text_color': 'white'},
        }
    },
    'current_theme': 'default',
}

def get_button_style(style_type='primary'):
    theme_name = BUTTON_CONF.get('current_theme', 'default')
    theme = BUTTON_CONF['themes'].get(theme_name, BUTTON_CONF['themes']['default'])
    return theme.get(style_type, theme['primary'])

def get_button_config(style_type='primary'):
    style = get_button_style(style_type)
    return {
        'width': BUTTON_CONF['width'],
        'height': BUTTON_CONF['height'],
        'corner_radius': BUTTON_CONF['corner_radius'],
        'border_width': BUTTON_CONF['border_width'],
        **style
    }

import re

def sanitize_filename(name: str, max_length: int = 100) -> str:
    """清理文件名，移除或替换特殊字符
    
    Args:
        name: 原始文件名
        max_length: 最大长度限制
    
    Returns:
        清理后的安全文件名
    """
    if not name:
        return 'unnamed'
    
    invalid_chars = r'[<>:"/\\|?*\[\]【】{}]'
    name = re.sub(invalid_chars, '_', name)
    
    name = re.sub(r'[\x00-\x1f\x7f]', '', name)
    
    name = re.sub(r'_+', '_', name)
    name = name.strip('_').strip()
    
    if not name:
        return 'unnamed'
    
    if len(name) > max_length:
        name = name[:max_length]
    
    return name
