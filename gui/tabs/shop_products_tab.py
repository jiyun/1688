import os
import re
import threading
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk
import webbrowser

from gui.utils import create_button


class ShopProductsTabMixin:
    
    def _init_db_shop_products_tab(self):
        """初始化店铺商品子选项卡"""
        from utils.column_config import get_column_config
        
        self._shop_products_all_columns = {
            'product_id': {'text': '商品ID', 'width': 105, 'anchor': 'center', 'default': True},
            'title': {'text': '商品标题', 'width': 200, 'anchor': 'w', 'default': True},
            'price': {'text': '价格', 'width': 70, 'anchor': 'center', 'default': True},
            'dropship_price': {'text': '代发价', 'width': 70, 'anchor': 'center', 'default': True},
            'sales_count': {'text': '销量', 'width': 55, 'anchor': 'center', 'default': True},
            'yearly_sales_qty': {'text': '年销量', 'width': 55, 'anchor': 'center', 'default': False},
            'review_count': {'text': '评论数', 'width': 55, 'anchor': 'center', 'default': True},
            'monthly_orders': {'text': '月成交', 'width': 55, 'anchor': 'center', 'default': False},
            'yearly_orders': {'text': '年成交', 'width': 55, 'anchor': 'center', 'default': False},
            'monthly_dropship': {'text': '月代销', 'width': 55, 'anchor': 'center', 'default': False},
            'repurchase_rate': {'text': '复购率', 'width': 55, 'anchor': 'center', 'default': False},
            'category': {'text': '类目', 'width': 80, 'anchor': 'w', 'default': True},
            'ship_time': {'text': '发货时间', 'width': 70, 'anchor': 'center', 'default': False},
            'list_time': {'text': '上架时间', 'width': 90, 'anchor': 'center', 'default': False},
            'tags': {'text': '标签', 'width': 80, 'anchor': 'w', 'default': False},
            'sales_tags': {'text': '销售标签', 'width': 80, 'anchor': 'w', 'default': False},
            'attr_tags': {'text': '属性标签', 'width': 80, 'anchor': 'w', 'default': False},
            'service_tags': {'text': '服务标签', 'width': 80, 'anchor': 'w', 'default': False},
            'support_dropship': {'text': '一件代发', 'width': 60, 'anchor': 'center', 'default': False},
            'collected': {'text': '已采集', 'width': 55, 'anchor': 'center', 'default': True},
            'product_url': {'text': '链接', 'width': 50, 'anchor': 'center', 'default': True},
        }
        
        config = get_column_config()
        saved_columns = config.get_visible_columns('shop_products')
        if saved_columns:
            self._shop_products_visible_columns = [col for col in saved_columns if col in self._shop_products_all_columns]
        else:
            self._shop_products_visible_columns = [col for col, cfg in self._shop_products_all_columns.items() if cfg['default']]
        
        self._current_supplier_filter = None
        
        filter_frame = ctk.CTkFrame(self.db_shop_products_tab, fg_color="transparent")
        filter_frame.pack(fill="x", padx=5, pady=2)
        
        ctk.CTkLabel(filter_frame, text="供应商筛选:", font=(self.available_font, self.font_size)).pack(side="left", padx=5)
        
        self.supplier_filter_var = ctk.StringVar(value="全部")
        self.supplier_filter_combo = ctk.CTkComboBox(
            filter_frame, 
            variable=self.supplier_filter_var,
            values=["全部"],
            width=200,
            command=self._on_supplier_filter_change
        )
        self.supplier_filter_combo.pack(side="left", padx=5)
        
        create_button(filter_frame, "刷新列表", self._refresh_shop_products, 'secondary', width=70).pack(side="left", padx=5)
        
        self.supplier_info_frame = ctk.CTkFrame(filter_frame)
        self.supplier_info_frame.pack(side="right", padx=10)
        
        self._supplier_info_labels = {}
        
        main_frame = ctk.CTkFrame(self.db_shop_products_tab, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=5, pady=2)
        
        self.shop_products_tree_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        self.shop_products_tree_frame.pack(side="left", fill="both", expand=True)
        
        self._create_shop_products_tree()
        
        self._shop_products_sort_column = None
        self._shop_products_sort_reverse = False
        self._shop_products_data_cache = []
        
        shop_btn_frame = ctk.CTkFrame(self.db_shop_products_tab, fg_color="transparent")
        shop_btn_frame.pack(fill="x", pady=5)
        
        self.shop_products_search_var = ctk.StringVar()
        ctk.CTkLabel(shop_btn_frame, text="搜索:").pack(side="left", padx=5)
        shop_search_entry = ctk.CTkEntry(shop_btn_frame, textvariable=self.shop_products_search_var, width=150)
        shop_search_entry.pack(side="left", padx=2)
        shop_search_entry.bind('<Return>', lambda e: self._search_shop_products())
        
        create_button(shop_btn_frame, "搜索", self._search_shop_products, 'primary', width=60).pack(side="left", padx=2)
        create_button(shop_btn_frame, "刷新", self._refresh_shop_products, 'secondary', width=60).pack(side="left", padx=5)
        create_button(shop_btn_frame, "导入Excel", self._show_excel_import_dialog, 'success', width=80).pack(side="left", padx=5)
        create_button(shop_btn_frame, "清空", self._clear_shop_products, 'danger', width=60).pack(side="left", padx=5)
        create_button(shop_btn_frame, "分析", self._show_product_analysis, 'primary', width=60).pack(side="left", padx=5)
        
        self.shop_products_status_label = ctk.CTkLabel(shop_btn_frame, text="")
        self.shop_products_status_label.pack(side="right", padx=10)
    

    def _create_shop_products_tree(self):
        """创建店铺商品树形视图"""
        for widget in self.shop_products_tree_frame.winfo_children():
            widget.destroy()
        
        columns = tuple(self._shop_products_visible_columns)
        self.shop_products_tree = ttk.Treeview(self.shop_products_tree_frame, columns=columns, show="headings", selectmode="browse")
        
        for col in self._shop_products_visible_columns:
            cfg = self._shop_products_all_columns[col]
            self.shop_products_tree.heading(col, text=cfg['text'], command=lambda c=col: self._sort_shop_products_column(c))
            anchor = cfg.get('anchor', 'center')
            self.shop_products_tree.column(col, width=cfg['width'], anchor=anchor)
        
        scrollbar = ttk.Scrollbar(self.shop_products_tree_frame, orient="vertical", command=self.shop_products_tree.yview)
        self.shop_products_tree.configure(yscrollcommand=scrollbar.set)
        
        self.shop_products_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.shop_products_tree.bind('<Double-1>', self._on_shop_products_tree_double_click)
        self.shop_products_tree.bind('<Button-3>', self._on_shop_products_right_click)
        
        self._setup_column_drag_drop()
    

    def _setup_column_drag_drop(self):
        """设置列拖放功能"""
        self._drag_column = None
        self._drag_start_x = 0
        self._drag_hint_label = None
        self._drag_indicator = None
        self._drag_animation_id = None
        self._drag_flash_state = False
        self._drag_source_col = None
        
        self.shop_products_tree.bind('<Button-1>', self._on_column_drag_press, add='+')
        self.shop_products_tree.bind('<B1-Motion>', self._on_column_drag_motion, add='+')
        self.shop_products_tree.bind('<ButtonRelease-1>', self._on_column_drag_release, add='+')
    

    def _on_shop_products_right_click(self, event):
        """处理店铺商品右键点击事件"""
        region = self.shop_products_tree.identify_region(event.x, event.y)
        if region == "heading":
            self._show_column_visibility_menu(event)
        else:
            self._show_shop_products_context_menu(event)
    

    def _refresh_shop_products(self):
        """刷新店铺商品列表"""
        for item in self.shop_products_tree.get_children():
            self.shop_products_tree.delete(item)
        
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            
            try:
                suppliers = db.query(
                    "SELECT DISTINCT shop_name FROM shop_products WHERE shop_name IS NOT NULL AND shop_name != '' ORDER BY shop_name"
                )
                supplier_names = ["全部"] + [s['shop_name'] for s in suppliers]
                self.supplier_filter_combo.configure(values=supplier_names)
                
                selected_supplier = self.supplier_filter_var.get()
                if selected_supplier and selected_supplier != "全部":
                    self._update_supplier_info(db, selected_supplier)
                else:
                    self._clear_supplier_info()
                
                where_clause = ""
                params = []
                if selected_supplier and selected_supplier != "全部":
                    where_clause = "WHERE sp.shop_name = ?"
                    params = [selected_supplier]
                
                sql = f'''
                    SELECT sp.*, 
                           p.id as product_exists,
                           (SELECT COUNT(*) FROM resources r WHERE r.product_id = sp.product_id) as resource_count
                    FROM shop_products sp
                    LEFT JOIN products p ON p.product_id = sp.product_id
                    {where_clause}
                    ORDER BY sp.collect_time DESC
                    LIMIT 1000
                '''
                
                products = db.query(sql, params)
                
                collected_count = 0
                for product in products:
                    row_values = []
                    
                    for col in self._shop_products_visible_columns:
                        if col == 'product_id':
                            row_values.append(product.get('product_id', ''))
                        elif col == 'title':
                            title = product.get('title', '')[:25] + '...' if len(product.get('title', '')) > 25 else product.get('title', '')
                            row_values.append(title)
                        elif col == 'price':
                            row_values.append(f"¥{product.get('price', 0):.2f}" if product.get('price') else '-')
                        elif col == 'dropship_price':
                            row_values.append(f"¥{product.get('dropship_price', 0):.2f}" if product.get('dropship_price') else '-')
                        elif col == 'sales_count':
                            row_values.append(product.get('sales_count', 0) or product.get('monthly_sales', 0) or 0)
                        elif col == 'yearly_sales_qty':
                            row_values.append(product.get('yearly_sales_qty', 0) or 0)
                        elif col == 'review_count':
                            row_values.append(product.get('review_count', 0) or 0)
                        elif col == 'monthly_orders':
                            row_values.append(product.get('monthly_orders', 0) or 0)
                        elif col == 'yearly_orders':
                            row_values.append(product.get('yearly_orders', 0) or 0)
                        elif col == 'monthly_dropship':
                            row_values.append(product.get('monthly_dropship', 0) or 0)
                        elif col == 'repurchase_rate':
                            rate = product.get('repurchase_rate')
                            row_values.append(f"{rate:.1f}%" if rate else '-')
                        elif col == 'category':
                            cat = product.get('category', '')[:12] if product.get('category') else ''
                            row_values.append(cat)
                        elif col == 'ship_time':
                            row_values.append(product.get('ship_time', '')[:8] if product.get('ship_time') else '')
                        elif col == 'list_time':
                            row_values.append(product.get('list_time', '')[:10] if product.get('list_time') else '')
                        elif col == 'tags':
                            tags = product.get('tags', '')[:10] if product.get('tags') else ''
                            row_values.append(tags)
                        elif col == 'sales_tags':
                            tags = product.get('sales_tags', '')[:10] if product.get('sales_tags') else ''
                            row_values.append(tags)
                        elif col == 'attr_tags':
                            tags = product.get('attr_tags', '')[:10] if product.get('attr_tags') else ''
                            row_values.append(tags)
                        elif col == 'service_tags':
                            tags = product.get('service_tags', '')[:10] if product.get('service_tags') else ''
                            row_values.append(tags)
                        elif col == 'support_dropship':
                            val = product.get('support_dropship')
                            if val == 1:
                                row_values.append('✓')
                            elif val == 0:
                                row_values.append('×')
                            else:
                                row_values.append('-')
                        elif col == 'collected':
                            resource_count = product.get('resource_count', 0) or 0
                            if resource_count > 0:
                                row_values.append(f"✓{resource_count}")
                                collected_count += 1
                            elif product.get('product_exists'):
                                row_values.append("○")
                            else:
                                row_values.append("-")
                        elif col == 'product_url':
                            row_values.append("查看")
                    
                    self.shop_products_tree.insert("", "end", values=row_values)
                
                self.shop_products_status_label.configure(text=f"共 {len(products)} 条, 已采集 {collected_count} 条")
                
            finally:
                db.close()
        except Exception as e:
            self.log(f"读取店铺商品失败: {e}", "error")
    

    def _on_supplier_filter_change(self, value):
        """供应商筛选变化处理"""
        self._refresh_shop_products()
    

    def _update_supplier_info(self, db, supplier_name):
        """更新供应商信息显示"""
        for widget in self.supplier_info_frame.winfo_children():
            widget.destroy()
        
        supplier = db.query_one(
            "SELECT * FROM ds_shops WHERE ds_shop_name = ?",
            [supplier_name]
        )
        
        if not supplier:
            ctk.CTkLabel(self.supplier_info_frame, text=f"供应商: {supplier_name} (无详细信息)").pack(side="left", padx=5)
            return
        
        product_count = db.query_one(
            "SELECT COUNT(*) as cnt FROM shop_products WHERE shop_name = ?",
            [supplier_name]
        )
        count = product_count.get('cnt', 0) if product_count else 0
        
        info_parts = [f"商品数: {count}"]
        
        if supplier.get('ds_platform'):
            platform = supplier.get('ds_platform')
            platform_name = {'alibaba': '1688', 'jd': '京东', 'pdd': '拼多多', 'tb': '淘宝'}.get(platform, platform)
            info_parts.append(f"平台: {platform_name}")
        
        if supplier.get('shop_type'):
            shop_type = supplier.get('shop_type')
            type_name = {'supplier': '供应商', 'user': '用户店铺'}.get(shop_type, shop_type)
            info_parts.append(f"类型: {type_name}")
        
        ctk.CTkLabel(
            self.supplier_info_frame, 
            text=" | ".join(info_parts),
            font=(self.available_font, self.font_size_small)
        ).pack(side="left", padx=5)
    

    def _search_shop_products(self):
        """搜索店铺商品"""
        search_term = self.shop_products_search_var.get().strip()
        
        if not search_term:
            self._refresh_shop_products()
            return
        
        for item in self.shop_products_tree.get_children():
            self.shop_products_tree.delete(item)
        
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            
            try:
                search_pattern = f'%{search_term}%'
                products = db.query('''
                    SELECT sp.product_id, sp.title, sp.price, sp.dropship_price,
                           sp.monthly_sales, sp.review_count, sp.category, sp.product_url,
                           p.id as product_exists,
                           (SELECT COUNT(*) FROM resources r WHERE r.product_id = sp.product_id) as resource_count
                    FROM shop_products sp
                    LEFT JOIN products p ON p.product_id = sp.product_id
                    WHERE sp.product_id LIKE ? OR sp.title LIKE ? OR sp.category LIKE ?
                    ORDER BY sp.collect_time DESC
                    LIMIT 500
                ''', [search_pattern, search_pattern, search_pattern])
                
                collected_count = 0
                for product in products:
                    title = product.get('title', '')[:30] + '...' if len(product.get('title', '')) > 30 else product.get('title', '')
                    price_str = f"¥{product.get('price', 0):.2f}" if product.get('price') else '-'
                    dropship_str = f"¥{product.get('dropship_price', 0):.2f}" if product.get('dropship_price') else '-'
                    
                    resource_count = product.get('resource_count', 0) or 0
                    if resource_count > 0:
                        collected = f"✓{resource_count}"
                        collected_count += 1
                    elif product.get('product_exists'):
                        collected = "○"
                    else:
                        collected = "-"
                    
                    self.shop_products_tree.insert("", "end", values=(
                        product.get('product_id', ''),
                        title,
                        price_str,
                        dropship_str,
                        product.get('monthly_sales', 0),
                        product.get('review_count', 0),
                        product.get('category', '')[:12] if product.get('category') else '',
                        collected,
                        "查看"
                    ))
                
                self.shop_products_status_label.configure(text=f"找到 {len(products)} 条, 已采集 {collected_count} 条")
                
            finally:
                db.close()
        except Exception as e:
            self.log(f"搜索店铺商品失败: {e}", "error")
    

    def _clear_shop_products(self):
        """清空店铺商品数据"""
        confirm = self.ask_yes_no("确认清空", "确定要清空所有店铺商品数据吗？\n\n此操作不可撤销！")
        if not confirm:
            return
        
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            
            db.execute("DELETE FROM shop_products")
            db.close()
            
            self._refresh_shop_products()
            self.log("已清空店铺商品数据", "success")
            
        except Exception as e:
            self.log(f"清空失败: {e}", "error")
    

    def _on_shop_products_tree_double_click(self, event):
        """店铺商品列表双击事件"""
        selection = self.shop_products_tree.selection()
        if not selection:
            return
        
        item = self.shop_products_tree.item(selection[0])
        values = item.get('values', [])
        
        if len(values) >= 1:
            product_id = values[0]
            product_url = f"https://detail.1688.com/offer/{product_id}.html"
            self._open_url(product_url)
    

    def _show_shop_products_context_menu(self, event):
        """显示店铺商品右键菜单"""
        item = self.shop_products_tree.identify_row(event.y)
        if not item:
            return
        
        self.shop_products_tree.selection_set(item)
        values = self.shop_products_tree.item(item).get('values', [])
        
        if len(values) < 1:
            return
        
        product_id = values[0]
        collected = values[7] if len(values) > 7 else "-"
        
        menu = tk.Menu(self.root, tearoff=0)
        
        main_image = None
        title = product_id
        
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            product = db.query_one("SELECT main_image, title FROM shop_products WHERE product_id = ?", [product_id])
            db.close()
            
            if product:
                main_image = product.get('main_image')
                title = product.get('title', product_id)
        except Exception as e:
            pass
        
        if main_image:
            try:
                import urllib.request
                from PIL import Image, ImageTk
                
                thumb_url = main_image
                if not thumb_url.endswith(('.jpg', '.png', '.jpeg')):
                    thumb_url = f"https://cbu01.alicdn.com/img/ibank/{product_id}_1.jpg"
                
                req = urllib.request.Request(thumb_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=3) as response:
                    img_data = response.read()
                
                img = Image.open(__import__('io').BytesIO(img_data))
                
                max_width = 150
                max_height = 200
                img_w, img_h = img.size
                ratio = min(max_width / img_w, max_height / img_h)
                if ratio < 1:
                    new_w = int(img_w * ratio)
                    new_h = int(img_h * ratio)
                    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
                photo = ImageTk.PhotoImage(img)
                
                preview_menu = tk.Menu(menu, tearoff=0)
                preview_menu.add_command(
                    label="点击查看大图",
                    image=photo,
                    compound='top',
                    command=lambda: self._show_image_preview(product_id, thumb_url, self._get_original_image_url(thumb_url), title)
                )
                preview_menu.image = photo
                
                menu.add_cascade(label="📷 图片预览", menu=preview_menu)
                menu.add_separator()
            except Exception as e:
                menu.add_command(label="📷 图片预览 (加载失败)", state="disabled")
                menu.add_separator()
        
        menu.add_command(label=f"商品ID: {product_id}", state="disabled")
        menu.add_separator()
        menu.add_command(label="打开商品页面", command=lambda: self._open_url(f"https://detail.1688.com/offer/{product_id}.html"))
        menu.add_command(label="复制商品ID", command=lambda: self._copy_to_clipboard(product_id))
        menu.add_separator()
        
        if collected and collected.startswith("✓"):
            menu.add_command(label="跳转到商品管理", command=lambda: self._jump_to_product_management(product_id))
            menu.add_command(label="查看资源详情", command=lambda: self._show_product_resources(product_id))
        elif collected == "○":
            menu.add_command(label="跳转到商品管理", command=lambda: self._jump_to_product_management(product_id))
        else:
            menu.add_command(label="添加到采集队列", command=lambda: self._add_to_collect_queue(product_id))
        
        menu.add_separator()
        menu.add_command(label="商品分析", command=lambda: self._show_single_product_analysis(product_id, values))
        
        menu.post(event.x_root, event.y_root)
    

    def _jump_to_product_management(self, product_id):
        """跳转到商品管理选项卡并定位商品"""
        self.db_sub_notebook.select(0)
        
        for item in self.db_tree.get_children():
            values = self.db_tree.item(item).get('values', [])
            if len(values) >= 2 and values[1] == product_id:
                self.db_tree.selection_set(item)
                self.db_tree.see(item)
                self.db_tree.focus(item)
                self.log(f"已定位到商品: {product_id}", "success")
                return
        
        self.db_search_var.set(product_id)
        self._search_db_records()
        self.log(f"已搜索商品: {product_id}", "info")
    

    def _show_product_resources(self, product_id):
        """显示商品资源详情"""
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            
            resources = db.query(
                "SELECT * FROM resources WHERE product_id = ? ORDER BY created_at DESC",
                [product_id]
            )
            db.close()
            
            if not resources:
                self.show_info("提示", f"商品 {product_id} 没有资源记录")
                return
            
            dialog = ctk.CTkToplevel(self.root)
            dialog.title(f"资源详情 - {product_id}")
            dialog.geometry("700x400")
            dialog.transient(self.root)
            
            main_frame = ctk.CTkFrame(dialog)
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            info_label = ctk.CTkLabel(main_frame, text=f"商品ID: {product_id}  共 {len(resources)} 条资源", font=(self.available_font, 12, "bold"))
            info_label.pack(pady=5)
            
            columns = ('type', 'name', 'url', 'downloaded', 'size')
            tree = ttk.Treeview(main_frame, columns=columns, show='headings', height=12)
            
            tree.heading('type', text='类型')
            tree.heading('name', text='名称')
            tree.heading('url', text='链接')
            tree.heading('downloaded', text='状态')
            tree.heading('size', text='大小')
            
            tree.column('type', width=80)
            tree.column('name', width=150)
            tree.column('url', width=280)
            tree.column('downloaded', width=60)
            tree.column('size', width=80)
            
            resource_data = []
            for res in resources:
                res_type = res.get('resource_type', '未知')
                res_name = res.get('resource_name', '-') or '-'
                res_url = res.get('resource_url', '')
                display_url = res_url
                if len(display_url) > 50:
                    display_url = display_url[:47] + '...'
                downloaded = '✓已下载' if res.get('downloaded') else '○未下载'
                file_size = res.get('file_size', 0) or 0
                if file_size > 0:
                    if file_size > 1024 * 1024:
                        size_str = f"{file_size / 1024 / 1024:.1f}MB"
                    elif file_size > 1024:
                        size_str = f"{file_size / 1024:.1f}KB"
                    else:
                        size_str = f"{file_size}B"
                else:
                    size_str = '-'
                
                item_id = tree.insert('', 'end', values=(res_type, res_name, display_url, downloaded, size_str))
                resource_data.append({
                    'item_id': item_id,
                    'res_url': res_url,
                    'downloaded': res.get('downloaded'),
                    'output_filename': res.get('output_filename')
                })
            
            scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            tree.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            def on_double_click(event):
                selection = tree.selection()
                if not selection:
                    return
                
                item_id = selection[0]
                res_info = None
                for rd in resource_data:
                    if rd['item_id'] == item_id:
                        res_info = rd
                        break
                
                if not res_info:
                    return
                
                if res_info['downloaded'] and res_info['output_filename']:
                    import os
                    import subprocess
                    local_path = res_info['output_filename']
                    if os.path.exists(local_path):
                        try:
                            os.startfile(local_path)
                            self.log(f"已打开本地文件: {local_path}", "success")
                        except Exception as e:
                            self.log(f"打开文件失败: {e}", "error")
                    else:
                        self.log(f"本地文件不存在: {local_path}", "warning")
                        self._copy_to_clipboard(res_info['res_url'])
                else:
                    self._copy_to_clipboard(res_info['res_url'])
            
            tree.bind('<Double-1>', on_double_click)
            
            btn_frame = ctk.CTkFrame(dialog)
            btn_frame.pack(fill="x", pady=5, padx=10)
            
            create_button(btn_frame, "关闭", dialog.destroy, 'secondary', width=60).pack(side="right", padx=5)
            
        except Exception as e:
            self.log(f"获取资源失败: {e}", "error")
    

    def _add_to_collect_queue(self, product_id):
        """添加商品到采集队列"""
        product_url = f"https://detail.1688.com/offer/{product_id}.html"
        
        current_text = self.url_text.get("1.0", "end").strip()
        if current_text:
            new_text = current_text + "\n" + product_url
        else:
            new_text = product_url
        
        self.url_text.delete("1.0", "end")
        self.url_text.insert("1.0", new_text)
        
        self.log(f"已添加 {product_id} 到采集队列", "success")
        self.notebook.select(0)
    

    def _sort_shop_products_column(self, column):
        """排序店铺商品列表"""
        if self._shop_products_sort_column == column:
            self._shop_products_sort_reverse = not self._shop_products_sort_reverse
        else:
            self._shop_products_sort_column = column
            self._shop_products_sort_reverse = False
        
        items = []
        for item in self.shop_products_tree.get_children():
            values = self.shop_products_tree.item(item).get('values', [])
            items.append((values, item))
        
        try:
            col_index = self._shop_products_visible_columns.index(column)
        except ValueError:
            col_index = 0
        
        numeric_columns = ('price', 'dropship_price', 'sales_count', 'yearly_sales_qty', 
                          'review_count', 'monthly_orders', 'yearly_orders', 
                          'monthly_dropship', 'repurchase_rate')
        
        def natural_sort_key(s):
            """自然排序键函数，支持数字排序"""
            import re
            s = str(s)
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]
        
        def sort_key(item):
            val = item[0][col_index] if len(item[0]) > col_index else ''
            if column == 'product_id':
                try:
                    return int(val)
                except:
                    return natural_sort_key(val)
            elif column in ('price', 'dropship_price'):
                val_str = str(val).replace('¥', '').replace('-', '0')
                try:
                    return float(val_str)
                except:
                    return 0
            elif column in numeric_columns:
                val_str = str(val).replace('%', '').replace(',', '').replace('-', '0')
                try:
                    return float(val_str)
                except:
                    return 0
            elif column == 'collected':
                if str(val).startswith('✓'):
                    return 2
                elif val == '○':
                    return 1
                else:
                    return 0
            elif column == 'support_dropship':
                if val == '✓':
                    return 2
                elif val == '×':
                    return 1
                else:
                    return 0
            return str(val)
        
        items.sort(key=sort_key, reverse=self._shop_products_sort_reverse)
        
        for item in self.shop_products_tree.get_children():
            self.shop_products_tree.delete(item)
        
        for values, _ in items:
            self.shop_products_tree.insert("", "end", values=values)
    

    def _show_product_analysis(self):
        """显示商品分析对话框"""
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            
            products = db.query('''
                SELECT sp.product_id, sp.title, sp.price, sp.dropship_price,
                       sp.monthly_sales, sp.review_count, sp.category,
                       (SELECT COUNT(*) FROM resources r WHERE r.product_id = sp.product_id) as resource_count
                FROM shop_products sp
                ORDER BY sp.monthly_sales DESC
                LIMIT 100
            ''')
            db.close()
            
            if not products:
                self.show_info("提示", "没有商品数据可供分析")
                return
            
            self._create_analysis_dialog(products)
            
        except Exception as e:
            self.log(f"分析失败: {e}", "error")
    

    def _show_single_product_analysis(self, product_id, values):
        """显示单个商品分析"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title(f"商品分析 - {product_id}")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        ctk.CTkLabel(main_frame, text=f"商品ID: {product_id}", font=(self.available_font, 14, "bold")).pack(anchor="w", pady=5)
        
        if len(values) >= 8:
            info_frame = ctk.CTkFrame(main_frame)
            info_frame.pack(fill="x", pady=10)
            
            metrics = [
                ("价格", values[2]),
                ("代发价", values[3]),
                ("销量", values[4]),
                ("评论数", values[5]),
                ("类目", values[6]),
                ("采集状态", values[7])
            ]
            
            for label, value in metrics:
                row = ctk.CTkFrame(info_frame)
                row.pack(fill="x", pady=2)
                ctk.CTkLabel(row, text=f"{label}:", width=80, anchor="w").pack(side="left", padx=5)
                ctk.CTkLabel(row, text=str(value), anchor="w").pack(side="left", padx=5)
        
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x", pady=10)
        
        create_button(btn_frame, "打开商品页", lambda: self._open_url(f"https://detail.1688.com/offer/{product_id}.html"), 'primary', width=100).pack(side="left", padx=5)
        create_button(btn_frame, "关闭", dialog.destroy, 'secondary', width=80).pack(side="right", padx=5)
    

    def _preview_product_image(self, product_id):
        """预览商品图片"""
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            
            product = db.query_one(
                "SELECT main_image, title FROM shop_products WHERE product_id = ?",
                [product_id]
            )
            db.close()
            
            if not product:
                self.show_info("提示", f"未找到商品 {product_id} 的图片信息")
                return
            
            main_image = product.get('main_image')
            title = product.get('title', product_id)
            
            if not main_image:
                main_image = f"https://cbu01.alicdn.com/img/ibank/{product_id}_1.jpg"
            
            original_image = self._get_original_image_url(main_image)
            
            self._show_image_preview(product_id, main_image, original_image, title)
            
        except Exception as e:
            self.log(f"获取图片失败: {e}", "error")
    

    def _get_original_image_url(self, image_url: str) -> str:
        """获取原图URL
        
        阿里图片URL规则：
        - 缩略图格式：xxx.310x310.jpg 或 xxx_310x310.jpg
        - 原图格式：去掉尺寸后缀
        """
        import re
        
        if not image_url:
            return image_url
        
        original_url = image_url
        
        patterns = [
            (r'\.(\d+)x(\d+)\.', '.'),
            (r'_(\d+)x(\d+)\.', '.'),
            (r'_(\d+)x(\d+)_', '_'),
        ]
        
        for pattern, replacement in patterns:
            if re.search(pattern, original_url):
                original_url = re.sub(pattern, replacement, original_url)
                break
        
        if original_url.endswith('_.webp'):
            original_url = original_url[:-6]
        
        return original_url
    

    def _show_image_preview(self, product_id, image_url, original_url, title):
        """显示图片预览窗口"""
        import threading
        from io import BytesIO
        
        preview_dialog = ctk.CTkToplevel(self.root)
        preview_dialog.title(f"商品图片 - {product_id}")
        preview_dialog.geometry("600x500")
        preview_dialog.transient(self.root)
        
        main_frame = ctk.CTkFrame(preview_dialog)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        title_label = ctk.CTkLabel(main_frame, text=title[:40] + "..." if len(title) > 40 else title, font=(self.available_font, 12))
        title_label.pack(pady=5)
        
        image_frame = ctk.CTkFrame(main_frame)
        image_frame.pack(fill="both", expand=True, pady=5)
        
        status_label = ctk.CTkLabel(image_frame, text="正在加载图片...")
        status_label.pack(expand=True)
        
        def load_image():
            try:
                import urllib.request
                from PIL import Image, ImageTk
                
                req = urllib.request.Request(original_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=15) as response:
                    img_data = response.read()
                
                img = Image.open(BytesIO(img_data))
                
                img.thumbnail((550, 400), Image.Resampling.LANCZOS)
                
                photo = ImageTk.PhotoImage(img)
                
                status_label.destroy()
                
                img_label = tk.Label(image_frame, image=photo, bg='#f0f0f0')
                img_label.image = photo
                img_label.pack(expand=True)
                
            except Exception as e:
                status_label.configure(text=f"加载失败: {e}")
        
        threading.Thread(target=load_image, daemon=True).start()
        
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x", pady=5)
        
        create_button(btn_frame, "浏览器打开", lambda: self._open_url(original_url), 'primary', width=80).pack(side="left", padx=5)
        create_button(btn_frame, "关闭", preview_dialog.destroy, 'secondary', width=60).pack(side="right", padx=5)
    

