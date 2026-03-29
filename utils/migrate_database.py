#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本
将现有数据库结构迁移到新的优化结构
"""

import os
import sys
import shutil
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def migrate_database():
    """执行数据库迁移"""
    from utils.database import Database
    
    db = Database()
    
    print("=" * 50)
    print("数据库迁移脚本")
    print("=" * 50)
    
    # 1. 备份数据库（如果可能）
    db_path = 'products.duckdb'
    if os.path.exists(db_path):
        try:
            backup_path = f'products_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.duckdb'
            shutil.copy2(db_path, backup_path)
            print(f"✓ 数据库已备份到: {backup_path}")
        except PermissionError:
            print("⚠ 无法备份数据库（文件被锁定），继续迁移...")
    else:
        print("⚠ 数据库文件不存在，将创建新数据库")
    
    # 2. 添加新字段到现有表
    print("\n正在更新表结构...")
    
    try:
        # 为 products 表添加新字段
        db.conn.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS platform VARCHAR DEFAULT '1688'")
        db.conn.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS main_category VARCHAR")
        db.conn.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        print("✓ products 表已更新")
    except Exception as e:
        print(f"  products 表更新: {e}")
    
    try:
        # 为 resources 表添加新字段
        db.conn.execute("ALTER TABLE resources ADD COLUMN IF NOT EXISTS resource_index INTEGER")
        print("✓ resources 表已更新")
    except Exception as e:
        print(f"  resources 表更新: {e}")
    
    try:
        # 为 sku_prices 表添加新字段
        db.conn.execute("ALTER TABLE sku_prices ADD COLUMN IF NOT EXISTS color VARCHAR")
        db.conn.execute("ALTER TABLE sku_prices ADD COLUMN IF NOT EXISTS size VARCHAR")
        db.conn.execute("ALTER TABLE sku_prices ADD COLUMN IF NOT EXISTS cost_price DOUBLE")
        db.conn.execute("ALTER TABLE sku_prices ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        print("✓ sku_prices 表已更新")
    except Exception as e:
        print(f"  sku_prices 表更新: {e}")
    
    # 3. 创建索引
    print("\n正在创建索引...")
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_products_product_id ON products(product_id)",
        "CREATE INDEX IF NOT EXISTS idx_products_shop_id ON products(shop_id)",
        "CREATE INDEX IF NOT EXISTS idx_products_platform ON products(platform)",
        "CREATE INDEX IF NOT EXISTS idx_resources_product_id ON resources(product_id)",
        "CREATE INDEX IF NOT EXISTS idx_resources_type ON resources(resource_type)",
        "CREATE INDEX IF NOT EXISTS idx_resources_downloaded ON resources(downloaded)",
        "CREATE INDEX IF NOT EXISTS idx_sku_prices_product_id ON sku_prices(product_id)",
        "CREATE INDEX IF NOT EXISTS idx_sku_prices_color ON sku_prices(color)",
        "CREATE INDEX IF NOT EXISTS idx_sku_prices_size ON sku_prices(size)",
        "CREATE INDEX IF NOT EXISTS idx_product_extended_product_id ON product_extended(product_id)",
        "CREATE INDEX IF NOT EXISTS idx_shops_shop_id ON shops(shop_id)",
    ]
    
    for idx_sql in indexes:
        try:
            db.conn.execute(idx_sql)
        except Exception as e:
            print(f"  索引创建失败: {e}")
    
    print("✓ 索引创建完成")
    
    # 4. 更新 sku_prices 表的颜色和规格字段
    print("\n正在更新SKU价格数据...")
    
    try:
        # 从 sku_name 中提取颜色和规格
        db.conn.execute('''
            UPDATE sku_prices 
            SET color = CASE 
                WHEN sku_name LIKE '%>%' THEN TRIM(SPLIT_PART(sku_name, '>', 1))
                WHEN sku_name LIKE '% %' THEN TRIM(SPLIT_PART(sku_name, ' ', 1))
                ELSE sku_name
            END,
            size = CASE 
                WHEN sku_name LIKE '%>%' THEN TRIM(SPLIT_PART(sku_name, '>', 2))
                WHEN sku_name LIKE '% %' THEN TRIM(SPLIT_PART(sku_name, ' ', 2))
                ELSE '默认规格'
            END
            WHERE sku_name IS NOT NULL AND (color IS NULL OR size IS NULL)
        ''')
        print("✓ SKU价格数据已更新")
    except Exception as e:
        print(f"  SKU价格数据更新失败: {e}")
    
    # 5. 创建视图
    print("\n正在创建视图...")
    
    views = [
        '''CREATE VIEW IF NOT EXISTS v_product_full AS
        SELECT 
            p.product_id,
            p.title,
            p.category,
            p.sales_count,
            s.shop_name,
            s.shop_rating as shop_return_rate,
            pe.shop_service_score,
            pe.dsid,
            pe.monthly_sales,
            pe.positive_rate,
            p.updated_at
        FROM products p
        LEFT JOIN shops s ON p.shop_id = s.shop_id
        LEFT JOIN product_extended pe ON p.product_id = pe.product_id''',
        
        '''CREATE VIEW IF NOT EXISTS v_resource_stats AS
        SELECT 
            product_id,
            COUNT(CASE WHEN resource_type = 'main_image' THEN 1 END) as main_images,
            COUNT(CASE WHEN resource_type = 'color_card' THEN 1 END) as color_cards,
            COUNT(CASE WHEN resource_type = 'detail' THEN 1 END) as details,
            COUNT(CASE WHEN resource_type = 'video' THEN 1 END) as videos,
            SUM(CASE WHEN downloaded THEN 1 ELSE 0 END) as downloaded_count
        FROM resources
        GROUP BY product_id''',
        
        '''CREATE VIEW IF NOT EXISTS v_price_stats AS
        SELECT 
            product_id,
            MIN(price) as min_price,
            MAX(price) as max_price,
            AVG(price) as avg_price,
            SUM(stock) as total_stock
        FROM sku_prices
        GROUP BY product_id'''
    ]
    
    for view_sql in views:
        try:
            db.conn.execute(view_sql)
        except Exception as e:
            print(f"  视图创建失败: {e}")
    
    print("✓ 视图创建完成")
    
    # 6. 统计数据
    print("\n" + "=" * 50)
    print("迁移完成统计")
    print("=" * 50)
    
    products_count = db.conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    resources_count = db.conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
    sku_count = db.conn.execute("SELECT COUNT(*) FROM sku_prices").fetchone()[0]
    shops_count = db.conn.execute("SELECT COUNT(*) FROM shops").fetchone()[0]
    
    print(f"商品数量: {products_count}")
    print(f"资源数量: {resources_count}")
    print(f"SKU数量: {sku_count}")
    print(f"店铺数量: {shops_count}")
    
    db.close()
    
    print("\n✓ 数据库迁移完成！")

if __name__ == '__main__':
    migrate_database()
