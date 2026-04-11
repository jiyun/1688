"""
图片编辑器画布组件

支持:
- 图片块显示
- 拖拽重排
- 噪音历史记录
- 智能布局拼接
- 列模式切换
- 涂抹工具
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Optional, Tuple
from PIL import Image, ImageTk
import os

from .image_block import ImageBlock
from .history import HistoryManager
from config import IMAGE_PROCESSING, FILE_NAMING, IMAGE_EDITOR_CONF


class LayoutType:
    """布局类型枚举"""
    HORIZONTAL = "horizontal"
    PIN_SHAPE = "pin"
    PIN_LIKE_4 = "pin_like_4"
    QI_SHAPE = "qi"


class EditorCanvas(tk.Canvas):
    """编辑器画布组件"""
    
    CANVAS_WIDTH = IMAGE_PROCESSING['detail_min_width']
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.blocks: List[ImageBlock] = []
        self.selected_blocks: List[ImageBlock] = []
        self.history = HistoryManager()
        
        self.mode = "block"
        self.merged_image: Optional[Image.Image] = None
        self._photo_images: List[ImageTk.PhotoImage] = []
        
        self._thumbnail_width = 200
        self._block_gap = 3
        self._padding = 10
        
        self._drag_data = {'block': None, 'start_y': 0, 'current_y': 0}
        self._drag_indicator = None
        
        self._tool = "select"
        self._brush_level = IMAGE_EDITOR_CONF['default_brush_level']
        self._brush_size = IMAGE_EDITOR_CONF['brush_sizes'][self._brush_level]
        self._paint_color = (255, 255, 255)
        self._last_paint_pos = None
        
        self._setup_bindings()
    
    def _setup_bindings(self):
        """设置事件绑定"""
        self.bind('<Button-1>', self._on_click)
        self.bind('<B1-Motion>', self._on_drag)
        self.bind('<ButtonRelease-1>', self._on_release)
        self.bind('<MouseWheel>', self._on_mousewheel)
        self.bind('<Double-Button-1>', self._on_double_click)
        self.bind('<Button-3>', self._on_paint_start)
        self.bind('<B3-Motion>', self._on_paint_move)
        self.bind('<ButtonRelease-3>', self._on_paint_end)
        self.bind('<Delete>', self._on_key_delete)
        self.bind('<Up>', self._on_key_up)
        self.bind('<Down>', self._on_key_down)
        self.bind('<Control-a>', self._on_key_select_all)
        
        self._heal_mask_points = []
    
    def set_on_update_callback(self, callback):
        """设置更新回调"""
        self._on_update_callback = callback
    
    def get_selected_block(self) -> Optional[ImageBlock]:
        """获取选中的块"""
        if self.selected_blocks:
            return self.selected_blocks[0]
        return None
    
    def set_tool(self, tool: str):
        """设置当前工具"""
        self._tool = tool
        if tool == "paint":
            self.config(cursor="crosshair")
        elif tool == "delete_row":
            self.config(cursor="X_cursor")
            self._delete_row_start = None
        elif tool == "pick_color":
            self.config(cursor="crosshair")
        elif tool == "spot_heal":
            self.config(cursor="circle")
            self._heal_mask = None
        else:
            self.config(cursor="")
    
    def set_brush_level(self, level: int):
        """设置画笔档位"""
        self._brush_level = max(1, min(5, level))
        self._brush_size = IMAGE_EDITOR_CONF['brush_sizes'][self._brush_level]
    
    def load_blocks(self, image_paths: List[str]):
        """加载图片块"""
        self.blocks = []
        self._block_items = {}
        self._block_heights = []
        
        for idx, path in enumerate(image_paths):
            block = ImageBlock(path, idx)
            self.blocks.append(block)
        
        self.history.save_state([b.to_dict() for b in self.blocks])
        self._refresh_canvas()
    
    def add_block(self, image_path: str, index: int = None) -> ImageBlock:
        """添加图片块"""
        if index is None:
            index = len(self.blocks)
        
        block = ImageBlock(image_path, index)
        self.blocks.insert(index, block)
        
        self.history.save_state([b.to_dict() for b in self.blocks])
        self._refresh_canvas()
        return block
    
    def remove_block(self, block: ImageBlock):
        """删除图片块"""
        if block in self.blocks:
            self.blocks.remove(block)
            self._reindex_blocks()
            self.history.save_state([b.to_dict() for b in self.blocks])
            self._refresh_canvas()
    
    def remove_selected_blocks(self):
        """删除选中的图片块"""
        if not self.selected_blocks:
            return
        
        for block in self.selected_blocks[:]:
            if block in self.blocks:
                self.blocks.remove(block)
        
        self.selected_blocks = []
        self._reindex_blocks()
        self.history.save_state([b.to_dict() for b in self.blocks])
        self._refresh_canvas()
    
    def _reindex_blocks(self):
        """重新索引图片块"""
        for idx, block in enumerate(self.blocks):
            block.index = idx
    
    def reorder_blocks(self, from_idx: int, to_idx: int):
        """重排图片块"""
        if from_idx == to_idx:
            return
        
        block = self.blocks.pop(from_idx)
        self.blocks.insert(to_idx, block)
        
        self._reindex_blocks()
        self.history.save_state([b.to_dict() for b in self.blocks])
        self._refresh_canvas()
    
    def get_selected_indices(self) -> List[int]:
        """获取选中块的索引"""
        return sorted([b.index for b in self.selected_blocks])
    
    def select_all(self):
        """全选"""
        self.selected_blocks = self.blocks.copy()
        self._refresh_canvas()
    
    def clear_selection(self):
        """清除选择"""
        self.selected_blocks = []
        self._refresh_canvas()
    
    def undo(self) -> bool:
        """撤销"""
        restored = self.history.undo()
        if restored:
            self._restore_from_history(restored)
            return True
        return False
    
    def redo(self) -> bool:
        """重做"""
        restored = self.history.redo()
        if restored:
            self._restore_from_history(restored)
            return True
        return False
    
    def _restore_from_history(self, blocks_data: List[dict]):
        """从历史记录恢复"""
        self.blocks = [ImageBlock.from_dict(d) for d in blocks_data]
        self._reindex_blocks()
        self._refresh_canvas()
    
    def _refresh_canvas(self):
        """刷新画布"""
        self.delete('all')
        self._block_items = {}
        self._block_heights = []
        self._total_height = 0
        self._photo_images = []
        
        if not self.blocks:
            return
        
        y_offset = self._padding
        
        for block in self.blocks:
            thumbnail = block.get_thumbnail()
            if thumbnail:
                thumb_height = int(thumbnail.height * self._thumbnail_width / thumbnail.width)
                
                resized_thumbnail = thumbnail.resize((self._thumbnail_width, thumb_height), Image.LANCZOS)
                photo_image = ImageTk.PhotoImage(resized_thumbnail)
                self._photo_images.append(photo_image)
                
                self._block_heights.append(thumb_height)
                self._total_height += thumb_height + self._block_gap
                
                item_id = self.create_image(
                    self._thumbnail_width // 2, y_offset + thumb_height // 2,
                    image=photo_image,
                    anchor='center'
                )
                
                self._block_items[item_id] = block
                
                if block in self.selected_blocks:
                    self.create_rectangle(
                        0, y_offset,
                        self._thumbnail_width, y_offset + thumb_height,
                        outline='red',
                        width=2
                    )
                
                y_offset += thumb_height + self._block_gap
        
        self.configure(scrollregion=(0, 0, self._thumbnail_width, self._total_height + 100))
        
        if self._on_update_callback:
            self._on_update_callback(len(self.blocks), self._total_height)
    
    def _on_click(self, event):
        """点击事件"""
        canvas_x = self.canvasx(event.x)
        canvas_y = self.canvasy(event.y)
        
        if self.mode == "column":
            if self._tool == "delete_row":
                self._delete_row_start = canvas_y
                self._show_delete_indicator(canvas_y, canvas_y)
                return
            elif self._tool == "pick_color":
                color = self.pick_color_from_position(int(canvas_x), int(canvas_y))
                if color:
                    self._paint_color = color
                    if self._on_update_callback:
                        self._on_update_callback(len(self.blocks), self.merged_image.height if self.merged_image else 0)
                return
            elif self._tool == "spot_heal":
                self._start_spot_heal(int(canvas_x), int(canvas_y))
                return
            return
        
        clicked_block = None
        current_y = self._padding
        
        for i, block in enumerate(self.blocks):
            if i < len(self._block_heights):
                block_height = self._block_heights[i]
                if current_y <= canvas_y <= current_y + block_height:
                    clicked_block = block
                    break
                current_y += block_height + self._block_gap
        
        if not clicked_block:
            clicked_items = self.find_overlapping(canvas_x - 10, canvas_y - 10, canvas_x + 10, canvas_y + 10)
            if not clicked_items:
                clicked_items = self.find_closest(canvas_x, canvas_y)
            
            if clicked_items:
                for item_id in clicked_items:
                    block = self._block_items.get(item_id)
                    if block:
                        clicked_block = block
                        break
        
        if clicked_block:
            if event.state & 0x0004:
                if clicked_block not in self.selected_blocks:
                    self.selected_blocks.append(clicked_block)
                else:
                    self.selected_blocks.remove(clicked_block)
            else:
                self.selected_blocks = [clicked_block]
            
            self._drag_data['block'] = clicked_block
            self._drag_data['start_y'] = event.y
            self._refresh_canvas()
    
    def _on_drag(self, event):
        """拖拽事件"""
        if self.mode == "column" and self._tool == "delete_row" and self._delete_row_start is not None:
            canvas_y = self.canvasy(event.y)
            self._show_delete_indicator(self._delete_row_start, canvas_y)
            return
        
        if self.mode == "column" and self._tool == "spot_heal":
            canvas_x = self.canvasx(event.x)
            canvas_y = self.canvasy(event.y)
            self._heal_mask_points.append((int(canvas_x), int(canvas_y)))
            self._show_heal_indicator(int(canvas_x), int(canvas_y))
            return
        
        if self._drag_data['block']:
            self._drag_data['current_y'] = event.y
            self._show_drag_indicator(event.y)
    
    def _on_release(self, event):
        """释放事件"""
        if self.mode == "column" and self._tool == "delete_row" and self._delete_row_start is not None:
            canvas_y = self.canvasy(event.y)
            start_y = min(int(self._delete_row_start), int(canvas_y))
            end_y = max(int(self._delete_row_start), int(canvas_y))
            
            if end_y - start_y > 5:
                self.delete_rows(start_y, end_y)
            
            self._hide_delete_indicator()
            self._delete_row_start = None
            self.set_tool("select")
            return
        
        if self.mode == "column" and self._tool == "spot_heal":
            if self._heal_mask_points:
                self._apply_spot_heal()
            self.set_tool("select")
            return
        
        block = self._drag_data['block']
        if block:
            if abs(event.y - self._drag_data['start_y']) > 10:
                insert_idx = self._get_insert_index(event.y)
                
                if insert_idx is not None and insert_idx != block.index:
                    self.reorder_blocks(block.index, insert_idx)
            
            self._hide_drag_indicator()
        
        self._drag_data = {'block': None, 'start_y': 0, 'current_y': 0}
    
    def _on_mousewheel(self, event):
        """鼠标滚轮 - 滚动画布"""
        if self.mode == "block":
            if event.delta > 0:
                self.yview_scroll(-1, "units")
            else:
                self.yview_scroll(1, "units")
        else:
            if event.delta > 0:
                self.yview_scroll(-2, "units")
            else:
                self.yview_scroll(2, "units")
    
    def _on_key_delete(self, event):
        """键盘删除"""
        if self.mode == "block":
            self.remove_selected_blocks()
    
    def _on_key_up(self, event):
        """键盘上移选择"""
        if self.mode == "block" and self.blocks:
            if not self.selected_blocks:
                self.selected_blocks = [self.blocks[0]]
            else:
                current_idx = self.selected_blocks[0].index
                if current_idx > 0:
                    self.selected_blocks = [self.blocks[current_idx - 1]]
            self._refresh_canvas()
    
    def _on_key_down(self, event):
        """键盘下移选择"""
        if self.mode == "block" and self.blocks:
            if not self.selected_blocks:
                self.selected_blocks = [self.blocks[0]]
            else:
                current_idx = self.selected_blocks[0].index
                if current_idx < len(self.blocks) - 1:
                    self.selected_blocks = [self.blocks[current_idx + 1]]
            self._refresh_canvas()
    
    def _on_key_select_all(self, event):
        """键盘全选"""
        if self.mode == "block":
            self.select_all()
    
    def _on_double_click(self, event):
        """双击事件 - 预览原图"""
        closest_items = self.find_closest(event.x, event.y)
        if not closest_items:
            return
        
        for item_id in closest_items:
            block = self._block_items.get(item_id)
            if block:
                self._show_preview(block)
                return
    
    def _get_insert_index(self, y: int) -> int:
        """计算插入位置"""
        if not self._block_heights:
            return 0
        
        current_y = self._padding
        for idx, height in enumerate(self._block_heights):
            block_center = current_y + height // 2
            if y < block_center:
                return idx
            current_y += height + self._block_gap
        
        return len(self.blocks)
    
    def _show_drag_indicator(self, y: int):
        """显示拖拽指示线（带动画效果）"""
        self.delete('drag_indicator')
        self.delete('drag_preview')
        
        insert_idx = self._get_insert_index(y)
        if insert_idx is None:
            return
        
        indicator_y = self._padding
        for i in range(insert_idx):
            if i < len(self._block_heights):
                indicator_y += self._block_heights[i] + self._block_gap
        
        self._drag_indicator = self.create_line(
            0, indicator_y,
            self._thumbnail_width, indicator_y,
            fill='#FF4444',
            width=4,
            tags='drag_indicator'
        )
        
        self._animate_drag_indicator()
        
        if self._drag_data['block']:
            block = self._drag_data['block']
            thumbnail = block.get_thumbnail()
            if thumbnail:
                canvas_y = self.canvasy(y)
                
                preview_img = thumbnail.copy()
                preview_img = preview_img.convert('RGBA')
                
                from PIL import ImageEnhance
                alpha = preview_img.split()[3]
                alpha = ImageEnhance.Brightness(alpha).enhance(0.6)
                preview_img.putalpha(alpha)
                
                preview_photo = ImageTk.PhotoImage(preview_img)
                self._drag_preview_photo = preview_photo
                
                self.create_image(
                    self._thumbnail_width // 2, canvas_y,
                    image=preview_photo,
                    anchor='center',
                    tags='drag_preview'
                )
    
    def _animate_drag_indicator(self):
        """拖拽指示线动画"""
        if not self._drag_indicator:
            return
        
        self.delete('drag_indicator_glow')
        
        indicator_y = self.coords(self._drag_indicator)[1]
        
        self.create_line(
            0, indicator_y - 2,
            self._thumbnail_width, indicator_y - 2,
            fill='#FF8888',
            width=8,
            stipple='gray50',
            tags='drag_indicator_glow'
        )
        
        self.tag_lower('drag_indicator_glow', 'drag_indicator')
    
    def _hide_drag_indicator(self):
        """隐藏拖拽指示线"""
        self.delete('drag_indicator')
        self.delete('drag_indicator_glow')
        self.delete('drag_preview')
        self._drag_indicator = None
        if hasattr(self, '_drag_preview_photo'):
            delattr(self, '_drag_preview_photo')
    
    def _show_preview(self, block: ImageBlock):
        """显示预览窗口"""
        preview_window = tk.Toplevel(self)
        preview_window.title(f"预览 - {os.path.basename(block.image_path) if block.image_path else '组合块'}")
        
        img = block.get_original_image()
        if img:
            max_size = (800, 800)
            img_copy = img.copy()
            img_copy.thumbnail(max_size, Image.LANCZOS)
            photo = ImageTk.PhotoImage(img_copy)
            
            label = ttk.Label(preview_window, image=photo)
            label.image = photo
            label.pack(padx=10, pady=10)
    
    def switch_mode(self, mode: str):
        """切换模式"""
        if self.mode == mode:
            return
        
        self.mode = mode
        
        if mode == "column":
            self._prepare_column_mode()
        else:
            self._prepare_block_mode()
        
        self._refresh_canvas()
    
    def _prepare_column_mode(self):
        """准备列模式"""
        if not self.blocks:
            return
        
        self.merged_image = self._stitch_vertical()
        
        if self.merged_image:
            self.delete('all')
            
            display_height = self.merged_image.height
            self._merged_photo = ImageTk.PhotoImage(self.merged_image)
            
            self.create_image(
                self.CANVAS_WIDTH // 2, 0,
                image=self._merged_photo,
                anchor='n'
            )
            
            self.configure(scrollregion=(0, 0, self.CANVAS_WIDTH, display_height))
            
            if self._on_update_callback:
                self._on_update_callback(len(self.blocks), display_height)
    
    def _prepare_block_mode(self):
        """准备块模式"""
        self.delete('all')
        self.merged_image = None
        self._refresh_canvas()
    
    def _stitch_vertical(self) -> Image.Image:
        """垂直拼接图片"""
        if not self.blocks:
            return None
        
        total_height = sum(b.height for b in self.blocks)
        canvas_width = self.CANVAS_WIDTH
        
        result = Image.new('RGB', (canvas_width, total_height), (255, 255, 255))
        
        y_offset = 0
        for block in self.blocks:
            img = block.get_original_image()
            if img:
                x_offset = (canvas_width - img.width) // 2
                result.paste(img, (x_offset, y_offset))
                y_offset += img.height
        
        return result
    
    def stitch_horizontal(self, blocks: List[ImageBlock], equal_height: bool = False) -> ImageBlock:
        """横向拼接"""
        if not blocks:
            return None
        
        if equal_height:
            target_height = max(b.height for b in blocks)
            resized_blocks = []
            for block in blocks:
                img = block.get_original_image()
                if img:
                    scale = target_height / img.height
                    new_width = int(img.width * scale)
                    resized = img.resize((new_width, target_height), Image.LANCZOS)
                    resized_blocks.append(resized)
        else:
            resized_blocks = blocks
        
        total_width = sum(b.width for b in resized_blocks)
        max_height = max(b.height for b in resized_blocks)
        
        result = Image.new('RGB', (total_width, max_height), (255, 255, 255))
        
        x_offset = 0
        for block in resized_blocks:
            x = (total_width - block.width) // 2
            y = (max_height - block.height) // 2
            result.paste(block, (x_offset, y))
            x_offset += block.width
        
        composite = ImageBlock(None, blocks[0].index)
        composite.original_image = result
        composite.width = total_width
        composite.height = max_height
        composite.sub_blocks = blocks
        
        return composite
    
    def detect_layout_type(self, blocks: List[ImageBlock]) -> str:
        """根据图片数量和横竖比例智能判断布局类型"""
        n = len(blocks)
        if n <= 2:
            return LayoutType.HORIZONTAL
        
        horizontal_count = sum(1 for b in blocks if b.width >= b.height)
        vertical_count = n - horizontal_count
        
        if n == 3:
            return LayoutType.PIN_SHAPE
        elif n == 4:
            return LayoutType.PIN_LIKE_4
        elif n == 5:
            return LayoutType.QI_SHAPE
        else:
            return LayoutType.HORIZONTAL
    
    def stitch_smart_layout(self, blocks: List[ImageBlock] = None, 
                           layout: str = None) -> ImageBlock:
        """智能布局拼接"""
        if blocks is None:
            blocks = self.selected_blocks
        
        if not blocks or len(blocks) < 2:
            return None
        
        if layout is None:
            layout = self.detect_layout_type(blocks)
        
        if layout == LayoutType.HORIZONTAL:
            return self._stitch_horizontal_simple(blocks)
        elif layout == LayoutType.PIN_SHAPE:
            return self._stitch_pin_shape(blocks)
        elif layout == LayoutType.PIN_LIKE_4:
            return self._stitch_pin_like_4(blocks)
        elif layout == LayoutType.QI_SHAPE:
            return self._stitch_qi_shape(blocks)
        
        return self._stitch_horizontal_simple(blocks)
    
    def _stitch_horizontal_simple(self, blocks: List[ImageBlock]) -> ImageBlock:
        """简单横向拼接"""
        images = []
        for block in blocks:
            img = block.get_original_image()
            if img:
                images.append(img)
        
        if not images:
            return None
        
        target_height = max(img.height for img in images)
        resized_images = []
        for img in images:
            if img.height != target_height:
                scale = target_height / img.height
                new_width = int(img.width * scale)
                resized_images.append(img.resize((new_width, target_height), Image.LANCZOS))
            else:
                resized_images.append(img)
        
        total_width = sum(img.width for img in resized_images)
        result = Image.new('RGB', (total_width, target_height), (255, 255, 255))
        
        x_offset = 0
        for img in resized_images:
            result.paste(img, (x_offset, 0))
            x_offset += img.width
        
        composite = ImageBlock(None, blocks[0].index)
        composite.original_image = result
        composite.width = total_width
        composite.height = target_height
        composite.sub_blocks = blocks
        
        return composite
    
    def _stitch_pin_shape(self, blocks: List[ImageBlock]) -> ImageBlock:
        """品字型拼接（3张）"""
        if len(blocks) != 3:
            return self._stitch_horizontal_simple(blocks)
        
        images = []
        for block in blocks:
            img = block.get_original_image()
            if img:
                images.append(img)
        
        if len(images) != 3:
            return None
        
        horizontal = [img for img in images if img.width >= img.height]
        vertical = [img for img in images if img.width < img.height]
        
        target_width = self.CANVAS_WIDTH
        
        if len(horizontal) >= 2:
            top_width = target_width // 2
            top_images = []
            for img in horizontal[:2]:
                scale = top_width / img.width
                new_height = int(img.height * scale)
                top_images.append(img.resize((top_width, new_height), Image.LANCZOS))
            
            top_height = max(img.height for img in top_images)
            
            bottom_img = vertical[0] if vertical else horizontal[2]
            bottom_scale = target_width / bottom_img.width
            bottom_height = int(bottom_img.height * bottom_scale)
            bottom_resized = bottom_img.resize((target_width, bottom_height), Image.LANCZOS)
            
            total_height = top_height + bottom_height
            result = Image.new('RGB', (target_width, total_height), (255, 255, 255))
            
            result.paste(top_images[0], (0, 0))
            result.paste(top_images[1], (top_width, 0))
            result.paste(bottom_resized, (0, top_height))
        else:
            left_width = target_width // 2
            left_img = vertical[0]
            left_scale = left_width / left_img.width
            left_height = int(left_img.height * left_scale)
            left_resized = left_img.resize((left_width, left_height), Image.LANCZOS)
            
            right_width = target_width - left_width
            right_images = []
            for img in horizontal:
                scale = right_width / img.width
                new_height = int(img.height * scale)
                right_images.append(img.resize((right_width, new_height), Image.LANCZOS))
            
            right_height = sum(img.height for img in right_images)
            total_height = max(left_height, right_height)
            
            result = Image.new('RGB', (target_width, total_height), (255, 255, 255))
            
            result.paste(left_resized, (0, 0))
            
            y_offset = 0
            for img in right_images:
                result.paste(img, (left_width, y_offset))
                y_offset += img.height
        
        composite = ImageBlock(None, blocks[0].index)
        composite.original_image = result
        composite.width = result.width
        composite.height = result.height
        composite.sub_blocks = blocks
        
        return composite
    
    def _stitch_pin_like_4(self, blocks: List[ImageBlock]) -> ImageBlock:
        """类品字型拼接（4张）"""
        if len(blocks) != 4:
            return self._stitch_horizontal_simple(blocks)
        
        images = []
        for block in blocks:
            img = block.get_original_image()
            if img:
                images.append(img)
        
        if len(images) != 4:
            return None
        
        horizontal = [img for img in images if img.width >= img.height]
        vertical = [img for img in images if img.width < img.height]
        
        target_width = self.CANVAS_WIDTH
        
        if len(horizontal) >= 3:
            left_width = target_width * 2 // 3
            right_width = target_width - left_width
            
            left_images = []
            for img in horizontal[:3]:
                scale = left_width // 2 / img.width
                new_height = int(img.height * scale)
                left_images.append(img.resize((left_width // 2, new_height), Image.LANCZOS))
            
            left_height = sum(img.height for img in left_images)
            
            right_img = vertical[0] if vertical else horizontal[3]
            right_scale = right_width / right_img.width
            right_height = int(right_img.height * right_scale)
            right_resized = right_img.resize((right_width, right_height), Image.LANCZOS)
            
            total_height = max(left_height, right_height)
            result = Image.new('RGB', (target_width, total_height), (255, 255, 255))
            
            y_offset = 0
            for img in left_images:
                result.paste(img, (0, y_offset))
                y_offset += img.height
            
            result.paste(right_resized, (left_width, 0))
        else:
            top_height = target_width // 2
            top_images = []
            for img in vertical[:3]:
                scale = top_height / img.height
                new_width = int(img.width * scale)
                top_images.append(img.resize((new_width, top_height), Image.LANCZOS))
            
            top_width = sum(img.width for img in top_images)
            
            bottom_img = horizontal[0] if horizontal else vertical[3]
            bottom_scale = target_width / bottom_img.width
            bottom_height = int(bottom_img.height * bottom_scale)
            bottom_resized = bottom_img.resize((target_width, bottom_height), Image.LANCZOS)
            
            total_height = top_height + bottom_height
            result = Image.new('RGB', (target_width, total_height), (255, 255, 255))
            
            x_offset = 0
            for img in top_images:
                result.paste(img, (x_offset, 0))
                x_offset += img.width
            
            result.paste(bottom_resized, (0, top_height))
        
        composite = ImageBlock(None, blocks[0].index)
        composite.original_image = result
        composite.width = result.width
        composite.height = result.height
        composite.sub_blocks = blocks
        
        return composite
    
    def _stitch_qi_shape(self, blocks: List[ImageBlock]) -> ImageBlock:
        """器字形拼接（5张）"""
        if len(blocks) != 5:
            return self._stitch_horizontal_simple(blocks)
        
        images = []
        for block in blocks:
            img = block.get_original_image()
            if img:
                images.append(img)
        
        if len(images) != 5:
            return None
        
        horizontal = [img for img in images if img.width >= img.height]
        vertical = [img for img in images if img.width < img.height]
        
        target_width = self.CANVAS_WIDTH
        
        if len(vertical) >= 1:
            center_width = target_width // 3
            side_width = (target_width - center_width) // 2
            
            center_img = vertical[0]
            center_scale = center_width / center_img.width
            center_height = int(center_img.height * center_scale)
            center_resized = center_img.resize((center_width, center_height), Image.LANCZOS)
            
            left_images = []
            for img in horizontal[:2]:
                scale = side_width / img.width
                new_height = int(img.height * scale)
                left_images.append(img.resize((side_width, new_height), Image.LANCZOS))
            
            right_images = []
            for img in horizontal[2:4]:
                scale = side_width / img.width
                new_height = int(img.height * scale)
                right_images.append(img.resize((side_width, new_height), Image.LANCZOS))
            
            left_height = sum(img.height for img in left_images)
            right_height = sum(img.height for img in right_images)
            total_height = max(left_height, center_height, right_height)
            
            result = Image.new('RGB', (target_width, total_height), (255, 255, 255))
            
            y_offset = 0
            for img in left_images:
                result.paste(img, (0, y_offset))
                y_offset += img.height
            
            result.paste(center_resized, (side_width, 0))
            
            y_offset = 0
            for img in right_images:
                result.paste(img, (side_width + center_width, y_offset))
                y_offset += img.height
        else:
            top_height = target_width // 3
            top_images = []
            for img in horizontal[:2]:
                scale = top_height / img.height
                new_width = int(img.width * scale)
                top_images.append(img.resize((new_width, top_height), Image.LANCZOS))
            
            middle_img = horizontal[2]
            middle_scale = target_width / middle_img.width
            middle_height = int(middle_img.height * middle_scale)
            middle_resized = middle_img.resize((target_width, middle_height), Image.LANCZOS)
            
            bottom_images = []
            for img in horizontal[3:5]:
                scale = top_height / img.height
                new_width = int(img.width * scale)
                bottom_images.append(img.resize((new_width, top_height), Image.LANCZOS))
            
            total_height = top_height + middle_height + top_height
            result = Image.new('RGB', (target_width, total_height), (255, 255, 255))
            
            x_offset = 0
            for img in top_images:
                result.paste(img, (x_offset, 0))
                x_offset += img.width
            
            result.paste(middle_resized, (0, top_height))
            
            x_offset = 0
            for img in bottom_images:
                result.paste(img, (x_offset, top_height + middle_height))
                x_offset += img.width
        
        composite = ImageBlock(None, blocks[0].index)
        composite.original_image = result
        composite.width = result.width
        composite.height = result.height
        composite.sub_blocks = blocks
        
        return composite
    
    def unbind_composite(self, composite_block: ImageBlock) -> List[ImageBlock]:
        """解绑组合块"""
        if not composite_block.is_composite():
            return [composite_block]
        
        original_blocks = composite_block.sub_blocks
        start_idx = composite_block.index
        
        for i in range(len(original_blocks)):
            original_blocks[i].index = start_idx + i
        
        return original_blocks
    
    def convert_aspect_ratio(self, target_ratio: str = "1:1"):
        """比例转换"""
        from .tools import convert_aspect_ratio as convert_aspect_ratio_func
        
        if not self.selected_blocks:
            return
        
        for block in self.selected_blocks:
            img = block.get_original_image()
            if img:
                converted = convert_aspect_ratio_func(img, target_ratio)
                block.original_image = converted
                block.width = converted.width
                block.height = converted.height
        
        self.history.save_state([b.to_dict() for b in self.blocks])
        self._refresh_canvas()
    
    def generate_video(self, duration: int = 15):
        """生成视频"""
        if not self.blocks:
            return
        
        from utils.video_generator import generate_scroll_video
        
        image_paths = [b.image_path for b in self.blocks]
        
        return generate_scroll_video(image_paths, duration=duration)
    
    def _on_paint_start(self, event):
        """开始涂抹"""
        if self.mode != "column" or not self.merged_image:
            return
        
        canvas_x = self.canvasx(event.x)
        canvas_y = self.canvasy(event.y)
        
        self._last_paint_pos = (int(canvas_x), int(canvas_y))
        self._paint_on_image(int(canvas_x), int(canvas_y))
    
    def _on_paint_move(self, event):
        """涂抹移动"""
        if self.mode != "column" or not self.merged_image:
            return
        
        canvas_x = self.canvasx(event.x)
        canvas_y = self.canvasy(event.y)
        
        if self._last_paint_pos:
            self._draw_line_on_image(
                self._last_paint_pos[0], self._last_paint_pos[1],
                int(canvas_x), int(canvas_y)
            )
        
        self._last_paint_pos = (int(canvas_x), int(canvas_y))
    
    def _on_paint_end(self, event):
        """结束涂抹"""
        self._last_paint_pos = None
        self.history.save_state([b.to_dict() for b in self.blocks])
    
    def _paint_on_image(self, x: int, y: int):
        """在图片上涂抹"""
        if not self.merged_image:
            return
        
        from PIL import ImageDraw
        
        img = self.merged_image
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        draw = ImageDraw.Draw(img)
        
        half_size = self._brush_size // 2
        draw.ellipse(
            [x - half_size, y - half_size, x + half_size, y + half_size],
            fill=self._paint_color
        )
        
        self.merged_image = img
        self._update_column_display()
    
    def _draw_line_on_image(self, x1: int, y1: int, x2: int, y2: int):
        """在图片上绘制线条"""
        if not self.merged_image:
            return
        
        from PIL import ImageDraw
        
        img = self.merged_image
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        draw = ImageDraw.Draw(img)
        
        draw.line(
            [(x1, y1), (x2, y2)],
            fill=self._paint_color,
            width=self._brush_size
        )
        
        self.merged_image = img
        self._update_column_display()
    
    def _update_column_display(self):
        """更新列模式显示"""
        if not self.merged_image:
            return
        
        self.delete('all')
        
        display_height = self.merged_image.height
        self._merged_photo = ImageTk.PhotoImage(self.merged_image)
        
        self.create_image(
            self.CANVAS_WIDTH // 2, 0,
            image=self._merged_photo,
            anchor='n'
        )
        
        self.configure(scrollregion=(0, 0, self.CANVAS_WIDTH, display_height))
    
    def set_paint_color(self, color: tuple):
        """设置涂抹颜色"""
        self._paint_color = color
    
    def pick_color_from_position(self, x: int, y: int):
        """从图片位置取色"""
        if not self.merged_image:
            return None
        
        if 0 <= x < self.merged_image.width and 0 <= y < self.merged_image.height:
            return self.merged_image.getpixel((x, y))
        
        return None
    
    def delete_rows(self, start_y: int, end_y: int):
        """删除指定行范围的像素"""
        if not self.merged_image or self.mode != "column":
            return False
        
        if start_y < 0:
            start_y = 0
        if end_y > self.merged_image.height:
            end_y = self.merged_image.height
        
        if start_y >= end_y:
            return False
        
        width = self.merged_image.width
        height = self.merged_image.height
        
        top_part = self.merged_image.crop((0, 0, width, start_y))
        bottom_part = self.merged_image.crop((0, end_y, width, height))
        
        new_height = top_part.height + bottom_part.height
        result = Image.new('RGB', (width, new_height), (255, 255, 255))
        
        result.paste(top_part, (0, 0))
        result.paste(bottom_part, (0, top_part.height))
        
        self.merged_image = result
        self._update_column_display()
        self.history.save_state([b.to_dict() for b in self.blocks])
        
        return True
    
    def split_to_blocks(self) -> List[ImageBlock]:
        """将merged_image拆分为多块详情图"""
        if not self.merged_image:
            return []
        
        from utils.image_processor import split_merged_image
        import tempfile
        
        target_width = self.CANVAS_WIDTH
        total_height = self.merged_image.height
        max_single_height = target_width * 2
        
        new_blocks = []
        
        if total_height <= max_single_height:
            block = ImageBlock(None, 0)
            block.original_image = self.merged_image.copy()
            block.width = self.merged_image.width
            block.height = self.merged_image.height
            new_blocks.append(block)
        else:
            num_parts = (total_height + max_single_height - 1) // max_single_height
            part_height = total_height // num_parts
            
            current_y = 0
            for i in range(num_parts):
                if i == num_parts - 1:
                    end_y = total_height
                else:
                    end_y = current_y + part_height
                
                end_y = min(end_y, total_height)
                
                part_image = self.merged_image.crop((0, current_y, target_width, end_y))
                
                block = ImageBlock(None, i)
                block.original_image = part_image
                block.width = part_image.width
                block.height = part_image.height
                new_blocks.append(block)
                
                current_y = end_y
        
        return new_blocks
    
    def apply_column_edits(self):
        """应用列模式编辑，拆分为新的块列表"""
        if self.mode != "column" or not self.merged_image:
            return False
        
        new_blocks = self.split_to_blocks()
        
        if new_blocks:
            self.blocks = new_blocks
            self._reindex_blocks()
            self.history.save_state([b.to_dict() for b in self.blocks])
            self.switch_mode("block")
            return True
        
        return False
    
    def get_row_position(self, y: int) -> int:
        """获取Y坐标对应的行位置（用于删除行）"""
        if not self.merged_image:
            return -1
    
    def _show_delete_indicator(self, start_y: float, end_y: float):
        """显示删除区域指示器"""
        self.delete('delete_indicator')
        
        min_y = min(start_y, end_y)
        max_y = max(start_y, end_y)
        
        self.create_rectangle(
            0, min_y,
            self.CANVAS_WIDTH, max_y,
            fill='red',
            stipple='gray50',
            outline='red',
            width=2,
            tags='delete_indicator'
        )
        
        self.create_text(
            self.CANVAS_WIDTH // 2, (min_y + max_y) // 2,
            text="删除区域",
            fill='white',
            font=("", 12, "bold"),
            tags='delete_indicator'
        )
    
    def _hide_delete_indicator(self):
        """隐藏删除区域指示器"""
        self.delete('delete_indicator')
    
    def _start_spot_heal(self, x: int, y: int):
        """开始污点去除"""
        if not self.merged_image:
            return
        
        self._heal_mask_points = [(x, y)]
        self._hide_heal_indicator()
        self._show_heal_indicator(x, y)
    
    def _on_spot_heal_move(self, x: int, y: int):
        """污点去除移动"""
        if not self.merged_image or not hasattr(self, '_heal_mask_points'):
            return
        
        self._heal_mask_points.append((x, y))
        self._show_heal_indicator(x, y)
    
    def _apply_spot_heal(self):
        """应用污点去除（使用OpenCV Inpainting）"""
        if not self.merged_image or not self._heal_mask_points:
            return False
        
        try:
            import cv2
            import numpy as np
            
            img_array = np.array(self.merged_image)
            mask = np.zeros(img_array.shape[:2], dtype=np.uint8)
            
            for x, y in self._heal_mask_points:
                if 0 <= y < mask.shape[0] and 0 <= x < mask.shape[1]:
                    cv2.circle(mask, (x, y), self._brush_size, 255, -1)
            
            result = cv2.inpaint(img_array, mask, 3, cv2.INPAINT_TELEA)
            
            self.merged_image = Image.fromarray(result)
            self._update_column_display()
            self.history.save_state([b.to_dict() for b in self.blocks])
            
            self._hide_heal_indicator()
            self._heal_mask_points = []
            
            return True
        except ImportError:
            print("需要安装opencv-python: pip install opencv-python")
            return False
        except Exception as e:
            print(f"污点去除失败: {e}")
            return False
    
    def _show_heal_indicator(self, x: int, y: int):
        """显示污点去除指示器"""
        half_size = self._brush_size // 2
        
        self.create_oval(
            x - half_size, y - half_size,
            x + half_size, y + half_size,
            outline='green',
            width=2,
            tags='heal_indicator'
        )
        
        if len(self._heal_mask_points) > 1:
            prev_x, prev_y = self._heal_mask_points[-2]
            self.create_line(
                prev_x, prev_y, x, y,
                fill='green',
                width=self._brush_size,
                tags='heal_indicator'
            )
    
    def _hide_heal_indicator(self):
        """隐藏污点去除指示器"""
        self.delete('heal_indicator')
