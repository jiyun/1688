# 下载管理工具
import os
import subprocess
from os.path import splitext

class Downloader:
    def __init__(self, config):
        self.config = config
    
    def _clean_duplicate_extension(self, url):
        """清理URL中的重复扩展名，如.jpg_b.jpg -> .jpg"""
        # 常见的媒体扩展名列表
        media_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.mp4', '.avi', '.mov']

        # 检查URL中是否包含重复扩展名
        for ext in media_extensions:
            # 查找所有可能的扩展名位置
            ext_positions = []
            pos = url.lower().find(ext)
            while pos != -1:
                ext_positions.append((pos, pos + len(ext)))
                pos = url.lower().find(ext, pos + len(ext))

            # 如果找到至少两个相同扩展名
            if len(ext_positions) >= 2:
                # 获取最后一个扩展名的位置
                last_pos, last_end = ext_positions[-1]
                # 获取倒数第二个扩展名的位置
                second_last_pos, second_last_end = ext_positions[-2]

                # 检查两个扩展名之间是否有内容（即_b这样的部分）
                if second_last_end < last_pos:
                    # 删除从倒数第二个扩展名结束到最后一个扩展名结束的部分
                    url = url[:second_last_end] + url[last_end:]

        return url

    def _clean_url(self, url):
        """清理URL，删除扩展名后的查询参数和重复扩展名"""
        # 首先处理重复扩展名
        url = self._clean_duplicate_extension(url)

        # 然后删除查询参数
        if '?' in url:
            base_url = url.split('?')[0]
            return base_url
        return url
    
    def generate_download_list(self, resources):
        """生成下载列表"""
        download_list = []
        
        # 添加主图
        for idx, (url, name) in enumerate(resources.get('main_images', [])):
            # 清理URL，删除查询参数
            clean_url = self._clean_url(url)
            ext = splitext(clean_url)[1]
            if not ext:
                ext = '.jpg'  # 默认扩展名
            output_name = f"{self.config['FILE_NAMING']['main_image_prefix']}{name}{ext}"
            download_list.append(f"{clean_url}\n out={output_name}")
        
        # 添加颜色色卡图片
        for idx, (url, name) in enumerate(resources.get('color_card_images', [])):
            # 清理URL，删除查询参数
            clean_url = self._clean_url(url)
            ext = splitext(clean_url)[1]
            if not ext:
                ext = '.jpg'  # 默认扩展名
            output_name = f"color_{name}{ext}"
            download_list.append(f"{clean_url}\n out={output_name}")
        
        # 添加详情图
        for idx, url in enumerate(resources.get('detail_images', [])):
            # 清理URL，删除查询参数
            clean_url = self._clean_url(url)
            ext = splitext(clean_url)[1]
            if not ext:
                ext = '.jpg'  # 默认扩展名
            output_name = f"{self.config['FILE_NAMING']['detail_image_prefix']}{idx+1}{ext}"
            download_list.append(f"{clean_url}\n out={output_name}")
        
        # 添加视频
        for idx, url in enumerate(resources.get('videos', [])):
            # 清理URL，删除查询参数
            clean_url = self._clean_url(url)
            ext = splitext(clean_url)[1]
            if not ext:
                ext = '.mp4'  # 默认扩展名
            output_name = f"{self.config['FILE_NAMING']['video_prefix']}{idx+1}{ext}"
            download_list.append(f"{clean_url}\n out={output_name}")
        
        # 去重
        download_list = self._remove_duplicates(download_list)
        
        return download_list
    
    def _remove_duplicates(self, download_list):
        """去重下载列表"""
        unique_uris = {}
        for item in download_list:
            if '\n out=' in item:
                uri, out = item.split('\n out=')
                # 清理URI，确保去重时使用的是干净的URL
                clean_uri = self._clean_url(uri)
                if clean_uri not in unique_uris:
                    unique_uris[clean_uri] = out
        new_list = [f"{uri}\n out={out}" for uri, out in unique_uris.items()]
        return new_list
    
    def save_download_list(self, download_list, filename='down.txt'):
        """保存下载列表到文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            for item in download_list:
                f.write(f"{item}\n")
    
    def download(self, download_list_file='down.txt'):
        """调用aria2c下载文件并显示进度条占位符"""
        if not os.path.exists(download_list_file):
            print(f"下载列表文件不存在: {download_list_file}")
            return False
        
        try:
            # 获取当前目录的绝对路径
            current_dir = os.getcwd()
            
            # 构建aria2c命令，尝试多种路径
            aria2c_paths = ['..\\aria2c.exe', 'aria2c.exe', '..\\..\\aria2c.exe', 'aria2c']
            cmd = None
            
            for aria2c_path in aria2c_paths:
                # 检查aria2c是否存在
                if os.name == 'nt':
                    # Windows系统
                    if os.path.exists(aria2c_path):
                        # 使用--dir参数指定下载目录为当前目录
                        cmd = f"{aria2c_path} {self.config['DOWNLOAD_CONF']['aria2c_args']} --dir={current_dir} -i {download_list_file}>>down_log.txt"
                        break
                else:
                    # 其他系统
                    if os.path.exists(aria2c_path) or aria2c_path == 'aria2c':
                        # 使用--dir参数指定下载目录为当前目录
                        cmd = f"{aria2c_path} {self.config['DOWNLOAD_CONF']['aria2c_args']} --dir={current_dir} -i {download_list_file}>>down_log.txt"
                        break
            
            if not cmd:
                # 尝试使用绝对路径
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                absolute_aria2c_path = os.path.join(base_dir, 'aria2c.exe')
                if os.path.exists(absolute_aria2c_path):
                    # 使用--dir参数指定下载目录为当前目录
                    cmd = f"{absolute_aria2c_path} {self.config['DOWNLOAD_CONF']['aria2c_args']} --dir={current_dir} -i {download_list_file}>>down_log.txt"
                else:
                    print("未找到aria2c可执行文件")
                    return False
            
            # 显示进度条占位符
            print("正在下载资源...")
            bar_length = 50
            print(f"[{'-' * bar_length}] 0.0%", end='')
            
            # 执行下载命令
            subprocess.run(cmd, shell=True, check=True)
            
            # 下载完成后更新进度条
            print('\r' + ' ' * 100, end='\r')
            print(f"[{'█' * bar_length}] 100.0%")
            print("下载完成")
            return True
        except Exception as e:
            print(f"下载失败: {e}")
            return False
    
    def clean_small_files(self, directory='.'):
        """清理小文件"""
        deleted_files = []
        min_size = self.config['DOWNLOAD_CONF']['min_file_size']
        
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path):
                # 检查是否为图片或视频文件
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.avi', '.mov')):
                    file_size = os.path.getsize(file_path)
                    if file_size < min_size:
                        os.remove(file_path)
                        deleted_files.append(file_path)
        
        if deleted_files:
            print(f"已删除 {len(deleted_files)} 个小文件")
        else:
            print("没有需要删除的小文件")
        
        return deleted_files
