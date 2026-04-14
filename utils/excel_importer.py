#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel导入模块 - 导入1688采购助手导出的商品数据
支持两种导出格式：全店导出和商品列表导出
"""

import os
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    from utils.logger import log_info, log_error, log_warning, log_success
    HAS_LOGGER = True
except ImportError:
    HAS_LOGGER = False
    def log_info(msg): print(f"[INFO] {msg}")
    def log_error(msg): print(f"[ERROR] {msg}")
    def log_warning(msg): print(f"[WARNING] {msg}")
    def log_success(msg): print(f"[SUCCESS] {msg}")


FULL_SHOP_MAPPING = {
    '序号': 'seq_no',
    '商品标题': 'title',
    '宝贝ID': 'product_id',
    '宝贝链接': 'product_url',
    '图片地址': 'main_image',
    '价格': 'price',
    '代发价': 'dropship_price',
    '销量': 'sales_count',
    '评论数': 'review_count',
    '月成交笔数': 'monthly_orders',
    '月代销': 'monthly_dropship',
    '发货时间': 'ship_time',
    '上架时间': 'list_time',
    '类目': 'category',
    '标签': 'tags',
}

PRODUCT_LIST_MAPPING = {
    '标题': 'title',
    '主图链接': 'main_image',
    '主图': 'main_image_thumb',
    '商品ID': 'product_id',
    '商品链接': 'product_url',
    '类目': 'category',
    '价格': 'price',
    '年销售件数': 'yearly_sales_qty',
    '年销售笔数': 'yearly_orders',
    '复购率': 'repurchase_rate',
    '上架时间': 'list_time',
    '月代销': 'monthly_dropship',
    '销售标签': 'sales_tags',
    '属性标签': 'attr_tags',
    '服务标签': 'service_tags',
    '48h揽收率': 'pickup_rate_48h',
    '支持面单': 'support_waybill',
    '综合服务': 'service_score',
    '采购咨询': 'consult_score',
    '采 购咨询': 'consult_score',
    '退换体验': 'return_score',
    '品质体验': 'quality_score',
    '纠纷解决': 'dispute_score',
    '物流时效': 'logistics_score',
    '店铺名称': 'shop_name',
    '店铺链接': 'shop_url',
    '所在地': 'location',
    '开店时长': 'shop_age',
}


def detect_export_type(file_path: str) -> str:
    """检测Excel文件的导出类型
    
    Args:
        file_path: Excel文件路径
        
    Returns:
        'full_shop' - 全店导出
        'product_list' - 商品列表导出
        'unknown' - 未知类型
    """
    filename = os.path.basename(file_path)
    
    if '全店导出' in filename or filename.startswith('1688采购助手-全店导出'):
        return 'full_shop'
    
    if '商品列表' in filename or filename.startswith('商品列表-1688采购助手'):
        return 'product_list'
    
    if not HAS_PANDAS:
        return 'unknown'
    
    try:
        df = pd.read_excel(file_path, engine='openpyxl', nrows=1)
        columns = [str(col).strip() for col in df.columns]
        
        full_shop_cols = set(FULL_SHOP_MAPPING.keys())
        product_list_cols = set(PRODUCT_LIST_MAPPING.keys())
        
        full_shop_match = len(set(columns) & full_shop_cols)
        product_list_match = len(set(columns) & product_list_cols)
        
        if full_shop_match > product_list_match:
            return 'full_shop'
        elif product_list_match > 0:
            return 'product_list'
        
        if '宝贝ID' in columns or '宝贝链接' in columns:
            return 'full_shop'
        if '商品ID' in columns and '店铺名称' in columns:
            return 'product_list'
            
    except Exception as e:
        log_warning(f"检测导出类型失败: {e}")
    
    return 'unknown'


def get_column_mapping(export_type: str) -> Dict[str, str]:
    """获取指定导出类型的列映射"""
    if export_type == 'full_shop':
        return FULL_SHOP_MAPPING
    elif export_type == 'product_list':
        return PRODUCT_LIST_MAPPING
    return {}


def parse_excel_file(file_path: str, export_type: str = None) -> Tuple[List[Dict], List[str], Dict]:
    """解析1688采购助手导出的Excel文件
    
    Args:
        file_path: Excel文件路径
        export_type: 导出类型（可选，自动检测）
        
    Returns:
        (商品数据列表, 错误消息列表, 店铺数据字典)
    """
    if not HAS_PANDAS:
        return [], ["pandas库未安装，请运行: pip install pandas openpyxl"], {}
    
    if not os.path.exists(file_path):
        return [], [f"文件不存在: {file_path}"], {}
    
    errors = []
    products = []
    shop_data = {}
    
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        
        if df.empty:
            return [], ["Excel文件为空"], {}
        
        if export_type is None:
            export_type = detect_export_type(file_path)
        
        column_mapping = get_column_mapping(export_type)
        
        if not column_mapping:
            return [], [f"未知的导出类型: {export_type}"], {}
        
        normalized_mapping = {}
        for key, value in column_mapping.items():
            normalized_mapping[key.replace(' ', '')] = value
            normalized_mapping[key] = value
        
        actual_columns = {}
        for col in df.columns:
            col_str = str(col).strip()
            col_normalized = col_str.replace(' ', '')
            if col_str in column_mapping:
                actual_columns[col] = column_mapping[col_str]
            elif col_normalized in normalized_mapping:
                actual_columns[col] = normalized_mapping[col_normalized]
        
        if 'product_id' not in actual_columns.values():
            for col in df.columns:
                col_str = str(col).strip()
                if 'ID' in col_str.upper() or 'id' in col_str:
                    actual_columns[col] = 'product_id'
                    break
        
        if not actual_columns:
            return [], [f"未找到有效列，可用列: {list(df.columns)}"], {}
        
        df_renamed = df.rename(columns=actual_columns)
        
        shop_columns = ['shop_name', 'shop_url', 'location', 'shop_age',
                       'pickup_rate_48h', 'support_waybill', 'service_score',
                       'consult_score', 'return_score', 'quality_score',
                       'dispute_score', 'logistics_score']
        
        for idx, row in df_renamed.iterrows():
            try:
                product_id = str(row.get('product_id', '')).strip()
                
                if not product_id or product_id == 'nan':
                    continue
                
                if not product_id.isdigit():
                    continue
                
                product = {
                    'product_id': product_id,
                    'title': _safe_str(row.get('title', '')),
                    'product_url': _safe_str(row.get('product_url', '')),
                    'main_image': _safe_str(row.get('main_image', '')),
                    'price': _safe_float(row.get('price')),
                    'dropship_price': _safe_float(row.get('dropship_price')),
                    'sales_count': _safe_int(row.get('sales_count')),
                    'yearly_sales_qty': _safe_int(row.get('yearly_sales_qty')),
                    'monthly_orders': _safe_int(row.get('monthly_orders')),
                    'yearly_orders': _safe_int(row.get('yearly_orders')),
                    'monthly_dropship': _safe_int(row.get('monthly_dropship')),
                    'review_count': _safe_int(row.get('review_count')),
                    'repurchase_rate': _safe_float(row.get('repurchase_rate')),
                    'ship_time': _safe_str(row.get('ship_time', '')),
                    'list_time': _safe_str(row.get('list_time', '')),
                    'category': _safe_str(row.get('category', '')),
                    'tags': _safe_str(row.get('tags', '')),
                    'sales_tags': _safe_str(row.get('sales_tags', '')),
                    'attr_tags': _safe_str(row.get('attr_tags', '')),
                    'service_tags': _safe_str(row.get('service_tags', '')),
                    'source_file': os.path.basename(file_path),
                    'import_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                }
                
                products.append(product)
                
                if not shop_data.get('shop_name'):
                    for shop_col in shop_columns:
                        if shop_col in row and not pd.isna(row.get(shop_col)):
                            shop_data[shop_col] = _safe_str(row.get(shop_col))
                
            except Exception as e:
                errors.append(f"第{idx+2}行解析错误: {e}")
        
        log_info(f"解析完成: {len(products)} 条商品数据, 导出类型: {export_type}")
        
    except Exception as e:
        errors.append(f"读取Excel文件失败: {e}")
        log_error(f"读取Excel文件失败: {e}")
    
    return products, errors, shop_data


def _safe_str(value) -> str:
    """安全转换为字符串"""
    if pd.isna(value):
        return ''
    return str(value).strip()


def _safe_float(value) -> Optional[float]:
    """安全转换为浮点数"""
    if pd.isna(value):
        return None
    try:
        s = str(value).replace('¥', '').replace('￥', '').replace(',', '').replace('%', '').strip()
        if s:
            return float(s)
    except (ValueError, TypeError):
        pass
    return None


def _safe_int(value) -> int:
    """安全转换为整数"""
    if pd.isna(value):
        return 0
    try:
        s = str(value).replace(',', '').strip()
        if s:
            return int(float(s))
    except (ValueError, TypeError):
        pass
    return 0


def import_to_database(products: List[Dict], db, shop_id: str = None, shop_name: str = None, 
                       support_dropship: int = None) -> Tuple[int, List[str]]:
    """将商品数据导入数据库
    
    Args:
        products: 商品数据列表
        db: 数据库连接
        shop_id: 店铺ID（可选）
        shop_name: 店铺名称（可选）
        support_dropship: 一件代发支持标记（可选）
        
    Returns:
        (导入数量, 错误消息列表)
    """
    if not products:
        return 0, ["没有商品数据需要导入"]
    
    errors = []
    imported = 0
    
    for product in products:
        try:
            product_id = product.get('product_id')
            if not product_id:
                continue
            
            shop_product_data = {
                'shop_id': shop_id if shop_id else '',
                'product_id': product_id,
                'title': product.get('title'),
                'price': product.get('price'),
                'dropship_price': product.get('dropship_price'),
                'main_image': product.get('main_image'),
                'product_url': product.get('product_url'),
                'category': product.get('category'),
                'sales_count': product.get('sales_count', 0),
                'yearly_sales_qty': product.get('yearly_sales_qty', 0),
                'monthly_orders': product.get('monthly_orders', 0),
                'yearly_orders': product.get('yearly_orders', 0),
                'monthly_dropship': product.get('monthly_dropship', 0),
                'review_count': product.get('review_count', 0),
                'repurchase_rate': product.get('repurchase_rate'),
                'ship_time': product.get('ship_time'),
                'list_time': product.get('list_time'),
                'tags': product.get('tags'),
                'sales_tags': product.get('sales_tags'),
                'attr_tags': product.get('attr_tags'),
                'service_tags': product.get('service_tags'),
                'shop_name': shop_name or product.get('shop_name'),
                'platform': 'alibaba',
            }
            
            if support_dropship is not None:
                shop_product_data['support_dropship'] = support_dropship
            
            if shop_id:
                db.save_shop_product(shop_id, shop_product_data)
            else:
                from datetime import datetime
                existing_shop_product = db.query_one(
                    "SELECT id FROM shop_products WHERE product_id = ?",
                    [product_id]
                )
                
                if existing_shop_product:
                    shop_product_data['updated_at'] = datetime.now()
                    db.update('shop_products', shop_product_data, 'product_id = ?', [product_id])
                else:
                    shop_product_data['collect_time'] = datetime.now()
                    db.insert('shop_products', shop_product_data)
            
            imported += 1
            
        except Exception as e:
            errors.append(f"导入商品 {product.get('product_id', '未知')} 失败: {e}")
    
    log_success(f"导入完成: {imported}/{len(products)} 条商品数据")
    return imported, errors


def mark_dropship_support(db, product_ids: List[str], shop_id: str = None):
    """标记商品的一件代发支持状态
    
    Args:
        db: 数据库连接
        product_ids: 支持一件代发的商品ID列表
        shop_id: 店铺ID（可选，用于限定范围）
    """
    if not product_ids:
        return
    
    try:
        if shop_id:
            db.conn.execute(
                "UPDATE shop_products SET support_dropship = 0 WHERE shop_id = ? AND support_dropship IS NULL",
                [shop_id]
            )
            
            placeholders = ','.join(['?' for _ in product_ids])
            db.conn.execute(
                f"UPDATE shop_products SET support_dropship = 1 WHERE shop_id = ? AND product_id IN ({placeholders})",
                [shop_id] + product_ids
            )
        else:
            db.conn.execute(
                "UPDATE shop_products SET support_dropship = 0 WHERE support_dropship IS NULL"
            )
            
            placeholders = ','.join(['?' for _ in product_ids])
            db.conn.execute(
                f"UPDATE shop_products SET support_dropship = 1 WHERE product_id IN ({placeholders})",
                product_ids
            )
        
        db.conn.execute('CHECKPOINT')
        log_success(f"已标记 {len(product_ids)} 个商品支持一件代发")
        
    except Exception as e:
        log_error(f"标记一件代发状态失败: {e}")


def get_excel_preview(file_path: str, max_rows: int = 10) -> Tuple[List[str], List[List], int, str]:
    """获取Excel文件预览
    
    Args:
        file_path: Excel文件路径
        max_rows: 最大预览行数
        
    Returns:
        (列名列表, 数据行列表, 总行数, 导出类型)
    """
    if not HAS_PANDAS:
        return [], [], 0, 'unknown'
    
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        
        columns = [str(col) for col in df.columns]
        
        preview_rows = []
        for _, row in df.head(max_rows).iterrows():
            row_data = [_safe_str(v) for v in row.values]
            preview_rows.append(row_data)
        
        export_type = detect_export_type(file_path)
        
        return columns, preview_rows, len(df), export_type
        
    except Exception as e:
        log_error(f"预览Excel文件失败: {e}")
        return [], [], 0, 'unknown'
