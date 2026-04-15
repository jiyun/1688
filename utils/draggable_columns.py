import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Callable, Optional, Tuple


class DraggableColumnMixin:
    """可拖放列的混入类
    
    为Treeview提供列拖放重排功能
    使用方法：在类中继承此混入类，并调用_setup_draggable_columns
    """
    
    def _setup_draggable_columns(self, tree: ttk.Treeview, table_name: str, 
                                  all_columns: Dict[str, Dict], 
                                  visible_columns: List[str],
                                  on_columns_changed: Optional[Callable] = None):
        """设置可拖放列功能
        
        Args:
            tree: Treeview控件
            table_name: 表格名称(用于保存配置)
            all_columns: 所有列的配置字典
            visible_columns: 当前可见列列表
            on_columns_changed: 列变化时的回调函数
        """
        self._drag_tree = tree
        self._drag_table_name = table_name
        self._drag_all_columns = all_columns
        self._drag_visible_columns = list(visible_columns)
        self._drag_on_columns_changed = on_columns_changed
        
        self._drag_column = None
        self._drag_column_index = None
        self._drag_start_x = 0
        self._drag_hint_label = None
        
        tree.bind('<Button-1>', self._on_drag_button_press, add='+')
        tree.bind('<B1-Motion>', self._on_drag_motion, add='+')
        tree.bind('<ButtonRelease-1>', self._on_drag_button_release, add='+')
    
    def _on_drag_button_press(self, event):
        """鼠标按下事件"""
        region = self._drag_tree.identify_region(event.x, event.y)
        if region != "heading":
            return
        
        column = self._drag_tree.identify_column(event.x)
        if column:
            self._drag_column = column
            self._drag_column_index = int(column.replace('#', '')) - 1
            self._drag_start_x = event.x
    
    def _on_drag_motion(self, event):
        """鼠标移动事件"""
        if self._drag_column is None:
            return
        
        region = self._drag_tree.identify_region(event.x, event.y)
        if region != "heading":
            return
        
        if abs(event.x - self._drag_start_x) > 10:
            self._show_drag_indicator(event.x)
    
    def _on_drag_button_release(self, event):
        """鼠标释放事件"""
        if self._drag_column is None:
            return
        
        self._hide_drag_indicator()
        
        region = self._drag_tree.identify_region(event.x, event.y)
        if region != "heading":
            self._drag_column = None
            self._drag_column_index = None
            return
        
        target_column = self._drag_tree.identify_column(event.x)
        if target_column and target_column != self._drag_column:
            target_index = int(target_column.replace('#', '')) - 1
            visible_columns = self._drag_visible_columns
            
            if 0 <= target_index < len(visible_columns):
                source_col_name = visible_columns[self._drag_column_index] if self._drag_column_index < len(visible_columns) else None
                
                if source_col_name and source_col_name in visible_columns:
                    old_index = visible_columns.index(source_col_name)
                    visible_columns.pop(old_index)
                    new_index = min(target_index, len(visible_columns))
                    visible_columns.insert(new_index, source_col_name)
                    
                    self._drag_visible_columns = visible_columns
                    
                    if self._drag_on_columns_changed:
                        self._drag_on_columns_changed(visible_columns)
        
        self._drag_column = None
        self._drag_column_index = None
    
    def _show_drag_indicator(self, x: int):
        """显示拖放指示器"""
        if self._drag_hint_label is None:
            self._drag_hint_label = tk.Label(
                self._drag_tree,
                text="↔ 拖动调整列顺序",
                bg='#4a90d9',
                fg='white',
                padx=8,
                pady=2,
                font=('Microsoft YaHei UI', 9)
            )
        
        column = self._drag_tree.identify_column(x)
        if column:
            col_index = int(column.replace('#', '')) - 1
            visible_columns = self._drag_visible_columns
            if 0 <= col_index < len(visible_columns):
                bbox = self._drag_tree.bbox(column)
                if bbox:
                    self._drag_hint_label.place(x=bbox[0], y=0, anchor='nw')
                    return
        
        self._drag_hint_label.place(x=x, y=2, anchor='n')
    
    def _hide_drag_indicator(self):
        """隐藏拖放指示器"""
        if self._drag_hint_label:
            self._drag_hint_label.place_forget()
    
    def get_drag_visible_columns(self) -> List[str]:
        """获取当前可见列列表"""
        return list(self._drag_visible_columns)
    
    def set_drag_visible_columns(self, columns: List[str]):
        """设置可见列列表"""
        self._drag_visible_columns = list(columns)


class ColumnMenuMixin:
    """列选择菜单混入类
    
    为Treeview提供右键列选择菜单功能
    """
    
    def _setup_column_menu(self, tree: ttk.Treeview, table_name: str,
                           all_columns: Dict[str, Dict],
                           visible_columns: List[str],
                           on_columns_changed: Optional[Callable] = None):
        """设置列选择菜单功能
        
        Args:
            tree: Treeview控件
            table_name: 表格名称
            all_columns: 所有列的配置字典
            visible_columns: 当前可见列列表
            on_columns_changed: 列变化时的回调函数
        """
        self._menu_tree = tree
        self._menu_table_name = table_name
        self._menu_all_columns = all_columns
        self._menu_visible_columns = list(visible_columns)
        self._menu_on_columns_changed = on_columns_changed
        
        tree.bind('<Button-3>', self._on_column_menu_right_click, add='+')
    
    def _on_column_menu_right_click(self, event):
        """右键点击事件"""
        region = self._menu_tree.identify_region(event.x, event.y)
        if region == "heading":
            self._show_column_visibility_menu(event)
    
    def _show_column_visibility_menu(self, event):
        """显示列可见性菜单"""
        menu = tk.Menu(self._menu_tree, tearoff=0)
        menu.add_command(label="显示/隐藏列", state="disabled")
        menu.add_separator()
        
        for col_name, cfg in self._menu_all_columns.items():
            is_visible = col_name in self._menu_visible_columns
            label = f"{'✓ ' if is_visible else '   '}{cfg['text']}"
            menu.add_command(
                label=label,
                command=lambda c=col_name: self._toggle_menu_column_visibility(c)
            )
        
        menu.add_separator()
        menu.add_command(label="重置为默认", command=self._reset_menu_columns_to_default)
        
        menu.post(event.x_root, event.y_root)
    
    def _toggle_menu_column_visibility(self, column_name: str):
        """切换列可见性"""
        if column_name in self._menu_visible_columns:
            if len(self._menu_visible_columns) > 1:
                self._menu_visible_columns.remove(column_name)
        else:
            self._menu_visible_columns.append(column_name)
        
        if self._menu_on_columns_changed:
            self._menu_on_columns_changed(self._menu_visible_columns)
    
    def _reset_menu_columns_to_default(self):
        """重置列配置"""
        default_columns = [col for col, cfg in self._menu_all_columns.items() if cfg.get('default', True)]
        self._menu_visible_columns = default_columns
        
        if self._menu_on_columns_changed:
            self._menu_on_columns_changed(self._menu_visible_columns)
    
    def get_menu_visible_columns(self) -> List[str]:
        """获取当前可见列列表"""
        return list(self._menu_visible_columns)
    
    def set_menu_visible_columns(self, columns: List[str]):
        """设置可见列列表"""
        self._menu_visible_columns = list(columns)
