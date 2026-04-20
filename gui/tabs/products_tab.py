import os
import re
import threading
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk
import webbrowser

from gui.utils import create_button
from gui.context_menu import ContextMenuManager, MenuItem, SEPARATOR, build_column_menu_items
from config import get_font


class ProductsTabMixin:
    
    def _init_db_products_tab(self):
        from utils.column_config import get_column_config
        
        self._products_menu = ContextMenuManager(self.root)
        self._products_all_columns = {
            'platform': {'text': '平台', 'width': 60, 'anchor': 'center', 'default': True},
            'product_id': {'text': '商品ID', 'width': 105, 'anchor': 'center', 'default': True},
            'title': {'text': '商品标题', 'width': 200, 'anchor': 'w', 'default': True},
            'ship_from': {'text': '发货地', 'width': 60, 'anchor': 'center', 'default': True},
            'resource_counts': {'text': '资源', 'width': 45, 'anchor': 'center', 'default': True},
            'sku_prices': {'text': 'SKU', 'width': 40, 'anchor': 'center', 'default': True},
            'remark': {'text': '备注', 'width': 80, 'anchor': 'w', 'default': True},
            'shop_name': {'text': 'DS店铺', 'width': 80, 'anchor': 'w', 'default': True},
            'shop_product_id': {'text': 'DSID', 'width': 85, 'anchor': 'center', 'default': True},
            'price_matrix': {'text': 'DS价格矩阵', 'width': 80, 'anchor': 'center', 'default': False},
            'output_path': {'text': '输出路径', 'width': 150, 'anchor': 'w', 'default': False},
            'status': {'text': '状态', 'width': 50, 'anchor': 'center', 'default': True},
            'created_at': {'text': '创建时间', 'width': 120, 'anchor': 'center', 'default': True},
        }
        
        config = get_column_config()
        saved_columns = config.get_visible_columns('products')
        if saved_columns:
            self._products_visible_columns = [col for col in saved_columns if col in self._products_all_columns]
        else:
            self._products_visible_columns = [col for col, cfg in self._products_all_columns.items() if cfg['default']]
        
        self.db_tree_frame = ctk.CTkFrame(self.db_products_tab, fg_color="transparent")
        self.db_tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self._create_products_tree()
        
        self._db_sort_column = None
        self._db_sort_reverse = False
        
        products_btn_frame = ctk.CTkFrame(self.db_products_tab, fg_color="transparent")
        products_btn_frame.pack(fill="x", pady=5)
        
        create_button(products_btn_frame, "导入", self._show_import_dialog, 'success', width=60).pack(side="left", padx=5)
        create_button(products_btn_frame, "导入扩展数据", self._import_extended_data, 'info', width=90).pack(side="left", padx=5)
        create_button(products_btn_frame, "刷新", self._refresh_db_data, 'secondary', width=60).pack(side="left", padx=5)
        
        self.products_status_label = ctk.CTkLabel(products_btn_frame, text="")
        self.products_status_label.pack(side="right", padx=10)
    
    def _create_products_tree(self):
        for widget in self.db_tree_frame.winfo_children():
            widget.destroy()
        
        columns = tuple(self._products_visible_columns)
        self.db_tree = ttk.Treeview(self.db_tree_frame, columns=columns, show="headings", selectmode="browse")
        
        for col in self._products_visible_columns:
            cfg = self._products_all_columns[col]
            self.db_tree.heading(col, text=cfg['text'], command=lambda c=col: self._sort_db_column(c))
            self.db_tree.column(col, width=cfg['width'], anchor=cfg.get('anchor', 'center'))
        
        db_scrollbar = ttk.Scrollbar(self.db_tree_frame, orient="vertical", command=self.db_tree.yview)
        self.db_tree.configure(yscrollcommand=db_scrollbar.set)
        
        self.db_tree.pack(side="left", fill="both", expand=True)
        db_scrollbar.pack(side="right", fill="y")
        
        self.db_tree.bind('<Button-3>', self._on_products_right_click)
        self.db_tree.bind('<Double-1>', self._on_db_tree_double_click)
        
        self._setup_products_drag_drop()
    
    def _setup_products_drag_drop(self):
        self._products_drag_start_x = 0
        self._products_drag_hint = None
        
        self.db_tree.bind('<Button-1>', self._on_products_drag_press, add='+')
        self.db_tree.bind('<B1-Motion>', self._on_products_drag_motion, add='+')
        self.db_tree.bind('<ButtonRelease-1>', self._on_products_drag_release, add='+')
    
    def _on_products_drag_press(self, event):
        region = self.db_tree.identify_region(event.x, event.y)
        if region == "heading":
            self._products_drag_start_x = event.x
    
    def _on_products_drag_motion(self, event):
        region = self.db_tree.identify_region(event.x, event.y)
        if region != "heading":
            self._hide_products_drag_hint()
            self._hide_products_drag_indicator()
            self._stop_products_drag_animation()
            return
        if abs(event.x - self._products_drag_start_x) > 15:
            self._show_products_drag_hint(event.x)
            self._show_products_drag_indicator(event.x)
            self._start_products_drag_animation()
    
    def _on_products_drag_release(self, event):
        self._hide_products_drag_hint()
        self._hide_products_drag_indicator()
        self._stop_products_drag_animation()
        
        region = self.db_tree.identify_region(event.x, event.y)
        if region != "heading" or abs(event.x - self._products_drag_start_x) < 15:
            return
        
        source_col = self.db_tree.identify_column(self._products_drag_start_x)
        target_col = self.db_tree.identify_column(event.x)
        
        if source_col and target_col and source_col != target_col:
            source_idx = int(source_col.replace('#', '')) - 1
            target_idx = int(target_col.replace('#', '')) - 1
            
            if 0 <= source_idx < len(self._products_visible_columns) and 0 <= target_idx < len(self._products_visible_columns):
                col_name = self._products_visible_columns[source_idx]
                self._products_visible_columns.pop(source_idx)
                self._products_visible_columns.insert(target_idx, col_name)
                
                from utils.column_config import get_column_config
                config = get_column_config()
                config.set_visible_columns('products', self._products_visible_columns)
                
                self._create_products_tree()
                self._refresh_db_data()
                self.log(f"列顺序已更新: 位置 {source_idx + 1} → {target_idx + 1}", "success")
    
    def _start_products_drag_animation(self):
        if not hasattr(self, '_products_drag_anim_id'):
            self._products_drag_anim_id = None
            self._products_drag_flash = False
        if self._products_drag_anim_id:
            return
        self._products_drag_flash = False
        self._animate_products_drag_flash()
    
    def _stop_products_drag_animation(self):
        if hasattr(self, '_products_drag_anim_id') and self._products_drag_anim_id:
            self.db_tree.after_cancel(self._products_drag_anim_id)
            self._products_drag_anim_id = None
    
    def _animate_products_drag_flash(self):
        if self._products_drag_hint and self._products_drag_hint.winfo_ismapped():
            self._products_drag_flash = not self._products_drag_flash
            self._products_drag_hint.configure(bg='#4a90d9' if self._products_drag_flash else '#2d6cb5')
            self._products_drag_anim_id = self.db_tree.after(300, self._animate_products_drag_flash)
    
    def _show_products_drag_hint(self, x: int):
        if self._products_drag_hint is None:
            self._products_drag_hint = tk.Label(
                self.db_tree, 
                text="↔ 拖动调整列顺序", 
                bg='#4a90d9', fg='white', padx=10, pady=3,
                font=('Microsoft YaHei UI', 9, 'bold'),
                relief='raised', borderwidth=1
            )
        col = self.db_tree.identify_column(x)
        if col:
            bbox = self.db_tree.bbox(col)
            if bbox:
                self._products_drag_hint.place(x=bbox[0], y=0, anchor='nw')
                return
        self._products_drag_hint.place(x=x, y=2, anchor='n')
    
    def _hide_products_drag_hint(self):
        if self._products_drag_hint:
            self._products_drag_hint.place_forget()
    
    def _show_products_drag_indicator(self, x: int):
        if not hasattr(self, '_products_drag_indicator'):
            self._products_drag_indicator = tk.Frame(self.db_tree, bg='#ff6b6b', width=3, height=25)
        col = self.db_tree.identify_column(x)
        if col:
            bbox = self.db_tree.bbox(col)
            if bbox:
                col_center = bbox[0] + bbox[2] // 2
                if x < col_center:
                    self._products_drag_indicator.place(x=bbox[0] - 2, y=0, anchor='nw')
                else:
                    self._products_drag_indicator.place(x=bbox[0] + bbox[2] - 1, y=0, anchor='nw')
                return
        self._products_drag_indicator.place(x=x, y=0, anchor='n')
    
    def _hide_products_drag_indicator(self):
        if hasattr(self, '_products_drag_indicator'):
            self._products_drag_indicator.place_forget()
    
    def _on_products_right_click(self, event):
        region = self.db_tree.identify_region(event.x, event.y)
        if region == "heading":
            self._show_products_column_menu(event)
        elif region == "cell" or region == "tree":
            self._show_db_context_menu(event)
    
    def _show_products_column_menu(self, event):
        items = build_column_menu_items(
            self._products_all_columns, self._products_visible_columns,
            self._toggle_products_column
        )
        self._products_menu.show(event, items)
    
    def _toggle_products_column(self, column_name):
        from utils.column_config import get_column_config
        
        if column_name in self._products_visible_columns:
            if len(self._products_visible_columns) > 1:
                self._products_visible_columns.remove(column_name)
        else:
            self._products_visible_columns.append(column_name)
        
        config = get_column_config()
        config.set_visible_columns('products', self._products_visible_columns)
        
        self._create_products_tree()
        self._refresh_db_data()
    
    def _import_extended_data(self):
        from tkinter import filedialog
        files = filedialog.askopenfilenames(
            title="选择HTML文件",
            filetypes=[("HTML文件", "*.html"), ("所有文件", "*.*")]
        )
        if not files:
            return
        
        from utils.extended_extractor import ExtendedDataExtractor
        from utils.database import get_shared_db
        
        db = get_shared_db()
        success_count = 0
        fail_count = 0
        
        for filepath in files:
            try:
                import re
                filename = os.path.basename(filepath)
                match = re.search(r'(\d+)', filename)
                if not match:
                    continue
                product_id = match.group(1)
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                extractor = ExtendedDataExtractor(html_content)
                data = extractor.extract_all()
                
                plugin_nav = data.get('plugin_nav', {})
                core_container = data.get('core_container', {})
                shop_ext = data.get('shop_info', {})
                
                ext_row = {}
                for key in ['category', 'listing_date', 'monthly_sales', 'monthly_dropship',
                           'yearly_volume', 'yearly_orders', 'review_count', 'positive_rate', 'pickup_rate']:
                    if plugin_nav.get(key) is not None:
                        ext_row[key] = plugin_nav[key]
                
                for key in ['procurement_trend', 'features', 'supplier_highlights']:
                    if core_container.get(key):
                        ext_row[key] = core_container[key]
                
                for key in ['shop_name', 'shop_years', 'shop_category', 'shop_return_rate',
                           'shop_service_score', 'shop_delivery_rate', 'shop_positive_rate']:
                    if shop_ext.get(key) is not None:
                        ext_row[key] = shop_ext[key]
                
                if ext_row:
                    db.save_product_extended(product_id, ext_row)
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                fail_count += 1
        
        db.close()
        
        if hasattr(self, 'log'):
            self.log(f"扩展数据导入完成: 成功 {success_count}, 失败 {fail_count}")
        self._refresh_db_data()

    def _refresh_db_data(self):
        for item in self.db_tree.get_children():
            self.db_tree.delete(item)
        
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            
            try:
                stats = db.get_statistics()
                self.db_stats_labels['total'].configure(text=str(stats['total_products']))
                self.db_stats_labels['resources'].configure(text=str(stats['total_resources']))
                self.db_stats_labels['downloaded'].configure(text=str(stats['downloaded_resources']))
                self.db_stats_labels['shops'].configure(text=str(stats['total_shops']))
                platform_str = '/'.join([f"{k}:{v}" for k, v in stats['by_platform'].items()])
                self.db_stats_labels['platform'].configure(text=platform_str if platform_str else '-')
                
                products = db.get_all_products()
                
                for product in products:
                    row_values = []

                    for col in self._products_visible_columns:
                        if col == 'platform':
                            platform = product.get('platform', 'alibaba')
                            # 统一平台名称显示
                            if platform in ('alibaba', '1688'):
                                row_values.append('1688')
                            elif platform == 'jd':
                                row_values.append('京东')
                            else:
                                row_values.append(platform or '未知')
                        elif col == 'product_id':
                            row_values.append(product.get('product_id', ''))
                        elif col == 'title':
                            title = product.get('title', '') or ''
                            if len(title) > 20:
                                title = title[:20] + '...'
                            row_values.append(title)
                        elif col == 'ship_from':
                            row_values.append(product.get('ship_from', '') or '-')
                        elif col == 'resource_counts':
                            resource_counts = db.count_resources(product.get('product_id', ''))
                            total = resource_counts['main_images'] + resource_counts['color_images'] + resource_counts['detail_images'] + resource_counts['videos']
                            row_values.append(f"{total}" if total > 0 else "-")
                        elif col == 'sku_prices':
                            count = db.count_sku_prices(product.get('product_id', ''))
                            row_values.append(f"{count}" if count > 0 else "-")
                        elif col == 'remark':
                            row_values.append(product.get('remark', '') or '-')
                        elif col == 'shop_name':
                            shop_name = product.get('ds_shop', '') or ''
                            if not shop_name:
                                shop_id = product.get('shop_id', '')
                                if shop_id:
                                    shop = db.get_shop(shop_id)
                                    if shop:
                                        shop_name = shop.get('shop_name', '')[:8]
                            row_values.append(shop_name)
                        elif col == 'shop_product_id':
                            row_values.append(product.get('shop_product_id', '') or '-')
                        elif col == 'price_matrix':
                            price_matrix = product.get('selling_prices', '')
                            if price_matrix:
                                try:
                                    import json
                                    prices_data = json.loads(price_matrix)
                                    if isinstance(prices_data, list) and len(prices_data) > 0:
                                        row_values.append(f"{len(prices_data)}条")
                                    else:
                                        row_values.append('-')
                                except:
                                    row_values.append('-')
                            else:
                                row_values.append('-')
                        elif col == 'output_path':
                            output_path = product.get('output_path', '') or ''
                            if len(output_path) > 18:
                                output_path = '...' + output_path[-15:]
                            row_values.append(output_path)
                        elif col == 'status':
                            status = product.get('status', '') or '-'
                            if status == 'pending':
                                status = '待处理'
                            elif status == 'completed':
                                status = '完成'
                            row_values.append(status)
                        elif col == 'created_at':
                            row_values.append(str(product.get('created_at', ''))[:16])
                    
                    self.db_tree.insert("", "end", values=row_values)
                
                self.products_status_label.configure(text=f"共 {len(products)} 条")
                
                self._update_ship_from_options(db, stats)
            finally:
                db.close()
        except Exception as e:
            self.log(f"读取数据库失败: {e}", "error")
            self.products_status_label.configure(text="读取失败")
    
    def _update_ship_from_options(self, db, stats):
        try:
            ship_from_list = ["全部"]
            for ship_from, count in stats.get('by_ship_from', {}).items():
                if ship_from and ship_from.strip():
                    ship_from_list.append(ship_from)
            
            current_selection = self.db_ship_from_var.get()
            self.db_ship_from_menu.configure(values=ship_from_list)
            
            if current_selection not in ship_from_list:
                self.db_ship_from_var.set("全部")
        except Exception:
            pass
    
    def _search_db_records(self):
        search_term = self.db_search_var.get().strip()
        
        if not search_term:
            self._refresh_db_data()
            return
        
        for item in self.db_tree.get_children():
            self.db_tree.delete(item)
        
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            
            products = db.search_products_by_id(search_term)
            
            for product in products:
                output_path = product.get('output_path', '') or ''
                if len(output_path) > 18:
                    output_path = '...' + output_path[-15:]
                
                title = product.get('title', '') or ''
                if len(title) > 20:
                    title = title[:20] + '...'
                
                product_id = product.get('product_id', '')
                
                platform = product.get('platform', 'alibaba')
                if platform == 'alibaba':
                    platform = '1688'
                elif platform == 'jd':
                    platform = '京东'
                
                sku_prices_count = db.count_sku_prices(product_id)
                sku_prices_str = f"{sku_prices_count}" if sku_prices_count > 0 else "-"
                
                resource_counts = db.count_resources(product_id)
                total_resources = resource_counts['main_images'] + resource_counts['color_images'] + resource_counts['detail_images'] + resource_counts['videos']
                resource_counts_str = f"{total_resources}" if total_resources > 0 else "-"
                
                shop_name = product.get('ds_shop', '') or ''
                if not shop_name:
                    shop_id = product.get('shop_id', '')
                    if shop_id:
                        shop = db.get_shop(shop_id)
                        if shop:
                            shop_name = shop.get('shop_name', '')[:8]
                
                ship_from = product.get('ship_from', '') or '-'
                shop_product_id = product.get('shop_product_id', '') or '-'
                
                price_matrix = product.get('selling_prices', '')
                if price_matrix:
                    try:
                        import json
                        prices_data = json.loads(price_matrix)
                        if isinstance(prices_data, list) and len(prices_data) > 0:
                            price_matrix = f"{len(prices_data)}条"
                        else:
                            price_matrix = '-'
                    except:
                        price_matrix = '-'
                else:
                    price_matrix = '-'
                
                status = product.get('status', '') or '-'
                if status == 'pending':
                    status = '待处理'
                elif status == 'completed':
                    status = '完成'
                
                remark = product.get('remark', '') or '-'
                
                self.db_tree.insert("", "end", values=(
                    platform, product_id, title, ship_from, resource_counts_str,
                    sku_prices_str, remark, shop_name, shop_product_id, price_matrix,
                    output_path, status, str(product.get('created_at', ''))[:16]
                ))
            
            self.db_status_label.configure(text=f"搜索结果: {len(products)} 条")
            
        except Exception as e:
            self.log(f"搜索失败: {e}", "error")
            self.db_status_label.configure(text="搜索失败")
    
    def _filter_by_platform(self, platform: str):
        self._apply_db_filters()
    
    def _filter_by_ship_from(self, ship_from: str):
        self._apply_db_filters()
    
    def _filter_by_status(self, status: str):
        self._apply_db_filters()
    
    def _apply_db_filters(self):
        for item in self.db_tree.get_children():
            self.db_tree.delete(item)
        
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            
            platform = self.db_platform_var.get()
            ship_from = self.db_ship_from_var.get()
            status = self.db_status_var.get()
            
            if platform == "全部" and ship_from == "全部" and status == "全部":
                products = db.get_all_products()
            else:
                products = db.search_products_full(
                    platform=platform if platform != "全部" else None,
                    ship_from=ship_from if ship_from != "全部" else None
                )
                if status != "全部":
                    status_map = {"完成": "completed", "待处理": "pending"}
                    products = [p for p in products if p.get('status') == status_map.get(status, status)]
            
            for product in products:
                output_path = product.get('output_path', '') or ''
                if len(output_path) > 18:
                    output_path = '...' + output_path[-15:]
                
                title = product.get('title', '') or ''
                if len(title) > 20:
                    title = title[:20] + '...'
                
                product_id = product.get('product_id', '')
                
                product_platform = product.get('platform', 'alibaba')
                if product_platform == 'alibaba':
                    product_platform = '1688'
                elif product_platform == 'jd':
                    product_platform = '京东'
                
                sku_prices_count = db.count_sku_prices(product_id)
                sku_prices_str = f"{sku_prices_count}" if sku_prices_count > 0 else "-"
                
                resource_counts = db.count_resources(product_id)
                total_resources = resource_counts['main_images'] + resource_counts['color_images'] + resource_counts['detail_images'] + resource_counts['videos']
                resource_counts_str = f"{total_resources}" if total_resources > 0 else "-"
                
                shop_name = product.get('ds_shop', '') or ''
                if not shop_name:
                    shop_id = product.get('shop_id', '')
                    if shop_id:
                        shop = db.get_shop(shop_id)
                        if shop:
                            shop_name = shop.get('shop_name', '')[:8]
                
                ship_from_val = product.get('ship_from', '') or '-'
                shop_product_id = product.get('shop_product_id', '') or '-'
                
                price_matrix = product.get('selling_prices', '')
                if price_matrix:
                    try:
                        import json
                        prices_data = json.loads(price_matrix)
                        if isinstance(prices_data, list) and len(prices_data) > 0:
                            price_matrix = f"{len(prices_data)}条"
                        else:
                            price_matrix = '-'
                    except:
                        price_matrix = '-'
                else:
                    price_matrix = '-'
                
                status_val = product.get('status', '') or '-'
                if status_val == 'pending':
                    status_val = '待处理'
                elif status_val == 'completed':
                    status_val = '完成'
                
                remark = product.get('remark', '') or '-'
                
                self.db_tree.insert("", "end", values=(
                    product_platform, product_id, title, ship_from_val, resource_counts_str,
                    sku_prices_str, remark, shop_name, shop_product_id, price_matrix,
                    output_path, status_val, str(product.get('created_at', ''))[:16]
                ))
            
            filter_desc = []
            if platform != "全部":
                filter_desc.append(f"平台:{platform}")
            if ship_from != "全部":
                filter_desc.append(f"发货地:{ship_from}")
            if status != "全部":
                filter_desc.append(f"状态:{status}")
            
            filter_str = " | ".join(filter_desc) if filter_desc else "全部"
            self.db_status_label.configure(text=f"{filter_str}: {len(products)} 条")
            
        except Exception as e:
            self.log(f"过滤失败: {e}", "error")
    
    def _validate_search_input(self, *args):
        pass
    
    def _open_product_page(self, product_id):
        from utils.database import get_shared_db
        
        db = get_shared_db()
        product = db.get_product(product_id)
        platform = product.get('platform', 'alibaba') if product else 'alibaba'
        
        if platform == 'jd':
            url = f"https://item.jd.com/{product_id}.html"
        else:
            url = f"https://detail.1688.com/offer/{product_id}.html"
        
        webbrowser.open(url)
        self.log(f"已打开商品页面: {url}")
    
    def _open_shop_page(self, product_id):
        from utils.database import get_shared_db
        
        db = get_shared_db()
        product = db.get_product(product_id)
        platform = product.get('platform', 'alibaba') if product else 'alibaba'
        shop_product_id = product.get('shop_product_id', '') if product else ''
        
        if platform == 'jd':
            if shop_product_id:
                url = f"https://mall.jd.com/index-{shop_product_id}.html"
            else:
                self.show_info("提示", "该商品没有店铺ID信息")
                return
        else:
            if shop_product_id:
                url = f"https://{shop_product_id}.1688.com"
            else:
                self.show_info("提示", "该商品没有店铺ID信息")
                return
        
        webbrowser.open(url)
        self.log(f"已打开店铺页面: {url}")
    
    def _on_db_tree_double_click(self, event):
        item = self.db_tree.identify_row(event.y)
        column = self.db_tree.identify_column(event.x)
        if not item:
            return
        
        self.db_tree.selection_set(item)
        values = self.db_tree.item(item, 'values')
        if not values:
            return
        
        columns = self._products_visible_columns
        product_id_idx = columns.index('product_id') if 'product_id' in columns else 1
        product_id = values[product_id_idx] if product_id_idx < len(values) else ''
        
        col_index = int(column.replace('#', '')) - 1
        
        if 'remark' in columns:
            remark_idx = columns.index('remark')
            if col_index == remark_idx and remark_idx < len(values):
                self._inline_edit_cell(item, product_id, 'remark', 'remark', values[remark_idx], column)
                return
        
        if 'shop_name' in columns:
            shop_name_idx = columns.index('shop_name')
            if col_index == shop_name_idx and shop_name_idx < len(values):
                self._inline_edit_cell(item, product_id, 'ds_shop', 'shop_name', values[shop_name_idx], column)
                return
        
        if 'shop_product_id' in columns:
            dsid_idx = columns.index('shop_product_id')
            if col_index == dsid_idx and dsid_idx < len(values):
                self._inline_edit_cell(item, product_id, 'shop_product_id', 'shop_product_id', values[dsid_idx], column, is_dsid=True)
                return
        
        self._show_product_detail(product_id)
    
    def _inline_edit_cell(self, item, product_id: str, db_field: str, tree_column: str, current_value: str, column, is_dsid: bool = False):
        from utils.database import get_shared_db
        
        if current_value == '-':
            current_value = ''
        
        x, y, width, height = self.db_tree.bbox(item, column)
        
        entry = tk.Entry(self.db_tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, current_value)
        entry.focus_set()
        entry.select_range(0, tk.END)
        
        db = get_shared_db()
        
        def save(event=None):
            new_value = entry.get().strip()
            
            if is_dsid and new_value and not new_value.isdigit():
                self.log("DSID必须为纯数字", "error")
                return
            
            try:
                db.update_product(product_id, {db_field: new_value if new_value else None})
                db.conn.execute('CHECKPOINT')
                self.db_tree.set(item, column=tree_column, value=new_value if new_value else '-')
                self.log(f"已保存: {product_id} -> {db_field}: {new_value}")
                
                if is_dsid and hasattr(self, '_refresh_ds_products'):
                    self._refresh_ds_products()
            except Exception as e:
                self.log(f"保存失败: {e}", "error")
            
            entry.destroy()
        
        def cancel(event=None):
            entry.destroy()
        
        entry.bind('<Return>', save)
        entry.bind('<Escape>', cancel)
        entry.bind('<FocusOut>', save)
    
    def _show_db_context_menu(self, event):
        item = self.db_tree.identify_row(event.y)
        if not item:
            return
        
        self.db_tree.selection_set(item)
        
        values = self.db_tree.item(item, 'values')
        if not values:
            return
        
        columns = self._products_visible_columns
        
        platform = values[columns.index('platform')] if 'platform' in columns else '1688'
        product_id = values[columns.index('product_id')] if 'product_id' in columns else values[0] if values else ''
        
        shop_product_id = values[columns.index('shop_product_id')] if 'shop_product_id' in columns else None
        output_path = values[columns.index('output_path')] if 'output_path' in columns and columns.index('output_path') < len(values) else None
        
        items = [
            MenuItem("查看商品详情", command=lambda: self._show_product_detail(product_id)),
            MenuItem("查看店铺信息", command=lambda: self._show_shop_info(product_id)),
            SEPARATOR,
        ]
        
        if platform == '1688':
            items.append(MenuItem("访问原址", command=lambda: self._open_product_page(product_id)))
        elif platform == '京东':
            items.append(MenuItem("访问原址", command=lambda: webbrowser.open(f"https://item.jd.com/{product_id}.html")))
        
        items.extend([
            MenuItem("显示资源", command=lambda: self._show_resources_dialog(product_id)),
            MenuItem("打开输出路径", command=lambda: self._open_output_directory(product_id, output_path)),
            MenuItem("重新定位目录", command=lambda: self._relocate_output_directory(product_id, output_path)),
        ])
        
        if shop_product_id and shop_product_id != '-':
            items.extend([MenuItem("访问店铺商品页", command=lambda: webbrowser.open(f"https://detail.1688.com/offer/{shop_product_id}.html?sk=consign"))])
        
        items.append(SEPARATOR)
        
        consign_url = f"https://detail.1688.com/offer/{product_id}.html?sk=consign"
        shop_new_url = f"https://item.upload.taobao.com/from1688/publish.htm?&sourceId={product_id}"
        items.extend([
            MenuItem("铺货页面", command=lambda: self._copy_url_to_clipboard(consign_url, "铺货页面")),
            MenuItem("店铺上新", command=lambda: self._copy_url_to_clipboard(shop_new_url, "店铺上新")),
        ])
        
        if shop_product_id and shop_product_id != '-':
            edit_url = f"https://item.upload.taobao.com/sell/v2/publish.htm?itemId={shop_product_id}&fromAIPublish=true&newRouter=1&fromAICategory=true"
            items.append(MenuItem("编辑商品", command=lambda: self._copy_url_to_clipboard(edit_url, "编辑商品")))
        
        items.extend([
            SEPARATOR,
            MenuItem("价格计算", command=lambda: self.open_pricing_tool(product_id)),
            MenuItem("图片编辑", command=lambda: self._open_image_editor(product_id)),
            MenuItem("在线采集", command=lambda: self._db_online_collect_for_item(product_id)),
            MenuItem("导入扩展数据", command=lambda: self._import_extended_data_for_item(product_id)),
            SEPARATOR,
            MenuItem("关联DS店铺", command=lambda: self._link_to_ds_shop(product_id)),
            MenuItem("查看DS关联", command=lambda: self._show_product_ds_status(product_id)),
            SEPARATOR,
            MenuItem("删除记录", command=self._delete_db_record),
        ])
        
        self._products_menu.show(event, items)
    
    def _copy_url_to_clipboard(self, url: str, name: str):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.log(f"已复制{name}链接: {url}")
        except Exception as e:
            self.log(f"复制失败: {e}", "error")
    
    def _open_output_directory(self, product_id: str, output_path: str = None, force_locate: bool = False):
        target_path = None
        
        if output_path and output_path != '-' and os.path.exists(output_path) and not force_locate:
            target_path = output_path
            self.log(f"打开输出路径: {target_path}")
        elif HAS_PATH_MATCHER:
            effective_path, match_result = get_effective_output_path(product_id, output_path or "")
            
            if match_result.match_type == "temp" and not force_locate:
                target_path = effective_path
            elif match_result.is_available and not force_locate:
                target_path = effective_path
            elif match_result.matched_path and match_result.match_confidence > 0.5 and not force_locate:
                target_path = match_result.matched_path
                self.log(f"智能匹配到路径: {target_path} (置信度: {match_result.match_confidence:.0%})")
            else:
                result = show_path_locator_dialog(
                    self.root, product_id, output_path or "",
                    match_result.suggestions if hasattr(match_result, 'suggestions') else [],
                    match_result.matched_path
                )
                
                if result and result != "__SKIP__":
                    set_temp_output_path(product_id, result)
                    target_path = result
                    self.log(f"已设置临时路径: {result}")
                elif result == "__SKIP__":
                    return
                else:
                    return
        else:
            default_base = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'products', 'upload')
            product_path = os.path.join(default_base, product_id)
            if os.path.exists(product_path):
                target_path = product_path
            elif os.path.exists(default_base):
                target_path = default_base
        
        if target_path:
            import subprocess
            subprocess.run(['explorer', target_path])
        else:
            self.show_info("提示", "输出目录不存在，请手动定位路径")
    
    def _relocate_output_directory(self, product_id: str, output_path: str = None):
        if HAS_PATH_MATCHER:
            _, match_result = get_effective_output_path(product_id, output_path or "")
            
            result = show_path_locator_dialog(
                self.root, product_id, output_path or "",
                match_result.suggestions if hasattr(match_result, 'suggestions') else [],
                match_result.matched_path
            )
            
            if result and result != "__SKIP__":
                set_temp_output_path(product_id, result)
                
                try:
                    from utils.database import get_shared_db
                    db = get_shared_db()
                    db.update_output_path(product_id, result)
                    self.log(f"已更新输出路径: {product_id} -> {result}")
                    self._refresh_db_view()
                except Exception as e:
                    self.log(f"更新输出路径失败: {e}", "warning")
                
                import subprocess
                subprocess.run(['explorer', result])
        else:
            self.show_info("提示", "路径匹配功能不可用")
    
    def _open_image_editor(self, product_id: str):
        try:
            from gui.image_editor import ImageEditorWindow
            editor = ImageEditorWindow(self.root, product_id)
            editor.focus_set()
            self.log(f"已打开图片编辑器: {product_id}")
        except Exception as e:
            self.log(f"打开图片编辑器失败: {e}", "error")
            self.show_info("错误", f"打开图片编辑器失败: {e}")
    
    def _show_product_detail(self, product_id: str):
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            product = db.get_product(product_id)
            
            if not product:
                self.show_info("提示", "未找到商品记录")
                return
            
            dialog = ctk.CTkToplevel(self.root)
            dialog.title(f"商品详情 - {product_id}")
            dialog.geometry("900x500")
            dialog.minsize(700, 400)
            dialog.transient(self.root)
            dialog.grab_set()
            
            main_frame = ctk.CTkFrame(dialog)
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            columns = ("字段", "值")
            tree = ttk.Treeview(main_frame, columns=columns, show="headings", height=20)
            
            tree.heading("字段", text="字段")
            tree.heading("值", text="值")
            
            tree.column("字段", width=150)
            tree.column("值", width=700)
            
            field_names = {
                'product_id': '商品ID', 'shop_product_id': '店铺商品ID', 'title': '标题',
                'description': '描述', 'product_url': '商品链接', 'product_code': '商品编码',
                'shop_id': '店铺ID', 'status': '状态', 'platform': '平台',
                'ship_from': '发货地', 'sales_count': '销量', 'min_order': '最小起订量',
                'shipping_cost': '运费', 'unit_price': '一口价', 'output_path': '输出路径',
                'resource_counts': '资源统计', 'cost_prices': '成本价格',
                'selling_prices': '销售价格', 'main_category': '主分类',
                'ds_shop_url': 'DS店铺', 'user_remark': '用户备注',
                'created_at': '创建时间', 'updated_at': '更新时间'
            }
            
            for key, label in field_names.items():
                value = product.get(key, '')
                if value is None:
                    value = ''
                if isinstance(value, str) and len(value) > 100:
                    value = value[:100] + '...'
                tree.insert("", "end", iid=key, values=(label, str(value)))
            
            for key, value in product.items():
                if key not in field_names:
                    if isinstance(value, str) and len(value) > 100:
                        value = value[:100] + '...'
                    tree.insert("", "end", iid=key, values=(key, str(value)))
            
            rate_info = db.get_rate_info(product_id)
            if rate_info:
                tree.insert("", "end", iid="_rate_sep", values=("─── 评价信息 ───", ""))
                tree.insert("", "end", iid="good_rates", values=("好评数", rate_info.get('good_rates', 0)))
                tree.insert("", "end", iid="goods_grade", values=("商品评分", rate_info.get('goods_grade', '-')))
                
                impression_tags = rate_info.get('impression_tags', [])
                if impression_tags:
                    tags_str = ', '.join([f"{t.get('name', '')}({t.get('count', 0)})" for t in impression_tags[:5]])
                    tree.insert("", "end", iid="impression_tags", values=("印象标签", tags_str))
                
                common_tags = rate_info.get('common_tags', [])
                if common_tags:
                    tags_str = ', '.join([f"{t.get('name', '')}({t.get('count', 0)})" for t in common_tags[:5]])
                    tree.insert("", "end", iid="common_tags", values=("常见标签", tags_str))
            
            def on_double_click(event):
                selected = tree.selection()
                if not selected:
                    return
                
                item_id = selected[0]
                item = tree.item(item_id)
                field_label = item['values'][0]
                value = item['values'][1]
                
                if item_id == 'description' or field_label == '描述':
                    self._show_description_dialog(product_id, value)
                else:
                    dialog.clipboard_clear()
                    dialog.clipboard_append(value)
                    self.log(f"已复制: {value[:50]}...")
            
            tree.bind("<Double-1>", on_double_click)
            
            scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            tree.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            btn_frame = ctk.CTkFrame(dialog)
            btn_frame.pack(fill="x", pady=10)
            
            ctk.CTkLabel(btn_frame, text="双击行可复制值，描述字段双击查看属性", font=get_font(self.available_font, 'sm')).pack(side="left", padx=10)
            create_button(btn_frame, "关闭", dialog.destroy, 'secondary', size='compact', width=80).pack(side="right", padx=5)
            
        except Exception as e:
            self.log(f"获取商品详情失败: {e}", "error")
            self.show_info("错误", f"获取商品详情失败: {e}")
    
    def _show_description_dialog(self, product_id: str, description: str):
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            
            attributes = db.get_attributes(product_id)
            
            dialog = ctk.CTkToplevel(self.root)
            dialog.title(f"商品属性 - {product_id}")
            dialog.geometry("600x400")
            dialog.minsize(450, 300)
            dialog.transient(self.root)
            dialog.grab_set()
            
            main_frame = ctk.CTkFrame(dialog)
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            columns = ("属性名", "属性值")
            tree = ttk.Treeview(main_frame, columns=columns, show="headings", height=15)
            
            tree.heading("属性名", text="属性名")
            tree.heading("属性值", text="属性值")
            
            tree.column("属性名", width=200)
            tree.column("属性值", width=350)
            
            if attributes:
                for attr in attributes:
                    attr_name = attr.get('attr_name', '') or attr.get('name', '')
                    attr_value = attr.get('attr_value', '') or attr.get('value', '')
                    tree.insert("", "end", values=(attr_name, attr_value))
            else:
                if description:
                    lines = description.split('\n')
                    for line in lines:
                        if ':' in line or '：' in line:
                            sep = '：' if '：' in line else ':'
                            parts = line.split(sep, 1)
                            if len(parts) == 2:
                                tree.insert("", "end", values=(parts[0].strip(), parts[1].strip()))
                        elif line.strip():
                            tree.insert("", "end", values=("", line.strip()))
                
                if not tree.get_children():
                    tree.insert("", "end", values=("-", "无属性数据"))
            
            def copy_value(event):
                selected = tree.selection()
                if selected:
                    item = tree.item(selected[0])
                    value = f"{item['values'][0]}: {item['values'][1]}"
                    dialog.clipboard_clear()
                    dialog.clipboard_append(value)
                    self.log(f"已复制: {value[:50]}...")
            
            tree.bind("<Double-1>", copy_value)
            
            scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            tree.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            btn_frame = ctk.CTkFrame(dialog)
            btn_frame.pack(fill="x", pady=10)
            
            ctk.CTkLabel(btn_frame, text="双击行可复制", font=get_font(self.available_font, 'sm')).pack(side="left", padx=10)
            create_button(btn_frame, "关闭", dialog.destroy, 'secondary', size='compact', width=80).pack(side="right", padx=5)
            
        except Exception as e:
            self.log(f"获取商品属性失败: {e}", "error")
            self.show_info("错误", f"获取商品属性失败: {e}")
    
    def _show_shop_info(self, product_id: str):
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            product = db.get_product(product_id)
            
            if not product:
                self.show_info("提示", "未找到商品记录")
                return
            
            shop_id = product.get('shop_id', '')
            if not shop_id:
                self.show_info("提示", "该商品没有关联店铺信息")
                return
            
            shop = db.get_shop(shop_id)
            if not shop:
                self.show_info("提示", "未找到店铺记录")
                return
            
            dialog = ctk.CTkToplevel(self.root)
            dialog.title(f"店铺信息 - {shop_id}")
            dialog.geometry("800x400")
            dialog.minsize(600, 300)
            dialog.transient(self.root)
            dialog.grab_set()
            
            main_frame = ctk.CTkFrame(dialog)
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            columns = ("字段", "值")
            tree = ttk.Treeview(main_frame, columns=columns, show="headings", height=15)
            
            tree.heading("字段", text="字段")
            tree.heading("值", text="值")
            
            tree.column("字段", width=150)
            tree.column("值", width=600)
            
            field_names = {
                'shop_id': '店铺ID', 'shop_name': '店铺名称', 'shop_url': '店铺链接',
                'platform': '平台', 'rating': '评分', 'sales': '销量',
                'location': '地址', 'created_at': '创建时间', 'updated_at': '更新时间'
            }
            
            for key, label in field_names.items():
                value = shop.get(key, '')
                if value is None:
                    value = ''
                if isinstance(value, str) and len(value) > 100:
                    value = value[:100] + '...'
                tree.insert("", "end", values=(label, str(value)))
            
            for key, value in shop.items():
                if key not in field_names:
                    if isinstance(value, str) and len(value) > 100:
                        value = value[:100] + '...'
                    tree.insert("", "end", values=(key, str(value)))
            
            def copy_value(event):
                selected = tree.selection()
                if selected:
                    item = tree.item(selected[0])
                    value = item['values'][1]
                    dialog.clipboard_clear()
                    dialog.clipboard_append(value)
                    self.log(f"已复制: {value[:50]}...")
            
            tree.bind("<Double-1>", copy_value)
            
            scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            tree.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            btn_frame = ctk.CTkFrame(dialog)
            btn_frame.pack(fill="x", pady=10)
            
            ctk.CTkLabel(btn_frame, text="双击行可复制值", font=get_font(self.available_font, 'sm')).pack(side="left", padx=10)
            create_button(btn_frame, "关闭", dialog.destroy, 'secondary', size='compact', width=80).pack(side="right", padx=5)
            
        except Exception as e:
            self.log(f"获取店铺信息失败: {e}", "error")
            self.show_info("错误", f"获取店铺信息失败: {e}")
    
    def _sort_db_column(self, col):
        items = [(self.db_tree.set(item, col), item) for item in self.db_tree.get_children('')]
        
        if self._db_sort_column == col:
            self._db_sort_reverse = not self._db_sort_reverse
        else:
            self._db_sort_column = col
            self._db_sort_reverse = False
        
        def natural_sort_key(s):
            s = str(s)
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]
        
        def sort_key(x):
            val = x[0]
            if col == 'product_id':
                try:
                    return int(val)
                except:
                    return natural_sort_key(val)
            try:
                return float(val.replace('-', '0').replace('条', ''))
            except ValueError:
                return natural_sort_key(val)
        
        items.sort(key=sort_key, reverse=self._db_sort_reverse)
        
        for index, (val, item) in enumerate(items):
            self.db_tree.move(item, '', index)
    
    def _db_online_collect_for_item(self, product_id: str):
        url = f"https://detail.1688.com/offer/{product_id}.html"
        
        self.log(f"准备在线采集: {url}", "info")
        
        def collect_thread():
            try:
                from gui.online_collector_gui import get_collector
                
                collector = get_collector(self.log)
                
                if not collector.browser_started:
                    self.log("正在启动浏览器...")
                    if not collector.start_browser():
                        self.log("浏览器启动失败", "error")
                        return
                
                self.log("正在采集数据...")
                data = collector.collect_data_direct(product_id)
                
                if data:
                    self.log("数据采集成功，正在保存到数据库...")
                    self._save_online_collect_data(data)
                    self.log("数据已保存到数据库", "success")
                    
                    self.root.after(0, self._refresh_db_data)
                else:
                    self.log("数据采集失败", "error")
                    
            except Exception as e:
                self.log(f"在线采集异常: {e}", "error")
                import traceback
                traceback.print_exc()
        
        thread = threading.Thread(target=collect_thread, daemon=True)
        thread.start()
    
    def _import_extended_data_for_item(self, product_id: str):
        from tkinter import filedialog
        files = filedialog.askopenfilenames(
            title=f"选择 {product_id} 的HTML文件",
            filetypes=[("HTML文件", "*.html"), ("所有文件", "*.*")]
        )
        if not files:
            return
        
        from utils.extended_extractor import ExtendedDataExtractor
        from utils.database import get_shared_db
        
        db = get_shared_db()
        success = False
        
        for filepath in files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                extractor = ExtendedDataExtractor(html_content)
                data = extractor.extract_all()
                
                plugin_nav = data.get('plugin_nav', {})
                core_container = data.get('core_container', {})
                shop_ext = data.get('shop_info', {})
                
                ext_row = {}
                for key in ['category', 'listing_date', 'monthly_sales', 'monthly_dropship',
                           'yearly_volume', 'yearly_orders', 'review_count', 'positive_rate', 'pickup_rate']:
                    if plugin_nav.get(key) is not None:
                        ext_row[key] = plugin_nav[key]
                for key in ['procurement_trend', 'features', 'supplier_highlights']:
                    if core_container.get(key):
                        ext_row[key] = core_container[key]
                for key in ['shop_name', 'shop_years', 'shop_category', 'shop_return_rate',
                           'shop_service_score', 'shop_delivery_rate', 'shop_positive_rate']:
                    if shop_ext.get(key) is not None:
                        ext_row[key] = shop_ext[key]
                
                if ext_row:
                    db.save_product_extended(product_id, ext_row)
                    success = True
                    if hasattr(self, 'log'):
                        self.log(f"扩展数据已导入: {product_id} ({len(ext_row)} 项)")
                    break
            except Exception as e:
                if hasattr(self, 'log'):
                    self.log(f"导入扩展数据失败: {e}", "error")
        
        db.close()
        
        if not success and hasattr(self, 'log'):
            self.log(f"未提取到有效扩展数据: {product_id}", "warning")
    
    def _show_resources_dialog(self, product_id: str):
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            resources = db.get_resources_by_type(product_id)
            
            product = db.get_product(product_id)
            output_path = product.get('output_path', '') if product else ''
            
            dialog = ctk.CTkToplevel(self.root)
            dialog.title(f"资源链接 - {product_id}")
            dialog.geometry("1100x650")
            dialog.minsize(850, 500)
            dialog.transient(self.root)
            dialog.grab_set()
            
            main_frame = ctk.CTkFrame(dialog)
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            notebook = ctk.CTkTabview(main_frame)
            notebook.pack(fill="both", expand=True)
            
            type_order = [
                ('main_image', '主图'),
                ('color_image', '色卡图'),
                ('detail_image', '详情图'),
                ('video', '视频')
            ]
            
            for res_type, tab_name in type_order:
                res_list = resources.get(res_type, [])
                
                tab = notebook.add(tab_name)
                
                columns = ("文件名", "URL", "状态", "分辨率", "大小", "下载时间")
                tree = ttk.Treeview(tab, columns=columns, show="headings", height=15)
                
                tree.heading("文件名", text="文件名")
                tree.heading("URL", text="URL")
                tree.heading("状态", text="状态")
                tree.heading("分辨率", text="分辨率")
                tree.heading("大小", text="大小")
                tree.heading("下载时间", text="下载时间")
                
                tree.column("文件名", width=150)
                tree.column("URL", width=400)
                tree.column("状态", width=80)
                tree.column("分辨率", width=80)
                tree.column("大小", width=100)
                tree.column("下载时间", width=150)
                
                for res in res_list:
                    status = "已下载" if res.get('downloaded') else "待下载"
                    file_size = res.get('file_size', 0) or 0
                    size_str = f"{file_size / 1024:.1f} KB" if file_size > 0 else "-"
                    download_time = str(res.get('download_time', ''))[:19] if res.get('download_time') else "-"
                    
                    resolution = "-"
                    local_path = None
                    if output_path and res.get('output_filename'):
                        local_path = os.path.join(output_path, res.get('output_filename'))
                    
                    if local_path and os.path.exists(local_path):
                        try:
                            if res_type == 'video':
                                try:
                                    import cv2
                                    cap = cv2.VideoCapture(local_path)
                                    if cap.isOpened():
                                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                                        resolution = f"{width}x{height}"
                                        cap.release()
                                except ImportError:
                                    pass
                            else:
                                from PIL import Image
                                with Image.open(local_path) as img:
                                    resolution = f"{img.width}x{img.height}"
                        except Exception:
                            resolution = "-"
                    
                    tree.insert("", "end", values=(
                        res.get('output_filename', ''),
                        res.get('resource_url', '')[:80] + '...' if len(res.get('resource_url', '')) > 80 else res.get('resource_url', ''),
                        status, resolution, size_str, download_time
                    ))
                
                if not res_list:
                    tree.insert("", "end", values=("-", "无数据", "-", "-", "-", "-"))
                
                scrollbar = ttk.Scrollbar(tab, orient="vertical", command=tree.yview)
                tree.configure(yscrollcommand=scrollbar.set)
                tree.pack(side="left", fill="both", expand=True)
                scrollbar.pack(side="right", fill="y")
                
                def copy_url(event, tree=tree):
                    selected = tree.selection()
                    if selected:
                        item = tree.item(selected[0])
                        url = item['values'][1]
                        if url.endswith('...'):
                            self.show_info("提示", "URL过长，请从数据库中查看完整URL")
                        else:
                            dialog.clipboard_clear()
                            dialog.clipboard_append(url)
                            self.log(f"已复制URL: {url[:50]}...")
                
                tree.bind("<Double-1>", copy_url)
            
            btn_frame = ctk.CTkFrame(main_frame)
            btn_frame.pack(fill="x", pady=10)
            
            def check_resources():
                self._check_resources_status(product_id, output_path)
                self._show_resources_dialog(product_id)
                dialog.destroy()
            
            def redownload_resources():
                dialog.destroy()
                self._download_product_resources(product_id, force=True)
            
            create_button(btn_frame, "检查", check_resources, 'primary', size='compact', width=80).pack(side="left", padx=5)
            create_button(btn_frame, "重新下载", redownload_resources, 'warning', size='compact', width=80).pack(side="left", padx=5)
            create_button(btn_frame, "关闭", dialog.destroy, 'secondary', size='compact', width=80).pack(side="right", padx=5)
            
        except Exception as e:
            self.log(f"获取资源链接失败: {e}", "error")
            self.show_info("错误", f"获取资源链接失败: {e}")
    
    def _check_resources_status(self, product_id: str, output_path: str):
        try:
            if not output_path or not os.path.exists(output_path):
                self.log("输出路径不存在", "warning")
                return
            
            from utils.database import get_shared_db
            db = get_shared_db()
            resources = db.get_resources_by_type(product_id)
            
            has_cv2 = False
            try:
                import cv2
                has_cv2 = True
            except ImportError:
                pass
            
            checked_count = 0
            for res_type in ['main_image', 'color_image', 'detail_image', 'video']:
                res_list = resources.get(res_type, [])
                
                for res in res_list:
                    local_path = None
                    if output_path and res.get('output_filename'):
                        local_path = os.path.join(output_path, res.get('output_filename'))
                    
                    if local_path and os.path.exists(local_path):
                        try:
                            file_size = os.path.getsize(local_path)
                            
                            db.update('resources', {
                                'file_size': file_size,
                                'downloaded': True
                            }, 'id = ?', [res['id']])
                            
                            checked_count += 1
                        except Exception as e:
                            self.log(f"检查资源失败 {res.get('output_filename')}: {e}", "warning")
            
            self.log(f"已检查 {checked_count} 个资源", "success")
            
        except Exception as e:
            self.log(f"检查资源失败: {e}", "error")
    
    def _delete_db_record(self):
        selection = self.db_tree.selection()
        if not selection:
            self.show_info("提示", "请先选择要删除的记录")
            return
        
        item = self.db_tree.selection()[0]
        values = self.db_tree.item(item, 'values')
        
        columns = self._products_visible_columns
        product_id_idx = columns.index('product_id') if 'product_id' in columns else 1
        product_id = values[product_id_idx] if product_id_idx < len(values) else ''
        
        if not product_id:
            return
        
        confirm = self.ask_yes_no("确认删除", f"确定要删除商品 {product_id} 的所有记录吗？\n\n此操作不可撤销！")
        if not confirm:
            return
        
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            db.delete_product(product_id)
            db.conn.execute('CHECKPOINT')
            db.close()
            
            self.db_tree.delete(item)
            self.log(f"已删除商品记录: {product_id}", "success")
            
        except Exception as e:
            self.log(f"删除记录失败: {e}", "error")
