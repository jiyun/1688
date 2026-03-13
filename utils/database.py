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
                CREATE INDEX IF NOT EXISTS idx_products_product_id ON products(product_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_products_shop_product_id ON products(shop_product_id)
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


db = Database()
