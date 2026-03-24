#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DuckDB数据库模块
使用DuckDB作为分析数据库，支持高效的批量导入
"""

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False
    print("警告: DuckDB未安装，请运行: pip install duckdb")


class DuckDBDatabase:
    """DuckDB数据库管理类"""
    
    def __init__(self, db_path: str = None):
        if not HAS_DUCKDB:
            raise ImportError("DuckDB未安装，请运行: pip install duckdb")
        
        if db_path is None:
            db_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(db_dir, "..", "products.duckdb")
        
        self.db_path = os.path.abspath(db_path)
        self.conn = None
        self._connect()
        self._init_database()
    
    def _connect(self):
        """连接数据库"""
        self.conn = duckdb.connect(self.db_path)
    
    def _init_database(self):
        """初始化数据库表结构"""
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                product_id VARCHAR UNIQUE NOT NULL,
                shop_product_id VARCHAR,
                output_path VARCHAR,
                title VARCHAR,
                status VARCHAR DEFAULT 'pending',
                resource_counts VARCHAR,
                cost_prices VARCHAR,
                selling_prices VARCHAR,
                platform VARCHAR DEFAULT 'alibaba',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY,
                product_id VARCHAR NOT NULL,
                resource_type VARCHAR NOT NULL,
                resource_url VARCHAR NOT NULL,
                resource_name VARCHAR,
                output_filename VARCHAR,
                downloaded BOOLEAN DEFAULT FALSE,
                download_time TIMESTAMP,
                file_size BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS sku_prices (
                id INTEGER PRIMARY KEY,
                product_id VARCHAR NOT NULL,
                sku_name VARCHAR,
                price DOUBLE,
                original_price DOUBLE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.execute('''
            CREATE SEQUENCE IF NOT EXISTS products_id_seq
        ''')
        self.conn.execute('''
            CREATE SEQUENCE IF NOT EXISTS resources_id_seq
        ''')
        self.conn.execute('''
            CREATE SEQUENCE IF NOT EXISTS sku_prices_id_seq
        ''')
        
        self.conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_products_product_id ON products(product_id)
        ''')
        self.conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_resources_product_id ON resources(product_id)
        ''')
        self.conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_resources_downloaded ON resources(downloaded)
        ''')
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def get_product(self, product_id: str) -> Optional[Dict]:
        """获取单个商品"""
        result = self.conn.execute(
            'SELECT * FROM products WHERE product_id = ?', [product_id]
        ).fetchone()
        if result:
            columns = [desc[0] for desc in self.conn.execute(
                'SELECT * FROM products WHERE product_id = ?', [product_id]
            ).description]
            return dict(zip(columns, result))
        return None
    
    def insert_product(self, data: Dict) -> int:
        """插入商品"""
        result = self.conn.execute("SELECT nextval('products_id_seq')")
        data['id'] = result.fetchone()[0]
        
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        sql = f"INSERT INTO products ({columns}) VALUES ({placeholders}) RETURNING id"
        result = self.conn.execute(sql, list(data.values()))
        return result.fetchone()[0]
    
    def update_product(self, data: Dict, product_id: str):
        """更新商品"""
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        sql = f"UPDATE products SET {set_clause} WHERE product_id = ?"
        self.conn.execute(sql, list(data.values()) + [product_id])
    
    def insert_resource(self, data: Dict) -> int:
        """插入资源"""
        result = self.conn.execute("SELECT nextval('resources_id_seq')")
        data['id'] = result.fetchone()[0]
        
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        sql = f"INSERT INTO resources ({columns}) VALUES ({placeholders}) RETURNING id"
        result = self.conn.execute(sql, list(data.values()))
        return result.fetchone()[0]
    
    def insert_sku_price(self, data: Dict) -> int:
        """插入SKU价格"""
        result = self.conn.execute("SELECT nextval('sku_prices_id_seq')")
        data['id'] = result.fetchone()[0]
        
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        sql = f"INSERT INTO sku_prices ({columns}) VALUES ({placeholders}) RETURNING id"
        result = self.conn.execute(sql, list(data.values()))
        return result.fetchone()[0]
    
    def get_all_products(self) -> List[Dict]:
        """获取所有商品"""
        result = self.conn.execute('SELECT * FROM products ORDER BY created_at DESC')
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    
    def search_products_by_id(self, search_term: str) -> List[Dict]:
        """搜索商品"""
        result = self.conn.execute(
            'SELECT * FROM products WHERE product_id = ? OR shop_product_id = ?',
            [search_term, search_term]
        )
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    
    def delete_product(self, product_id: str) -> bool:
        """删除商品"""
        self.conn.execute('DELETE FROM resources WHERE product_id = ?', [product_id])
        self.conn.execute('DELETE FROM products WHERE product_id = ?', [product_id])
        return True
    
    def update_shop_product_id(self, product_id: str, shop_product_id: str, output_path: str = None):
        """更新店铺商品ID"""
        existing = self.get_product(product_id)
        if existing:
            data = {'shop_product_id': shop_product_id}
            if output_path:
                data['output_path'] = output_path
            self.update_product(data, product_id)
        else:
            self.insert_product({
                'product_id': product_id,
                'shop_product_id': shop_product_id,
                'output_path': output_path,
                'status': 'pending'
            })
    
    def get_download_stats(self, product_id: str = None) -> Dict:
        """获取下载统计"""
        if product_id:
            result = self.conn.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN downloaded THEN 1 ELSE 0 END) as completed,
                    COUNT(*) - SUM(CASE WHEN downloaded THEN 1 ELSE 0 END) as pending
                FROM resources WHERE product_id = ?
            ''', [product_id])
        else:
            result = self.conn.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN downloaded THEN 1 ELSE 0 END) as completed,
                    COUNT(*) - SUM(CASE WHEN downloaded THEN 1 ELSE 0 END) as pending
                FROM resources
            ''')
        
        row = result.fetchone()
        if row:
            return {'total': row[0], 'completed': row[1], 'pending': row[2]}
        return {'total': 0, 'completed': 0, 'pending': 0}


def get_duckdb() -> Optional[DuckDBDatabase]:
    """获取DuckDB连接"""
    if not HAS_DUCKDB:
        return None
    return DuckDBDatabase()


def import_pending_data():
    """批量导入临时数据到DuckDB"""
    from utils.temp_storage import (
        get_pending_resources, get_pending_prices, get_pending_counts,
        clear_pending_data, has_pending_data
    )
    
    if not has_pending_data():
        print("没有待导入的数据")
        return 0
    
    db = get_duckdb()
    if not db:
        print("DuckDB未安装")
        return 0
    
    total_imported = 0
    
    from config import FILE_NAMING
    
    # 导入资源数据
    resources_data = get_pending_resources()
    for item in resources_data:
        product_id = item['product_id']
        output_path = None
        
        # 从 counts 数据获取 output_path
        counts_data = get_pending_counts()
        for c in counts_data:
            if c['product_id'] == product_id:
                output_path = c.get('output_path')
                break
        
        for idx, (url, name) in enumerate(item.get('main_images', [])):
            filename = f"{FILE_NAMING['main_image_prefix']}{name}.jpg"
            filepath = os.path.join(output_path, filename) if output_path else None
            downloaded = filepath and os.path.exists(filepath)
            file_size = os.path.getsize(filepath) if downloaded else 0
            
            db.insert_resource({
                'product_id': product_id,
                'resource_type': 'main_image',
                'resource_url': url,
                'resource_name': name,
                'output_filename': filename,
                'downloaded': downloaded,
                'file_size': file_size if file_size > 0 else None
            })
        
        for idx, (url, name) in enumerate(item.get('color_images', [])):
            filename = f"{FILE_NAMING['color_option_prefix']}{name}.jpg"
            filepath = os.path.join(output_path, filename) if output_path else None
            downloaded = filepath and os.path.exists(filepath)
            file_size = os.path.getsize(filepath) if downloaded else 0
            
            db.insert_resource({
                'product_id': product_id,
                'resource_type': 'color_image',
                'resource_url': url,
                'resource_name': name,
                'output_filename': filename,
                'downloaded': downloaded,
                'file_size': file_size if file_size > 0 else None
            })
        
        for idx, url in enumerate(item.get('detail_images', [])):
            filename = f"{FILE_NAMING['detail_image_prefix']}{idx+1}.jpg"
            filepath = os.path.join(output_path, filename) if output_path else None
            downloaded = filepath and os.path.exists(filepath)
            file_size = os.path.getsize(filepath) if downloaded else 0
            
            db.insert_resource({
                'product_id': product_id,
                'resource_type': 'detail_image',
                'resource_url': url,
                'resource_name': f'detail_{idx+1}',
                'output_filename': filename,
                'downloaded': downloaded,
                'file_size': file_size if file_size > 0 else None
            })
        
        for idx, url in enumerate(item.get('videos', [])):
            filename = f"{FILE_NAMING['video_prefix']}{idx+1}.mp4"
            filepath = os.path.join(output_path, filename) if output_path else None
            downloaded = filepath and os.path.exists(filepath)
            file_size = os.path.getsize(filepath) if downloaded else 0
            
            db.insert_resource({
                'product_id': product_id,
                'resource_type': 'video',
                'resource_url': url,
                'resource_name': f'video_{idx+1}',
                'output_filename': filename,
                'downloaded': downloaded,
                'file_size': file_size if file_size > 0 else None
            })
        
        total_imported += 1
    
    # 导入价格数据
    prices_data = get_pending_prices()
    for item in prices_data:
        product_id = item['product_id']
        prices = item.get('prices', {})
        
        if prices.get('sku_prices'):
            for sku in prices['sku_prices']:
                db.insert_sku_price({
                    'product_id': product_id,
                    'sku_name': sku.get('name', ''),
                    'price': sku.get('price', 0),
                    'original_price': sku.get('original_price')
                })
        
        total_imported += 1
    
    # 导入资源计数数据
    counts_data = get_pending_counts()
    for item in counts_data:
        product_id = item['product_id']
        counts = item.get('resource_counts', [0, 0, 0, 0])
        output_path = item.get('output_path')
        platform = item.get('platform', 'alibaba')
        
        existing = db.get_product(product_id)
        if existing:
            db.update_product({
                'resource_counts': json.dumps(counts),
                'output_path': output_path,
                'platform': platform,
                'status': 'completed'
            }, product_id)
        else:
            db.insert_product({
                'product_id': product_id,
                'resource_counts': json.dumps(counts),
                'output_path': output_path,
                'platform': platform,
                'status': 'completed'
            })
        
        total_imported += 1
    
    # 清空临时数据
    clear_pending_data()
    
    db.close()
    
    print(f"批量导入完成: {total_imported} 条记录")
    return total_imported
