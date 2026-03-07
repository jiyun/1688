# 下载管理工具
import os
import subprocess
import time
import sys
from os.path import splitext
from .tool_downloader import ensure_aria2c, get_aria2c_path

if sys.stdout:
    sys.stdout.reconfigure(line_buffering=True)

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
        """调用aria2c下载文件并显示进度条"""
        if not os.path.exists(download_list_file):
            print(f"下载列表文件不存在: {download_list_file}")
            return False
        
        try:
            current_dir = os.getcwd()
            
            expected_files = {}
            with open(download_list_file, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                i = 0
                while i < len(lines) - 1:
                    url = lines[i]
                    out_line = lines[i + 1]
                    if out_line.startswith('out='):
                        filename = out_line[4:]
                        expected_files[filename] = url
                    i += 2
            
            total_items = len(expected_files)
            
            if total_items == 0:
                print("下载列表为空")
                return False
            
            aria2c_path = get_aria2c_path()
            
            if not aria2c_path:
                print("aria2c 不存在，正在自动下载...")
                aria2c_path = ensure_aria2c()
            
            if not aria2c_path:
                print("无法获取 aria2c，请手动下载")
                return False
            
            print(f"下载项目总数: {total_items}", flush=True)
            
            cmd = [
                aria2c_path,
                '--console-log-level=warn',
                '-d', current_dir,
                '-i', download_list_file
            ]
            
            cmd.extend(self.config["DOWNLOAD_CONF"]["aria2c_args"].split())
            
            log_file = open('down_log.txt', 'w', encoding='utf-8')
            
            process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            bar_length = 40
            last_count = 0
            
            def get_downloaded_count():
                count = 0
                for f in os.listdir(current_dir):
                    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.avi', '.mov', '.webp')):
                        if not f.startswith('new_') and f != '拼接结果.jpg':
                            count += 1
                return count
            
            initial_count = get_downloaded_count()
            
            print("正在下载资源...", flush=True)
            
            while process.poll() is None:
                current_count = get_downloaded_count() - initial_count
                
                if current_count > last_count:
                    last_count = current_count
                    
                    if current_count > total_items:
                        current_count = total_items
                    
                    percent = (current_count / total_items) * 100
                    filled = int(bar_length * current_count / total_items)
                    bar = '█' * filled + '-' * (bar_length - filled)
                    print(f'\r[{bar}] {current_count}/{total_items} ({percent:.1f}%)', end='', flush=True)
                
                time.sleep(0.2)
            
            final_count = get_downloaded_count() - initial_count
            if final_count > total_items:
                final_count = total_items
            
            bar = '█' * bar_length
            print(f'\r[{bar}] {final_count}/{total_items} (100.0%)', flush=True)
            
            log_file.close()
            
            failed_files = []
            for filename, url in expected_files.items():
                if not os.path.exists(os.path.join(current_dir, filename)):
                    failed_files.append((filename, url))
            
            if failed_files:
                print(f"\n下载失败的项目 ({len(failed_files)}):", flush=True)
                for filename, url in failed_files:
                    print(f"  [失败] {filename}", flush=True)
            
            success_count = total_items - len(failed_files)
            print(f"\n下载完成: 成功 {success_count}/{total_items}", flush=True)
            return len(failed_files) == 0
                
        except Exception as e:
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
