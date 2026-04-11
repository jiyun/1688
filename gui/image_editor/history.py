"""
历史记录管理器

支持撤销/重做功能:
- 最多50步历史记录
- 状态序列化/反序列化
- 内存优化
"""

from typing import List, Optional, Dict, Any
from copy import deepcopy


class HistoryManager:
    """历史记录管理器 - 支持撤销/重做"""
    
    MAX_HISTORY = 50
    
    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        self.current_index: int = -1
    
    def can_undo(self) -> bool:
        """是否可以撤销"""
        return self.current_index > 0
    
    def can_redo(self) -> bool:
        """是否可以重做"""
        return self.current_index < len(self.history) - 1
    
    def get_history_count(self) -> int:
        """获取历史记录数量"""
        return len(self.history)
    
    def get_current_position(self) -> int:
        """获取当前位置"""
        return self.current_index + 1
    
    def save_state(self, blocks_data: List[Dict]):
        """
        保存当前状态
        
        Args:
            blocks_data: 块状态列表(序列化后的字典)
        """
        if not blocks_data:
            return
        
        state = {
            'blocks': deepcopy(blocks_data),
            'timestamp': self._get_timestamp()
        }
        
        if self.current_index < len(self.history) - 1:
            self.history = self.history[:self.current_index + 1]
        
        self.history.append(state)
        self.current_index = len(self.history) - 1
        
        if len(self.history) > self.MAX_HISTORY:
            removed = self.history.pop(0)
            self.current_index -= 1
    
    def undo(self) -> Optional[List[Dict]]:
        """
        撤销操作
        
        Returns:
            恢复的状态数据,如果无法撤销则返回None
        """
        if not self.can_undo():
            return None
        
        self.current_index -= 1
        return deepcopy(self.history[self.current_index]['blocks'])
    
    def redo(self) -> Optional[List[Dict]]:
        """
        重做操作
        
        Returns:
            恢复的状态数据,如果无法重做则返回None
        """
        if not self.can_redo():
            return None
        
        self.current_index += 1
        return deepcopy(self.history[self.current_index]['blocks'])
    
    def clear(self):
        """清空历史记录"""
        self.history = []
        self.current_index = -1
    
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def get_status_text(self) -> str:
        """获取状态文本"""
        total = len(self.history)
        current = self.current_index + 1
        return f"历史记录: {current}/{total}"
