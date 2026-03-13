#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶梯价格生成器
功能：根据产品配置的成本和最高配置的目标价格，生成阶梯价格
"""

import json
import os
from typing import List, Dict, Any


class TieredPriceGenerator:
    """阶梯价格生成器类"""
    
    def __init__(self):
        self.configurations = []
        self.highest_target_price = 0
    
    def add_configuration(self, name: str, total_cost: float):
        """添加产品配置
        
        Args:
            name: 配置名称
            total_cost: 总成本
        """
        self.configurations.append({
            'name': name,
            'total_cost': total_cost
        })
    
    def set_highest_target_price(self, price: float):
        """设置最高配置的目标价格
        
        Args:
            price: 目标价格
        """
        self.highest_target_price = price
    
    def calculate_tiered_prices(self, rounding: int = 0, strategy: str = 'multiplier') -> List[Dict[str, Any]]:
        """计算阶梯价格
        
        Args:
            rounding: 价格保留小数位数，0表示整数
            strategy: 定价策略，'multiplier'表示统一倍率，'margin'表示统一利润率
            
        Returns:
            包含阶梯价格的配置列表
            
        Raises:
            ValueError: 配置无效时抛出
        """
        if not self.configurations:
            raise ValueError("请先添加产品配置")
        
        if self.highest_target_price <= 0:
            raise ValueError("请设置有效的最高目标价格")
        
        sorted_configs = sorted(self.configurations, key=lambda x: x['total_cost'])
        highest_cost = sorted_configs[-1]['total_cost']
        
        if strategy == 'multiplier':
            factor = self.highest_target_price / highest_cost
        elif strategy == 'margin':
            margin_rate = (self.highest_target_price - highest_cost) / highest_cost
            factor = 1 + margin_rate
        else:
            raise ValueError(f"不支持的定价策略：{strategy}")
        
        result = []
        for config in sorted_configs:
            target_price = round(config['total_cost'] * factor, rounding)
            profit = target_price - config['total_cost']
            profit_rate = (profit / config['total_cost']) * 100 if config['total_cost'] > 0 else 0
            
            result.append({
                'name': config['name'],
                'total_cost': config['total_cost'],
                'target_price': target_price,
                'profit': round(profit, 2),
                'profit_rate': round(profit_rate, 2),
                'factor': round(factor, 4)
            })
        
        return result
    
    def load_from_json_file(self, file_path: str):
        """从JSON文件加载配置
        
        Args:
            file_path: JSON文件路径
            
        Raises:
            FileNotFoundError: 文件不存在时抛出
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在：{file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.configurations = data.get('configurations', [])
        self.highest_target_price = data.get('highest_target_price', 0)
    
    def save_to_json_file(self, file_path: str):
        """将配置保存为JSON文件
        
        Args:
            file_path: 保存路径
        """
        data = {
            'configurations': self.configurations,
            'highest_target_price': self.highest_target_price
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def clear(self):
        """清空所有配置"""
        self.configurations = []
        self.highest_target_price = 0
