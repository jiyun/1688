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

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from utils.tool_downloader import ensure_all_dependencies
ensure_all_dependencies()

from utils.parser import HTMLParser
from utils.downloader import Downloader
from utils.file_handler import FileHandler
import config

class AlibabaScraper:
    def __init__(self, html_file):
        self.html_file = html_file
        self.product_id = self._extract_product_id()
        self.parser = None
        self.downloader = Downloader({
            'DOWNLOAD_CONF': config.DOWNLOAD_CONF,
            'FILE_NAMING': config.FILE_NAMING
        })
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
            self.parser = HTMLParser(html_content)
            print(f"HTML文件加载成功: {self.html_file}")
            return True
        except Exception as e:
            print(f"HTML文件加载失败: {e}")
            return False
    
    def extract_resources(self):
        """提取资源"""
        if not self.parser:
            print("请先加载HTML文件")
            return False
        
        # 提取主图
        main_images = self.parser.get_main_images()
        
        # 提取颜色选项
        color_options = self.parser.get_color_options()
        
        # 提取颜色色卡图片
        color_card_images = []
        for color_name, color_image in color_options:
            if color_image:
                color_card_images.append((color_image, color_name))
        
        # 提取详情图
        detail_images = self.parser.get_detail_images()
        
        # 提取视频
        videos = self.parser.get_videos()
        
        # 提取属性
        attributes = self.parser.get_attributes()
        
        # 关联主图和颜色选项，按顺序命名为T_[n].jpg
        main_images_with_names = []
        if main_images:
            for idx, img in enumerate(main_images):
                # 按顺序命名为T_[n].jpg
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
            print(f"资源提取完成: {', '.join(parts)}")
        else:
            print("资源提取完成: 未发现有效资源")
        return True
    
    def download_resources(self):
        """下载资源"""
        if not hasattr(self, 'resources'):
            print("请先提取资源")
            return False
        
        # 生成下载列表
        download_list = self.downloader.generate_download_list(self.resources)
        
        if not download_list:
            print("没有可下载的资源")
            return False
        
        # 保存下载列表
        self.downloader.save_download_list(download_list)
        
        # 开始下载
        success = self.downloader.download()
        
        if success:
            # 清理小文件
            self.downloader.clean_small_files()
        
        return success
    
    def save_attributes(self):
        """保存属性"""
        if not hasattr(self, 'resources'):
            print("请先提取资源")
            return False
        
        attributes = self.resources.get('attributes', [])
        if attributes:
            self.file_handler.save_attributes(attributes)
        
        return True
    
    def generate_shortcut(self):
        """生成URL快捷方式"""
        self.file_handler.generate_url_shortcut(self.product_id)
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
        print("=== 1688详情页资源采集工具 ====")
        
        # 确保在正确的目录中工作
        if not os.path.basename(os.getcwd()) == self.product_id:
            # 如果当前目录不是商品ID目录，创建并进入
            if os.path.exists(self.product_id):
                # 检查是否是文件而非目录
                if os.path.isfile(self.product_id):
                    print(f"错误: '{self.product_id}' 是一个文件而非目录")
                    print(f"请删除或重命名该文件后重试")
                    return False
            else:
                try:
                    os.makedirs(self.product_id)
                except PermissionError as e:
                    print(f"错误: 无法在当前目录创建文件夹 '{self.product_id}'")
                    print(f"请检查当前目录是否有写入权限: {os.getcwd()}")
                    print(f"详细错误: {e}")
                    return False
            try:
                os.chdir(self.product_id)
            except PermissionError as e:
                print(f"错误: 无法进入目录 '{self.product_id}'")
                print(f"详细错误: {e}")
                return False
        
        # 检查HTML文件是否存在
        if not os.path.exists(self.html_file):
            # 尝试相对于当前工作目录的路径
            html_path = os.path.basename(self.html_file)
            if os.path.exists(html_path):
                self.html_file = html_path
            else:
                # 尝试上级目录
                html_path = os.path.join("..", os.path.basename(self.html_file))
                if os.path.exists(html_path):
                    self.html_file = html_path
        
        # 1. 加载HTML文件
        if not self.load_html():
            print("加载HTML文件失败")
            return False
        
        # 2. 提取资源
        if not self.extract_resources():
            print("提取资源失败")
            return False
        
        # 3. 下载资源
        self.download_resources()
        
        # 4. 保存属性
        self.save_attributes()
        
        # 5. 生成URL快捷方式
        self.generate_shortcut()
        
        # 6. 创建脚本（仅在批处理模式下）
        if create_rebuild_script:
            self.create_rebuild_script()
            self.create_recutpic_script()
        
        print("=== 处理完成 ====")
        return True
    
    def process_images(self, image_path=None):
        """处理图片"""
        # 导入图片处理模块
        import utils.recutpic
        
        # 如果提供了图片路径，直接处理单张图片
        if image_path:
            utils.recutpic.process_single_image(image_path)
        else:
            # 运行图片处理
            utils.recutpic.main()
        
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
    
    # 检查帮助参数
    if len(sys.argv) > 1 and (sys.argv[1] == "--help" or sys.argv[1] == "-h"):
        print("====================================")
        print("1688详情页资源采集工具")
        print("====================================")
        print("版本: 0.2.0")
        print("作者: 急云")
        print("描述: 用于采集1688详情页资源的工具，支持图片、视频和属性的提取与下载")
        print("====================================")
        print("用法:")
        print("  python main.py <html_file> [--no-rebuild]")
        print("  python main.py --process-images")
        print("  python main.py <image_file> (处理单张图片)")
        print("  python main.py --help | -h (显示此帮助信息)")
        print("====================================")
        print("参数说明:")
        print("  <html_file>          : 要处理的1688详情页HTML文件路径")
        print("  --no-rebuild         : 可选参数，不创建重建脚本")
        print("  --process-images     : 处理当前目录中的所有详情图")
        print("  <image_file>         : 要处理的单张图片文件路径")
        print("  --help, -h           : 显示此帮助信息")
        print("====================================")
        return 0
    
    if len(sys.argv) < 2:
        print("用法: python main.py <html_file> [--no-rebuild]")
        print("或: python main.py --process-images")
        print("或: python main.py <image_file> (处理单张图片)")
        print("或: python main.py --help | -h (显示帮助信息)")
        return 1
    else:
        if sys.argv[1] == "--process-images":
            process_images_flag = True
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
            
            # 检查是否有 --no-rebuild 参数
            if len(sys.argv) > 2 and sys.argv[2] == "--no-rebuild":
                create_rebuild_script = False
    
    if process_images_flag:
        # 处理图片
        # 创建一个临时的 AlibabaScraper 实例
        scraper = AlibabaScraper("")
        success = scraper.process_images()
        return 0 if success else 1
    elif image_path:
        # 处理单张图片
        print(f"开始处理单张图片: {image_path}")
        # 创建一个临时的 AlibabaScraper 实例
        scraper = AlibabaScraper("")
        success = scraper.process_images(image_path)
        return 0 if success else 1
    else:
        print(f"处理文件: {html_file}")
        
        if not os.path.exists(html_file):
            print(f"HTML文件不存在: {html_file}")
            print(f"当前目录: {os.getcwd()}")
            print(f"文件列表: {os.listdir('.')}")
            return 1
        
        print(f"HTML文件存在，大小: {os.path.getsize(html_file)} 字节")
        
        scraper = AlibabaScraper(html_file)
        success = scraper.run(create_rebuild_script)
        
        return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
