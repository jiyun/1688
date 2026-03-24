#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库模块 - SQLite版本
使用SQLite作为嵌入式数据库，支持多进程访问
"""

import os
import json
import sqlite3
from typing import Dict, List, Optional, Any
from datetime import datetime

HAS_SQLITE = True


class Database:
    """SQLite数据库管理类"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(db_dir, "..", "products.db")
        
        self.db_path = os.path.abspath(db_path)
        self.conn = None
        self._connect()
        self._init_database()
    
    def _connect(self):
        """连接数据库"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
    
    def _init_database(self):
        """初始化数据库表结构"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT UNIQUE NOT NULL,
                shop_product_id TEXT,
                output_path TEXT,
                title TEXT,
                status TEXT DEFAULT 'pending',
                resource_counts TEXT,
                cost_prices TEXT,
                selling_prices TEXT,
                platform TEXT DEFAULT 'alibaba',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_url TEXT NOT NULL,
                resource_name TEXT,
                output_filename TEXT,
                downloaded INTEGER DEFAULT 0,
                download_time TIMESTAMP,
                file_size INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sku_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                sku_name TEXT,
                price REAL,
                original_price REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pricing (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                cost_price REAL,
                selling_price REAL,
                profit_margin REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_products_product_id ON products(product_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_products_shop_product_id ON products(shop_product_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_resources_product_id ON resources(product_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_resources_type ON resources(resource_type)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_resources_downloaded ON resources(downloaded)
        ''')
        
        self.conn.commit()
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def execute(self, sql: str, params: tuple = None) -> Any:
        """执行SQL语句"""
        cursor = self.conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        self.conn.commit()
        return cursor
    
    def query(self, sql: str, params: tuple = None) -> List[Dict]:
        """查询并返回字典列表"""
        cursor = self.conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    
    def query_one(self, sql: str, params: tuple = None) -> Optional[Dict]:
        """查询单条记录"""
        results = self.query(sql, params)
        return results[0] if results else None
    
    def insert(self, table: str, data: Dict) -> int:
        """插入数据并返回ID"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        cursor = self.conn.cursor()
        cursor.execute(sql, list(data.values()))
        self.conn.commit()
        return cursor.lastrowid
    
    def update(self, table: str, data: Dict, where: str, where_params: tuple = None):
        """更新数据"""
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
        params = list(data.values()) + (list(where_params) if where_params else [])
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        self.conn.commit()
    
    def delete(self, table: str, where: str, where_params: tuple = None):
        """删除数据"""
        sql = f"DELETE FROM {table} WHERE {where}"
        cursor = self.conn.cursor()
        if where_params:
            cursor.execute(sql, where_params)
        else:
            cursor.execute(sql)
        self.conn.commit()
    
    def search_products(self, search_term: str, search_field: str = 'product_id') -> List[Dict]:
        """搜索商品记录"""
        if not search_term:
            return []
        
        if search_field not in ('product_id', 'shop_product_id'):
            search_field = 'product_id'
        
        return self.query(f'''
            SELECT * FROM products WHERE {search_field} = ?
        ''', (search_term,))
    
    def search_products_by_id(self, search_term: str) -> List[Dict]:
        """自动匹配商品ID和DSID搜索"""
        if not search_term:
            return []
        
        return self.query('''
            SELECT * FROM products WHERE product_id = ? OR shop_product_id = ?
        ''', (search_term, search_term))
    
    def get_product(self, product_id: str) -> Optional[Dict]:
        """获取单个商品"""
        return self.query_one('''
            SELECT * FROM products WHERE product_id = ?
        ''', (product_id,))
    
    def get_all_products(self) -> List[Dict]:
        """获取所有商品"""
        return self.query('''
            SELECT * FROM products ORDER BY created_at DESC
        ''')
    
    def update_shop_product_id(self, product_id: str, shop_product_id: str, output_path: str = None) -> bool:
        """更新或插入商品"""
        existing = self.get_product(product_id)
        
        if existing:
            update_data = {
                'shop_product_id': shop_product_id,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            if output_path:
                update_data['output_path'] = output_path
            self.update('products', update_data, 'product_id = ?', (product_id,))
        else:
            self.insert('products', {
                'product_id': product_id,
                'shop_product_id': shop_product_id,
                'output_path': output_path,
                'status': 'pending'
            })
        
        return True
    
    def update_output_path(self, product_id: str, output_path: str) -> bool:
        """更新输出路径"""
        existing = self.get_product(product_id)
        
        if existing:
            self.update('products', {
                'output_path': output_path,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }, 'product_id = ?', (product_id,))
        else:
            self.insert('products', {
                'product_id': product_id,
                'output_path': output_path,
                'status': 'pending'
            })
        
        return True
    
    def update_resource_counts(self, product_id: str, main_images: int, color_images: int, 
                               detail_images: int, videos: int, output_path: str = None, 
                               platform: str = 'alibaba') -> bool:
        """更新资源计数"""
        resource_counts = json.dumps([main_images, color_images, detail_images, videos])
        
        existing = self.get_product(product_id)
        
        if existing:
            update_data = {
                'resource_counts': resource_counts,
                'platform': platform,
                'status': 'completed',
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            if output_path:
                update_data['output_path'] = output_path
            self.update('products', update_data, 'product_id = ?', (product_id,))
        else:
            self.insert('products', {
                'product_id': product_id,
                'resource_counts': resource_counts,
                'output_path': output_path,
                'platform': platform,
                'status': 'completed'
            })
        
        return True
    
    def get_resource_counts(self, product_id: str) -> Optional[List[int]]:
        """获取资源计数"""
        product = self.get_product(product_id)
        if product and product.get('resource_counts'):
            try:
                return json.loads(product['resource_counts'])
            except:
                pass
        return None
    
    def save_resources(self, product_id: str, main_images: List, color_images: List, 
                       detail_images: List, videos: List) -> bool:
        """保存资源URL到数据库"""
        try:
            for idx, (url, name) in enumerate(main_images):
                self.insert('resources', {
                    'product_id': product_id,
                    'resource_type': 'main_image',
                    'resource_url': url,
                    'resource_name': name,
                    'output_filename': f'main_{name}.jpg'
                })
            
            for idx, (url, name) in enumerate(color_images):
                self.insert('resources', {
                    'product_id': product_id,
                    'resource_type': 'color_image',
                    'resource_url': url,
                    'resource_name': name,
                    'output_filename': f'color_{name}.jpg'
                })
            
            for idx, url in enumerate(detail_images):
                self.insert('resources', {
                    'product_id': product_id,
                    'resource_type': 'detail_image',
                    'resource_url': url,
                    'resource_name': f'detail_{idx+1}',
                    'output_filename': f'detail_{idx+1}.jpg'
                })
            
            for idx, url in enumerate(videos):
                self.insert('resources', {
                    'product_id': product_id,
                    'resource_type': 'video',
                    'resource_url': url,
                    'resource_name': f'video_{idx+1}',
                    'output_filename': f'video_{idx+1}.mp4'
                })
            
            return True
        except Exception as e:
            print(f"保存资源失败: {e}")
            return False
    
    def get_pending_resources(self, product_id: str = None, resource_type: str = None, 
                               limit: int = None) -> List[Dict]:
        """获取待下载资源"""
        sql = "SELECT * FROM resources WHERE downloaded = 0"
        params = []
        
        if product_id:
            sql += " AND product_id = ?"
            params.append(product_id)
        
        if resource_type:
            sql += " AND resource_type = ?"
            params.append(resource_type)
        
        sql += " ORDER BY created_at ASC"
        
        if limit:
            sql += f" LIMIT {limit}"
        
        return self.query(sql, tuple(params) if params else None)
    
    def mark_resource_downloaded(self, resource_id: int, file_size: int = None):
        """标记资源已下载"""
        update_data = {
            'downloaded': 1,
            'download_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        if file_size:
            update_data['file_size'] = file_size
        
        self.update('resources', update_data, 'id = ?', (resource_id,))
    
    def get_download_stats(self, product_id: str = None) -> Dict:
        """获取下载统计"""
        where_clause = ""
        params = []
        
        if product_id:
            where_clause = "WHERE product_id = ?"
            params = [product_id]
        
        stats = self.query_one(f'''
            SELECT 
                COUNT(*) as total,
                SUM(downloaded) as completed,
                COUNT(*) - SUM(downloaded) as pending
            FROM resources
            {where_clause}
        ''', tuple(params) if params else None)
        
        return stats or {'total': 0, 'completed': 0, 'pending': 0}
    
    def get_resources_by_type(self, product_id: str = None) -> Dict[str, List[Dict]]:
        """按类型获取资源"""
        where_clause = ""
        params = []
        
        if product_id:
            where_clause = "WHERE product_id = ?"
            params = [product_id]
        
        resources = self.query(f'''
            SELECT * FROM resources 
            {where_clause}
            ORDER BY resource_type, id
        ''', tuple(params) if params else None)
        
        result = {
            'main_image': [],
            'color_image': [],
            'detail_image': [],
            'video': []
        }
        
        for r in resources:
            rtype = r.get('resource_type')
            if rtype in result:
                result[rtype].append(r)
        
        return result
    
    def delete_product(self, product_id: str) -> bool:
        """删除商品及其资源"""
        try:
            self.delete('resources', 'product_id = ?', (product_id,))
            self.delete('products', 'product_id = ?', (product_id,))
            return True
        except Exception as e:
            print(f"删除商品失败: {e}")
            return False
    
    def save_cost_prices(self, product_id: str, cost_prices: List) -> bool:
        """保存成本价格"""
        try:
            cost_prices_json = json.dumps(cost_prices)
            existing = self.get_product(product_id)
            
            if existing:
                self.update('products', {
                    'cost_prices': cost_prices_json,
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }, 'product_id = ?', (product_id,))
            else:
                self.insert('products', {
                    'product_id': product_id,
                    'cost_prices': cost_prices_json,
                    'status': 'pending'
                })
            
            return True
        except Exception as e:
            print(f"保存成本价格失败: {e}")
            return False
    
    def save_selling_prices(self, product_id: str, prices: List[Dict]) -> bool:
        """保存销售价格"""
        try:
            selling_prices_json = json.dumps(prices)
            existing = self.get_product(product_id)
            
            if existing:
                self.update('products', {
                    'selling_prices': selling_prices_json,
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }, 'product_id = ?', (product_id,))
            else:
                self.insert('products', {
                    'product_id': product_id,
                    'selling_prices': selling_prices_json,
                    'status': 'pending'
                })
            
            return True
        except Exception as e:
            print(f"保存销售价格失败: {e}")
            return False
    
    def save_main_price(self, product_id: str, price: float, min_amount: int = 1):
        """保存主价格"""
        existing = self.get_product(product_id)
        
        if existing:
            self.update('products', {
                'title': f'商品_{product_id}',
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }, 'product_id = ?', (product_id,))
        else:
            self.insert('products', {
                'product_id': product_id,
                'status': 'pending'
            })
    
    def save_sku_prices(self, product_id: str, sku_prices: List[Dict]):
        """保存SKU价格"""
        for sku in sku_prices:
            self.insert('sku_prices', {
                'product_id': product_id,
                'sku_name': sku.get('name', ''),
                'price': sku.get('price', 0),
                'original_price': sku.get('original_price')
            })
    
    def save_consign_prices(self, product_id: str, consign_prices: List[Dict]):
        """保存代发价格（存储到sku_prices表）"""
        for cp in consign_prices:
            self.insert('sku_prices', {
                'product_id': product_id,
                'sku_name': cp.get('name', '代发'),
                'price': cp.get('price', 0),
                'original_price': cp.get('original_price')
            })
    
    def get_products_with_stats(self) -> List[Dict]:
        """获取商品列表及其资源统计"""
        return self.query('''
            SELECT 
                p.*,
                COUNT(r.id) as resource_count,
                SUM(r.downloaded) as downloaded_count
            FROM products p
            LEFT JOIN resources r ON p.product_id = r.product_id
            GROUP BY p.id
            ORDER BY p.created_at DESC
        ''')
    
    def count_resources(self, product_id: str) -> Optional[List[int]]:
        """统计商品资源数量"""
        return self.query_one('''
            SELECT 
                SUM(CASE WHEN resource_type = 'main_image' THEN 1 ELSE 0 END) as main_images,
                SUM(CASE WHEN resource_type = 'color_image' THEN 1 ELSE 0 END) as color_images,
                SUM(CASE WHEN resource_type = 'detail_image' THEN 1 ELSE 0 END) as detail_images,
                SUM(CASE WHEN resource_type = 'video' THEN 1 ELSE 0 END) as videos
            FROM resources
            WHERE product_id = ?
        ''', (product_id,))


def get_db():
    """获取数据库连接"""
    if not HAS_SQLITE:
        return None
    return Database()


def get_shared_db():
    """获取数据库连接（SQLite支持多进程）"""
    return get_db()


db = Database() if HAS_SQLITE else None
