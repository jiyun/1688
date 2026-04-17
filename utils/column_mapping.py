import json
import os
from typing import Dict, List, Optional, Any
from pathlib import Path
from utils.config_manager import get_config_manager


class ColumnMappingConfig:
    """列映射配置管理器"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self._load_config()
    
    def _load_config(self):
        self._config = get_config_manager().get_json_config("column_mapping")
        if not self._config:
            self._config = self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "export_types": {
                "full_shop": {
                    "name": "全店导出",
                    "file_pattern": "1688采购助手-全店导出-*.xlsx",
                    "columns": {}
                },
                "product_list": {
                    "name": "商品列表导出",
                    "file_pattern": "商品列表-1688采购助手*.xlsx",
                    "columns": {}
                }
            },
            "column_aliases": {},
            "data_types": {},
            "special_markers": {}
        }
    
    def get_export_type(self, filename: str) -> Optional[str]:
        """根据文件名判断导出类型"""
        import fnmatch
        
        for type_key, type_info in self._config.get("export_types", {}).items():
            pattern = type_info.get("file_pattern", "")
            if fnmatch.fnmatch(filename, pattern):
                return type_key
        
        return None
    
    def get_column_mapping(self, export_type: str) -> Dict[str, Dict]:
        """获取指定导出类型的列映射"""
        type_info = self._config.get("export_types", {}).get(export_type, {})
        return type_info.get("columns", {})
    
    def get_target_column(self, export_type: str, source_column: str) -> Optional[str]:
        """获取源列名对应的目标列名"""
        columns = self.get_column_mapping(export_type)
        col_info = columns.get(source_column, {})
        return col_info.get("target")
    
    def get_column_type(self, export_type: str, source_column: str) -> str:
        """获取列的数据类型（product/shop/meta）"""
        columns = self.get_column_mapping(export_type)
        col_info = columns.get(source_column, {})
        return col_info.get("type", "product")
    
    def get_product_columns(self, export_type: str) -> List[str]:
        """获取商品属性列列表"""
        columns = self.get_column_mapping(export_type)
        return [col for col, info in columns.items() if info.get("type") == "product"]
    
    def get_shop_columns(self, export_type: str) -> List[str]:
        """获取店铺属性列列表"""
        columns = self.get_column_mapping(export_type)
        return [col for col, info in columns.items() if info.get("type") == "shop"]
    
    def get_all_target_columns(self) -> List[str]:
        """获取所有目标列名（去重）"""
        targets = set()
        for type_info in self._config.get("export_types", {}).values():
            for col_info in type_info.get("columns", {}).values():
                target = col_info.get("target")
                if target:
                    targets.add(target)
        return list(targets)
    
    def map_excel_row(self, export_type: str, row: Dict, include_shop_data: bool = True) -> tuple:
        """
        将Excel行数据映射为目标格式
        
        Returns:
            (product_data, shop_data) 元组
        """
        columns = self.get_column_mapping(export_type)
        
        product_data = {}
        shop_data = {}
        
        for source_col, value in row.items():
            col_info = columns.get(source_col, {})
            target = col_info.get("target")
            col_type = col_info.get("type", "product")
            
            if target and value is not None:
                if col_type == "shop":
                    shop_data[target] = value
                elif col_type != "meta":
                    product_data[target] = value
        
        if not include_shop_data:
            return product_data
        
        return product_data, shop_data
    
    def get_special_marker(self, marker_name: str) -> Optional[Dict]:
        """获取特殊标记配置"""
        return self._config.get("special_markers", {}).get(marker_name)
    
    def reload(self):
        get_config_manager().invalidate("column_mapping")
        self._config = None
        self._load_config()


def get_column_mapping_config() -> ColumnMappingConfig:
    """获取列映射配置实例"""
    return ColumnMappingConfig()
