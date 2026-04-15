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
except ImportError as e:
    HAS_DUCKDB = False
    print(f"警告: DuckDB未安装或导入失败: {e}")
    print("请运行: pip install duckdb")


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
        self._migrate_sku_prices_table()
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                product_id VARCHAR UNIQUE NOT NULL,
                shop_product_id VARCHAR,
                output_path VARCHAR,
                title VARCHAR,
                description VARCHAR,
                product_url VARCHAR,
                product_code VARCHAR,
                shop_id VARCHAR,
                status VARCHAR DEFAULT 'pending',
                resource_counts VARCHAR,
                cost_prices VARCHAR,
                selling_prices VARCHAR,
                platform VARCHAR DEFAULT 'alibaba',
                ship_from VARCHAR,
                sales_count INTEGER DEFAULT 0,
                min_order INTEGER DEFAULT 1,
                shipping_cost DOUBLE DEFAULT 0,
                unit_price DOUBLE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS shops (
                id INTEGER PRIMARY KEY,
                shop_id VARCHAR UNIQUE NOT NULL,
                shop_name VARCHAR,
                shop_url VARCHAR,
                shop_rating DOUBLE,
                shop_address VARCHAR,
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
                sku_id VARCHAR,
                color VARCHAR,
                size VARCHAR,
                price DOUBLE,
                discount_price DOUBLE,
                can_book_count INTEGER,
                sale_count INTEGER,
                spec_id VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS product_extended (
                id INTEGER PRIMARY KEY,
                product_id VARCHAR NOT NULL UNIQUE,
                
                -- 插件导航数据
                category VARCHAR,
                listing_date DATE,
                monthly_sales INTEGER,
                monthly_dropship INTEGER,
                yearly_volume INTEGER,
                yearly_orders INTEGER,
                review_count INTEGER,
                positive_rate FLOAT,
                pickup_rate FLOAT,
                
                -- 核心容器数据
                procurement_trend TEXT,
                features TEXT,
                supplier_highlights TEXT,
                
                -- 店铺数据
                shop_name VARCHAR,
                shop_years INTEGER,
                shop_category VARCHAR,
                shop_return_rate FLOAT,
                shop_service_score FLOAT,
                shop_delivery_rate FLOAT,
                shop_positive_rate FLOAT,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key VARCHAR PRIMARY KEY,
                value VARCHAR,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS attributes (
                id INTEGER PRIMARY KEY,
                product_id VARCHAR NOT NULL,
                fid VARCHAR,
                attr_name VARCHAR,
                attr_value VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS rate_info (
                id INTEGER PRIMARY KEY,
                product_id VARCHAR NOT NULL UNIQUE,
                good_rates INTEGER DEFAULT 0,
                goods_grade DOUBLE,
                impression_tags TEXT,
                common_tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS shop_products (
                id INTEGER PRIMARY KEY,
                shop_id VARCHAR NOT NULL,
                product_id VARCHAR NOT NULL,
                title VARCHAR,
                price DOUBLE,
                price_range VARCHAR,
                dropship_price DOUBLE,
                main_image VARCHAR,
                product_url VARCHAR,
                category VARCHAR,
                category_path VARCHAR,
                sales_count INTEGER DEFAULT 0,
                monthly_sales INTEGER DEFAULT 0,
                yearly_sales INTEGER DEFAULT 0,
                yearly_sales_qty INTEGER DEFAULT 0,
                monthly_orders INTEGER DEFAULT 0,
                yearly_orders INTEGER DEFAULT 0,
                review_count INTEGER DEFAULT 0,
                monthly_dropship INTEGER DEFAULT 0,
                repurchase_rate DOUBLE,
                ship_time VARCHAR,
                list_time VARCHAR,
                tags VARCHAR,
                sales_tags VARCHAR,
                attr_tags VARCHAR,
                service_tags VARCHAR,
                support_dropship INTEGER,
                positive_rate DOUBLE,
                min_order INTEGER DEFAULT 1,
                ship_from VARCHAR,
                shop_name VARCHAR,
                platform VARCHAR DEFAULT 'alibaba',
                collect_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(shop_id, product_id)
            )
        ''')
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS ds_shops (
                id INTEGER PRIMARY KEY,
                ds_shop_id VARCHAR UNIQUE NOT NULL,
                ds_shop_name VARCHAR NOT NULL,
                ds_platform VARCHAR DEFAULT 'alibaba',
                ds_shop_url VARCHAR,
                shop_type VARCHAR DEFAULT 'supplier',
                shop_status VARCHAR DEFAULT 'active',
                config TEXT,
                remark VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS product_ds_mapping (
                id INTEGER PRIMARY KEY,
                product_id VARCHAR NOT NULL,
                ds_shop_id VARCHAR NOT NULL,
                ds_product_id VARCHAR,
                ds_product_url VARCHAR,
                listing_status VARCHAR DEFAULT 'pending',
                listing_time TIMESTAMP,
                price_adjust DOUBLE DEFAULT 0,
                remark VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(product_id, ds_shop_id)
            )
        ''')
        
        self.conn.execute('CREATE SEQUENCE IF NOT EXISTS products_id_seq')
        self.conn.execute('CREATE SEQUENCE IF NOT EXISTS resources_id_seq')
        self.conn.execute('CREATE SEQUENCE IF NOT EXISTS sku_prices_id_seq')
        self.conn.execute('CREATE SEQUENCE IF NOT EXISTS shops_id_seq')
        self.conn.execute('CREATE SEQUENCE IF NOT EXISTS attributes_id_seq')
        self.conn.execute('CREATE SEQUENCE IF NOT EXISTS rate_info_id_seq')
        self.conn.execute('CREATE SEQUENCE IF NOT EXISTS shop_products_id_seq')
        
        self._migrate_products_table()
        self._migrate_shop_products_table()
        self._migrate_ds_shops_table()
        
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_products_product_id ON products(product_id)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_products_shop_product_id ON products(shop_product_id)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_products_shop_id ON products(shop_id)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_products_platform ON products(platform)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_products_ship_from ON products(ship_from)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_resources_product_id ON resources(product_id)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_resources_type ON resources(resource_type)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_resources_downloaded ON resources(downloaded)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_shops_shop_id ON shops(shop_id)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_shops_platform ON shops(platform)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_attributes_product_id ON attributes(product_id)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_rate_info_product_id ON rate_info(product_id)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_shop_products_shop_id ON shop_products(shop_id)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_shop_products_product_id ON shop_products(product_id)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_shop_products_collect_time ON shop_products(collect_time)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_ds_shops_shop_id ON ds_shops(ds_shop_id)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_ds_shops_platform ON ds_shops(ds_platform)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_product_ds_mapping_product_id ON product_ds_mapping(product_id)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_product_ds_mapping_ds_shop_id ON product_ds_mapping(ds_shop_id)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_product_ds_mapping_status ON product_ds_mapping(listing_status)')
    
    def _migrate_products_table(self):
        """迁移 products 表，添加新字段"""
        try:
            columns = self.conn.execute("DESCRIBE products").fetchall()
            existing_columns = {col[0] for col in columns}
            
            new_columns = {
                'description': 'VARCHAR',
                'product_url': 'VARCHAR',
                'product_code': 'VARCHAR',
                'shop_id': 'VARCHAR',
                'ship_from': 'VARCHAR',
                'sales_count': 'INTEGER DEFAULT 0',
                'min_order': 'INTEGER DEFAULT 1',
                'main_category': 'VARCHAR',
                'ds_shop_url': 'VARCHAR',
                'user_remark': 'VARCHAR'
            }
            
            for col_name, col_type in new_columns.items():
                if col_name not in existing_columns:
                    try:
                        self.conn.execute(f'ALTER TABLE products ADD COLUMN {col_name} {col_type}')
                        log_info(f"已添加字段: {col_name}")
                    except Exception as e:
                        log_warning(f"添加字段 {col_name} 失败: {e}")
            
            rename_columns = {
                'ds_shop': 'ds_shop_url',
                'remark': 'user_remark'
            }
            
            for old_name, new_name in rename_columns.items():
                if old_name in existing_columns and new_name not in existing_columns:
                    try:
                        self.conn.execute(f'ALTER TABLE products RENAME COLUMN {old_name} TO {new_name}')
                        log_info(f"已重命名字段: {old_name} -> {new_name}")
                    except Exception as e:
                        log_warning(f"重命名字段 {old_name} 失败: {e}")
                        
        except Exception as e:
            log_warning(f"迁移检查失败: {e}")
    
    def _migrate_shop_products_table(self):
        """迁移 shop_products 表，添加新字段"""
        try:
            columns = self.conn.execute("DESCRIBE shop_products").fetchall()
            existing_columns = {col[0] for col in columns}
            
            new_columns = {
                'dropship_price': 'DOUBLE',
                'sales_count': 'INTEGER DEFAULT 0',
                'yearly_sales_qty': 'INTEGER DEFAULT 0',
                'monthly_orders': 'INTEGER DEFAULT 0',
                'yearly_orders': 'INTEGER DEFAULT 0',
                'monthly_dropship': 'INTEGER DEFAULT 0',
                'repurchase_rate': 'DOUBLE',
                'ship_time': 'VARCHAR',
                'list_time': 'VARCHAR',
                'tags': 'VARCHAR',
                'sales_tags': 'VARCHAR',
                'attr_tags': 'VARCHAR',
                'service_tags': 'VARCHAR',
                'support_dropship': 'INTEGER',
            }
            
            for col_name, col_type in new_columns.items():
                if col_name not in existing_columns:
                    try:
                        self.conn.execute(f'ALTER TABLE shop_products ADD COLUMN {col_name} {col_type}')
                        log_info(f"已添加字段: shop_products.{col_name}")
                    except Exception as e:
                        log_warning(f"添加字段 shop_products.{col_name} 失败: {e}")
                        
        except Exception as e:
            log_warning(f"迁移 shop_products 表失败: {e}")
    
    def _migrate_ds_shops_table(self):
        """迁移 ds_shops 表，添加新字段"""
        try:
            columns = self.conn.execute("DESCRIBE ds_shops").fetchall()
            existing_columns = {col[0] for col in columns}
            
            new_columns = {
                'shop_type': "VARCHAR DEFAULT 'supplier'",
            }
            
            for col_name, col_type in new_columns.items():
                if col_name not in existing_columns:
                    try:
                        self.conn.execute(f'ALTER TABLE ds_shops ADD COLUMN {col_name} {col_type}')
                        log_info(f"已添加字段: ds_shops.{col_name}")
                    except Exception as e:
                        log_warning(f"添加字段 ds_shops.{col_name} 失败: {e}")
                        
        except Exception as e:
            log_warning(f"迁移 ds_shops 表失败: {e}")
    
    def _migrate_sku_prices_table(self):
        """迁移 sku_prices 表，重建表结构"""
        try:
            print("[数据库迁移] 检查 sku_prices 表结构...")
            result = self.conn.execute("SELECT table_name FROM information_schema.tables WHERE table_name = 'sku_prices'").fetchone()
            if not result:
                print("[数据库迁移] sku_prices 表不存在，将创建新表")
                return
            
            columns = self.conn.execute("DESCRIBE sku_prices").fetchall()
            existing_columns = {col[0] for col in columns}
            print(f"[数据库迁移] sku_prices 现有字段: {existing_columns}")
            
            required_columns = {'sku_id', 'color', 'size', 'price', 'discount_price', 
                              'can_book_count', 'sale_count', 'spec_id'}
            
            old_columns = {'sku_name', 'cost_price', 'original_price'}
            has_old_columns = bool(existing_columns & old_columns)
            
            if not required_columns.issubset(existing_columns) or has_old_columns:
                print("[数据库迁移] 检测到旧版 sku_prices 表结构，正在重建...")
                
                try:
                    self.conn.execute('DROP TABLE IF EXISTS sku_prices_old')
                    print("[数据库迁移] 步骤1: 删除旧的备份表")
                except Exception as e:
                    print(f"[数据库迁移] 步骤1失败: {e}")
                
                try:
                    self.conn.execute('ALTER TABLE sku_prices RENAME TO sku_prices_old')
                    print("[数据库迁移] 步骤2: 重命名旧表")
                except Exception as e:
                    print(f"[数据库迁移] 步骤2失败: {e}")
                    raise
                
                try:
                    self.conn.execute('''
                        CREATE TABLE sku_prices (
                            id INTEGER PRIMARY KEY,
                            product_id VARCHAR NOT NULL,
                            sku_id VARCHAR,
                            color VARCHAR,
                            size VARCHAR,
                            price DOUBLE,
                            discount_price DOUBLE,
                            can_book_count INTEGER,
                            sale_count INTEGER,
                            spec_id VARCHAR,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    print("[数据库迁移] 步骤3: 创建新表")
                except Exception as e:
                    print(f"[数据库迁移] 步骤3失败: {e}")
                    raise
                
                try:
                    self.conn.execute('CREATE INDEX IF NOT EXISTS idx_sku_prices_product_id ON sku_prices(product_id)')
                    self.conn.execute('CREATE INDEX IF NOT EXISTS idx_sku_prices_sku_id ON sku_prices(sku_id)')
                    print("[数据库迁移] 步骤4: 创建索引")
                except Exception as e:
                    print(f"[数据库迁移] 步骤4失败: {e}")
                
                try:
                    self.conn.execute('DROP TABLE sku_prices_old')
                    print("[数据库迁移] 步骤5: 删除旧表备份")
                except Exception as e:
                    print(f"[数据库迁移] 步骤5失败: {e}")
                
                new_columns = self.conn.execute("DESCRIBE sku_prices").fetchall()
                new_col_names = {col[0] for col in new_columns}
                print(f"[数据库迁移] sku_prices 表结构已更新: {new_col_names}")
            else:
                print("[数据库迁移] sku_prices 表结构正确，无需迁移")
        except Exception as e:
            print(f"[数据库迁移] 迁移 sku_prices 表失败: {e}")
            import traceback
            traceback.print_exc()
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            try:
                self.conn.execute('CHECKPOINT')
            except:
                pass
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
    
    def get_setting(self, key: str, default=None):
        """获取设置值"""
        try:
            result = self.conn.execute(
                "SELECT value FROM settings WHERE key = ?",
                [key]
            ).fetchone()
            if result:
                import json
                return json.loads(result[0])
            return default
        except Exception as e:
            print(f"获取设置失败: {e}")
            return default
    
    def save_setting(self, key: str, value):
        """保存设置值"""
        try:
            import json
            from datetime import datetime
            value_str = json.dumps(value, ensure_ascii=False)
            self.conn.execute('''
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT (key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
            ''', [key, value_str, datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
            return True
        except Exception as e:
            print(f"保存设置失败: {e}")
            return False
    
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
        self.conn.execute('CHECKPOINT')
        return result.fetchone()[0]
    
    def update(self, table: str, data: Dict, where: str, where_params: List = None):
        """更新数据"""
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
        params = list(data.values()) + (where_params or [])
        self.conn.execute(sql, params)
        self.conn.execute('CHECKPOINT')
    
    def delete(self, table: str, where: str, where_params: List = None):
        """删除数据"""
        sql = f"DELETE FROM {table} WHERE {where}"
        if where_params:
            self.conn.execute(sql, where_params)
        else:
            self.conn.execute(sql)
        self.conn.execute('CHECKPOINT')
    
    def search_products(self, search_term: str, search_field: str = 'product_id') -> List[Dict]:
        """搜索商品记录"""
        if not search_term:
            return []
        
        if search_field not in ('product_id', 'shop_product_id'):
            search_field = 'product_id'
        
        return self.query(f'SELECT * FROM products WHERE {search_field} = ?', [search_term])
    
    def search_products_by_id(self, search_term: str) -> List[Dict]:
        """模糊搜索商品 - 支持商品ID、DSID、标题、发货地"""
        if not search_term:
            return []
        
        search_pattern = f'%{search_term}%'
        return self.query('''
            SELECT * FROM products 
            WHERE product_id LIKE ? 
               OR shop_product_id LIKE ? 
               OR title LIKE ?
               OR ship_from LIKE ?
            ORDER BY created_at DESC
        ''', [search_pattern, search_pattern, search_pattern, search_pattern])
    
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
            from config import sanitize_filename
            
            for idx, (url, name) in enumerate(main_images):
                safe_name = sanitize_filename(name)
                self.insert('resources', {
                    'product_id': product_id,
                    'resource_type': 'main_image',
                    'resource_url': url,
                    'resource_name': name,
                    'output_filename': f'main_{safe_name}.jpg'
                })
            
            for idx, (url, name) in enumerate(color_images):
                safe_name = sanitize_filename(name)
                self.insert('resources', {
                    'product_id': product_id,
                    'resource_type': 'color_image',
                    'resource_url': url,
                    'resource_name': name,
                    'output_filename': f'color_{safe_name}.jpg'
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
    
    def insert_resource(self, product_id: str, resource_type: str, resource_url: str,
                        resource_name: str = None, output_filename: str = None,
                        downloaded: bool = False, file_size: int = None) -> bool:
        """插入单个资源记录
        
        Args:
            product_id: 商品ID
            resource_type: 资源类型 (main_image, color_image, detail_image, video)
            resource_url: 资源URL
            resource_name: 资源名称
            output_filename: 输出文件名
            downloaded: 是否已下载
            file_size: 文件大小
            
        Returns:
            是否成功
        """
        try:
            existing = self.query_one(
                "SELECT id, downloaded FROM resources WHERE product_id = ? AND resource_url = ? AND resource_type = ?",
                [product_id, resource_url, resource_type]
            )
            
            if existing:
                if existing.get('downloaded'):
                    self.update('resources', {'downloaded': False, 'download_time': None, 'file_size': None}, 'id = ?', [existing['id']])
                return True
            
            data = {
                'product_id': product_id,
                'resource_type': resource_type,
                'resource_url': resource_url,
                'resource_name': resource_name,
                'output_filename': output_filename,
                'downloaded': downloaded,
            }
            
            if downloaded:
                data['download_time'] = datetime.now()
            if file_size:
                data['file_size'] = file_size
            
            self.insert('resources', data)
            return True
        except Exception as e:
            print(f"插入资源失败: {e}")
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
    
    def mark_resource_pending(self, resource_id: int):
        """标记资源待下载（重置下载状态）"""
        update_data = {'downloaded': False, 'download_time': None, 'file_size': None}
        self.update('resources', update_data, 'id = ?', [resource_id])
    
    def get_all_resources(self, product_id: str = None, resource_type: str = None) -> List[Dict]:
        """获取所有资源（包括已下载和待下载）"""
        sql = "SELECT * FROM resources WHERE 1=1"
        params = []
        
        if product_id:
            sql += " AND product_id = ?"
            params.append(product_id)
        
        if resource_type:
            sql += " AND resource_type = ?"
            params.append(resource_type)
        
        sql += " ORDER BY resource_type, created_at ASC"
        
        return self.query(sql, params if params else None)
    
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
        """保存SKU价格和库存"""
        for sku in sku_prices:
            self.insert('sku_prices', {
                'product_id': product_id,
                'sku_name': sku.get('sku_name', sku.get('name', '')),
                'sku_id': sku.get('sku_id', ''),
                'price': sku.get('price', 0),
                'original_price': sku.get('original_price'),
                'stock': sku.get('stock', 0)
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
    
    def count_resources(self, product_id: str) -> Dict:
        """统计商品资源数量"""
        result = self.query_one('''
            SELECT 
                SUM(CASE WHEN resource_type = 'main_image' THEN 1 ELSE 0 END) as main_images,
                SUM(CASE WHEN resource_type = 'color_image' THEN 1 ELSE 0 END) as color_images,
                SUM(CASE WHEN resource_type = 'detail_image' THEN 1 ELSE 0 END) as detail_images,
                SUM(CASE WHEN resource_type = 'video' THEN 1 ELSE 0 END) as videos
            FROM resources
            WHERE product_id = ?
        ''', [product_id])
        
        if result is None:
            return {'main_images': 0, 'color_images': 0, 'detail_images': 0, 'videos': 0}
        
        return {
            'main_images': result.get('main_images') or 0,
            'color_images': result.get('color_images') or 0,
            'detail_images': result.get('detail_images') or 0,
            'videos': result.get('videos') or 0
        }
    
    def get_sku_prices(self, product_id: str) -> List[Dict]:
        """获取商品的SKU价格和库存"""
        return self.query('''
            SELECT id, product_id, sku_id, color, size, price, discount_price, can_book_count, sale_count, spec_id, created_at, updated_at
            FROM sku_prices
            WHERE product_id = ?
            ORDER BY id
        ''', [product_id])
    
    def count_sku_prices(self, product_id: str) -> int:
        """统计商品SKU价格数量"""
        result = self.query_one('''
            SELECT COUNT(*) as count
            FROM sku_prices
            WHERE product_id = ?
        ''', [product_id])
        return result['count'] if result else 0
    
    def save_shop(self, shop_id: str, shop_name: str = None, shop_url: str = None, 
                  shop_rating: float = None, shop_address: str = None, 
                  platform: str = 'alibaba') -> bool:
        """保存或更新店铺信息"""
        existing = self.query_one('SELECT * FROM shops WHERE shop_id = ?', [shop_id])
        
        if existing:
            update_data = {'updated_at': datetime.now()}
            if shop_name:
                update_data['shop_name'] = shop_name
            if shop_url:
                update_data['shop_url'] = shop_url
            if shop_rating is not None:
                update_data['shop_rating'] = shop_rating
            if shop_address:
                update_data['shop_address'] = shop_address
            self.update('shops', update_data, 'shop_id = ?', [shop_id])
        else:
            self.insert('shops', {
                'shop_id': shop_id,
                'shop_name': shop_name,
                'shop_url': shop_url,
                'shop_rating': shop_rating,
                'shop_address': shop_address,
                'platform': platform
            })
        return True
    
    def get_shop(self, shop_id: str) -> Optional[Dict]:
        """获取店铺信息"""
        return self.query_one('SELECT * FROM shops WHERE shop_id = ?', [shop_id])
    
    def get_attributes(self, product_id: str) -> List[Dict]:
        """获取商品属性"""
        return self.query('SELECT * FROM attributes WHERE product_id = ?', [product_id])
    
    def insert_attribute(self, product_id: str, fid: str = None, attr_name: str = None, attr_value: str = None) -> bool:
        """插入商品属性"""
        try:
            self.insert('attributes', {
                'product_id': product_id,
                'fid': fid,
                'attr_name': attr_name,
                'attr_value': attr_value
            })
            return True
        except Exception as e:
            log_warning(f"插入属性失败: {e}")
            return False
    
    def clear_attributes(self, product_id: str) -> bool:
        """清除商品属性"""
        try:
            self.conn.execute('DELETE FROM attributes WHERE product_id = ?', [product_id])
            return True
        except Exception as e:
            log_warning(f"清除属性失败: {e}")
            return False
    
    def save_rate_info(self, product_id: str, good_rates: int = 0, goods_grade: float = None,
                       impression_tags: List = None, common_tags: List = None) -> bool:
        """保存评价信息"""
        try:
            existing = self.query_one('SELECT * FROM rate_info WHERE product_id = ?', [product_id])
            
            tags_json = json.dumps(impression_tags or [], ensure_ascii=False)
            common_json = json.dumps(common_tags or [], ensure_ascii=False)
            
            if existing:
                self.update('rate_info', {
                    'good_rates': good_rates,
                    'goods_grade': goods_grade,
                    'impression_tags': tags_json,
                    'common_tags': common_json,
                    'updated_at': datetime.now()
                }, 'product_id = ?', [product_id])
            else:
                self.insert('rate_info', {
                    'product_id': product_id,
                    'good_rates': good_rates,
                    'goods_grade': goods_grade,
                    'impression_tags': tags_json,
                    'common_tags': common_json
                })
            return True
        except Exception as e:
            log_warning(f"保存评价信息失败: {e}")
            return False
    
    def get_rate_info(self, product_id: str) -> Optional[Dict]:
        """获取评价信息"""
        result = self.query_one('SELECT * FROM rate_info WHERE product_id = ?', [product_id])
        if result:
            if result.get('impression_tags'):
                try:
                    result['impression_tags'] = json.loads(result['impression_tags'])
                except:
                    pass
            if result.get('common_tags'):
                try:
                    result['common_tags'] = json.loads(result['common_tags'])
                except:
                    pass
        return result
    
    def get_all_shops(self) -> List[Dict]:
        """获取所有店铺"""
        return self.query('SELECT * FROM shops ORDER BY updated_at DESC')
    
    def get_products_by_shop(self, shop_id: str) -> List[Dict]:
        """获取店铺下的所有商品"""
        return self.query('SELECT * FROM products WHERE shop_id = ? ORDER BY created_at DESC', [shop_id])
    
    def update_product_info(self, product_id: str, title: str = None, description: str = None,
                            product_url: str = None, product_code: str = None, 
                            shop_id: str = None, ship_from: str = None,
                            sales_count: int = None, min_order: int = None,
                            main_category: str = None) -> bool:
        """更新商品详细信息"""
        existing = self.get_product(product_id)
        
        update_data = {'updated_at': datetime.now()}
        if title:
            update_data['title'] = title
        if description:
            update_data['description'] = description
        if product_url:
            update_data['product_url'] = product_url
        if product_code:
            update_data['product_code'] = product_code
        if shop_id:
            update_data['shop_id'] = shop_id
        if ship_from:
            update_data['ship_from'] = ship_from
        if sales_count is not None:
            update_data['sales_count'] = sales_count
        if min_order is not None:
            update_data['min_order'] = min_order
        if main_category:
            update_data['main_category'] = main_category
        
        if existing:
            self.update('products', update_data, 'product_id = ?', [product_id])
        else:
            update_data['product_id'] = product_id
            update_data['status'] = 'pending'
            self.insert('products', update_data)
        
        return True
    
    def update_product(self, product_id: str, data: Dict) -> bool:
        """更新商品信息
        
        Args:
            product_id: 商品ID
            data: 要更新的数据字典
            
        Returns:
            是否成功
        """
        existing = self.get_product(product_id)
        
        update_data = {'updated_at': datetime.now()}
        update_data.update(data)
        
        if existing:
            self.update('products', update_data, 'product_id = ?', [product_id])
        else:
            update_data['product_id'] = product_id
            update_data['status'] = 'pending'
            self.insert('products', update_data)
        
        return True
    
    def insert_sku_price(self, product_id: str, sku_id: str, color: str, size: str,
                         price: float = None, discount_price: float = None,
                         can_book_count: int = None, sale_count: int = None,
                         spec_id: str = None) -> bool:
        """插入或更新SKU价格
        
        Args:
            product_id: 商品ID
            sku_id: SKU ID
            color: 颜色
            size: 尺码
            price: 价格
            discount_price: 折扣价
            can_book_count: 库存
            sale_count: 销量
            spec_id: 规格ID
            
        Returns:
            是否成功
        """
        existing = self.query_one(
            "SELECT * FROM sku_prices WHERE product_id = ? AND sku_id = ?",
            [product_id, sku_id]
        )
        
        data = {
            'product_id': product_id,
            'sku_id': sku_id,
            'color': color,
            'size': size,
            'price': price,
            'discount_price': discount_price,
            'can_book_count': can_book_count,
            'sale_count': sale_count,
            'spec_id': spec_id,
            'created_at': datetime.now()
        }
        
        if existing:
            del data['created_at']
            data['updated_at'] = datetime.now()
            self.update('sku_prices', data, 'product_id = ? AND sku_id = ?', [product_id, sku_id])
        else:
            self.insert('sku_prices', data)
        
        return True
    
    def get_sku_prices(self, product_id: str) -> List[Dict]:
        """获取商品的所有SKU价格
        
        Args:
            product_id: 商品ID
            
        Returns:
            SKU价格列表
        """
        return self.query(
            "SELECT * FROM sku_prices WHERE product_id = ? ORDER BY color, size",
            [product_id]
        )
    
    def delete_sku_prices(self, product_id: str) -> bool:
        """删除商品的所有SKU价格
        
        Args:
            product_id: 商品ID
            
        Returns:
            是否成功
        """
        self.execute("DELETE FROM sku_prices WHERE product_id = ?", [product_id])
        return True
    
    def get_statistics(self) -> Dict:
        """获取整体统计数据"""
        stats = {}
        
        stats['total_products'] = self.query_one('SELECT COUNT(*) as count FROM products')['count']
        stats['total_shops'] = self.query_one('SELECT COUNT(*) as count FROM shops')['count']
        stats['total_resources'] = self.query_one('SELECT COUNT(*) as count FROM resources')['count']
        stats['downloaded_resources'] = self.query_one(
            'SELECT COUNT(*) as count FROM resources WHERE downloaded = TRUE'
        )['count']
        
        platform_stats = self.query('''
            SELECT platform, COUNT(*) as count 
            FROM products 
            GROUP BY platform
        ''')
        stats['by_platform'] = {p['platform']: p['count'] for p in platform_stats}
        
        ship_from_stats = self.query('''
            SELECT ship_from, COUNT(*) as count 
            FROM products 
            WHERE ship_from IS NOT NULL AND ship_from != ''
            GROUP BY ship_from
            ORDER BY count DESC
            LIMIT 10
        ''')
        stats['by_ship_from'] = {s['ship_from']: s['count'] for s in ship_from_stats}
        
        return stats
    
    def search_products_full(self, keyword: str = None, shop_id: str = None, 
                             platform: str = None, ship_from: str = None,
                             limit: int = 100) -> List[Dict]:
        """综合搜索商品"""
        conditions = []
        params = []
        
        if keyword:
            conditions.append('(title LIKE ? OR product_id LIKE ? OR shop_product_id LIKE ?)')
            params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])
        if shop_id:
            conditions.append('shop_id = ?')
            params.append(shop_id)
        if platform:
            conditions.append('platform = ?')
            params.append(platform)
        if ship_from:
            conditions.append('ship_from = ?')
            params.append(ship_from)
        
        where_clause = ' AND '.join(conditions) if conditions else '1=1'
        sql = f'SELECT * FROM products WHERE {where_clause} ORDER BY created_at DESC LIMIT {limit}'
        
        return self.query(sql, params if params else None)
    
    def save_shop_product(self, shop_id: str, product_data: Dict) -> bool:
        """保存店铺商品数据
        
        Args:
            shop_id: 店铺ID
            product_data: 商品数据字典
            
        Returns:
            是否成功
        """
        product_id = product_data.get('product_id')
        if not product_id:
            return False
        
        existing = self.query(
            'SELECT id FROM shop_products WHERE shop_id = ? AND product_id = ?',
            [shop_id, product_id]
        )
        
        data = {
            'shop_id': shop_id,
            'product_id': product_id,
            'title': product_data.get('title'),
            'price': product_data.get('price'),
            'price_range': product_data.get('price_range'),
            'main_image': product_data.get('main_image'),
            'product_url': product_data.get('product_url'),
            'category': product_data.get('category'),
            'category_path': product_data.get('category_path'),
            'monthly_sales': product_data.get('monthly_sales', 0),
            'yearly_sales': product_data.get('yearly_sales', 0),
            'review_count': product_data.get('review_count', 0),
            'positive_rate': product_data.get('positive_rate'),
            'min_order': product_data.get('min_order', 1),
            'ship_from': product_data.get('ship_from'),
            'shop_name': product_data.get('shop_name'),
            'platform': product_data.get('platform', 'alibaba'),
            'updated_at': datetime.now()
        }
        
        if existing:
            self.update('shop_products', data, 'shop_id = ? AND product_id = ?', [shop_id, product_id])
        else:
            data['collect_time'] = datetime.now()
            self.insert('shop_products', data)
        
        return True
    
    def get_shop_products(self, shop_id: str, limit: int = 500) -> List[Dict]:
        """获取店铺所有商品
        
        Args:
            shop_id: 店铺ID
            limit: 返回数量限制
            
        Returns:
            商品列表
        """
        return self.query(
            'SELECT * FROM shop_products WHERE shop_id = ? ORDER BY collect_time DESC LIMIT ?',
            [shop_id, limit]
        )
    
    def get_shop_products_stats(self, shop_id: str) -> Dict:
        """获取店铺商品统计
        
        Args:
            shop_id: 店铺ID
            
        Returns:
            统计数据
        """
        stats = {}
        
        total = self.query(
            'SELECT COUNT(*) as count FROM shop_products WHERE shop_id = ?',
            [shop_id]
        )
        stats['total_products'] = total[0]['count'] if total else 0
        
        total_sales = self.query(
            'SELECT SUM(monthly_sales) as total FROM shop_products WHERE shop_id = ?',
            [shop_id]
        )
        stats['total_monthly_sales'] = total_sales[0]['total'] if total_sales and total_sales[0]['total'] else 0
        
        category_stats = self.query(
            'SELECT category, COUNT(*) as count FROM shop_products WHERE shop_id = ? GROUP BY category ORDER BY count DESC LIMIT 10',
            [shop_id]
        )
        stats['by_category'] = {c['category']: c['count'] for c in category_stats if c['category']}
        
        return stats
    
    def save_ds_shop(self, ds_shop_id: str, ds_shop_name: str, ds_platform: str = 'jd',
                     ds_shop_url: str = None, config: Dict = None, remark: str = None) -> bool:
        existing = self.query_one('SELECT * FROM ds_shops WHERE ds_shop_id = ?', [ds_shop_id])
        
        data = {
            'ds_shop_id': ds_shop_id,
            'ds_shop_name': ds_shop_name,
            'ds_platform': ds_platform,
            'ds_shop_url': ds_shop_url,
            'config': json.dumps(config) if config else None,
            'remark': remark,
            'updated_at': datetime.now()
        }
        
        if existing:
            self.update('ds_shops', data, 'ds_shop_id = ?', [ds_shop_id])
        else:
            data['created_at'] = datetime.now()
            self.insert('ds_shops', data)
        
        return True
    
    def get_ds_shop(self, ds_shop_id: str) -> Optional[Dict]:
        return self.query_one('SELECT * FROM ds_shops WHERE ds_shop_id = ?', [ds_shop_id])
    
    def get_all_ds_shops(self) -> List[Dict]:
        return self.query('SELECT * FROM ds_shops ORDER BY created_at DESC')
    
    def delete_ds_shop(self, ds_shop_id: str) -> bool:
        self.execute("DELETE FROM product_ds_mapping WHERE ds_shop_id = ?", [ds_shop_id])
        self.execute("DELETE FROM ds_shops WHERE ds_shop_id = ?", [ds_shop_id])
        return True
    
    def save_product_ds_mapping(self, product_id: str, ds_shop_id: str,
                                 ds_product_id: str = None, ds_product_url: str = None,
                                 listing_status: str = 'pending', price_adjust: float = 0,
                                 remark: str = None) -> bool:
        existing = self.query_one(
            'SELECT * FROM product_ds_mapping WHERE product_id = ? AND ds_shop_id = ?',
            [product_id, ds_shop_id]
        )
        
        data = {
            'product_id': product_id,
            'ds_shop_id': ds_shop_id,
            'ds_product_id': ds_product_id,
            'ds_product_url': ds_product_url,
            'listing_status': listing_status,
            'price_adjust': price_adjust,
            'remark': remark,
            'updated_at': datetime.now()
        }
        
        if existing:
            self.update('product_ds_mapping', data, 'product_id = ? AND ds_shop_id = ?', [product_id, ds_shop_id])
        else:
            data['created_at'] = datetime.now()
            self.insert('product_ds_mapping', data)
        
        return True
    
    def get_product_ds_mappings(self, product_id: str) -> List[Dict]:
        return self.query(
            'SELECT m.*, d.ds_shop_name, d.ds_platform FROM product_ds_mapping m '
            'LEFT JOIN ds_shops d ON m.ds_shop_id = d.ds_shop_id '
            'WHERE m.product_id = ? ORDER BY m.created_at DESC',
            [product_id]
        )
    
    def delete_product_ds_mapping(self, product_id: str, ds_shop_id: str) -> bool:
        self.execute(
            "DELETE FROM product_ds_mapping WHERE product_id = ? AND ds_shop_id = ?",
            [product_id, ds_shop_id]
        )
        return True
    
    def get_product_ds_status(self, product_id: str) -> Dict:
        mappings = self.get_product_ds_mappings(product_id)
        
        return {
            'total_shops': len(mappings),
            'listed_count': sum(1 for m in mappings if m.get('listing_status') == 'listed'),
            'pending_count': sum(1 for m in mappings if m.get('listing_status') == 'pending'),
            'delisted_count': sum(1 for m in mappings if m.get('listing_status') == 'delisted'),
            'shops': mappings
        }


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
    
    from utils.shared_cache import (
        get_pending_resources, get_pending_prices, get_pending_counts,
        get_pending_product_info, get_pending_shop_info,
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
    
    # 尝试使用 GUI 日志
    try:
        from utils.logger import get_gui_logger
        gui_logger = get_gui_logger()
        if gui_logger:
            gui_logger.log(f"获取到 {len(prices_data)} 条价格数据", "info")
    except:
        pass
    
    for item in prices_data:
        product_id = item['product_id']
        prices = item.get('prices', {})
        
        try:
            from utils.logger import get_gui_logger
            gui_logger = get_gui_logger()
            if gui_logger:
                gui_logger.log(f"处理商品 {product_id} 的价格数据: sku_prices={len(prices.get('sku_prices', []))}, consign_prices={len(prices.get('consign_prices', []))}", "info")
        except:
            pass
        
        if prices.get('sku_prices'):
            for sku in prices['sku_prices']:
                color = sku.get('color', '')
                size = sku.get('size', '')
                
                if '代发' in color or '代发' in size:
                    continue
                
                sku_name = f"{color} {size}".strip() if color or size else sku.get('name', '')
                sku_id = sku.get('skuId', '') or sku.get('sku_id', '')
                
                existing = db.query_one(
                    "SELECT * FROM sku_prices WHERE product_id = ? AND sku_id = ?",
                    [product_id, sku_id]
                ) if sku_id else None
                
                data = {
                    'product_id': product_id,
                    'sku_name': sku_name,
                    'color': color,
                    'size': size,
                    'price': sku.get('price', 0),
                    'original_price': sku.get('original_price'),
                    'discount_price': sku.get('discountPrice'),
                    'can_book_count': sku.get('canBookCount'),
                    'sale_count': sku.get('saleCount'),
                    'spec_id': sku.get('specId', ''),
                    'updated_at': datetime.now()
                }
                
                if existing:
                    del data['created_at']
                    db.update('sku_prices', data, 'product_id = ? AND sku_id = ?', [product_id, sku_id])
                else:
                    data['created_at'] = datetime.now()
                    db.insert('sku_prices', data)
        
        if prices.get('consign_prices'):
            pass
        
        if prices.get('shipping_cost'):
            try:
                shipping_cost = float(prices['shipping_cost'])
                if shipping_cost > 0:
                    existing_product = db.get_product(product_id)
                    if existing_product:
                        db.update('products', {
                            'shipping_cost': shipping_cost,
                            'updated_at': datetime.now()
                        }, 'product_id = ?', [product_id])
            except (ValueError, TypeError):
                pass
        
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
    
    # 导入商品详细信息
    product_info_data = get_pending_product_info()
    for item in product_info_data:
        product_id = item['product_id']
        info = item.get('info', {})
        
        db.update_product_info(
            product_id=product_id,
            title=info.get('title'),
            description=info.get('description'),
            product_url=info.get('product_url'),
            product_code=info.get('product_code'),
            shop_id=info.get('shop_info', {}).get('shop_id') if info.get('shop_info') else None,
            ship_from=info.get('ship_from'),
            sales_count=info.get('sales_count'),
            min_order=info.get('min_order')
        )
        
        total_imported += 1
    
    # 导入店铺信息
    shop_info_data = get_pending_shop_info()
    for item in shop_info_data:
        shop_info = item.get('shop_info', {})
        if shop_info and shop_info.get('shop_id'):
            db.save_shop(
                shop_id=shop_info['shop_id'],
                shop_name=shop_info.get('shop_name'),
                shop_url=shop_info.get('shop_url'),
                shop_rating=shop_info.get('shop_rating'),
                shop_address=shop_info.get('shop_address'),
                platform=shop_info.get('platform', 'alibaba')
            )
            total_imported += 1
    
    # 清空临时数据
    clear_pending_data()
    
    db.close()
    
    print(f"批量导入完成: {total_imported} 条记录")
    return total_imported


# 不再创建全局 db 实例，避免模块导入时锁定数据库文件
