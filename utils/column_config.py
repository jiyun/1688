import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
from utils.config_manager import get_config_manager


class ColumnConfigManager:
    """通用列配置管理器
    
    管理数据库页面的列可见性、顺序、宽度等配置
    支持自动保存和加载
    """
    
    _instance = None
    _config = None
    
    DEFAULT_CONFIG = {
        "shop_products": {
            "visible_columns": ["product_id", "title", "price", "dropship_price", "sales_count", "review_count", "category", "collected", "product_url"],
            "column_widths": {}
        },
        "products": {
            "visible_columns": ["product_id", "title", "platform", "status", "created_at"],
            "column_widths": {}
        },
        "ds_shops": {
            "visible_columns": ["ds_shop_id", "ds_shop_name", "ds_platform", "shop_status", "product_count"],
            "column_widths": {}
        }
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self._load_config()
    
    def _load_config(self):
        self._config = get_config_manager().get_json_config("column_config")
        for key, value in self.DEFAULT_CONFIG.items():
            if key not in self._config:
                self._config[key] = value.copy()
    
    def _save_config(self):
        get_config_manager().save_json_config("column_config", self._config)
    
    def get_visible_columns(self, table_name: str) -> List[str]:
        """获取指定表格的可见列列表"""
        table_config = self._config.get(table_name, {})
        return list(table_config.get("visible_columns", []))
    
    def set_visible_columns(self, table_name: str, columns: List[str]):
        """设置指定表格的可见列列表"""
        if table_name not in self._config:
            self._config[table_name] = {}
        self._config[table_name]["visible_columns"] = list(columns)
        self._save_config()
    
    def get_column_width(self, table_name: str, column_name: str) -> Optional[int]:
        """获取指定列的宽度"""
        table_config = self._config.get(table_name, {})
        widths = table_config.get("column_widths", {})
        return widths.get(column_name)
    
    def set_column_width(self, table_name: str, column_name: str, width: int):
        """设置指定列的宽度"""
        if table_name not in self._config:
            self._config[table_name] = {}
        if "column_widths" not in self._config[table_name]:
            self._config[table_name]["column_widths"] = {}
        self._config[table_name]["column_widths"][column_name] = width
        self._save_config()
    
    def toggle_column_visibility(self, table_name: str, column_name: str, all_columns: List[str]) -> List[str]:
        """切换列可见性"""
        visible = self.get_visible_columns(table_name)
        
        if not visible:
            visible = list(all_columns)
        
        if column_name in visible:
            if len(visible) > 1:
                visible.remove(column_name)
        else:
            visible.append(column_name)
        
        self.set_visible_columns(table_name, visible)
        return visible
    
    def move_column(self, table_name: str, column_name: str, new_index: int) -> List[str]:
        """移动列到新位置"""
        visible = self.get_visible_columns(table_name)
        
        if column_name in visible:
            old_index = visible.index(column_name)
            visible.pop(old_index)
            new_index = min(new_index, len(visible))
            visible.insert(new_index, column_name)
            self.set_visible_columns(table_name, visible)
        
        return visible
    
    def reset_to_default(self, table_name: str) -> List[str]:
        """重置为默认配置"""
        if table_name in self.DEFAULT_CONFIG:
            self._config[table_name] = self.DEFAULT_CONFIG[table_name].copy()
            self._save_config()
            return list(self._config[table_name].get("visible_columns", []))
        return []


def get_column_config() -> ColumnConfigManager:
    """获取列配置管理器实例"""
    return ColumnConfigManager()
