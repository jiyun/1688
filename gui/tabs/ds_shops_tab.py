import os
import re
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk
import webbrowser

from gui.utils import create_button


class DsShopsTabMixin:
    
    def _init_db_ds_shops_tab(self):
        """初始化店铺信息子选项卡"""
        from utils.column_config import get_column_config
        
        self._ds_shops_all_columns = {
            'ds_shop_id': {'text': '店铺ID', 'width': 100, 'anchor': 'center', 'default': True},
            'ds_shop_name': {'text': '店铺名称', 'width': 150, 'anchor': 'w', 'default': True},
            'shop_type': {'text': '类型', 'width': 60, 'anchor': 'center', 'default': True},
            'ds_platform': {'text': '平台', 'width': 60, 'anchor': 'center', 'default': True},
            'ds_shop_url': {'text': '店铺链接', 'width': 200, 'anchor': 'w', 'default': True},
            'shop_status': {'text': '状态', 'width': 60, 'anchor': 'center', 'default': True},
            'product_count': {'text': '商品数', 'width': 60, 'anchor': 'center', 'default': True},
            'remark': {'text': '备注', 'width': 100, 'anchor': 'w', 'default': True},
        }
        
        config = get_column_config()
        saved_columns = config.get_visible_columns('ds_shops')
        if saved_columns:
            self._ds_shops_visible_columns = [col for col in saved_columns if col in self._ds_shops_all_columns]
        else:
            self._ds_shops_visible_columns = [col for col, cfg in self._ds_shops_all_columns.items() if cfg['default']]
        
        self.ds_shops_tree_frame = ctk.CTkFrame(self.db_ds_shops_tab, fg_color="transparent")
        self.ds_shops_tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self._create_ds_shops_tree()
        
        ds_btn_frame = ctk.CTkFrame(self.db_ds_shops_tab, fg_color="transparent")
        ds_btn_frame.pack(fill="x", pady=5)
        
        create_button(ds_btn_frame, "添加用户店铺", self._add_ds_shop, 'success', width=90).pack(side="left", padx=5)
        create_button(ds_btn_frame, "刷新", self._refresh_ds_shops, 'secondary', width=60).pack(side="left", padx=5)
        
        self.ds_shops_status_label = ctk.CTkLabel(ds_btn_frame, text="")
        self.ds_shops_status_label.pack(side="right", padx=10)
    

    def _create_ds_shops_tree(self):
        """创建DS店铺树形视图"""
        for widget in self.ds_shops_tree_frame.winfo_children():
            widget.destroy()
        
        columns = tuple(self._ds_shops_visible_columns)
        self.ds_shops_tree = ttk.Treeview(self.ds_shops_tree_frame, columns=columns, show="headings", selectmode="browse")
        
        for col in self._ds_shops_visible_columns:
            cfg = self._ds_shops_all_columns[col]
            self.ds_shops_tree.heading(col, text=cfg['text'], command=lambda c=col: self._sort_ds_shops_column(c))
            self.ds_shops_tree.column(col, width=cfg['width'], anchor=cfg.get('anchor', 'center'))
        
        ds_scrollbar = ttk.Scrollbar(self.ds_shops_tree_frame, orient="vertical", command=self.ds_shops_tree.yview)
        self.ds_shops_tree.configure(yscrollcommand=ds_scrollbar.set)
        
        self.ds_shops_tree.pack(side="left", fill="both", expand=True)
        ds_scrollbar.pack(side="right", fill="y")
        
        self.ds_shops_tree.bind('<Double-1>', self._on_ds_shops_tree_double_click)
        self.ds_shops_tree.bind('<Button-3>', self._on_ds_shops_right_click)
        
        self._setup_ds_shops_drag_drop()
    

    def _setup_ds_shops_drag_drop(self):
        """设置DS店铺列拖放功能"""
        self._ds_shops_drag_start_x = 0
        self._ds_shops_drag_hint = None
        self._ds_shops_drag_indicator = None
        self._ds_shops_drag_anim_id = None
        self._ds_shops_drag_flash = False
        
        self.ds_shops_tree.bind('<Button-1>', self._on_ds_shops_drag_press, add='+')
        self.ds_shops_tree.bind('<B1-Motion>', self._on_ds_shops_drag_motion, add='+')
        self.ds_shops_tree.bind('<ButtonRelease-1>', self._on_ds_shops_drag_release, add='+')
    

    def _on_ds_shops_drag_press(self, event):
        region = self.ds_shops_tree.identify_region(event.x, event.y)
        if region == "heading":
            self._ds_shops_drag_start_x = event.x
    

    def _on_ds_shops_drag_motion(self, event):
        region = self.ds_shops_tree.identify_region(event.x, event.y)
        if region != "heading":
            self._hide_ds_shops_drag_hint()
            self._hide_ds_shops_drag_indicator()
            self._stop_ds_shops_drag_animation()
            return
        if abs(event.x - self._ds_shops_drag_start_x) > 15:
            self._show_ds_shops_drag_hint(event.x)
            self._show_ds_shops_drag_indicator(event.x)
            self._start_ds_shops_drag_animation()
    

    def _on_ds_shops_drag_release(self, event):
        self._hide_ds_shops_drag_hint()
        self._hide_ds_shops_drag_indicator()
        self._stop_ds_shops_drag_animation()
        
        region = self.ds_shops_tree.identify_region(event.x, event.y)
        if region != "heading" or abs(event.x - self._ds_shops_drag_start_x) < 15:
            return
        
        source_col = self.ds_shops_tree.identify_column(self._ds_shops_drag_start_x)
        target_col = self.ds_shops_tree.identify_column(event.x)
        
        if source_col and target_col and source_col != target_col:
            source_idx = int(source_col.replace('#', '')) - 1
            target_idx = int(target_col.replace('#', '')) - 1
            
            if 0 <= source_idx < len(self._ds_shops_visible_columns) and 0 <= target_idx < len(self._ds_shops_visible_columns):
                col_name = self._ds_shops_visible_columns[source_idx]
                self._ds_shops_visible_columns.pop(source_idx)
                self._ds_shops_visible_columns.insert(target_idx, col_name)
                
                from utils.column_config import get_column_config
                config = get_column_config()
                config.set_visible_columns('ds_shops', self._ds_shops_visible_columns)
                
                self._create_ds_shops_tree()
                self._refresh_ds_shops()
                self.log(f"列顺序已更新: 位置 {source_idx + 1} → {target_idx + 1}", "success")
    

    def _start_ds_shops_drag_animation(self):
        if self._ds_shops_drag_anim_id:
            return
        self._ds_shops_drag_flash = False
        self._animate_ds_shops_drag_flash()
    

    def _stop_ds_shops_drag_animation(self):
        if self._ds_shops_drag_anim_id:
            self.ds_shops_tree.after_cancel(self._ds_shops_drag_anim_id)
            self._ds_shops_drag_anim_id = None
    

    def _animate_ds_shops_drag_flash(self):
        if self._ds_shops_drag_hint and self._ds_shops_drag_hint.winfo_ismapped():
            self._ds_shops_drag_flash = not self._ds_shops_drag_flash
            self._ds_shops_drag_hint.configure(bg='#4a90d9' if self._ds_shops_drag_flash else '#2d6cb5')
            self._ds_shops_drag_anim_id = self.ds_shops_tree.after(300, self._animate_ds_shops_drag_flash)
    

    def _show_ds_shops_drag_hint(self, x: int):
        if self._ds_shops_drag_hint is None:
            self._ds_shops_drag_hint = tk.Label(
                self.ds_shops_tree, 
                text="↔ 拖动调整列顺序", 
                bg='#4a90d9', 
                fg='white', 
                padx=10, 
                pady=3,
                font=('Microsoft YaHei UI', 9, 'bold'),
                relief='raised',
                borderwidth=1
            )
        col = self.ds_shops_tree.identify_column(x)
        if col:
            bbox = self.ds_shops_tree.bbox(col)
            if bbox:
                self._ds_shops_drag_hint.place(x=bbox[0], y=0, anchor='nw')
                return
        self._ds_shops_drag_hint.place(x=x, y=2, anchor='n')
    

    def _hide_ds_shops_drag_hint(self):
        if self._ds_shops_drag_hint:
            self._ds_shops_drag_hint.place_forget()
    

    def _show_ds_shops_drag_indicator(self, x: int):
        if self._ds_shops_drag_indicator is None:
            self._ds_shops_drag_indicator = tk.Frame(self.ds_shops_tree, bg='#ff6b6b', width=3, height=25)
        col = self.ds_shops_tree.identify_column(x)
        if col:
            bbox = self.ds_shops_tree.bbox(col)
            if bbox:
                col_center = bbox[0] + bbox[2] // 2
                if x < col_center:
                    self._ds_shops_drag_indicator.place(x=bbox[0] - 2, y=0, anchor='nw')
                else:
                    self._ds_shops_drag_indicator.place(x=bbox[0] + bbox[2] - 1, y=0, anchor='nw')
                return
        self._ds_shops_drag_indicator.place(x=x, y=0, anchor='n')
    

    def _hide_ds_shops_drag_indicator(self):
        if self._ds_shops_drag_indicator:
            self._ds_shops_drag_indicator.place_forget()
    

    def _on_ds_shops_right_click(self, event):
        region = self.ds_shops_tree.identify_region(event.x, event.y)
        if region == "heading":
            self._show_ds_shops_column_menu(event)
        else:
            self._show_ds_shops_context_menu(event)
    

    def _show_ds_shops_column_menu(self, event):
        menu = tk.Menu(self.ds_shops_tree, tearoff=0)
        menu.add_command(label="显示/隐藏列", state="disabled")
        menu.add_separator()
        
        for col_name, cfg in self._ds_shops_all_columns.items():
            is_visible = col_name in self._ds_shops_visible_columns
            label = f"{'✓ ' if is_visible else '   '}{cfg['text']}"
            menu.add_command(label=label, command=lambda c=col_name: self._toggle_ds_shops_column(c))
        
        menu.post(event.x_root, event.y_root)
    

    def _toggle_ds_shops_column(self, column_name):
        from utils.column_config import get_column_config
        
        if column_name in self._ds_shops_visible_columns:
            if len(self._ds_shops_visible_columns) > 1:
                self._ds_shops_visible_columns.remove(column_name)
        else:
            self._ds_shops_visible_columns.append(column_name)
        
        config = get_column_config()
        config.set_visible_columns('ds_shops', self._ds_shops_visible_columns)
        
        self._create_ds_shops_tree()
        self._refresh_ds_shops()
    

    def _refresh_ds_shops(self):
        """刷新DS店铺列表"""
        for item in self.ds_shops_tree.get_children():
            self.ds_shops_tree.delete(item)
        
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            
            shops = db.get_all_ds_shops()
            
            for shop in shops:
                ds_shop_id = shop.get('ds_shop_id', '')
                product_count = db.query_one(
                    'SELECT COUNT(*) as cnt FROM product_ds_mapping WHERE ds_shop_id = ?',
                    [ds_shop_id]
                )
                
                row_values = []
                for col in self._ds_shops_visible_columns:
                    if col == 'ds_shop_id':
                        row_values.append(ds_shop_id)
                    elif col == 'ds_shop_name':
                        row_values.append(shop.get('ds_shop_name', ''))
                    elif col == 'shop_type':
                        shop_type = shop.get('shop_type', 'supplier')
                        if shop_type == 'supplier':
                            row_values.append('供应商')
                        elif shop_type == 'user':
                            row_values.append('用户店铺')
                        else:
                            row_values.append(shop_type)
                    elif col == 'ds_platform':
                        platform = shop.get('ds_platform', 'alibaba')
                        if platform == 'alibaba':
                            row_values.append('1688')
                        elif platform == 'jd':
                            row_values.append('京东')
                        elif platform == 'pdd':
                            row_values.append('拼多多')
                        elif platform == 'tb':
                            row_values.append('淘宝')
                        else:
                            row_values.append(platform)
                    elif col == 'ds_shop_url':
                        row_values.append(shop.get('ds_shop_url', '')[:40])
                    elif col == 'shop_status':
                        row_values.append(shop.get('shop_status', 'active'))
                    elif col == 'product_count':
                        row_values.append(product_count.get('cnt', 0) if product_count else 0)
                    elif col == 'remark':
                        row_values.append(shop.get('remark', '')[:20])
                
                self.ds_shops_tree.insert("", "end", values=row_values)
            
            self.ds_shops_status_label.configure(text=f"共 {len(shops)} 个店铺")
            db.close()
            
        except Exception as e:
            self.log(f"刷新DS店铺失败: {e}", "error")
    

    def _add_ds_shop(self):
        """添加用户店铺"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("添加用户店铺")
        dialog.geometry("500x450")
        dialog.transient(self.root)
        dialog.grab_set()
        
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        ctk.CTkLabel(main_frame, text="添加用户店铺", font=(self.available_font, 16, "bold")).pack(pady=10)
        
        ctk.CTkLabel(main_frame, text="输入店铺链接将自动识别平台和店铺ID", text_color="gray").pack()
        
        form_frame = ctk.CTkFrame(main_frame)
        form_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(form_frame, text="店铺链接:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        ds_shop_url_var = ctk.StringVar()
        ds_shop_url_entry = ctk.CTkEntry(form_frame, textvariable=ds_shop_url_var, width=300)
        ds_shop_url_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ctk.CTkLabel(form_frame, text="店铺ID:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        ds_shop_id_var = ctk.StringVar()
        ctk.CTkEntry(form_frame, textvariable=ds_shop_id_var, width=300).grid(row=1, column=1, padx=5, pady=5)
        
        ctk.CTkLabel(form_frame, text="店铺名称:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        ds_shop_name_var = ctk.StringVar()
        ctk.CTkEntry(form_frame, textvariable=ds_shop_name_var, width=300).grid(row=2, column=1, padx=5, pady=5)
        
        ctk.CTkLabel(form_frame, text="平台:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        ds_platform_var = ctk.StringVar(value="alibaba")
        platform_label = ctk.CTkLabel(form_frame, text="1688", font=(self.available_font, 12, "bold"))
        platform_label.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(form_frame, text="备注:").grid(row=4, column=0, padx=5, pady=5, sticky="e")
        remark_var = ctk.StringVar()
        ctk.CTkEntry(form_frame, textvariable=remark_var, width=300).grid(row=4, column=1, padx=5, pady=5)
        
        def parse_shop_url(*args):
            url = ds_shop_url_var.get().strip()
            if not url:
                return
            
            import re
            
            platform = 'other'
            shop_id = ''
            
            jd_patterns = [
                r'shop\.jd\.com/(\d+)',
                r'mall\.jd\.com/index-(\d+)',
                r'jd\.com.*shopId[=](\d+)',
                r'shop(\d+)\.jd\.com',
            ]
            for pattern in jd_patterns:
                match = re.search(pattern, url)
                if match:
                    platform = 'jd'
                    shop_id = match.group(1)
                    break
            
            if not shop_id:
                pdd_patterns = [
                    r'mobile\.yangkeduo\.com/shop\.html\?shop_id=(\d+)',
                    r'yangkeduo\.com.*shop_id[=](\d+)',
                ]
                for pattern in pdd_patterns:
                    match = re.search(pattern, url)
                    if match:
                        platform = 'pdd'
                        shop_id = match.group(1)
                        break
            
            if not shop_id:
                tb_patterns = [
                    r'shop\d+\.taobao\.com',
                    r'shop\.taobao\.com/shop/shop_index\.htm\?shop_id=(\d+)',
                    r'taobao\.com.*shopId[=](\d+)',
                ]
                for pattern in tb_patterns:
                    match = re.search(pattern, url)
                    if match:
                        platform = 'tb'
                        if match.group(1):
                            shop_id = match.group(1)
                        else:
                            match2 = re.search(r'shop(\d+)\.taobao', url)
                            if match2:
                                shop_id = match2.group(1)
                        break
            
            if shop_id:
                ds_shop_id_var.set(shop_id)
            if platform:
                ds_platform_var.set(platform)
                platform_label.configure(text=platform)
        
        ds_shop_url_var.trace_add("write", parse_shop_url)
        
        def save_shop():
            ds_shop_id = ds_shop_id_var.get().strip()
            ds_shop_name = ds_shop_name_var.get().strip()
            
            if not ds_shop_id or not ds_shop_name:
                self.show_info("错误", "店铺ID和店铺名称不能为空")
                return
            
            try:
                from utils.database import get_shared_db
                db = get_shared_db()
                
                db.save_ds_shop(
                    ds_shop_id=ds_shop_id,
                    ds_shop_name=ds_shop_name,
                    ds_platform=ds_platform_var.get(),
                    ds_shop_url=ds_shop_url_var.get().strip(),
                    remark=remark_var.get().strip(),
                    shop_type='user'
                )
                db.close()
                
                self.log(f"已添加用户店铺: {ds_shop_name}", "success")
                self._refresh_ds_shops()
                dialog.destroy()
                
            except Exception as e:
                self.log(f"添加用户店铺失败: {e}", "error")
                self.show_info("错误", f"添加失败: {e}")
        
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x", pady=10)
        
        create_button(btn_frame, "保存", save_shop, 'success', width=80).pack(side="left", padx=10)
        create_button(btn_frame, "取消", dialog.destroy, 'secondary', width=60).pack(side="left", padx=5)
    

    def _on_ds_shops_tree_double_click(self, event):
        """店铺列表双击事件"""
        selection = self.ds_shops_tree.selection()
        if not selection:
            return
        
        item = self.ds_shops_tree.item(selection[0])
        values = item.get('values', [])
        
        try:
            url_col_idx = self._ds_shops_visible_columns.index('ds_shop_url')
            if len(values) > url_col_idx:
                ds_shop_url = values[url_col_idx]
                if ds_shop_url:
                    self._open_url(ds_shop_url)
        except (ValueError, IndexError):
            pass
    

    def _show_ds_shops_context_menu(self, event):
        """显示店铺右键菜单"""
        item = self.ds_shops_tree.identify_row(event.y)
        if not item:
            return
        
        self.ds_shops_tree.selection_set(item)
        values = self.ds_shops_tree.item(item).get('values', [])
        
        if len(values) < 1:
            return
        
        try:
            id_col_idx = self._ds_shops_visible_columns.index('ds_shop_id')
            name_col_idx = self._ds_shops_visible_columns.index('ds_shop_name')
            url_col_idx = self._ds_shops_visible_columns.index('ds_shop_url')
        except ValueError:
            id_col_idx, name_col_idx, url_col_idx = 0, 1, 4
        
        ds_shop_id = values[id_col_idx] if len(values) > id_col_idx else ''
        ds_shop_name = values[name_col_idx] if len(values) > name_col_idx else ''
        ds_shop_url = values[url_col_idx] if len(values) > url_col_idx else ''
        
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=f"店铺: {ds_shop_name}", state="disabled")
        menu.add_separator()
        menu.add_command(label="打开店铺", command=lambda: self._open_url(ds_shop_url) if ds_shop_url else None)
        menu.add_command(label="查看关联商品", command=lambda: self._show_ds_shop_products(ds_shop_id))
        menu.add_separator()
        menu.add_command(label="编辑", command=lambda: self._edit_ds_shop(ds_shop_id))
        menu.add_command(label="删除", command=lambda: self._delete_ds_shop(ds_shop_id, ds_shop_name))
        
        menu.post(event.x_root, event.y_root)
    

    def _show_ds_shop_products(self, ds_shop_id):
        """显示DS店铺的关联商品"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title(f"店铺商品 - {ds_shop_id}")
        dialog.geometry("800x500")
        dialog.transient(self.root)
        
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(main_frame, text=f"DS店铺: {ds_shop_id}", font=(self.available_font, 14, "bold")).pack(anchor="w", pady=5)
        
        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=5)
        
        columns = ("product_id", "ds_product_id", "listing_status", "price_adjust", "remark")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        
        tree.heading("product_id", text="供应商品ID")
        tree.heading("ds_product_id", text="DS商品ID")
        tree.heading("listing_status", text="状态")
        tree.heading("price_adjust", text="价格调整")
        tree.heading("remark", text="备注")
        
        tree.column("product_id", width=120, anchor="center")
        tree.column("ds_product_id", width=120, anchor="center")
        tree.column("listing_status", width=80, anchor="center")
        tree.column("price_adjust", width=80, anchor="center")
        tree.column("remark", width=150, anchor="w")
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            
            mappings = db.get_ds_shop_products(ds_shop_id)
            db.close()
            
            for m in mappings:
                tree.insert("", "end", values=(
                    m.get('product_id', ''),
                    m.get('ds_product_id', ''),
                    m.get('listing_status', 'pending'),
                    m.get('price_adjust', 0),
                    m.get('remark', '')
                ))
            
        except Exception as e:
            self.log(f"获取店铺商品失败: {e}", "error")
        
        create_button(main_frame, "关闭", dialog.destroy, 'secondary', width=60).pack(pady=10)
    

    def _edit_ds_shop(self, ds_shop_id):
        """编辑DS店铺"""
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            
            shop = db.get_ds_shop(ds_shop_id)
            db.close()
            
            if not shop:
                self.show_info("错误", f"未找到店铺: {ds_shop_id}")
                return
            
            dialog = ctk.CTkToplevel(self.root)
            dialog.title(f"编辑DS店铺 - {ds_shop_id}")
            dialog.geometry("500x400")
            dialog.transient(self.root)
            dialog.grab_set()
            
            main_frame = ctk.CTkFrame(dialog)
            main_frame.pack(fill="both", expand=True, padx=15, pady=15)
            
            ctk.CTkLabel(main_frame, text=f"编辑DS店铺: {ds_shop_id}", font=(self.available_font, 16, "bold")).pack(pady=10)
            
            form_frame = ctk.CTkFrame(main_frame)
            form_frame.pack(fill="x", pady=10)
            
            ctk.CTkLabel(form_frame, text="店铺名称:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
            ds_shop_name_var = ctk.StringVar(value=shop.get('ds_shop_name', ''))
            ctk.CTkEntry(form_frame, textvariable=ds_shop_name_var, width=300).grid(row=0, column=1, padx=5, pady=5)
            
            ctk.CTkLabel(form_frame, text="平台:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
            ds_platform_var = ctk.StringVar(value=shop.get('ds_platform', 'jd'))
            ctk.CTkOptionMenu(form_frame, variable=ds_platform_var, values=["jd", "pdd", "tb", "other"], width=100).grid(row=1, column=1, padx=5, pady=5, sticky="w")
            
            ctk.CTkLabel(form_frame, text="店铺链接:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
            ds_shop_url_var = ctk.StringVar(value=shop.get('ds_shop_url', ''))
            ctk.CTkEntry(form_frame, textvariable=ds_shop_url_var, width=300).grid(row=2, column=1, padx=5, pady=5)
            
            ctk.CTkLabel(form_frame, text="状态:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
            shop_status_var = ctk.StringVar(value=shop.get('shop_status', 'active'))
            ctk.CTkOptionMenu(form_frame, variable=shop_status_var, values=["active", "inactive"], width=100).grid(row=3, column=1, padx=5, pady=5, sticky="w")
            
            ctk.CTkLabel(form_frame, text="备注:").grid(row=4, column=0, padx=5, pady=5, sticky="e")
            remark_var = ctk.StringVar(value=shop.get('remark', ''))
            ctk.CTkEntry(form_frame, textvariable=remark_var, width=300).grid(row=4, column=1, padx=5, pady=5)
            
            def save_changes():
                try:
                    from utils.database import get_shared_db
                    db = get_shared_db()
                    
                    db.save_ds_shop(
                        ds_shop_id=ds_shop_id,
                        ds_shop_name=ds_shop_name_var.get().strip(),
                        ds_platform=ds_platform_var.get(),
                        ds_shop_url=ds_shop_url_var.get().strip(),
                        remark=remark_var.get().strip()
                    )
                    db.execute("UPDATE ds_shops SET shop_status = ? WHERE ds_shop_id = ?", [shop_status_var.get(), ds_shop_id])
                    db.close()
                    
                    self.log(f"已更新DS店铺: {ds_shop_id}", "success")
                    self._refresh_ds_shops()
                    dialog.destroy()
                    
                except Exception as e:
                    self.log(f"更新DS店铺失败: {e}", "error")
            
            btn_frame = ctk.CTkFrame(main_frame)
            btn_frame.pack(fill="x", pady=10)
            
            create_button(btn_frame, "保存", save_changes, 'success', width=80).pack(side="left", padx=10)
            create_button(btn_frame, "取消", dialog.destroy, 'secondary', width=60).pack(side="left", padx=5)
            
        except Exception as e:
            self.log(f"获取店铺信息失败: {e}", "error")
    

    def _delete_ds_shop(self, ds_shop_id, ds_shop_name):
        """删除DS店铺"""
        confirm = self.ask_yes_no("确认删除", f"确定要删除店铺 '{ds_shop_name}' 吗？\n\n关联的商品映射也会被删除。")
        if not confirm:
            return
        
        try:
            from utils.database import get_shared_db
            db = get_shared_db()
            
            db.delete_ds_shop(ds_shop_id)
            db.close()
            
            self.log(f"已删除DS店铺: {ds_shop_name}", "success")
            self._refresh_ds_shops()
            
        except Exception as e:
            self.log(f"删除DS店铺失败: {e}", "error")
    

