#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库模块 - DuckDB版本
使用DuckDB作为嵌入式分析数据库
"""

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    from utils.logger import log_info, log_error, log_warning, log_success
    HAS_LOGGER = True
except ImportError:
    HAS_LOGGER = False
    def log_info(msg): print(f"[INFO] {msg}")
    def log_error(msg): print(f"[ERROR] {msg}")
    def log_warning(msg): print(f"[WARNING] {msg}")
    def log_success(msg): print(f"[SUCCESS] {msg}")

try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False
    print("警告: DuckDB未安装，请运行: pip install duckdb")


class Database:
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
                download_log VARCHAR,
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
            CREATE TABLE IF NOT EXISTS pricing (
                id INTEGER PRIMARY KEY,
                product_id VARCHAR NOT NULL,
                cost_price DOUBLE,
                selling_price DOUBLE,
                profit_margin DOUBLE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.execute('CREATE SEQUENCE IF NOT EXISTS products_id_seq')
        self.conn.execute('CREATE SEQUENCE IF NOT EXISTS resources_id_seq')
        self.conn.execute('CREATE SEQUENCE IF NOT EXISTS sku_prices_id_seq')
        
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_products_product_id ON products(product_id)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_products_shop_product_id ON products(shop_product_id)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_resources_product_id ON resources(product_id)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_resources_type ON resources(resource_type)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_resources_downloaded ON resources(downloaded)')
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def execute(self, sql: str, params: List = None) -> Any:
        """执行SQL语句"""
        if params:
            return self.conn.execute(sql, params)
        return self.conn.execute(sql)
    
    def query(self, sql: str, params: List = None) -> List[Dict]:
        """查询并返回字典列表"""
        if params:
            result = self.conn.execute(sql, params)
        else:
            result = self.conn.execute(sql)
        
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    
    def query_one(self, sql: str, params: List = None) -> Optional[Dict]:
        """查询单条记录"""
        results = self.query(sql, params)
        return results[0] if results else None
    
    def insert(self, table: str, data: Dict) -> int:
        """插入数据并返回ID"""
        if 'id' not in data:
            seq_name = f'{table}_id_seq'
            try:
                result = self.conn.execute(f"SELECT nextval('{seq_name}')")
                data['id'] = result.fetchone()[0]
            except:
                result = self.conn.execute(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table}")
                data['id'] = result.fetchone()[0]
        
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING id"
        result = self.conn.execute(sql, list(data.values()))
        return result.fetchone()[0]
    
    def update(self, table: str, data: Dict, where: str, where_params: List = None):
        """更新数据"""
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
        params = list(data.values()) + (where_params or [])
        self.conn.execute(sql, params)
    
    def delete(self, table: str, where: str, where_params: List = None):
        """删除数据"""
        sql = f"DELETE FROM {table} WHERE {where}"
        if where_params:
            self.conn.execute(sql, where_params)
        else:
            self.conn.execute(sql)
    
    def search_products(self, search_term: str, search_field: str = 'product_id') -> List[Dict]:
        """搜索商品记录"""
        if not search_term:
            return []
        
        if search_field not in ('product_id', 'shop_product_id'):
            search_field = 'product_id'
        
        return self.query(f'SELECT * FROM products WHERE {search_field} = ?', [search_term])
    
    def search_products_by_id(self, search_term: str) -> List[Dict]:
        """自动匹配商品ID和DSID搜索"""
        if not search_term:
            return []
        
        return self.query('SELECT * FROM products WHERE product_id = ? OR shop_product_id = ?', [search_term, search_term])
    
    def get_product(self, product_id: str) -> Optional[Dict]:
        """获取单个商品"""
        return self.query_one('SELECT * FROM products WHERE product_id = ?', [product_id])
    
    def get_all_products(self) -> List[Dict]:
        """获取所有商品"""
        return self.query('SELECT * FROM products ORDER BY created_at DESC')
    
    def update_shop_product_id(self, product_id: str, shop_product_id: str, output_path: str = None) -> bool:
        """更新或插入商品"""
        existing = self.get_product(product_id)
        
        if existing:
            update_data = {'shop_product_id': shop_product_id, 'updated_at': datetime.now()}
            if output_path:
                update_data['output_path'] = output_path
            self.update('products', update_data, 'product_id = ?', [product_id])
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
            self.update('products', {'output_path': output_path, 'updated_at': datetime.now()}, 'product_id = ?', [product_id])
        else:
            self.insert('products', {'product_id': product_id, 'output_path': output_path, 'status': 'pending'})
        
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
                'updated_at': datetime.now()
            }
            if output_path:
                update_data['output_path'] = output_path
            self.update('products', update_data, 'product_id = ?', [product_id])
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
        sql = "SELECT * FROM resources WHERE downloaded = FALSE"
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
        
        return self.query(sql, params if params else None)
    
    def mark_resource_downloaded(self, resource_id: int, file_size: int = None):
        """标记资源已下载"""
        update_data = {'downloaded': True, 'download_time': datetime.now()}
        if file_size:
            update_data['file_size'] = file_size
        
        self.update('resources', update_data, 'id = ?', [resource_id])
    
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
                SUM(CASE WHEN downloaded THEN 1 ELSE 0 END) as completed,
                COUNT(*) - SUM(CASE WHEN downloaded THEN 1 ELSE 0 END) as pending
            FROM resources
            {where_clause}
        ''', params if params else None)
        
        return stats or {'total': 0, 'completed': 0, 'pending': 0}
    
    def get_resources_by_type(self, product_id: str = None) -> Dict[str, List[Dict]]:
        """按类型获取资源"""
        where_clause = ""
        params = []
        
        if product_id:
            where_clause = "WHERE product_id = ?"
            params = [product_id]
        
        resources = self.query(f'SELECT * FROM resources {where_clause} ORDER BY resource_type, id', params if params else None)
        
        result = {'main_image': [], 'color_image': [], 'detail_image': [], 'video': []}
        
        for r in resources:
            rtype = r.get('resource_type')
            if rtype in result:
                result[rtype].append(r)
        
        return result
    
    def delete_product(self, product_id: str) -> bool:
        """删除商品及其资源"""
        try:
            self.delete('resources', 'product_id = ?', [product_id])
            self.delete('products', 'product_id = ?', [product_id])
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
                self.update('products', {'cost_prices': cost_prices_json, 'updated_at': datetime.now()}, 'product_id = ?', [product_id])
            else:
                self.insert('products', {'product_id': product_id, 'cost_prices': cost_prices_json, 'status': 'pending'})
            
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
                self.update('products', {'selling_prices': selling_prices_json, 'updated_at': datetime.now()}, 'product_id = ?', [product_id])
            else:
                self.insert('products', {'product_id': product_id, 'selling_prices': selling_prices_json, 'status': 'pending'})
            
            return True
        except Exception as e:
            print(f"保存销售价格失败: {e}")
            return False
    
    def save_main_price(self, product_id: str, price: float, min_amount: int = 1):
        """保存主价格"""
        existing = self.get_product(product_id)
        
        if existing:
            self.update('products', {'title': f'商品_{product_id}', 'updated_at': datetime.now()}, 'product_id = ?', [product_id])
        else:
            self.insert('products', {'product_id': product_id, 'status': 'pending'})
    
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
                SUM(CASE WHEN r.downloaded THEN 1 ELSE 0 END) as downloaded_count
            FROM products p
            LEFT JOIN resources r ON p.product_id = r.product_id
            GROUP BY p.id
            ORDER BY p.created_at DESC
        ''')
    
    def count_resources(self, product_id: str) -> Optional[Dict]:
        """统计商品资源数量"""
        return self.query_one('''
            SELECT 
                SUM(CASE WHEN resource_type = 'main_image' THEN 1 ELSE 0 END) as main_images,
                SUM(CASE WHEN resource_type = 'color_image' THEN 1 ELSE 0 END) as color_images,
                SUM(CASE WHEN resource_type = 'detail_image' THEN 1 ELSE 0 END) as detail_images,
                SUM(CASE WHEN resource_type = 'video' THEN 1 ELSE 0 END) as videos
            FROM resources
            WHERE product_id = ?
        ''', [product_id])


def get_db():
    """获取数据库连接"""
    if not HAS_DUCKDB:
        return None
    return Database()


def get_shared_db():
    """获取数据库连接（每次创建新连接，操作后需关闭）"""
    return get_db()


def import_pending_data():
    """批量导入临时数据到DuckDB"""
    # 获取共享内存（GUI进程已经创建了，不需要再连接）
    from utils.shared_cache import get_shared_cache, HAS_SHARED_MEMORY
    
    cache = get_shared_cache()
    if not cache or not cache.shm:
        log_info("共享内存不可用")
        return 0
    
    from utils.temp_storage import (
        get_pending_resources, get_pending_prices, get_pending_counts,
        clear_pending_data, has_pending_data
    )
    
    if not has_pending_data():
        log_info("没有待导入的数据")
        return 0
    
    db = get_db()
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
            
            # 检查是否已存在相同URL
            existing = db.query_one(
                'SELECT id FROM resources WHERE resource_url = ?',
                [url]
            )
            
            if existing:
                # 更新已存在记录
                db.update('resources', {
                    'downloaded': downloaded,
                    'download_time': datetime.now() if downloaded else None,
                    'file_size': file_size if file_size > 0 else None
                }, 'id = ?', [existing['id']])
            else:
                # 插入新记录
                db.insert('resources', {
                    'product_id': product_id,
                    'resource_type': 'main_image',
                    'resource_url': url,
                    'resource_name': name,
                    'output_filename': filename,
                    'downloaded': downloaded,
                    'download_time': datetime.now() if downloaded else None,
                    'file_size': file_size if file_size > 0 else None
                })
        
        for idx, (url, name) in enumerate(item.get('color_images', [])):
            filename = f"{FILE_NAMING['color_option_prefix']}{name}.jpg"
            filepath = os.path.join(output_path, filename) if output_path else None
            downloaded = filepath and os.path.exists(filepath)
            file_size = os.path.getsize(filepath) if downloaded else 0
            
            existing = db.query_one(
                'SELECT id FROM resources WHERE resource_url = ?',
                [url]
            )
            
            if existing:
                db.update('resources', {
                    'downloaded': downloaded,
                    'download_time': datetime.now() if downloaded else None,
                    'file_size': file_size if file_size > 0 else None
                }, 'id = ?', [existing['id']])
            else:
                db.insert('resources', {
                    'product_id': product_id,
                    'resource_type': 'color_image',
                    'resource_url': url,
                    'resource_name': name,
                    'output_filename': filename,
                    'downloaded': downloaded,
                    'download_time': datetime.now() if downloaded else None,
                    'file_size': file_size if file_size > 0 else None
                })
        
        for idx, url in enumerate(item.get('detail_images', [])):
            filename = f"{FILE_NAMING['detail_image_prefix']}{idx+1}.jpg"
            filepath = os.path.join(output_path, filename) if output_path else None
            downloaded = filepath and os.path.exists(filepath)
            file_size = os.path.getsize(filepath) if downloaded else 0
            
            existing = db.query_one(
                'SELECT id FROM resources WHERE resource_url = ?',
                [url]
            )
            
            if existing:
                db.update('resources', {
                    'downloaded': downloaded,
                    'download_time': datetime.now() if downloaded else None,
                    'file_size': file_size if file_size > 0 else None
                }, 'id = ?', [existing['id']])
            else:
                db.insert('resources', {
                    'product_id': product_id,
                    'resource_type': 'detail_image',
                    'resource_url': url,
                    'resource_name': f'detail_{idx+1}',
                    'output_filename': filename,
                    'downloaded': downloaded,
                    'download_time': datetime.now() if downloaded else None,
                    'file_size': file_size if file_size > 0 else None
                })
        
        for idx, url in enumerate(item.get('videos', [])):
            filename = f"{FILE_NAMING['video_prefix']}{idx+1}.mp4"
            filepath = os.path.join(output_path, filename) if output_path else None
            downloaded = filepath and os.path.exists(filepath)
            file_size = os.path.getsize(filepath) if downloaded else 0
            
            existing = db.query_one(
                'SELECT id FROM resources WHERE resource_url = ?',
                [url]
            )
            
            if existing:
                db.update('resources', {
                    'downloaded': downloaded,
                    'download_time': datetime.now() if downloaded else None,
                    'file_size': file_size if file_size > 0 else None
                }, 'id = ?', [existing['id']])
            else:
                db.insert('resources', {
                    'product_id': product_id,
                    'resource_type': 'video',
                    'resource_url': url,
                    'resource_name': f'video_{idx+1}',
                    'output_filename': filename,
                    'downloaded': downloaded,
                    'download_time': datetime.now() if downloaded else None,
                    'file_size': file_size if file_size > 0 else None
                })
        
        total_imported += 1
    
    # 导入价格数据
    prices_data = get_pending_prices()
    print(f"[DEBUG] 获取到 {len(prices_data)} 条价格数据")
    log_info(f"获取到 {len(prices_data)} 条价格数据")
    for item in prices_data:
        product_id = item['product_id']
        prices = item.get('prices', {})
        print(f"[DEBUG] 处理商品 {product_id} 的价格数据: sku_prices={len(prices.get('sku_prices', []))}, consign_prices={len(prices.get('consign_prices', []))}")
        log_info(f"处理商品 {product_id} 的价格数据: sku_prices={len(prices.get('sku_prices', []))}, consign_prices={len(prices.get('consign_prices', []))}")
        
        if prices.get('sku_prices'):
            for sku in prices['sku_prices']:
                color = sku.get('color', '')
                size = sku.get('size', '')
                sku_name = f"{color} {size}".strip() if color or size else sku.get('name', '')
                db.insert('sku_prices', {
                    'product_id': product_id,
                    'sku_name': sku_name,
                    'price': sku.get('price', 0),
                    'original_price': sku.get('original_price')
                })
        
        if prices.get('consign_prices'):
            for cp in prices['consign_prices']:
                db.insert('sku_prices', {
                    'product_id': product_id,
                    'sku_name': f"代发-{cp.get('type', 'single')}",
                    'price': cp.get('price', 0),
                    'original_price': None
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
            db.update('products', {
                'resource_counts': json.dumps(counts),
                'output_path': output_path,
                'platform': platform,
                'status': 'completed'
            }, 'product_id = ?', [product_id])
        else:
            db.insert('products', {
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


# 不再创建全局 db 实例，避免模块导入时锁定数据库文件
