#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查数据库中的价格数据"""

import os
import sys
sys.path.insert(0, r'c:\Users\jiyun\.trae-cn\1688')

from utils.database import Database

db = Database()

# 检查 sku_prices 表
print("=== sku_prices 表 ===")
sku_prices = db.query("SELECT * FROM sku_prices WHERE product_id = '724609852628'")
print(f"总记录数: {len(sku_prices)}")

# 统计每个 sku_name 的数量
from collections import Counter
sku_names = [s['sku_name'] for s in sku_prices]
sku_name_counts = Counter(sku_names)
print("\nSKU 名称统计:")
for name, count in sku_name_counts.items():
    print(f"  {name}: {count} 条")

# 显示前 20 条记录
print("\n前 20 条记录:")
for i, s in enumerate(sku_prices[:20]):
    print(f"  {i+1}. id={s['id']}, sku_name={s['sku_name']}, price={s['price']}")

db.close()
