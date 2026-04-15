import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path


class ColumnConfigManager:
    """通用列配置管理器
    
    管理数据库页面的列可见性、顺序、宽度等配置
    支持自动保存和加载
    """
    
    _instance = None
    _config = None
    _config_path = None
    
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
    
    def _get_config_path(self) -> Path:
        if self._config_path is None:
            self._config_path = Path(__file__).parent.parent / "config" / "column_config.json"
        return self._config_path
    
    def _load_config(self):
        config_path = self._get_config_path()
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                for key, value in self.DEFAULT_CONFIG.items():
                    if key not in self._config:
                        self._config[key] = value.copy()
            except Exception as e:
                print(f"加载列配置失败: {e}")
                self._config = self.DEFAULT_CONFIG.copy()
        else:
            self._config = {}
            for key, value in self.DEFAULT_CONFIG.items():
                self._config[key] = value.copy()
    
    def _save_config(self):
        config_path = self._get_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存列配置失败: {e}")
    
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
