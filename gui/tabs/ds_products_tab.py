import os
import re
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk
import webbrowser

from gui.utils import create_button


class DsProductsTabMixin:
    
    def _init_db_ds_products_tab(self):
        from utils.column_config import get_column_config
        
        self._ds_products_all_columns = {
            'product_id': {'text': '供应商商品ID', 'width': 105, 'anchor': 'center', 'default': True},
            'title': {'text': '商品标题', 'width': 180, 'anchor': 'w', 'default': True},
            'shop_product_id': {'text': 'DSID', 'width': 100, 'anchor': 'center', 'default': True},
            'ds_shop_url': {'text': 'DS店铺', 'width': 120, 'anchor': 'w', 'default': True},
            'price_matrix': {'text': 'DS价格矩阵', 'width': 100, 'anchor': 'center', 'default': True},
            'platform': {'text': '平台', 'width': 50, 'anchor': 'center', 'default': True},
            'resource_counts': {'text': '资源', 'width': 45, 'anchor': 'center', 'default': True},
            'status': {'text': '状态', 'width': 50, 'anchor': 'center', 'default': True},
            'created_at': {'text': '创建时间', 'width': 100, 'anchor': 'center', 'default': False},
        }
        
        config = get_column_config()
        saved_columns = config.get_visible_columns('ds_products')
        if saved_columns:
            self._ds_products_visible_columns = [col for col in saved_columns if col in self._ds_products_all_columns]
        else:
            self._ds_products_visible_columns = [col for col, cfg in self._ds_products_all_columns.items() if cfg['default']]
        
        self._ds_products_sort_column = None
        self._ds_products_sort_reverse = False
        
        filter_frame = ctk.CTkFrame(self.db_ds_products_tab, fg_color="transparent")
        filter_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(filter_frame, text="DS店铺:").pack(side="left", padx=5)
        self.ds_products_shop_filter = ctk.CTkOptionMenu(filter_frame, values=["全部"], width=150, command=self._on_ds_products_shop_filter_change)
        self.ds_products_shop_filter.pack(side="left", padx=5)
        self.ds_products_shop_filter.set("全部")
        
        self.ds_products_tree_frame = ctk.CTkFrame(self.db_ds_products_tab, fg_color="transparent")
        self.ds_products_tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self._create_ds_products_tree()
        
        ds_pro_btn_frame = ctk.CTkFrame(self.db_ds_products_tab, fg_color="transparent")
        ds_pro_btn_frame.pack(fill="x", pady=5)
        
        create_button(ds_pro_btn_frame, "刷新", self._refresh_ds_products, 'secondary', width=60).pack(side="left", padx=5)
        create_button(ds_pro_btn_frame, "关联供应商", self._link_supplier_product, 'primary', width=90).pack(side="left", padx=5)
        
        self.ds_products_status_label = ctk.CTkLabel(ds_pro_btn_frame, text="")
        self.ds_products_status_label.pack(side="right", padx=10)
    
    def _create_ds_products_tree(self):
        for widget in self.ds_products_tree_frame.winfo_children():
            widget.destroy()
        
        columns = tuple(self._ds_products_visible_columns)
        self.ds_products_tree = ttk.Treeview(self.ds_products_tree_frame, columns=columns, show="headings", selectmode="browse")
        
        for col in self._ds_products_visible_columns:
            cfg = self._ds_products_all_columns[col]
            self.ds_products_tree.heading(col, text=cfg['text'], command=lambda c=col: self._sort_ds_products_column(c))
            self.ds_products_tree.column(col, width=cfg['width'], anchor=cfg.get('anchor', 'center'))
        
        ds_pro_scrollbar = ttk.Scrollbar(self.ds_products_tree_frame, orient="vertical", command=self.ds_products_tree.yview)
        self.ds_products_tree.configure(yscrollcommand=ds_pro_scrollbar.set)
        
        self.ds_products_tree.pack(side="left", fill="both", expand=True)
        ds_pro_scrollbar.pack(side="right", fill="y")
        
        self.ds_products_tree.bind('<Double-1>', self._on_ds_products_tree_double_click)
        self.ds_products_tree.bind('<Button-3>', self._on_ds_products_right_click)
    
    def _on_ds_products_tree_double_click(self, event):
        selection = self.ds_products_tree.selection()
        if not selection:
            return
        
        item = self.ds_products_tree.item(selection[0])
        values = item.get('values', [])
        
        columns = self._ds_products_visible_columns
        if 'product_id' in columns and values:
            product_id = values[columns.index('product_id')]
            product_url = f"https://detail.1688.com/offer/{product_id}.html?sk=consign"
            self._open_url(product_url)
    
    def _on_ds_products_right_click(self, event):
        region = self.ds_products_tree.identify_region(event.x, event.y)
        if region == "heading":
            self._show_ds_products_column_menu(event)
        elif region == "cell" or region == "tree":
            self._show_ds_products_context_menu(event)
    
    def _show_ds_products_column_menu(self, event):
        menu = tk.Menu(self.ds_products_tree, tearoff=0)
        menu.add_command(label="显示/隐藏列", state="disabled")
        menu.add_separator()
        
        for col_name, cfg in self._ds_products_all_columns.items():
            is_visible = col_name in self._ds_products_visible_columns
            label = f"{'✓ ' if is_visible else '   '}{cfg['text']}"
            menu.add_command(label=label, command=lambda c=col_name: self._toggle_ds_products_column(c))
        
        menu.post(event.x_root, event.y_root)
    
    def _toggle_ds_products_column(self, column_name):
        from utils.column_config import get_column_config
        
        if column_name in self._ds_products_visible_columns:
            if len(self._ds_products_visible_columns) > 1:
                self._ds_products_visible_columns.remove(column_name)
        else:
            self._ds_products_visible_columns.append(column_name)
        
        config = get_column_config()
        config.set_visible_columns('ds_products', self._ds_products_visible_columns)
        
        self._create_ds_products_tree()
        self._refresh_ds_products()
    
    def _show_ds_products_context_menu(self, event):
        item = self.ds_products_tree.identify_row(event.y)
        if not item:
            return
        
        self.ds_products_tree.selection_set(item)
        values = self.ds_products_tree.item(item, 'values')
        if not values:
            return
        
        columns = self._ds_products_visible_columns
        product_id = values[columns.index('product_id')] if 'product_id' in columns else ''
        shop_product_id = values[columns.index('shop_product_id')] if 'shop_product_id' in columns else ''
        
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="访问供应商商品", command=lambda: self._open_url(f"https://detail.1688.com/offer/{product_id}.html?sk=consign"))
        
        if shop_product_id and shop_product_id != '-':
            menu.add_command(label="访问DS商品", command=lambda: self._open_url(f"https://detail.1688.com/offer/{shop_product_id}.html?sk=consign"))
        
        menu.add_separator()
        menu.add_command(label="查看商品详情", command=lambda: self._show_product_detail(product_id))
        menu.add_command(label="编辑DSID", command=lambda: self._edit_ds_product_id(item, product_id, shop_product_id))
        menu.add_separator()
        menu.add_command(label="关联供应商商品", command=lambda: self._link_supplier_to_ds_product(product_id))
        
        menu.post(event.x_root, event.y_root)
    
    def _sort_ds_products_column(self, column):
        if self._ds_products_sort_column == column:
            self._ds_products_sort_reverse = not self._ds_products_sort_reverse
        else:
            self._ds_products_sort_column = column
            self._ds_products_sort_reverse = False
        
        self._refresh_ds_products()
    
    def _on_ds_products_shop_filter_change(self, value):
        self._refresh_ds_products()
    
    def _refresh_ds_products(self):
        for item in self.ds_products_tree.get_children():
            self.ds_products_tree.delete(item)
        
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            
            shop_filter = self.ds_products_shop_filter.get()
            
            query = '''
                SELECT p.product_id, p.title, p.shop_product_id, p.ds_shop_url, 
                       p.price_matrix, p.platform, p.resource_counts, p.status, p.created_at
                FROM products p
                WHERE p.shop_product_id IS NOT NULL AND p.shop_product_id != ''
            '''
            params = []
            
            if shop_filter and shop_filter != "全部":
                query += " AND p.ds_shop_url LIKE ?"
                params.append(f"%{shop_filter}%")
            
            if self._ds_products_sort_column:
                col = self._ds_products_sort_column
                if col == 'product_id':
                    query += f" ORDER BY CAST(p.product_id AS BIGINT) {'DESC' if self._ds_products_sort_reverse else 'ASC'}"
                else:
                    query += f" ORDER BY p.{col} {'DESC' if self._ds_products_sort_reverse else 'ASC'}"
            else:
                query += " ORDER BY p.updated_at DESC"
            
            products = db.query(query, params if params else None)
            db.close()
            
            shops = set()
            for product in products:
                if product.get('ds_shop_url'):
                    shops.add(product.get('ds_shop_url'))
            
            shop_options = ["全部"] + sorted(list(shops))
            self.ds_products_shop_filter.configure(values=shop_options)
            
            for product in products:
                values = []
                for col in self._ds_products_visible_columns:
                    val = product.get(col, '') or '-'
                    if col == 'title' and val and len(str(val)) > 30:
                        val = str(val)[:30] + '...'
                    values.append(val)
                
                self.ds_products_tree.insert("", "end", values=values)
            
            self.ds_products_status_label.configure(text=f"共 {len(products)} 条DS商品关联")
            
        except Exception as e:
            self.log(f"刷新DS商品关联失败: {e}", "error")
    
    def _link_supplier_product(self):
        selection = self.ds_products_tree.selection()
        if not selection:
            self.show_info("提示", "请先选择一条DS商品记录")
            return
        
        item = self.ds_products_tree.item(selection[0])
        values = item.get('values', [])
        
        columns = self._ds_products_visible_columns
        product_id = values[columns.index('product_id')] if 'product_id' in columns else ''
        
        self._link_supplier_to_ds_product(product_id)
    
    def _link_supplier_to_ds_product(self, product_id: str):
        from tkinter import simpledialog
        
        supplier_id = simpledialog.askstring("关联供应商", f"请输入供应商商品ID:\n当前商品ID: {product_id}")
        if not supplier_id:
            return
        
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            
            supplier_product = db.query_one(
                "SELECT product_id, title FROM shop_products WHERE product_id = ?",
                [supplier_id]
            )
            
            if supplier_product:
                self.log(f"找到供应商商品: {supplier_id} - {supplier_product.get('title', '')[:30]}", "success")
            else:
                self.log(f"未在店铺商品中找到供应商商品: {supplier_id}", "warning")
            
            db.close()
            
        except Exception as e:
            self.log(f"关联供应商失败: {e}", "error")
    
    def _edit_ds_product_id(self, item, product_id: str, current_dsid: str):
        from tkinter import simpledialog
        
        new_dsid = simpledialog.askstring("编辑DSID", f"请输入新的DSID:\n当前DSID: {current_dsid}", initialvalue=current_dsid if current_dsid != '-' else '')
        if not new_dsid:
            return
        
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            
            db.update_product(product_id, {'shop_product_id': new_dsid})
            db.conn.execute('CHECKPOINT')
            db.close()
            
            self._refresh_ds_products()
            self.log(f"已更新DSID: {product_id} -> {new_dsid}", "success")
            
        except Exception as e:
            self.log(f"更新DSID失败: {e}", "error")
