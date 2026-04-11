"""
视频生成模块

将详情图生成为瀑布流滚动视频
"""

import os
import subprocess
from typing import List, Optional
from PIL import Image
import tempfile


def generate_scroll_video(image_paths: List[str], output_path: str = None,
                         duration: int = 15, fps: int = 30,
                         width: int = 1440) -> Optional[str]:
    """
    将详情图生成为瀑布流滚动视频
    
    Args:
        image_paths: 图片路径列表
        output_path: 输出视频路径，None则使用临时路径
        duration: 视频时长（秒）
        fps: 帧率
        width: 视频宽度
    
    Returns:
        输出视频路径，失败返回None
    """
    if not image_paths:
        print("没有图片可生成视频")
        return None
    
    valid_paths = [p for p in image_paths if os.path.exists(p)]
    if not valid_paths:
        print("所有图片路径无效")
        return None
    
    try:
        merged_image = _stitch_images_vertical(valid_paths, width)
        if merged_image is None:
            return None
        
        if output_path is None:
            output_dir = os.path.dirname(valid_paths[0])
            output_path = os.path.join(output_dir, "scroll_video.mp4")
        
        result = _generate_scroll_video_ffmpeg(merged_image, output_path, duration, fps)
        
        if result:
            print(f"视频生成成功: {output_path}")
            return output_path
        
        return None
    
    except Exception as e:
        print(f"生成视频失败: {e}")
        return None


def _stitch_images_vertical(image_paths: List[str], width: int) -> Optional[Image.Image]:
    """垂直拼接图片"""
    images = []
    total_height = 0
    
    for path in image_paths:
        try:
            img = Image.open(path)
            if img.width != width:
                scale = width / img.width
                new_height = int(img.height * scale)
                img = img.resize((width, new_height), Image.LANCZOS)
            
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            images.append(img)
            total_height += img.height
        except Exception as e:
            print(f"加载图片失败 {path}: {e}")
    
    if not images:
        return None
    
    result = Image.new('RGB', (width, total_height), (255, 255, 255))
    
    y_offset = 0
    for img in images:
        result.paste(img, (0, y_offset))
        y_offset += img.height
    
    return result


def _generate_scroll_video_ffmpeg(image: Image.Image, output_path: str,
                                  duration: int, fps: int) -> bool:
    """使用ffmpeg生成滚动视频"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ffmpeg未安装，尝试使用moviepy")
        return _generate_scroll_video_moviepy(image, output_path, duration, fps)
    
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        temp_path = tmp.name
        image.save(temp_path, 'PNG')
    
    try:
        image_height = image.height
        total_frames = duration * fps
        scroll_speed = (image_height - image.width) / total_frames
        
        cmd = [
            'ffmpeg',
            '-y',
            '-loop', '1',
            '-i', temp_path,
            '-vf', f'scroll=v={scroll_speed}:h={image.width}',
            '-t', str(duration),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-r', str(fps),
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"ffmpeg错误: {result.stderr}")
            return False
        
        return True
    
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def _generate_scroll_video_moviepy(image: Image.Image, output_path: str,
                                   duration: int, fps: int) -> bool:
    """使用moviepy生成滚动视频"""
    try:
        from moviepy.editor import ImageClip
    except ImportError:
        print("moviepy未安装，无法生成视频")
        print("请安装: pip install moviepy")
        return False
    
    try:
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            temp_path = tmp.name
            image.save(temp_path, 'PNG')
        
        clip = ImageClip(temp_path, duration=duration)
        
        image_height = image.height
        scroll_distance = image_height - image.width
        
        def scroll_effect(get_frame, t):
            frame = get_frame(t)
            y = int(scroll_distance * t / duration)
            return frame[y:y + image.width, :]
        
        clip = clip.fl(scroll_effect, apply_to=['mask'])
        clip = clip.set_fps(fps)
        
        clip.write_videofile(output_path, fps=fps, codec='libx264')
        
        return True
    
    except Exception as e:
        print(f"moviepy生成视频失败: {e}")
        return False
    
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def generate_slideshow(image_paths: List[str], output_path: str = None,
                      duration_per_image: float = 3.0,
                      fps: int = 30, width: int = 1440) -> Optional[str]:
    """
    生成幻灯片视频
    
    Args:
        image_paths: 图片路径列表
        output_path: 输出视频路径
        duration_per_image: 每张图片显示时长（秒）
        fps: 帧率
        width: 视频宽度
    
    Returns:
        输出视频路径
    """
    if not image_paths:
        return None
    
    try:
        from moviepy.editor import ImageSequenceClip
    except ImportError:
        print("moviepy未安装")
        return None
    
    valid_paths = []
    for path in image_paths:
        if os.path.exists(path):
            valid_paths.append(path)
    
    if not valid_paths:
        return None
    
    if output_path is None:
        output_dir = os.path.dirname(valid_paths[0])
        output_path = os.path.join(output_dir, "slideshow.mp4")
    
    try:
        clip = ImageSequenceClip(valid_paths, durations=[duration_per_image] * len(valid_paths))
        clip = clip.set_fps(fps)
        clip.write_videofile(output_path, fps=fps, codec='libx264')
        return output_path
    except Exception as e:
        print(f"生成幻灯片视频失败: {e}")
        return None
