# 下载管理工具
import os
import subprocess
import sys
from os.path import splitext
from .tool_downloader import get_aria2c_path

if sys.stdout:
    sys.stdout.reconfigure(line_buffering=True)


def get_aria2c_path():
    """获取aria2c路径"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    
    aria2c_path = os.path.join(project_dir, 'tools', 'aria2c.exe')
    if os.path.exists(aria2c_path):
        return aria2c_path
    
    return None


class Downloader:
    def __init__(self, config, keep_avif=False):
        self.config = config
        self.keep_avif = keep_avif
    
    def _clean_duplicate_extension(self, url):
        """清理URL中的重复扩展名，如.jpg_b.jpg -> .jpg"""
        media_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.mp4', '.avi', '.mov']

        for ext in media_extensions:
            ext_positions = []
            pos = url.lower().find(ext)
            while pos != -1:
                ext_positions.append((pos, pos + len(ext)))
                pos = url.lower().find(ext, pos + len(ext))

            if len(ext_positions) >= 2:
                last_pos, last_end = ext_positions[-1]
                second_last_pos, second_last_end = ext_positions[-2]

                if second_last_end < last_pos:
                    url = url[:second_last_end] + url[last_end:]

        return url

    def _clean_url(self, url):
        """清理URL，删除扩展名后的查询参数和重复扩展名"""
        url = self._clean_duplicate_extension(url)
        
        if not self.keep_avif and url.endswith('.avif'):
            url = url[:-5]

        if '?' in url:
            base_url = url.split('?')[0]
            return base_url
        return url
    
    def generate_download_list(self, resources):
        """生成下载列表"""
        download_list = []
        
        for idx, (url, name) in enumerate(resources.get('main_images', [])):
            clean_url = self._clean_url(url)
            ext = splitext(clean_url)[1]
            if not ext:
                ext = '.jpg'
            output_name = f"{self.config['FILE_NAMING']['main_image_prefix']}{name}{ext}"
            download_list.append(f"{clean_url}\n out={output_name}")
        
        for idx, (url, name) in enumerate(resources.get('color_card_images', [])):
            clean_url = self._clean_url(url)
            ext = splitext(clean_url)[1]
            if not ext:
                ext = '.jpg'
            output_name = f"color_{name}{ext}"
            download_list.append(f"{clean_url}\n out={output_name}")
        
        for idx, url in enumerate(resources.get('detail_images', [])):
            clean_url = self._clean_url(url)
            ext = splitext(clean_url)[1]
            if not ext:
                ext = '.jpg'
            output_name = f"{self.config['FILE_NAMING']['detail_image_prefix']}{idx+1}{ext}"
            download_list.append(f"{clean_url}\n out={output_name}")
        
        for idx, url in enumerate(resources.get('videos', [])):
            clean_url = self._clean_url(url)
            ext = splitext(clean_url)[1]
            if not ext:
                ext = '.mp4'
            output_name = f"{self.config['FILE_NAMING']['video_prefix']}{idx+1}{ext}"
            download_list.append(f"{clean_url}\n out={output_name}")
        
        download_list = self._remove_duplicates(download_list)
        
        return download_list
    
    def _remove_duplicates(self, download_list):
        """去重下载列表"""
        unique_uris = {}
        for item in download_list:
            if '\n out=' in item:
                uri, out = item.split('\n out=')
                clean_uri = self._clean_url(uri)
                if clean_uri not in unique_uris:
                    unique_uris[clean_uri] = out
        new_list = [f"{uri}\n out={out}" for uri, out in unique_uris.items()]
        return new_list
    
    def clean_small_files(self, directory='.'):
        """清理小文件"""
        deleted_files = []
        min_size = self.config['DOWNLOAD_CONF']['min_file_size']
        
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path):
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.avi', '.mov', '.webp')):
                    file_size = os.path.getsize(file_path)
                    if file_size < min_size:
                        os.remove(file_path)
                        deleted_files.append(file_path)
        
        return deleted_files
