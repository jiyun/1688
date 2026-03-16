import sqlite3
import os
import json
from typing import Dict, List, Optional, Any
from contextlib import contextmanager


class Database:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(db_dir, "..", "products.db")
        
        self.db_path = os.path.abspath(db_path)
        self._init_database()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT UNIQUE NOT NULL,
                    shop_product_id TEXT,
                    output_path TEXT,
                    title TEXT,
                    status TEXT DEFAULT 'pending',
                    resource_counts TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sku_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT NOT NULL,
                    sku_name TEXT,
                    price REAL,
                    original_price REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(product_id)
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
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(product_id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS resources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_url TEXT NOT NULL,
                    resource_name TEXT,
                    downloaded INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(product_id)
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
            
            try:
                cursor.execute('ALTER TABLE products ADD COLUMN output_path TEXT')
            except:
                pass
            
            try:
                cursor.execute('ALTER TABLE products ADD COLUMN resource_counts TEXT')
            except:
                pass
            
            try:
                cursor.execute('ALTER TABLE products ADD COLUMN cost_prices TEXT')
            except:
                pass
            
            try:
                cursor.execute('ALTER TABLE products ADD COLUMN selling_prices TEXT')
            except:
                pass
    
    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM products WHERE product_id = ?
            ''', (product_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def get_all_products(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM products ORDER BY created_at DESC
            ''')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def update_shop_product_id(self, product_id: str, shop_product_id: str, output_path: str = None) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE products 
                SET shop_product_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE product_id = ?
            ''', (shop_product_id, product_id))
            
            if cursor.rowcount == 0:
                cursor.execute('''
                    INSERT INTO products (product_id, shop_product_id, output_path, status)
                    VALUES (?, ?, ?, 'pending')
                ''', (product_id, shop_product_id, output_path))
            elif output_path:
                cursor.execute('''
                    UPDATE products 
                    SET output_path = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE product_id = ?
                ''', (output_path, product_id))
            
            return True
    
    def update_output_path(self, product_id: str, output_path: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE products 
                SET output_path = ?, updated_at = CURRENT_TIMESTAMP
                WHERE product_id = ?
            ''', (output_path, product_id))
            
            if cursor.rowcount == 0:
                cursor.execute('''
                    INSERT INTO products (product_id, output_path, status)
                    VALUES (?, ?, 'pending')
                ''', (product_id, output_path))
            
            return True
    
    def update_resource_counts(self, product_id: str, main_images: int, color_images: int, detail_images: int, videos: int, output_path: str = None) -> bool:
        resource_counts = json.dumps([main_images, color_images, detail_images, videos])
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE products 
                SET resource_counts = ?, output_path = ?, status = 'completed', updated_at = CURRENT_TIMESTAMP
                WHERE product_id = ?
            ''', (resource_counts, output_path, product_id))
            
            if cursor.rowcount == 0:
                cursor.execute('''
                    INSERT INTO products (product_id, resource_counts, output_path, status)
                    VALUES (?, ?, ?, 'completed')
                ''', (product_id, resource_counts, output_path))
            
            return True
    
    def get_resource_counts(self, product_id: str) -> Optional[List[int]]:
        product = self.get_product(product_id)
        if product and product.get('resource_counts'):
            try:
                return json.loads(product['resource_counts'])
            except:
                return None
        return None
    
    def delete_product(self, product_id: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM sku_prices WHERE product_id = ?
            ''', (product_id,))
            cursor.execute('''
                DELETE FROM pricing WHERE product_id = ?
            ''', (product_id,))
            cursor.execute('''
                DELETE FROM products WHERE product_id = ?
            ''', (product_id,))
            return cursor.rowcount > 0
    
    def insert_product(self, product_id: str, title: str = None, shop_product_id: str = None, output_path: str = None) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO products (product_id, title, shop_product_id, output_path, status)
                VALUES (?, ?, ?, ?, 'pending')
            ''', (product_id, title, shop_product_id, output_path))
            return True
    
    def update_product_status(self, product_id: str, status: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE products 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE product_id = ?
            ''', (status, product_id))
            return cursor.rowcount > 0
    
    def insert_sku_price(self, product_id: str, sku_name: str, price: float, original_price: float = None) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sku_prices (product_id, sku_name, price, original_price)
                VALUES (?, ?, ?, ?)
            ''', (product_id, sku_name, price, original_price))
            return True
    
    def get_sku_prices(self, product_id: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM sku_prices WHERE product_id = ?
            ''', (product_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def save_sku_prices(self, product_id: str, sku_prices: List[Dict]) -> bool:
        cost_prices_array = []
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM sku_prices WHERE product_id = ?
            ''', (product_id,))
            
            for sku in sku_prices:
                color = sku.get('color', '')
                size = sku.get('size', '')
                price = sku.get('price')
                
                if color and size:
                    sku_name = f"{color}-{size}"
                elif color:
                    sku_name = color
                elif size:
                    sku_name = size
                else:
                    sku_name = "默认"
                
                if price is not None:
                    cursor.execute('''
                        INSERT INTO sku_prices (product_id, sku_name, price)
                        VALUES (?, ?, ?)
                    ''', (product_id, sku_name, price))
                    
                    cost_prices_array.append([color, size, str(price)])
            
            if cost_prices_array:
                cursor.execute('''
                    UPDATE products 
                    SET cost_prices = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE product_id = ?
                ''', (json.dumps(cost_prices_array, ensure_ascii=False), product_id))
            
            return True
    
    def save_main_price(self, product_id: str, price: float, min_amount: int = 1) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE products 
                SET title = ?, updated_at = CURRENT_TIMESTAMP
                WHERE product_id = ?
            ''', (f"¥{price} ({min_amount}件起批)", product_id))
            return True
    
    def save_consign_prices(self, product_id: str, consign_prices: List[Dict]) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for cp in consign_prices:
                min_amount = cp.get('min_amount', 1)
                price = cp.get('price')
                if price is not None:
                    cursor.execute('''
                        INSERT INTO sku_prices (product_id, sku_name, price)
                        VALUES (?, ?, ?)
                    ''', (product_id, f"代发{min_amount}件", price))
            return True
    
    def save_selling_prices(self, product_id: str, selling_prices: List[List]) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE products 
                SET selling_prices = ?, updated_at = CURRENT_TIMESTAMP
                WHERE product_id = ?
            ''', (json.dumps(selling_prices, ensure_ascii=False), product_id))
            return True
    
    def get_selling_prices(self, product_id: str) -> Optional[List]:
        product = self.get_product(product_id)
        if product and product.get('selling_prices'):
            try:
                return json.loads(product['selling_prices'])
            except:
                return None
        return None
    
    def save_resources(self, product_id: str, resources: Dict[str, List]) -> bool:
        """保存资源URL到数据库
        
        Args:
            product_id: 商品ID
            resources: 资源字典，包含 main_images, color_card_images, detail_images, videos
        
        Returns:
            是否保存成功
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 先删除该商品的旧资源记录
            cursor.execute('DELETE FROM resources WHERE product_id = ?', (product_id,))
            
            # 保存主图
            main_images = resources.get('main_images', [])
            for idx, item in enumerate(main_images):
                if isinstance(item, tuple):
                    url, name = item
                else:
                    url, name = item, str(idx + 1)
                
                cursor.execute('''
                    INSERT INTO resources (product_id, resource_type, resource_name, resource_url)
                    VALUES (?, ?, ?, ?)
                ''', (product_id, 'main_image', name, url))
            
            # 保存色卡图
            color_cards = resources.get('color_card_images', [])
            for item in color_cards:
                if isinstance(item, tuple):
                    url, name = item
                else:
                    url, name = item, ''
                
                if url:
                    cursor.execute('''
                        INSERT INTO resources (product_id, resource_type, resource_name, resource_url)
                        VALUES (?, ?, ?, ?)
                    ''', (product_id, 'color_image', name, url))
            
            # 保存详情图
            detail_images = resources.get('detail_images', [])
            for idx, url in enumerate(detail_images):
                cursor.execute('''
                    INSERT INTO resources (product_id, resource_type, resource_name, resource_url)
                    VALUES (?, ?, ?, ?)
                ''', (product_id, 'detail_image', str(idx + 1), url))
            
            # 保存视频
            videos = resources.get('videos', [])
            for idx, url in enumerate(videos):
                cursor.execute('''
                    INSERT INTO resources (product_id, resource_type, resource_name, resource_url)
                    VALUES (?, ?, ?, ?)
                ''', (product_id, 'video', str(idx + 1), url))
            
            return True
    
    def get_resources(self, product_id: str, resource_type: str = None) -> List[Dict[str, Any]]:
        """获取商品资源
        
        Args:
            product_id: 商品ID
            resource_type: 资源类型，None表示获取所有
        
        Returns:
            资源列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if resource_type:
                cursor.execute('''
                    SELECT * FROM resources 
                    WHERE product_id = ? AND resource_type = ?
                    ORDER BY id
                ''', (product_id, resource_type))
            else:
                cursor.execute('''
                    SELECT * FROM resources 
                    WHERE product_id = ?
                    ORDER BY 
                        CASE resource_type
                            WHEN 'main_image' THEN 1
                            WHEN 'color_image' THEN 2
                            WHEN 'video' THEN 3
                            WHEN 'detail_image' THEN 4
                        END,
                        id
                ''', (product_id,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_resources_by_type(self, product_id: str) -> Dict[str, List[Dict]]:
        """按类型获取商品资源
        
        Args:
            product_id: 商品ID
        
        Returns:
            按类型分组的资源字典
        """
        resources = self.get_resources(product_id)
        
        result = {
            'main_images': [],
            'color_images': [],
            'detail_images': [],
            'videos': []
        }
        
        for res in resources:
            res_type = res.get('resource_type', '')
            if res_type == 'main_image':
                result['main_images'].append(res)
            elif res_type == 'color_image':
                result['color_images'].append(res)
            elif res_type == 'detail_image':
                result['detail_images'].append(res)
            elif res_type == 'video':
                result['videos'].append(res)
        
        return result
    
    def mark_resource_downloaded(self, resource_id: int) -> bool:
        """标记资源已下载"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE resources SET downloaded = 1 WHERE id = ?
            ''', (resource_id,))
            return cursor.rowcount > 0
    
    def clear_resources(self, product_id: str) -> bool:
        """清除商品的所有资源记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM resources WHERE product_id = ?', (product_id,))
            return True
    
    def count_resources(self, product_id: str) -> Dict[str, int]:
        """从resources表实时计算资源计数
        
        Args:
            product_id: 商品ID
        
        Returns:
            各类型资源数量字典
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT resource_type, COUNT(*) as count
                FROM resources
                WHERE product_id = ?
                GROUP BY resource_type
            ''', (product_id,))
            
            result = {
                'main_images': 0,
                'color_images': 0,
                'detail_images': 0,
                'videos': 0
            }
            
            for row in cursor.fetchall():
                res_type = row['resource_type']
                count = row['count']
                if res_type == 'main_image':
                    result['main_images'] = count
                elif res_type == 'color_image':
                    result['color_images'] = count
                elif res_type == 'detail_image':
                    result['detail_images'] = count
                elif res_type == 'video':
                    result['videos'] = count
            
            return result


db = Database()
