"""
共享内存进度管理器

使用multiprocessing.Manager创建共享的进度管理器，实现GUI与子进程之间的实时进度同步。
"""

import time
from multiprocessing import Manager


class SharedProgressManager:
    """共享内存进度管理器
    
    使用multiprocessing.Manager创建共享的进度状态，实现GUI与子进程之间的实时进度同步。
    """
    
    def __init__(self):
        """初始化进度管理器"""
        self.manager = Manager()
        
        # 共享进度状态
        self.main_progress = self.manager.dict({
            'total': 0,
            'processed': 0,
            'skipped': 0,
            'generated': 0,
            'status': 'pending',
            'start_time': None,
            'current': 0,
            'percent': 0,
            'elapsed': 0
        })
        
        self.detail_progress = self.manager.dict({
            'total': 0,
            'processed': 0,
            'skipped': 0,
            'generated': 0,
            'status': 'pending',
            'start_time': None,
            'current': 0,
            'step': 0,
            'percent': 0,
            'elapsed': 0
        })
        
        self.color_progress = self.manager.dict({
            'total': 0,
            'processed': 0,
            'skipped': 0,
            'generated': 0,
            'status': 'pending',
            'start_time': None,
            'current': 0,
            'percent': 0,
            'elapsed': 0
        })
        
        # 共享的整体状态
        self.status = self.manager.Value('s', 'pending')
        self.error = self.manager.Value('s', '')
        self.deleted_count = self.manager.Value('i', 0)
        
        # 共享锁
        self.lock = self.manager.Lock()
    
    def start_main(self):
        """开始主图处理"""
        with self.lock:
            self.main_progress['status'] = 'processing'
            self.main_progress['start_time'] = time.time()
            self.main_progress['current'] = 0
    
    def start_detail(self):
        """开始详情图处理"""
        with self.lock:
            self.detail_progress['status'] = 'processing'
            self.detail_progress['start_time'] = time.time()
            self.detail_progress['current'] = 0
    
    def start_color(self):
        """开始色卡图处理"""
        with self.lock:
            self.color_progress['status'] = 'processing'
            self.color_progress['start_time'] = time.time()
            self.color_progress['current'] = 0
    
    def update_main(self, total=None, current=None, generated=None):
        """更新主图进度"""
        with self.lock:
            if total is not None:
                self.main_progress['total'] = total
            if current is not None:
                self.main_progress['current'] = current
                percent = int((current / total) * 100) if total > 0 else 0
                self.main_progress['percent'] = percent
            if generated is not None:
                self.main_progress['generated'] = generated
    
    def update_detail(self, total=None, current=None, generated=None, step=None):
        """更新详情图进度"""
        with self.lock:
            if total is not None:
                self.detail_progress['total'] = total
            if current is not None:
                self.detail_progress['current'] = current
                percent = int((current / total) * 100) if total > 0 else 0
                self.detail_progress['percent'] = percent
            if generated is not None:
                self.detail_progress['generated'] = generated
            if step is not None:
                self.detail_progress['step'] = step
    
    def update_color(self, total=None, current=None, generated=None):
        """更新色卡图进度"""
        with self.lock:
            if total is not None:
                self.color_progress['total'] = total
            if current is not None:
                self.color_progress['current'] = current
                percent = int((current / total) * 100) if total > 0 else 0
                self.color_progress['percent'] = percent
            if generated is not None:
                self.color_progress['generated'] = generated
    
    def complete_main(self):
        """完成主图处理"""
        with self.lock:
            self.main_progress['status'] = 'completed'
            elapsed = time.time() - self.main_progress['start_time'] if self.main_progress['start_time'] else 0
            self.main_progress['elapsed'] = elapsed
    
    def complete_detail(self):
        """完成详情图处理"""
        with self.lock:
            self.detail_progress['status'] = 'completed'
            elapsed = time.time() - self.detail_progress['start_time'] if self.detail_progress['start_time'] else 0
            self.detail_progress['elapsed'] = elapsed
    
    def complete_color(self):
        """完成色卡图处理"""
        with self.lock:
            self.color_progress['status'] = 'completed'
            elapsed = time.time() - self.color_progress['start_time'] if self.color_progress['start_time'] else 0
            self.color_progress['elapsed'] = elapsed
    
    def get_progress(self):
        """获取所有进度信息"""
        with self.lock:
            return {
                'main': dict(self.main_progress),
                'detail': dict(self.detail_progress),
                'color': dict(self.color_progress),
                'status': self.status.value,
                'error': self.error.value,
                'deleted_count': self.deleted_count.value
            }
    
    def set_status(self, status):
        """设置整体状态"""
        with self.lock:
            self.status.value = status
    
    def set_error(self, error):
        """设置错误信息"""
        with self.lock:
            self.error.value = error
    
    def set_deleted_count(self, count):
        """设置删除文件数量"""
        with self.lock:
            self.deleted_count.value = count
    
    def shutdown(self):
        """关闭进度管理器"""
        self.manager.shutdown()
