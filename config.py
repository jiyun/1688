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
