"""
图片编辑器主窗口

提供完整的图片编辑功能界面
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog
from typing import List, Optional

import customtkinter as ctk
from PIL import Image, ImageTk

from .editor_canvas import EditorCanvas
from .image_block import ImageBlock
from .tools import convert_aspect_ratio, detect_image_ratio
from config import IMAGE_EDITOR_CONF, IMAGE_PROCESSING, FILE_NAMING


class ImageEditorWindow(ctk.CTkToplevel):
    """图片编辑器主窗口"""
    
    MAIN_IMAGE_COUNT = 5
    
    def __init__(self, master, product_id: str = None):
        super().__init__(master)
        
        self.product_id = product_id
        self.output_path = None
        
        self.title("商品图片编辑器")
        self.geometry("1400x900")
        
        self._setup_ui()
        self._setup_bindings()
        
        if product_id:
            self.load_product_images(product_id)
    
    def _setup_ui(self):
        """设置UI"""
        self._create_tabview()
        self._create_status_bar()
    
    def _create_tabview(self):
        """创建选项卡"""
        self._tabview = ctk.CTkTabview(self)
        self._tabview.add("详情图")
        self._tabview.add("主图")
        self._tabview.add("色卡")
        self._tabview.add("视频")
        self._tabview.pack(fill="both", expand=True, padx=5, pady=5)
        
        self._setup_detail_tab()
        self._setup_main_image_tab()
        self._setup_color_tab()
        self._setup_video_tab()
    
    def _setup_detail_tab(self):
        """设置详情图选项卡"""
        detail_frame = self._tabview.tab("详情图")
        
        toolbar = ctk.CTkFrame(detail_frame)
        toolbar.pack(side="left", fill="y", padx=5, pady=5)
        
        self._create_product_input(toolbar)
        self._create_tool_buttons(toolbar)
        self._create_mode_switch(toolbar)
        self._create_history_buttons(toolbar)
        
        main_content = ctk.CTkFrame(detail_frame)
        main_content.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        canvas_frame = ctk.CTkFrame(main_content)
        canvas_frame.pack(side="left", fill="both", expand=True)
        
        self._canvas = EditorCanvas(canvas_frame, width=IMAGE_PROCESSING['detail_min_width'])
        self._canvas.pack(side="left", fill="both", expand=True)
        
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=v_scrollbar.set)
        v_scrollbar.pack(side="right", fill="y")
        
        resource_frame = ctk.CTkFrame(main_content, width=150)
        resource_frame.pack(side="right", fill="y", padx=5, pady=5)
        resource_frame.pack_propagate(False)
        
        ctk.CTkLabel(resource_frame, text="可用资源", font=("", 11, "bold")).pack(pady=5)
        
        self._detail_resource_scroll = ctk.CTkScrollableFrame(resource_frame, width=140)
        self._detail_resource_scroll.pack(fill="both", expand=True, padx=2, pady=2)
        
        self._detail_resource_container = ctk.CTkFrame(self._detail_resource_scroll)
        self._detail_resource_container.pack(fill="x")
        
        self._detail_resource_photos = []
    
    def _create_product_input(self, parent):
        """创建商品ID输入区"""
        input_frame = ctk.CTkFrame(parent)
        input_frame.pack(side="top", padx=5, pady=5)
        
        self._product_var = tk.StringVar()
        product_entry = ctk.CTkEntry(input_frame, textvariable=self._product_var, width=150)
        product_entry.pack(side="top", padx=5, pady=2)
        
        ctk.CTkButton(input_frame, text="载入", width=60, command=self._on_load).pack(side="left", padx=2)
        ctk.CTkButton(input_frame, text="保存", width=60, command=self._on_save).pack(side="left", padx=2)
    
    def _create_tool_buttons(self, parent):
        """创建工具按钮"""
        btn_frame = ctk.CTkFrame(parent)
        btn_frame.pack(side="top", padx=5, pady=5)
        
        tools = [
            ("选择", self._on_select_tool),
            ("拖拽", self._on_drag_tool),
            ("涂抹", self._on_paint_tool),
            ("添加", self._on_add_image),
            ("删除", self._on_delete),
            ("横拼", self._on_stitch_horizontal),
            ("解绑", self._on_unbind),
            ("比例", self._on_aspect_ratio),
        ]
        
        for text, command in tools:
            btn = ctk.CTkButton(btn_frame, text=text, width=60, height=28, command=command)
            btn.pack(pady=2)
        
        column_tools_frame = ctk.CTkFrame(parent)
        column_tools_frame.pack(side="top", padx=5, pady=5)
        
        ctk.CTkLabel(column_tools_frame, text="列模式工具", font=("", 10)).pack(pady=2)
        
        column_tools = [
            ("删行", self._on_delete_row),
            ("污点", self._on_spot_heal),
            ("取色", self._on_pick_color),
            ("应用", self._on_apply_column),
        ]
        
        for text, command in column_tools:
            btn = ctk.CTkButton(column_tools_frame, text=text, width=60, height=24, command=command)
            btn.pack(pady=1)
    
    def _create_mode_switch(self, parent):
        """创建模式切换"""
        mode_frame = ctk.CTkFrame(parent)
        mode_frame.pack(side="top", padx=5, pady=5)
        
        ctk.CTkLabel(mode_frame, text="编辑模式").pack(pady=2)
        
        self._mode_var = tk.StringVar(value="block")
        ctk.CTkRadioButton(mode_frame, text="块模式", variable=self._mode_var, 
                          value="block", command=lambda: self._canvas.switch_mode("block")).pack(anchor="w")
        ctk.CTkRadioButton(mode_frame, text="列模式", variable=self._mode_var,
                          value="column", command=lambda: self._canvas.switch_mode("column")).pack(anchor="w")
    
    def _create_history_buttons(self, parent):
        """创建历史记录按钮"""
        history_frame = ctk.CTkFrame(parent)
        history_frame.pack(side="top", padx=5, pady=5)
        
        self._undo_btn = ctk.CTkButton(history_frame, text="撤销 (Ctrl+Z)", width=80, command=self._on_undo)
        self._undo_btn.pack(pady=2)
        
        self._redo_btn = ctk.CTkButton(history_frame, text="重做 (Ctrl+Y)", width=80, command=self._on_redo)
        self._redo_btn.pack(pady=2)
    
    def _setup_main_image_tab(self):
        """设置主图选项卡 - 上方1:1五张，下方3:4五张，支持拖放调整顺序"""
        main_frame = self._tabview.tab("主图")
        
        self._main_images_1_1: List[Optional[str]] = [None] * self.MAIN_IMAGE_COUNT
        self._main_images_3_4: List[Optional[str]] = [None] * self.MAIN_IMAGE_COUNT
        self._main_photos_1_1 = [None] * self.MAIN_IMAGE_COUNT
        self._main_photos_3_4 = [None] * self.MAIN_IMAGE_COUNT
        
        self._main_drag_data = {'source_idx': None, 'drag_label': None}
        
        header = ctk.CTkFrame(main_frame)
        header.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(header, text="主图管理 (可拖放调整顺序)", font=("", 14, "bold")).pack(side="left", padx=5)
        ctk.CTkButton(header, text="自动填充", width=80, command=self._auto_fill_main_images).pack(side="left", padx=5)
        ctk.CTkButton(header, text="保存全部", width=80, command=self._save_all_main_images).pack(side="left", padx=5)
        
        row_1_1_frame = ctk.CTkFrame(main_frame)
        row_1_1_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(row_1_1_frame, text="1:1 主图", font=("", 12, "bold")).pack(anchor="w", padx=5)
        
        images_1_1_frame = ctk.CTkFrame(row_1_1_frame)
        images_1_1_frame.pack(fill="x", padx=5, pady=5)
        
        self._main_1_1_labels = []
        self._main_1_1_ratio_labels = []
        self._main_1_1_frames = []
        
        for i in range(self.MAIN_IMAGE_COUNT):
            frame = ctk.CTkFrame(images_1_1_frame)
            frame.pack(side="left", padx=5, pady=2)
            self._main_1_1_frames.append(frame)
            
            ctk.CTkLabel(frame, text=f"主图{i+1}", font=("", 10)).pack()
            
            label = ctk.CTkLabel(frame, text="未设置", width=100, height=100)
            label.pack(pady=2)
            self._main_1_1_labels.append(label)
            
            ratio_label = ctk.CTkLabel(frame, text="-", font=("", 9))
            ratio_label.pack()
            self._main_1_1_ratio_labels.append(ratio_label)
            
            btn_frame = ctk.CTkFrame(frame)
            btn_frame.pack(fill="x")
            
            ctk.CTkButton(btn_frame, text="选择", width=40, height=24,
                         command=lambda idx=i: self._select_main_image_1_1(idx)).pack(side="left", padx=1)
            ctk.CTkButton(btn_frame, text="生成", width=40, height=24,
                         command=lambda idx=i: self._generate_1_1_from_3_4(idx)).pack(side="left", padx=1)
            ctk.CTkButton(btn_frame, text="清除", width=40, height=24,
                         command=lambda idx=i: self._clear_main_image_1_1(idx)).pack(side="left", padx=1)
            
            label.bind('<Button-1>', lambda e, idx=i: self._on_main_drag_start(e, idx))
            label.bind('<B1-Motion>', self._on_main_drag_motion)
            label.bind('<ButtonRelease-1>', self._on_main_drag_release)
        
        row_3_4_frame = ctk.CTkFrame(main_frame)
        row_3_4_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(row_3_4_frame, text="3:4 主图", font=("", 12, "bold")).pack(anchor="w", padx=5)
        
        images_3_4_frame = ctk.CTkFrame(row_3_4_frame)
        images_3_4_frame.pack(fill="x", padx=5, pady=5)
        
        self._main_3_4_labels = []
        self._main_3_4_ratio_labels = []
        self._main_3_4_frames = []
        
        for i in range(self.MAIN_IMAGE_COUNT):
            frame = ctk.CTkFrame(images_3_4_frame)
            frame.pack(side="left", padx=5, pady=2)
            self._main_3_4_frames.append(frame)
            
            title = f"主图{i+1}" if i < 4 else f"主图{i+1}(白底)"
            ctk.CTkLabel(frame, text=title, font=("", 10)).pack()
            
            label = ctk.CTkLabel(frame, text="未设置", width=100, height=100)
            label.pack(pady=2)
            self._main_3_4_labels.append(label)
            
            ratio_label = ctk.CTkLabel(frame, text="-", font=("", 9))
            ratio_label.pack()
            self._main_3_4_ratio_labels.append(ratio_label)
            
            btn_frame = ctk.CTkFrame(frame)
            btn_frame.pack(fill="x")
            
            ctk.CTkButton(btn_frame, text="选择", width=40, height=24,
                         command=lambda idx=i: self._select_main_image_3_4(idx)).pack(side="left", padx=1)
            ctk.CTkButton(btn_frame, text="生成", width=40, height=24,
                         command=lambda idx=i: self._generate_3_4_from_1_1(idx)).pack(side="left", padx=1)
            ctk.CTkButton(btn_frame, text="清除", width=40, height=24,
                         command=lambda idx=i: self._clear_main_image_3_4(idx)).pack(side="left", padx=1)
            
            label.bind('<Button-1>', lambda e, idx=i: self._on_main_drag_start(e, idx))
            label.bind('<B1-Motion>', self._on_main_drag_motion)
            label.bind('<ButtonRelease-1>', self._on_main_drag_release)
        
        resource_frame = ctk.CTkFrame(main_frame)
        resource_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        resource_header = ctk.CTkFrame(resource_frame)
        resource_header.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(resource_header, text="可用资源 (点击设为主图)", font=("", 11)).pack(side="left", padx=5)
        ctk.CTkButton(resource_header, text="从文件添加", width=70, height=24, command=self._add_main_from_file).pack(side="left", padx=2)
        ctk.CTkButton(resource_header, text="刷新", width=50, height=24, command=self._refresh_main_resources).pack(side="left", padx=2)
        
        self._main_resource_scroll = ctk.CTkScrollableFrame(resource_frame, height=120, orientation="horizontal")
        self._main_resource_scroll.pack(fill="x", padx=5, pady=5)
        
        self._main_resource_container = ctk.CTkFrame(self._main_resource_scroll)
        self._main_resource_container.pack(side="left")
        
        self._main_resource_photos = []
    
    def _setup_color_tab(self):
        """设置色卡选项卡"""
        color_frame = self._tabview.tab("色卡")
        
        self._color_images: List[str] = []
        self._color_photos = []
        
        header = ctk.CTkFrame(color_frame)
        header.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header, text="色卡图管理", font=("", 14, "bold")).pack(side="left", padx=5)
        ctk.CTkButton(header, text="添加", width=60, command=self._add_color_image).pack(side="left", padx=2)
        ctk.CTkButton(header, text="全部转1:1", width=80, command=self._convert_all_color_1_1).pack(side="left", padx=2)
        ctk.CTkButton(header, text="保存全部", width=80, command=self._save_all_color).pack(side="left", padx=2)
        
        self._color_scroll_frame = ctk.CTkScrollableFrame(color_frame, height=300)
        self._color_scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self._color_container = ctk.CTkFrame(self._color_scroll_frame)
        self._color_container.pack(fill="x")
        
        resource_frame = ctk.CTkFrame(color_frame)
        resource_frame.pack(fill="x", padx=10, pady=5)
        
        resource_header = ctk.CTkFrame(resource_frame)
        resource_header.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(resource_header, text="可用资源 (点击添加为色卡)", font=("", 12)).pack(side="left", padx=5)
        ctk.CTkButton(resource_header, text="从文件添加", width=80, command=self._add_color_from_file).pack(side="left", padx=2)
        
        self._color_resource_scroll = ctk.CTkScrollableFrame(resource_frame, height=120, orientation="horizontal")
        self._color_resource_scroll.pack(fill="x", padx=5, pady=5)
        
        self._color_resource_container = ctk.CTkFrame(self._color_resource_scroll)
        self._color_resource_container.pack(side="left")
        
        self._color_resource_photos = []
    
    def _setup_video_tab(self):
        """设置视频选项卡"""
        video_frame = self._tabview.tab("视频")
        
        self._video_duration = tk.IntVar(value=15)
        
        control_frame = ctk.CTkFrame(video_frame)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(control_frame, text="视频时长:").pack(side="left", padx=5)
        
        duration_menu = ctk.CTkOptionMenu(
            control_frame, 
            variable=self._video_duration,
            values=["10", "15", "20", "25", "30", "35", "40", "45"],
            width=80
        )
        duration_menu.pack(side="left", padx=5)
        
        ctk.CTkLabel(control_frame, text="秒").pack(side="left", padx=5)
        
        ctk.CTkButton(control_frame, text="生成视频", width=100, command=self._generate_video).pack(side="left", padx=20)
        ctk.CTkButton(control_frame, text="打开输出目录", width=100, command=self._open_output_dir).pack(side="left", padx=5)
        
        existing_videos_frame = ctk.CTkFrame(video_frame)
        existing_videos_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(existing_videos_frame, text="已有视频 (点击预览)", font=("", 12, "bold")).pack(anchor="w", padx=5, pady=5)
        
        self._existing_videos_scroll = ctk.CTkScrollableFrame(existing_videos_frame, height=100, orientation="horizontal")
        self._existing_videos_scroll.pack(fill="x", padx=5, pady=5)
        
        self._existing_videos_container = ctk.CTkFrame(self._existing_videos_scroll)
        self._existing_videos_container.pack(side="left")
        
        self._existing_video_thumbs = []
        
        preview_frame = ctk.CTkFrame(video_frame)
        preview_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        ctk.CTkLabel(preview_frame, text="视频预览", font=("", 14, "bold")).pack(pady=10)
        
        self._video_preview_label = ctk.CTkLabel(preview_frame, text="点击\"生成视频\"开始", height=300)
        self._video_preview_label.pack(fill="both", expand=True, padx=10, pady=10)
        
        image_list_frame = ctk.CTkFrame(video_frame)
        image_list_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(image_list_frame, text="参与视频的图片 (从详情图页加载)", font=("", 12)).pack(anchor="w", padx=5, pady=5)
        
        self._video_image_scroll = ctk.CTkScrollableFrame(image_list_frame, height=120, orientation="horizontal")
        self._video_image_scroll.pack(fill="x", padx=5, pady=5)
        
        self._video_image_container = ctk.CTkFrame(self._video_image_scroll)
        self._video_image_container.pack(side="left")
    
    def _create_status_bar(self):
        """创建状态栏"""
        status_frame = ctk.CTkFrame(self)
        status_frame.pack(side="bottom", fill="x", padx=5, pady=5)
        
        self._status_label = ctk.CTkLabel(status_frame, text="就绪")
        self._status_label.pack(side="left")
        
        self._total_height_label = ctk.CTkLabel(status_frame, text="总高度: 0px")
        self._total_height_label.pack(side="left", padx=20)
        
        self._history_label = ctk.CTkLabel(status_frame, text="历史记录: 0/0")
        self._history_label.pack(side="left")
    
    def _setup_bindings(self):
        """设置绑定"""
        self._canvas.set_on_update_callback(self._on_canvas_update)
        
        self.bind('<Control-z>', lambda e: self._on_undo())
        self.bind('<Control-y>', lambda e: self._on_redo())
        self.bind('<Control-s>', lambda e: self._on_save())
        self.bind('<Control-a>', lambda e: self._on_select_all())
        self.bind('<Control-h>', lambda e: self._on_stitch_horizontal())
        self.bind('<Delete>', lambda e: self._on_delete())
        self.bind('<Escape>', lambda e: self._on_clear_selection())
    
    def _on_select_tool(self):
        self._canvas.set_tool("select")
        self._update_status("选择模式")
    
    def _on_drag_tool(self):
        self._canvas.set_tool("drag")
        self._update_status("拖拽模式")
    
    def _on_paint_tool(self):
        self._canvas.set_tool("paint")
        self._update_status("涂抹模式 (列模式下右键涂抹)")
    
    def _on_add_image(self):
        file_paths = filedialog.askopenfilenames(
            title="添加图片",
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.webp")]
        )
        if file_paths:
            for path in file_paths:
                self._canvas.add_block(path)
    
    def _on_delete(self):
        self._canvas.remove_selected_blocks()
    
    def _on_stitch_horizontal(self):
        if not self._canvas.selected_blocks or len(self._canvas.selected_blocks) < 2:
            self._update_status("请选择至少2张图片进行拼接")
            return
        
        composite = self._canvas.stitch_smart_layout()
        if composite:
            for block in self._canvas.selected_blocks:
                if block in self._canvas.blocks:
                    self._canvas.blocks.remove(block)
            
            insert_idx = min(b.index for b in self._canvas.selected_blocks)
            composite.index = insert_idx
            self._canvas.blocks.insert(insert_idx, composite)
            
            self._canvas._reindex_blocks()
            self._canvas.selected_blocks = [composite]
            self._canvas.history.save_state([b.to_dict() for b in self._canvas.blocks])
            self._canvas._refresh_canvas()
            
            layout_type = self._canvas.detect_layout_type(composite.sub_blocks)
            self._update_status(f"拼接完成: {layout_type}")
    
    def _on_unbind(self):
        selected = self._canvas.get_selected_block()
        if selected and selected.is_composite():
            self._canvas.unbind_composite(selected)
    
    def _on_aspect_ratio(self):
        if not self._canvas.selected_blocks:
            self._update_status("请先选择图片")
            return
        
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="转换为 1:1 (正方形)", command=lambda: self._do_convert_ratio("1:1"))
        menu.add_command(label="转换为 3:4 (竖图)", command=lambda: self._do_convert_ratio("3:4"))
        menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
    
    def _do_convert_ratio(self, ratio: str):
        self._canvas.convert_aspect_ratio(ratio)
        self._update_status(f"已转换为 {ratio}")
    
    def load_product_images(self, product_id: str):
        from utils.database import get_shared_db
        from utils.image_processor import collect_image_files
        
        db = get_shared_db()
        product = db.get_product(product_id)
        
        if not product:
            self._log(f"未找到商品: {product_id}")
            return
        
        self.output_path = product.get('output_path', '')
        if not self.output_path or not os.path.exists(self.output_path):
            self._log(f"输出路径不存在: {self.output_path}")
            return
        
        self._product_var.set(product_id)
        
        detail_images = collect_image_files(self.output_path, FILE_NAMING['detail_image_prefix'])
        
        if detail_images:
            self._log(f"加载 {len(detail_images)} 张详情图")
            self._canvas.load_blocks(detail_images)
        
        self._load_main_images()
        self._load_color_images()
        self._load_existing_videos()
        self._refresh_detail_resources()
        self._update_video_image_list()
    
    def _load_main_images(self):
        """加载主图 - 自动检测比例填充到1:1或3:4位置"""
        from utils.image_processor import collect_image_files
        
        if not self.output_path or not os.path.exists(self.output_path):
            return
        
        self._main_images_1_1 = [None] * self.MAIN_IMAGE_COUNT
        self._main_images_3_4 = [None] * self.MAIN_IMAGE_COUNT
        
        main_images = collect_image_files(self.output_path, FILE_NAMING['main_image_prefix'])
        
        slot_1_1 = 0
        slot_3_4 = 0
        
        for path in main_images:
            if not os.path.exists(path):
                continue
            
            try:
                img = Image.open(path)
                ratio = detect_image_ratio(img)
                
                if ratio == "1:1" and slot_1_1 < self.MAIN_IMAGE_COUNT:
                    self._main_images_1_1[slot_1_1] = path
                    slot_1_1 += 1
                elif ratio == "3:4" and slot_3_4 < self.MAIN_IMAGE_COUNT:
                    self._main_images_3_4[slot_3_4] = path
                    slot_3_4 += 1
                elif slot_1_1 < self.MAIN_IMAGE_COUNT:
                    self._main_images_1_1[slot_1_1] = path
                    slot_1_1 += 1
                elif slot_3_4 < self.MAIN_IMAGE_COUNT:
                    self._main_images_3_4[slot_3_4] = path
                    slot_3_4 += 1
            except:
                pass
        
        self._update_all_main_image_previews()
        self._refresh_main_resources()
    
    def _auto_fill_main_images(self):
        """自动填充主图 - 根据资源图片比例自动填充"""
        from utils.image_processor import collect_image_files
        
        if not self.output_path or not os.path.exists(self.output_path):
            self._update_status("未设置输出路径")
            return
        
        resources = collect_image_files(self.output_path, FILE_NAMING['detail_image_prefix'])
        
        slot_1_1 = 0
        slot_3_4 = 0
        
        for i in range(self.MAIN_IMAGE_COUNT):
            if self._main_images_1_1[i] is None:
                slot_1_1 = i
                break
        
        for i in range(self.MAIN_IMAGE_COUNT):
            if self._main_images_3_4[i] is None:
                slot_3_4 = i
                break
        
        for path in resources:
            if not os.path.exists(path):
                continue
            
            try:
                img = Image.open(path)
                ratio = detect_image_ratio(img)
                
                if ratio == "1:1":
                    if slot_1_1 < self.MAIN_IMAGE_COUNT and self._main_images_1_1[slot_1_1] is None:
                        self._main_images_1_1[slot_1_1] = path
                        slot_1_1 = self._find_next_empty_slot(self._main_images_1_1, slot_1_1)
                elif ratio == "3:4":
                    if slot_3_4 < self.MAIN_IMAGE_COUNT and self._main_images_3_4[slot_3_4] is None:
                        self._main_images_3_4[slot_3_4] = path
                        slot_3_4 = self._find_next_empty_slot(self._main_images_3_4, slot_3_4)
            except:
                pass
        
        self._update_all_main_image_previews()
        self._update_status("自动填充完成")
    
    def _find_next_empty_slot(self, images_list: List, current_slot: int) -> int:
        """找到下一个空槽位"""
        for i in range(current_slot + 1, len(images_list)):
            if images_list[i] is None:
                return i
        return len(images_list)
    
    def _update_all_main_image_previews(self):
        """更新所有主图预览"""
        for i in range(self.MAIN_IMAGE_COUNT):
            self._update_main_image_preview_1_1(i)
            self._update_main_image_preview_3_4(i)
    
    def _update_main_image_preview_1_1(self, index: int):
        """更新1:1主图预览"""
        if index < 0 or index >= self.MAIN_IMAGE_COUNT:
            return
        
        path = self._main_images_1_1[index]
        
        if not path or not os.path.exists(path):
            self._main_1_1_labels[index].configure(text="未设置", image=None)
            self._main_1_1_ratio_labels[index].configure(text="-")
            self._main_photos_1_1[index] = None
            return
        
        try:
            img = Image.open(path)
            img_thumb = img.copy()
            img_thumb.thumbnail((100, 100), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img_thumb)
            self._main_photos_1_1[index] = photo
            self._main_1_1_labels[index].configure(text="", image=photo)
            
            ratio = detect_image_ratio(img)
            self._main_1_1_ratio_labels[index].configure(text=ratio)
        except:
            self._main_1_1_labels[index].configure(text="加载失败", image=None)
            self._main_photos_1_1[index] = None
    
    def _update_main_image_preview_3_4(self, index: int):
        """更新3:4主图预览"""
        if index < 0 or index >= self.MAIN_IMAGE_COUNT:
            return
        
        path = self._main_images_3_4[index]
        
        if not path or not os.path.exists(path):
            self._main_3_4_labels[index].configure(text="未设置", image=None)
            self._main_3_4_ratio_labels[index].configure(text="-")
            self._main_photos_3_4[index] = None
            return
        
        try:
            img = Image.open(path)
            img_thumb = img.copy()
            img_thumb.thumbnail((100, 100), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img_thumb)
            self._main_photos_3_4[index] = photo
            self._main_3_4_labels[index].configure(text="", image=photo)
            
            ratio = detect_image_ratio(img)
            self._main_3_4_ratio_labels[index].configure(text=ratio)
        except:
            self._main_3_4_labels[index].configure(text="加载失败", image=None)
            self._main_photos_3_4[index] = None
    
    def _select_main_image_1_1(self, index: int):
        """选择1:1主图"""
        file_path = filedialog.askopenfilename(
            title=f"选择1:1主图{index+1}",
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.webp")]
        )
        if file_path:
            self._main_images_1_1[index] = file_path
            self._update_main_image_preview_1_1(index)
    
    def _select_main_image_3_4(self, index: int):
        """选择3:4主图"""
        file_path = filedialog.askopenfilename(
            title=f"选择3:4主图{index+1}",
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.webp")]
        )
        if file_path:
            self._main_images_3_4[index] = file_path
            self._update_main_image_preview_3_4(index)
    
    def _clear_main_image_1_1(self, index: int):
        """清除1:1主图"""
        self._main_images_1_1[index] = None
        self._update_main_image_preview_1_1(index)
    
    def _clear_main_image_3_4(self, index: int):
        """清除3:4主图"""
        self._main_images_3_4[index] = None
        self._update_main_image_preview_3_4(index)
    
    def _generate_1_1_from_3_4(self, index: int):
        """从3:4主图生成1:1主图"""
        path_3_4 = self._main_images_3_4[index]
        if path_3_4 and os.path.exists(path_3_4):
            try:
                img = Image.open(path_3_4)
                converted = convert_aspect_ratio(img, "1:1")
                
                if self.output_path and os.path.exists(self.output_path):
                    new_path = os.path.join(self.output_path, f"{FILE_NAMING['new_image_prefix']}T_1x1_{index+1}.jpg")
                else:
                    base, ext = os.path.splitext(path_3_4)
                    new_path = f"{base}_1x1{ext}"
                
                converted.save(new_path, quality=IMAGE_PROCESSING['jpeg_quality'])
                
                self._main_images_1_1[index] = new_path
                self._update_main_image_preview_1_1(index)
                self._update_status(f"已从3:4主图{index+1}生成1:1主图")
            except Exception as e:
                self._update_status(f"生成失败: {e}")
        else:
            self._update_status(f"请先设置3:4主图{index+1}")
    
    def _generate_3_4_from_1_1(self, index: int):
        """从1:1主图生成3:4主图"""
        path_1_1 = self._main_images_1_1[index]
        if path_1_1 and os.path.exists(path_1_1):
            try:
                img = Image.open(path_1_1)
                converted = convert_aspect_ratio(img, "3:4")
                
                if self.output_path and os.path.exists(self.output_path):
                    new_path = os.path.join(self.output_path, f"{FILE_NAMING['new_image_prefix']}T_3x4_{index+1}.jpg")
                else:
                    base, ext = os.path.splitext(path_1_1)
                    new_path = f"{base}_3x4{ext}"
                
                converted.save(new_path, quality=IMAGE_PROCESSING['jpeg_quality'])
                
                self._main_images_3_4[index] = new_path
                self._update_main_image_preview_3_4(index)
                self._update_status(f"已从1:1主图{index+1}生成3:4主图")
            except Exception as e:
                self._update_status(f"生成失败: {e}")
        else:
            self._update_status(f"请先设置1:1主图{index+1}")
    
    def _load_color_images(self):
        """加载色卡图"""
        from utils.image_processor import collect_image_files
        
        if not self.output_path or not os.path.exists(self.output_path):
            return
        
        self._color_images = collect_image_files(self.output_path, FILE_NAMING['color_option_prefix'])
        self._update_color_images_preview()
        self._refresh_color_resources()
    
    def _load_existing_videos(self):
        """加载已有视频"""
        for widget in self._existing_videos_container.winfo_children():
            widget.destroy()
        
        self._existing_video_thumbs = []
        
        if not self.output_path or not os.path.exists(self.output_path):
            return
        
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        videos = []
        
        for f in os.listdir(self.output_path):
            if any(f.lower().endswith(ext) for ext in video_extensions):
                videos.append(os.path.join(self.output_path, f))
        
        for video_path in videos:
            try:
                frame = ctk.CTkFrame(self._existing_videos_container)
                frame.pack(side="left", padx=5, pady=5)
                
                name = os.path.basename(video_path)
                
                label = ctk.CTkLabel(frame, text="🎬\n" + name[:15], width=80, height=60)
                label.pack()
                label.bind('<Button-1>', lambda e, p=video_path: self._preview_video(p))
                
                ctk.CTkButton(frame, text="打开", width=60, height=24,
                             command=lambda p=video_path: self._open_video_file(p)).pack(pady=2)
                
                self._existing_video_thumbs.append(frame)
            except:
                pass
    
    def _preview_video(self, video_path: str):
        """预览视频"""
        self._video_preview_label.configure(text=f"已选择视频:\n{os.path.basename(video_path)}")
        self._open_video_file(video_path)
    
    def _open_video_file(self, video_path: str):
        """打开视频文件"""
        if os.path.exists(video_path):
            import subprocess
            subprocess.run(['start', '', video_path], shell=True)
    
    def _refresh_main_resources(self):
        """刷新主图资源列表 - 加载所有采集的资源（主图、色卡图、详情图），不含新生成的图"""
        from utils.image_processor import collect_image_files
        
        for widget in self._main_resource_container.winfo_children():
            widget.destroy()
        
        self._main_resource_photos = []
        
        if not self.output_path or not os.path.exists(self.output_path):
            return
        
        all_resources = []
        
        main_images = collect_image_files(self.output_path, FILE_NAMING['main_image_prefix'])
        for path in main_images:
            filename = os.path.basename(path)
            if not filename.startswith(FILE_NAMING['new_image_prefix']):
                all_resources.append(('主图', path))
        
        color_images = collect_image_files(self.output_path, FILE_NAMING['color_option_prefix'])
        for path in color_images:
            filename = os.path.basename(path)
            if not filename.startswith(FILE_NAMING['new_image_prefix']):
                all_resources.append(('色卡', path))
        
        detail_images = collect_image_files(self.output_path, FILE_NAMING['detail_image_prefix'])
        for path in detail_images:
            filename = os.path.basename(path)
            if not filename.startswith(FILE_NAMING['new_image_prefix']):
                all_resources.append(('详情', path))
        
        for resource_type, path in all_resources[:50]:
            if not os.path.exists(path):
                continue
            
            try:
                img = Image.open(path)
                img_thumb = img.copy()
                img_thumb.thumbnail((80, 80), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img_thumb)
                self._main_resource_photos.append(photo)
                
                frame = ctk.CTkFrame(self._main_resource_container)
                frame.pack(side="left", padx=3, pady=3)
                
                label = ctk.CTkLabel(frame, text="", image=photo)
                label.pack()
                
                ratio = detect_image_ratio(img)
                
                menu = tk.Menu(frame, tearoff=0)
                for i in range(self.MAIN_IMAGE_COUNT):
                    menu.add_command(label=f"设为1:1主图{i+1}", 
                                   command=lambda p=path, idx=i: self._set_main_image_1_1(idx, p))
                for i in range(self.MAIN_IMAGE_COUNT):
                    menu.add_command(label=f"设为3:4主图{i+1}", 
                                   command=lambda p=path, idx=i: self._set_main_image_3_4(idx, p))
                label.bind('<Button-1>', lambda e, m=menu: m.tk_popup(e.widget.winfo_pointerx(), e.widget.winfo_pointery()))
                
                name = os.path.basename(path)
                ctk.CTkLabel(frame, text=f"[{resource_type}]\n{name[:8]}\n{ratio}", font=("", 7)).pack()
            except:
                pass
    
    def _set_main_image_1_1(self, index: int, path: str):
        """设置1:1主图"""
        if 0 <= index < self.MAIN_IMAGE_COUNT:
            self._main_images_1_1[index] = path
            self._update_main_image_preview_1_1(index)
    
    def _set_main_image_3_4(self, index: int, path: str):
        """设置3:4主图"""
        if 0 <= index < self.MAIN_IMAGE_COUNT:
            self._main_images_3_4[index] = path
            self._update_main_image_preview_3_4(index)
    
    def _refresh_color_resources(self):
        """刷新色卡资源列表 - 使用与主图/详情图一致的可用资源"""
        from utils.image_processor import collect_image_files
        
        for widget in self._color_resource_container.winfo_children():
            widget.destroy()
        
        self._color_resource_photos = []
        
        if not self.output_path or not os.path.exists(self.output_path):
            return
        
        all_resources = []
        
        main_images = collect_image_files(self.output_path, FILE_NAMING['main_image_prefix'])
        for path in main_images:
            filename = os.path.basename(path)
            if not filename.startswith(FILE_NAMING['new_image_prefix']):
                all_resources.append(('主图', path))
        
        color_images = collect_image_files(self.output_path, FILE_NAMING['color_option_prefix'])
        for path in color_images:
            filename = os.path.basename(path)
            if not filename.startswith(FILE_NAMING['new_image_prefix']):
                all_resources.append(('色卡', path))
        
        detail_images = collect_image_files(self.output_path, FILE_NAMING['detail_image_prefix'])
        for path in detail_images:
            filename = os.path.basename(path)
            if not filename.startswith(FILE_NAMING['new_image_prefix']):
                all_resources.append(('详情', path))
        
        for resource_type, path in all_resources[:30]:
            if not os.path.exists(path):
                continue
            
            try:
                img = Image.open(path)
                img_thumb = img.copy()
                img_thumb.thumbnail((80, 80), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img_thumb)
                self._color_resource_photos.append(photo)
                
                frame = ctk.CTkFrame(self._color_resource_container)
                frame.pack(side="left", padx=3, pady=3)
                
                label = ctk.CTkLabel(frame, text="", image=photo)
                label.pack()
                label.bind('<Button-1>', lambda e, p=path: self._add_to_color_images(p))
                
                name = os.path.basename(path)
                ctk.CTkLabel(frame, text=f"[{resource_type}]\n{name[:10]}", font=("", 7)).pack()
            except:
                pass
    
    def _select_main_image(self, index: int):
        """选择主图"""
        file_path = filedialog.askopenfilename(
            title=f"选择主图{index+1}",
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.webp")]
        )
        if file_path:
            self._set_main_image(index, file_path)
    
    def _set_main_image(self, index: int, path: str):
        """设置主图"""
        if 0 <= index < self.MAIN_IMAGE_COUNT:
            self._main_images[index] = path
            self._update_main_image_preview(index)
    
    def _convert_main_image_ratio(self, index: int, target_ratio: str):
        """转换单个主图比例"""
        if index < 0 or index >= self.MAIN_IMAGE_COUNT:
            return
        
        path = self._main_images[index]
        if not path or not os.path.exists(path):
            return
        
        try:
            img = Image.open(path)
            converted = convert_aspect_ratio(img, target_ratio)
            
            base, ext = os.path.splitext(path)
            new_path = f"{base}_{target_ratio.replace(':', 'x')}{ext}"
            converted.save(new_path, quality=IMAGE_PROCESSING['jpeg_quality'])
            
            self._main_images[index] = new_path
            self._update_main_image_preview(index)
            self._update_status(f"主图{index+1}已转换为 {target_ratio}")
        except Exception as e:
            self._update_status(f"转换失败: {e}")
    
    def _convert_all_main_1_1(self):
        """转换所有主图为1:1"""
        for i in range(self.MAIN_IMAGE_COUNT):
            path = self._main_images[i]
            if not path or not os.path.exists(path):
                continue
            try:
                img = Image.open(path)
                converted = convert_aspect_ratio(img, "1:1")
                
                base, ext = os.path.splitext(path)
                new_path = f"{base}_1x1{ext}"
                converted.save(new_path, quality=IMAGE_PROCESSING['jpeg_quality'])
                self._main_images[i] = new_path
            except:
                pass
        
        self._update_all_main_image_previews()
        self._update_status("所有主图已转换为1:1")
    
    def _save_all_main_images(self):
        """保存所有主图"""
        if not self.output_path:
            self._update_status("未设置输出路径")
            return
        
        saved_1_1 = 0
        saved_3_4 = 0
        
        for i in range(self.MAIN_IMAGE_COUNT):
            path_1_1 = self._main_images_1_1[i]
            if path_1_1 and os.path.exists(path_1_1):
                try:
                    img = Image.open(path_1_1)
                    save_path = os.path.join(self.output_path, f"{FILE_NAMING['main_image_prefix']}1_1_{i+1}.jpg")
                    img.save(save_path, quality=IMAGE_PROCESSING['jpeg_quality'])
                    saved_1_1 += 1
                except:
                    pass
            
            path_3_4 = self._main_images_3_4[i]
            if path_3_4 and os.path.exists(path_3_4):
                try:
                    img = Image.open(path_3_4)
                    save_path = os.path.join(self.output_path, f"{FILE_NAMING['main_image_prefix']}3_4_{i+1}.jpg")
                    img.save(save_path, quality=IMAGE_PROCESSING['jpeg_quality'])
                    saved_3_4 += 1
                except:
                    pass
        
        self._update_status(f"已保存 1:1: {saved_1_1}张, 3:4: {saved_3_4}张主图")
    
    def _add_main_from_file(self):
        """从文件添加主图资源"""
        file_paths = filedialog.askopenfilenames(
            title="添加资源",
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.webp")]
        )
        self._refresh_main_resources()
    
    def _update_color_images_preview(self):
        """更新色卡图预览"""
        for widget in self._color_container.winfo_children():
            widget.destroy()
        
        self._color_photos = []
        
        for idx, path in enumerate(self._color_images):
            if not os.path.exists(path):
                continue
            
            frame = ctk.CTkFrame(self._color_container)
            frame.pack(side="left", padx=5, pady=5)
            
            try:
                img = Image.open(path)
                img_thumb = img.copy()
                img_thumb.thumbnail((100, 100), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img_thumb)
                self._color_photos.append(photo)
                
                label = ctk.CTkLabel(frame, text="", image=photo)
                label.pack()
                
                ratio = detect_image_ratio(img)
                ctk.CTkLabel(frame, text=ratio, font=("", 10)).pack()
                
                btn_frame = ctk.CTkFrame(frame)
                btn_frame.pack(fill="x")
                
                ctk.CTkButton(btn_frame, text="删除", width=50,
                             command=lambda i=idx: self._remove_color_image(i)).pack(side="left", padx=1)
            except:
                pass
    
    def _add_color_image(self):
        """添加色卡图"""
        file_paths = filedialog.askopenfilenames(
            title="添加色卡图",
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.webp")]
        )
        for path in file_paths:
            if path not in self._color_images:
                self._color_images.append(path)
        self._update_color_images_preview()
    
    def _add_to_color_images(self, path: str):
        """添加到色卡图"""
        if path not in self._color_images:
            self._color_images.append(path)
            self._update_color_images_preview()
    
    def _remove_color_image(self, index: int):
        """删除色卡图"""
        if 0 <= index < len(self._color_images):
            self._color_images.pop(index)
            self._update_color_images_preview()
    
    def _convert_all_color_1_1(self):
        """转换所有色卡图为1:1"""
        for idx, path in enumerate(self._color_images):
            if not os.path.exists(path):
                continue
            try:
                img = Image.open(path)
                converted = convert_aspect_ratio(img, "1:1")
                
                base, ext = os.path.splitext(path)
                new_path = f"{base}_1x1{ext}"
                converted.save(new_path, quality=IMAGE_PROCESSING['jpeg_quality'])
                self._color_images[idx] = new_path
            except:
                pass
        
        self._update_color_images_preview()
        self._update_status("所有色卡图已转换为1:1")
    
    def _save_all_color(self):
        """保存所有色卡图"""
        if not self.output_path:
            return
        
        saved_count = 0
        for idx, path in enumerate(self._color_images):
            if not os.path.exists(path):
                continue
            try:
                img = Image.open(path)
                save_path = os.path.join(self.output_path, f"{FILE_NAMING['color_option_prefix']}{idx+1}.jpg")
                img.save(save_path, quality=IMAGE_PROCESSING['jpeg_quality'])
                saved_count += 1
            except:
                pass
        
        self._update_status(f"已保存 {saved_count} 张色卡图")
    
    def _add_color_from_file(self):
        """从文件添加色卡资源"""
        self._refresh_color_resources()
    
    def _update_video_image_list(self):
        """更新视频图片列表"""
        for widget in self._video_image_container.winfo_children():
            widget.destroy()
        
        self._video_photos = []
        
        for idx, block in enumerate(self._canvas.blocks):
            if not block.image_path or not os.path.exists(block.image_path):
                continue
            
            try:
                img = Image.open(block.image_path)
                img_thumb = img.copy()
                img_thumb.thumbnail((80, 80), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img_thumb)
                self._video_photos.append(photo)
                
                frame = ctk.CTkFrame(self._video_image_container)
                frame.pack(side="left", padx=3, pady=3)
                
                label = ctk.CTkLabel(frame, text="", image=photo)
                label.pack()
                
                ctk.CTkLabel(frame, text=f"#{idx+1}", font=("", 9)).pack()
            except:
                pass
    
    def _generate_video(self):
        """生成视频"""
        if not self._canvas.blocks:
            self._update_status("没有图片可生成视频")
            return
        
        if not self.output_path:
            self._update_status("未设置输出路径")
            return
        
        image_paths = [b.image_path for b in self._canvas.blocks if b.image_path]
        if not image_paths:
            self._update_status("没有有效的图片路径")
            return
        
        self._update_status("正在生成视频...")
        
        from utils.video_generator import generate_scroll_video
        
        duration = self._video_duration.get()
        output_path = os.path.join(self.output_path, "scroll_video.mp4")
        result = generate_scroll_video(image_paths, output_path, duration=duration)
        
        if result:
            self._update_status(f"视频已生成: {result}")
            self._video_preview_label.configure(text=f"视频已保存:\n{result}")
        else:
            self._update_status("视频生成失败 (需要ffmpeg或moviepy)")
            self._video_preview_label.configure(text="视频生成失败\n请安装ffmpeg或moviepy")
    
    def _open_output_dir(self):
        """打开输出目录"""
        if self.output_path and os.path.exists(self.output_path):
            import subprocess
            subprocess.run(['explorer', self.output_path])
    
    def _on_load(self):
        product_id = self._product_var.get().strip()
        if product_id:
            self.load_product_images(product_id)
    
    def _on_save(self):
        if not self._canvas.blocks:
            self._update_status("没有图片可保存")
            return
        
        if not self.output_path:
            self._update_status("未设置输出路径")
            return
        
        self._update_status("保存中...")
        
        try:
            if self._canvas.mode == "column":
                result = self._canvas.merged_image
                if result:
                    self._save_result(result)
            else:
                result = self._canvas._stitch_vertical()
                if result:
                    self._save_result(result)
            
            self._update_status("保存成功")
        except Exception as e:
            self._update_status(f"保存失败: {e}")
    
    def _save_result(self, image: Image.Image):
        from utils.image_processor import split_merged_image
        
        output_dir = self.output_path
        os.makedirs(output_dir, exist_ok=True)
        
        total_height = image.height
        target_width = IMAGE_PROCESSING['detail_min_width']
        
        new_detail_prefix = FILE_NAMING['new_image_prefix'] + FILE_NAMING['detail_image_prefix']
        
        if total_height <= target_width * 2:
            output_path = os.path.join(output_dir, f"{new_detail_prefix}1.jpg")
            image.save(output_path, quality=IMAGE_PROCESSING['jpeg_quality'])
        else:
            split_merged_image(image, target_width, total_height, output_dir, new_detail_prefix)
    
    def _on_undo(self):
        if self._canvas.undo():
            self._update_history_status()
    
    def _on_redo(self):
        if self._canvas.redo():
            self._update_history_status()
    
    def _on_select_all(self):
        self._canvas.select_all()
        self._update_status(f"已选择 {len(self._canvas.blocks)} 张图片")
    
    def _on_clear_selection(self):
        self._canvas.clear_selection()
        self._update_status("已清除选择")
    
    def _on_canvas_update(self, block_count: int, total_height: int):
        self._total_height_label.configure(text=f"总高度: {total_height}px")
        self._update_history_status()
        self._update_video_image_list()
    
    def _update_history_status(self):
        self._history_label.configure(text=self._canvas.history.get_status_text())
    
    def _update_status(self, text: str):
        self._status_label.configure(text=text)
    
    def _log(self, message: str, level: str = "info"):
        print(f"[图片编辑器] {message}")
    
    def _on_main_drag_start(self, event, index: int):
        """主图拖放开始"""
        self._main_drag_data['source_idx'] = index
        self._main_drag_data['drag_label'] = event.widget
        self._main_drag_data['is_3_4'] = False
        
        if self._main_images_1_1[index] or self._main_images_3_4[index]:
            self._main_1_1_frames[index].configure(border_width=2, border_color="red")
            self._main_3_4_frames[index].configure(border_width=2, border_color="blue")
    
    def _on_main_drag_motion(self, event):
        """主图拖放移动 - 显示拖拽预览"""
        if self._main_drag_data['source_idx'] is None:
            return
        
        source_idx = self._main_drag_data['source_idx']
        
        if not hasattr(self, '_drag_preview_window'):
            self._create_drag_preview_window(source_idx)
        
        if hasattr(self, '_drag_preview_window') and self._drag_preview_window:
            x = self.winfo_pointerx() + 10
            y = self.winfo_pointery() + 10
            self._drag_preview_window.geometry(f"+{x}+{y}")
        
        self._highlight_target_frame(event)
    
    def _create_drag_preview_window(self, source_idx: int):
        """创建拖拽预览窗口"""
        if hasattr(self, '_drag_preview_window') and self._drag_preview_window:
            return
        
        self._drag_preview_window = tk.Toplevel(self)
        self._drag_preview_window.overrideredirect(True)
        self._drag_preview_window.attributes('-topmost', True)
        self._drag_preview_window.attributes('-alpha', 0.7)
        
        photo_1_1 = self._main_photos_1_1[source_idx]
        photo_3_4 = self._main_photos_3_4[source_idx]
        
        if photo_1_1 or photo_3_4:
            label = ctk.CTkLabel(self._drag_preview_window, 
                                text=f"主图{source_idx+1}",
                                image=photo_1_1 or photo_3_4)
            label.pack()
        else:
            label = ctk.CTkLabel(self._drag_preview_window, text=f"主图{source_idx+1}\n(空)")
            label.pack()
    
    def _highlight_target_frame(self, event):
        """高亮目标位置"""
        all_frames = self._main_1_1_frames + self._main_3_4_frames
        
        for i, frame in enumerate(all_frames):
            x = event.widget.winfo_pointerx()
            y = event.widget.winfo_pointery()
            frame_x = frame.winfo_rootx() + frame.winfo_width() // 2
            frame_y = frame.winfo_rooty() + frame.winfo_height() // 2
            
            distance = ((x - frame_x) ** 2 + (y - frame_y) ** 2) ** 0.5
            
            if distance < 80:
                if i < self.MAIN_IMAGE_COUNT:
                    frame.configure(border_width=3, border_color="#00FF00")
                else:
                    frame.configure(border_width=3, border_color="#00FFFF")
            else:
                if i < self.MAIN_IMAGE_COUNT:
                    if i == self._main_drag_data['source_idx']:
                        frame.configure(border_width=2, border_color="red")
                    else:
                        frame.configure(border_width=0)
                else:
                    if i - self.MAIN_IMAGE_COUNT == self._main_drag_data['source_idx']:
                        frame.configure(border_width=2, border_color="blue")
                    else:
                        frame.configure(border_width=0)
    
    def _on_main_drag_release(self, event):
        """主图拖放释放"""
        source_idx = self._main_drag_data['source_idx']
        
        if hasattr(self, '_drag_preview_window') and self._drag_preview_window:
            self._drag_preview_window.destroy()
            self._drag_preview_window = None
        
        target_idx = None
        min_distance = float('inf')
        
        all_frames = self._main_1_1_frames + self._main_3_4_frames
        
        for i, frame in enumerate(all_frames):
            x = event.widget.winfo_pointerx()
            y = event.widget.winfo_pointery()
            frame_x = frame.winfo_rootx() + frame.winfo_width() // 2
            frame_y = frame.winfo_rooty() + frame.winfo_height() // 2
            
            distance = ((x - frame_x) ** 2 + (y - frame_y) ** 2) ** 0.5
            if distance < min_distance and distance < 150:
                min_distance = distance
                target_idx = i
        
        if source_idx is not None and target_idx is not None:
            if target_idx < self.MAIN_IMAGE_COUNT and source_idx < self.MAIN_IMAGE_COUNT:
                if source_idx != target_idx:
                    self._swap_main_images(source_idx, target_idx)
            elif target_idx >= self.MAIN_IMAGE_COUNT and source_idx >= self.MAIN_IMAGE_COUNT:
                src_3_4_idx = source_idx
                tgt_3_4_idx = target_idx - self.MAIN_IMAGE_COUNT
                if src_3_4_idx != tgt_3_4_idx:
                    self._swap_main_images_3_4(src_3_4_idx, tgt_3_4_idx)
        
        for i in range(self.MAIN_IMAGE_COUNT):
            self._main_1_1_frames[i].configure(border_width=0)
            self._main_3_4_frames[i].configure(border_width=0)
        
        self._main_drag_data = {'source_idx': None, 'drag_label': None}
    
    def _swap_main_images(self, source_idx: int, target_idx: int):
        """交换主图位置（同时交换1:1和3:4）"""
        self._main_images_1_1[source_idx], self._main_images_1_1[target_idx] = \
            self._main_images_1_1[target_idx], self._main_images_1_1[source_idx]
        
        self._main_images_3_4[source_idx], self._main_images_3_4[target_idx] = \
            self._main_images_3_4[target_idx], self._main_images_3_4[source_idx]
        
        self._update_main_image_preview_1_1(source_idx)
        self._update_main_image_preview_1_1(target_idx)
        self._update_main_image_preview_3_4(source_idx)
        self._update_main_image_preview_3_4(target_idx)
        
        self._update_status(f"已交换主图 {source_idx+1} 和 {target_idx+1}")
    
    def _swap_main_images_3_4(self, source_idx: int, target_idx: int):
        """交换3:4主图位置（同时交换1:1）"""
        self._swap_main_images(source_idx, target_idx)
    
    def _refresh_detail_resources(self):
        """刷新详情图页可用资源列表"""
        from utils.image_processor import collect_image_files
        
        for widget in self._detail_resource_container.winfo_children():
            widget.destroy()
        
        self._detail_resource_photos = []
        
        if not self.output_path or not os.path.exists(self.output_path):
            return
        
        all_resources = []
        
        main_images = collect_image_files(self.output_path, FILE_NAMING['main_image_prefix'])
        for path in main_images:
            filename = os.path.basename(path)
            if not filename.startswith(FILE_NAMING['new_image_prefix']):
                all_resources.append(('主图', path))
        
        color_images = collect_image_files(self.output_path, FILE_NAMING['color_option_prefix'])
        for path in color_images:
            filename = os.path.basename(path)
            if not filename.startswith(FILE_NAMING['new_image_prefix']):
                all_resources.append(('色卡', path))
        
        detail_images = collect_image_files(self.output_path, FILE_NAMING['detail_image_prefix'])
        for path in detail_images:
            filename = os.path.basename(path)
            if not filename.startswith(FILE_NAMING['new_image_prefix']):
                all_resources.append(('详情', path))
        
        for resource_type, path in all_resources[:30]:
            if not os.path.exists(path):
                continue
            
            try:
                img = Image.open(path)
                img_thumb = img.copy()
                img_thumb.thumbnail((60, 60), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img_thumb)
                self._detail_resource_photos.append(photo)
                
                frame = ctk.CTkFrame(self._detail_resource_container)
                frame.pack(fill="x", pady=2)
                
                label = ctk.CTkLabel(frame, text="", image=photo)
                label.pack(side="left", padx=2)
                label.bind('<Button-1>', lambda e, p=path: self._add_to_detail_canvas(p))
                
                name = os.path.basename(path)
                ctk.CTkLabel(frame, text=f"[{resource_type}]\n{name[:10]}", font=("", 7)).pack(side="left")
            except:
                pass
    
    def _add_to_detail_canvas(self, path: str):
        """添加图片到详情图画布"""
        if os.path.exists(path):
            self._canvas.add_block(path)
            self._update_status(f"已添加: {os.path.basename(path)}")
    
    def _on_delete_row(self):
        """删除行模式下的选中行"""
        if self._canvas.mode != "column":
            self._update_status("请先切换到列模式")
            return
        
        self._update_status("请在画布上拖拽选择要删除的行区域")
        self._canvas.set_tool("delete_row")
    
    def _on_pick_color(self):
        """取色工具"""
        if self._canvas.mode != "column":
            self._update_status("请先切换到列模式")
            return
        
        self._update_status("请点击画布取色")
        self._canvas.set_tool("pick_color")
    
    def _on_spot_heal(self):
        """污点去除工具"""
        if self._canvas.mode != "column":
            self._update_status("请先切换到列模式")
            return
        
        self._update_status("请拖拽选择要去除的区域（松开应用）")
        self._canvas.set_tool("spot_heal")
    
    def _on_apply_column(self):
        """应用列模式编辑，拆分为新块"""
        if self._canvas.mode != "column":
            self._update_status("请先切换到列模式")
            return
        
        if self._canvas.apply_column_edits():
            self._update_status("已应用编辑并拆分为新的详情图")
        else:
            self._update_status("应用失败，请确保有编辑内容")
