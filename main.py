#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
1688详情页资源采集工具

功能：
1. 解析本地1688详情页HTML文件
2. 提取商品头图、详情图、视频和属性信息
3. 批量下载资源文件
4. 自动分类保存文件
5. 生成URL快捷方式和重建脚本
"""

import os
import sys
import io

sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from utils.tool_downloader import ensure_all_dependencies
ensure_all_dependencies()

from utils.version import __version__
from utils.parser import HTMLParser
from utils.downloader import Downloader
from utils.file_handler import FileHandler
from utils.logger import log_info, log_success, log_warning, log_error
import config

class AlibabaScraper:
    def __init__(self, html_file, output_path=None, keep_avif=False):
        self.html_file = html_file
        self.output_path = output_path
        self.keep_avif = keep_avif
        self.product_id = self._extract_product_id()
        self.parser = None
        self.downloader = Downloader({
            'DOWNLOAD_CONF': config.DOWNLOAD_CONF,
            'FILE_NAMING': config.FILE_NAMING
        }, keep_avif=self.keep_avif)
        self.file_handler = FileHandler({
            'DOWNLOAD_CONF': config.DOWNLOAD_CONF,
            'FILE_NAMING': config.FILE_NAMING
        })
    
    def _extract_product_id(self):
        """从HTML文件名中提取商品ID"""
        base_name = os.path.basename(self.html_file)
        product_id = os.path.splitext(base_name)[0]
        return product_id
    
    def load_html(self):
        """加载HTML文件"""
        try:
            with open(self.html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            self.parser = HTMLParser(html_content, keep_avif=self.keep_avif)
            log_info(f"HTML文件加载成功: {self.html_file}", "Main")
            return True
        except Exception as e:
            log_error(f"HTML文件加载失败: {e}", "Main")
            return False
    
    def extract_resources(self):
        """提取资源"""
        if not self.parser:
            log_warning("请先加载HTML文件", "Main")
            return False
        
        main_images = self.parser.get_main_images()
        
        color_options = self.parser.get_color_options()
        
        color_card_images = []
        for color_name, color_image in color_options:
            if color_image:
                color_card_images.append((color_image, color_name))
        
        detail_images = self.parser.get_detail_images()
        
        videos = self.parser.get_videos()
        
        attributes = self.parser.get_attributes()
        
        main_images_with_names = []
        if main_images:
            for idx, img in enumerate(main_images):
                main_images_with_names.append((img, f"{idx+1}"))
        
        self.resources = {
            'main_images': main_images_with_names,
            'detail_images': detail_images,
            'color_card_images': color_card_images,
            'videos': videos,
            'attributes': attributes
        }
        
        parts = []
        if len(main_images) > 0:
            parts.append(f"主图({len(main_images)})")
        if len(videos) > 0:
            parts.append(f"视频({len(videos)})")
        if len(color_card_images) > 0:
            parts.append(f"色卡图({len(color_card_images)})")
        if len(detail_images) > 0:
            parts.append(f"详情图({len(detail_images)})")
        
        if parts:
            log_info(f"资源提取完成: {', '.join(parts)}", "Main")
        else:
            log_info("资源提取完成: 未发现有效资源", "Main")
        
        from utils.temp_storage import save_resources_temp
        save_resources_temp(
            self.product_id,
            self.resources.get('main_images', []),
            self.resources.get('color_card_images', []),
            self.resources.get('detail_images', []),
            self.resources.get('videos', [])
        )
        
        return True
    
    def extract_prices(self):
        """提取价格信息"""
        if not self.parser:
            log_warning("请先加载HTML文件", "Main")
            return False
        
        from utils.price_extractor import PriceExtractor
        
        with open(self.html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        extractor = PriceExtractor(html_content)
        prices = extractor.extract_all_prices()
        
        self.prices = prices
        
        from utils.temp_storage import save_prices_temp
        save_prices_temp(self.product_id, prices)
        
        return True
    
    def download_resources(self):
        """下载资源 - 从数据库读取资源URL"""
        # 先导入资源数据到数据库
        from utils.duckdb_database import get_duckdb
        try:
            db = get_duckdb()
            if db:
                db.save_resources(
                    self.product_id,
                    self.resources.get('main_images', []),
                    self.resources.get('color_card_images', []),
                    self.resources.get('detail_images', []),
                    self.resources.get('videos', [])
                )
                db.close()
        except Exception as e:
            log_error(f"导入资源到数据库失败: {e}", "Main")
        
        # 从数据库获取待下载资源
        from utils.resource_downloader import ResourceDownloader
        try:
            downloader = ResourceDownloader()
            resources = downloader.get_pending_resources(self.product_id)
            
            if not resources:
                log_warning("没有可下载的资源", "Main")
                return False
            
            # 直接下载
            output_dir = os.getcwd()
            success = downloader.download_with_aria2c(resources, output_dir)
            
            if success:
                downloader.clean_small_files()
            
            return success
        except Exception as e:
            log_error(f"下载失败: {e}", "Main")
            return False
    
    def save_attributes(self):
        """保存属性"""
        if not hasattr(self, 'resources'):
            log_warning("请先提取资源", "Main")
            return False
        
        attributes = self.resources.get('attributes', [])
        if attributes:
            self.file_handler.save_attributes(attributes)
        
        return True
    
    def generate_shortcut(self):
        """生成URL快捷方式"""
        platform = self.parser.get_platform() if self.parser else 'alibaba'
        self.file_handler.generate_url_shortcut(self.product_id, platform=platform)
        return True
    
    def create_rebuild_script(self):
        """创建重建脚本"""
        # 在当前工作目录创建重建脚本
        self.file_handler.create_rebuild_script('.')
        return True
    
    def organize_files(self):
        """整理文件"""
        self.file_handler.move_files_to_directories()
        return True
    
    def run(self, create_rebuild_script=True):
        """运行完整流程"""
        log_info("=== 1688详情页资源采集工具 ====", "Main")
        
        html_abs_path = os.path.abspath(self.html_file)
        
        if not os.path.exists(html_abs_path):
            log_error(f"HTML文件不存在: {html_abs_path}", "Main")
            return False
        
        self.html_file = html_abs_path
        
        if self.output_path:
            output_dir = os.path.abspath(os.path.join(self.output_path, self.product_id))
        else:
            html_dir = os.path.dirname(html_abs_path)
            output_dir = os.path.abspath(os.path.join(html_dir, self.product_id))
        
        log_info(f"输出目录: {output_dir}", "Main")
        
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
                log_info(f"已创建输出目录: {output_dir}", "Main")
            except PermissionError as e:
                log_error(f"无法创建文件夹 '{output_dir}'", "Main")
                log_error(f"请检查是否有写入权限", "Main")
                log_error(f"详细错误: {e}", "Main")
                return False
        elif os.path.isfile(output_dir):
            log_error(f"'{output_dir}' 是一个文件而非目录", "Main")
            log_error(f"请删除或重命名该文件后重试", "Main")
            return False
        
        try:
            os.chdir(output_dir)
            log_info(f"工作目录: {os.getcwd()}", "Main")
        except PermissionError as e:
            log_error(f"无法进入目录 '{output_dir}'", "Main")
            log_error(f"详细错误: {e}", "Main")
            return False
        
        if not self.load_html():
            log_error("加载HTML文件失败", "Main")
            return False
        
        # 2. 提取价格信息
        self.extract_prices()
        
        # 3. 提取资源
        if not self.extract_resources():
            log_error("提取资源失败", "Main")
            return False
        
        # 4. 下载资源
        self.download_resources()
        
        # 5. 保存属性
        self.save_attributes()
        
        # 6. 生成URL快捷方式
        self.generate_shortcut()
        
        # 7. 创建脚本（仅在批处理模式下）
        if create_rebuild_script:
            self.create_rebuild_script()
            self.create_recutpic_script()
        
        from utils.temp_storage import save_resource_counts_temp
        main_count = len(self.resources.get('main_images', []))
        color_count = len(self.resources.get('color_card_images', []))
        detail_count = len(self.resources.get('detail_images', []))
        video_count = len(self.resources.get('videos', []))
        platform = self.parser.get_platform() if self.parser else 'alibaba'
        save_resource_counts_temp(self.product_id, main_count, color_count, detail_count, video_count, output_dir, platform)
        log_info(f"已保存资源计数: 主图({main_count}), 色卡图({color_count}), 详情图({detail_count}), 视频({video_count})", "Main")
        
        log_success("=== 处理完成 ====", "Main")
        return True
    
    def process_images(self, image_path=None, with_animated=False, output_webp=False, convert_main=False, convert_color=False):
        """处理图片"""
        # 导入图片处理模块
        import utils.image_utils
        import utils.image_processor
        
        # 设置全局变量
        utils.image_utils.WITH_ANIMATED = with_animated
        utils.image_utils.OUTPUT_WEBP = output_webp
        utils.image_utils.CONVERT_MAIN = convert_main
        utils.image_utils.CONVERT_COLOR = convert_color
        
        # 如果提供了图片路径，直接处理单张图片
        if image_path:
            utils.image_processor.process_single_image(image_path)
        else:
            # 运行图片处理
            utils.image_processor.enlarge_main_images()
            utils.image_processor.process_regular_detail_images()
            utils.image_processor.enlarge_color_card_images()
            
            # 显示最终汇总报告
            utils.image_processor.reporter.show_final_summary()
        
        return True
    
    def create_recutpic_script(self):
        """创建图片处理脚本"""
        # 在当前工作目录创建图片处理脚本
        self.file_handler.create_recutpic_script('.')
        return True

def main():
    """主函数"""
    # 解析命令行参数
    create_rebuild_script = True  # 默认创建重建脚本
    html_file = None
    process_images_flag = False
    image_path = None
    with_animated = False
    output_webp = False
    convert_main = False
    convert_color = False
    output_path = None  # 新增：输出路径参数
    keep_avif = False  # 新增：保留AVIF格式参数
    
    # 检查帮助参数
    if len(sys.argv) > 1 and (sys.argv[1] == "--help" or sys.argv[1] == "-h"):
        print("====================================")
        print("1688详情页资源采集工具")
        print("====================================")
        print("版本:", __version__)
        print("作者: 急云")
        print("描述: 用于采集1688详情页资源的工具，支持图片、视频和属性的提取与下载")
        print("====================================")
        print("用法:")
        print("  python main.py <html_file> [--no-rebuild] [--output <path>]")
        print("  python main.py --process-images [--webp [--t] [--color]] [--with-animated]")
        print("  python main.py <image_file> (处理单张图片)")
        print("  python main.py --gui (启动GUI模式)")
        print("  python main.py --help | -h (显示此帮助信息)")
        print("====================================")
        print("参数说明:")
        print("  <html_file>          : 要处理的1688详情页HTML文件路径")
        print("  --no-rebuild         : 可选参数，不创建重建脚本")
        print("  --output <path>      : 可选参数，指定输出目录路径")
        print("  --keep-avif          : 可选参数，保留AVIF格式（京东平台专用）")
        print("  --process-images     : 处理当前目录中的所有详情图")
        print("    --webp             : 输出图片格式为WebP")
        print("      --t              : 将主图转换为WebP格式")
        print("      --color          : 将色卡图转换为WebP格式")
        print("    --with-animated    : 包含GIF、WebP等动图")
        print("  <image_file>         : 要处理的单张图片文件路径")
        print("  --gui                : 启动图形用户界面模式")
        print("  --help, -h           : 显示此帮助信息")
        return 0
    
    # 检测启动方式，自动判断GUI/CLI模式
    from utils.launcher import should_start_gui
    
    if should_start_gui():
        from gui.app import main as gui_main
        gui_main()
        return 0
    
    # 检查--process-images参数是否存在
    has_process_images = False
    if len(sys.argv) > 1 and sys.argv[1] == "--process-images":
        has_process_images = True
    
    # 如果没有--process-images参数，过滤掉所有子参数
    filtered_args = [sys.argv[0]]
    if has_process_images:
        filtered_args = sys.argv
    else:
        # 只保留非子参数，忽略所有--process-images的子参数
        i = 1
        while i < len(sys.argv):
            arg = sys.argv[i]
            # 检查是否是--process-images的子参数
            if arg in ["--webp", "--t", "--color", "--with-animated"]:
                i += 1
                continue  # 忽略子参数
            # 保留--no-rebuild参数
            if arg == "--no-rebuild":
                filtered_args.append(arg)
                i += 1
                continue
            # 保留--keep-avif参数
            if arg == "--keep-avif":
                filtered_args.append(arg)
                i += 1
                continue
            # 保留--output参数及其值
            if arg == "--output" and i + 1 < len(sys.argv):
                filtered_args.append(arg)
                filtered_args.append(sys.argv[i + 1])
                i += 2
                continue
            # 只保留第一个非子参数（HTML文件路径或图片文件路径）
            if len(filtered_args) == 1:
                filtered_args.append(arg)
            i += 1
    
    # 重新解析参数
    sys.argv = filtered_args
    
    if len(sys.argv) < 2:
        print("用法: python main.py <html_file> [--no-rebuild]")
        print("或: python main.py --process-images [--webp [--t] [--color]] [--with-animated]")
        print("或: python main.py <image_file> (处理单张图片)")
        print("或: python main.py --gui (启动GUI模式)")
        print("或: python main.py --help | -h (显示帮助信息)")
        return 1
    else:
        if sys.argv[1] == "--process-images":
            process_images_flag = True
            # 检查子参数
            webp_found = False
            for arg in sys.argv[2:]:
                if arg == "--with-animated":
                    with_animated = True
                elif arg == "--webp":
                    output_webp = True
                    webp_found = True
                elif arg == "--t" and webp_found:
                    convert_main = True
                elif arg == "--color" and webp_found:
                    convert_color = True
        else:
            # 检查是否是图片文件
            file_path = sys.argv[1]
            if os.path.exists(file_path) and os.path.isfile(file_path):
                # 检查文件扩展名是否为图片
                ext = os.path.splitext(file_path)[1].lower()
                if ext in ['.jpg', '.jpeg', '.png']:
                    # 是图片文件，处理单张图片
                    image_path = file_path
                else:
                    # 不是图片文件，当作HTML文件处理
                    html_file = file_path
            else:
                # 路径不存在，当作HTML文件处理
                html_file = file_path
            
            # 解析其他参数
            args = sys.argv[2:]
            i = 0
            while i < len(args):
                if args[i] == "--no-rebuild":
                    create_rebuild_script = False
                    i += 1
                elif args[i] == "--keep-avif":
                    keep_avif = True
                    i += 1
                elif args[i] == "--output" and i + 1 < len(args):
                    output_path = args[i + 1]
                    i += 2
                else:
                    i += 1
    
    if process_images_flag:
        # 处理图片
        # 创建一个临时的 AlibabaScraper 实例
        scraper = AlibabaScraper("")
        success = scraper.process_images(with_animated=with_animated, output_webp=output_webp, convert_main=convert_main, convert_color=convert_color)
        return 0 if success else 1
    elif image_path:
        log_info(f"开始处理单张图片: {image_path}", "Main")
        scraper = AlibabaScraper("")
        success = scraper.process_images(image_path)
        return 0 if success else 1
    else:
        log_info(f"处理文件: {html_file}", "Main")
        
        if not os.path.exists(html_file):
            log_error(f"HTML文件不存在: {html_file}", "Main")
            log_info(f"当前目录: {os.getcwd()}", "Main")
            log_info(f"文件列表: {os.listdir('.')}", "Main")
            return 1
        
        log_info(f"HTML文件存在，大小: {os.path.getsize(html_file)} 字节", "Main")
        
        scraper = AlibabaScraper(html_file, output_path, keep_avif)
        success = scraper.run(create_rebuild_script)
        
        return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
