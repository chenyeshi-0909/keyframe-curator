#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import os
import sys
import numpy as np
from pathlib import Path
from PIL import Image, ImageTk
import shutil
import json
import threading

class HistoricalSceneApp:
    def __init__(self, root):
        self.root = root
        self.root.title("历史场景提取工具 v2.0")
        self.root.geometry("1300x900")
        self.root.configure(bg='#1a1a1a')
        
        # Workflow state - connects all three steps
        self.current_workflow = {
            'video_path': None,
            'video_name': None,
            'keyframes_folder': None,
            'sorted_folder': None,
            'background_folder': None,
            'human_folder': None,
            'cropped_folder': None,
            'extraction_stats': None
        }
        
        # Style configuration
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background='#1a1a1a', borderwidth=0)
        style.configure('TNotebook.Tab', padding=[20, 10], background='#2d2d2d', foreground='white')
        style.map('TNotebook.Tab', background=[('selected', '#4CAF50')])
        
        # Top status bar for workflow
        self.create_status_bar()
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Three tabs
        self.extract_frame = tk.Frame(self.notebook, bg='#1a1a1a')
        self.sort_frame = tk.Frame(self.notebook, bg='#1a1a1a')
        self.crop_frame = tk.Frame(self.notebook, bg='#1a1a1a')
        
        self.notebook.add(self.extract_frame, text="步骤1: 提取关键帧")
        self.notebook.add(self.sort_frame, text="步骤2: 分类图像")
        self.notebook.add(self.crop_frame, text="步骤3: 裁剪人物")
        
        # Initialize each module
        self.setup_extractor()
        self.setup_sorter()
        self.setup_cropper()
        
        # Use YOUR original extraction settings
        self.extraction_settings = {
            'scene_threshold': 0.1,      # Your original setting
            'min_frames_between': 3,      # Your original: only 3 frames
            'black_threshold': 15,
            'black_ratio': 0.90,
            'max_keyframes_per_minute': 180,  # Your original: 180 not 30!
            'jpeg_quality': 95
        }
        
        # Bind global keyboard shortcuts
        self.root.bind('<Key>', self.on_global_key_press)
        self.root.focus_set()
        
    def create_status_bar(self):
        """Create workflow status bar at top"""
        status_frame = tk.Frame(self.root, bg='#2d2d2d', height=50, relief='solid', bd=1)
        status_frame.pack(fill='x', padx=10, pady=(10, 5))
        status_frame.pack_propagate(False)
        
        # Project info
        self.project_label = tk.Label(status_frame, 
                                     text="当前项目: 未选择",
                                     bg='#2d2d2d', fg='white',
                                     font=('Microsoft YaHei', 11, 'bold'))
        self.project_label.pack(side='left', padx=20, pady=10)
        
        # Step indicators
        self.step_indicators = []
        steps = ["✓ 提取完成", "✓ 分类完成", "✓ 裁剪完成"]
        for i, step in enumerate(steps):
            indicator = tk.Label(status_frame, text=f"○ 步骤{i+1}",
                               bg='#2d2d2d', fg='#888',
                               font=('Microsoft YaHei', 10))
            indicator.pack(side='left', padx=15, pady=10)
            self.step_indicators.append(indicator)
    
    def update_workflow_status(self, step_completed=None):
        """Update the workflow status display"""
        if self.current_workflow['video_name']:
            self.project_label.config(text=f"当前项目: {self.current_workflow['video_name']}")
        
        if step_completed == 1:
            self.step_indicators[0].config(text="✓ 提取完成", fg='#4CAF50')
        elif step_completed == 2:
            self.step_indicators[1].config(text="✓ 分类完成", fg='#4CAF50')
        elif step_completed == 3:
            self.step_indicators[2].config(text="✓ 裁剪完成", fg='#4CAF50')
    
    def setup_extractor(self):
        """Setup keyframe extraction interface"""
        main_frame = tk.Frame(self.extract_frame, bg='#1a1a1a')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        title = tk.Label(main_frame, text="视频关键帧提取", 
                        font=('Microsoft YaHei', 16, 'bold'),
                        bg='#1a1a1a', fg='white')
        title.pack(pady=(0, 20))
        
        # Video selection
        select_frame = tk.Frame(main_frame, bg='#2d2d2d', relief='solid', bd=1)
        select_frame.pack(fill='x', pady=10)
        
        self.video_path_var = tk.StringVar(value="请选择视频文件...")
        path_label = tk.Label(select_frame, textvariable=self.video_path_var,
                             bg='#2d2d2d', fg='#e0e0e0', font=('Microsoft YaHei', 10),
                             anchor='w')
        path_label.pack(side='left', fill='x', expand=True, padx=10, pady=10)
        
        select_btn = tk.Button(select_frame, text="选择视频",
                              font=('Microsoft YaHei', 11, 'bold'),
                              bg='#4CAF50', fg='black', padx=20,
                              command=self.select_video)
        select_btn.pack(side='right', padx=10, pady=5)
        
        # Settings frame
        settings_frame = tk.LabelFrame(main_frame, text="提取设置",
                                      font=('Microsoft YaHei', 11, 'bold'),
                                      bg='#2d2d2d', fg='white', relief='solid', bd=1)
        settings_frame.pack(fill='x', pady=20)
        
        # Scene threshold slider
        tk.Label(settings_frame, text="场景变化阈值:",
                bg='#2d2d2d', fg='white').grid(row=0, column=0, sticky='w', padx=10, pady=10)
        
        self.threshold_var = tk.DoubleVar(value=0.1)  # Default to your original 0.1
        threshold_scale = tk.Scale(settings_frame, from_=0.1, to=0.7,
                                   resolution=0.05, orient='horizontal',
                                   variable=self.threshold_var, length=200,
                                   bg='#2d2d2d', fg='white', highlightthickness=0)
        threshold_scale.grid(row=0, column=1, padx=10, pady=10)
        
        threshold_label = tk.Label(settings_frame, text="(0.1=提取更多帧, 0.7=提取更少帧)",
                                  bg='#2d2d2d', fg='#888', font=('Microsoft YaHei', 9))
        threshold_label.grid(row=0, column=2, padx=10)
        
        # Progress bar
        self.extract_progress = ttk.Progressbar(main_frame, length=600, mode='determinate')
        self.extract_progress.pack(pady=20)
        
        self.extract_status = tk.Label(main_frame, text="准备就绪",
                                      bg='#1a1a1a', fg='white',
                                      font=('Microsoft YaHei', 10))
        self.extract_status.pack()
        
        # Button frame
        btn_frame = tk.Frame(main_frame, bg='#1a1a1a')
        btn_frame.pack(pady=20)
        
        self.extract_btn = tk.Button(btn_frame, text="开始提取",
                                     font=('Microsoft YaHei', 12, 'bold'),
                                     bg='#2196F3', fg='black', padx=30, pady=10,
                                     command=self.start_extraction,
                                     state='disabled')
        self.extract_btn.pack(side='left', padx=10)
        
        self.continue_sort_btn = tk.Button(btn_frame, text="继续到分类 →",
                                          font=('Microsoft YaHei', 12, 'bold'),
                                          bg='#4CAF50', fg='black', padx=30, pady=10,
                                          command=self.continue_to_sorting,
                                          state='disabled')
        self.continue_sort_btn.pack(side='left', padx=10)
        
        # Results display
        self.results_text = tk.Text(main_frame, height=8, width=80,
                                   bg='#2d2d2d', fg='white',
                                   font=('Consolas', 9))
        self.results_text.pack(pady=10)
    
    def setup_sorter(self):
        """Setup image sorting interface with thumbnail gallery"""
        # Main container
        main_container = tk.Frame(self.sort_frame, bg='#1a1a1a')
        main_container.pack(fill='both', expand=True)
        
        # Top frame - Load folder button and progress
        top_frame = tk.Frame(main_container, bg='#1a1a1a', pady=10)
        top_frame.pack(fill='x', padx=15)
        
        load_btn = tk.Button(top_frame, text="选择关键帧文件夹",
                           font=('Microsoft YaHei', 12, 'bold'),
                           bg='#4CAF50', fg='black', padx=25, pady=10,
                           command=self.load_folder_for_sorting)
        load_btn.pack(side='left')
        
        self.auto_load_btn = tk.Button(top_frame, text="加载当前项目",
                                      font=('Microsoft YaHei', 11, 'bold'),
                                      bg='#2196F3', fg='black', padx=20, pady=10,
                                      command=self.load_current_project_for_sorting,
                                      state='disabled')
        self.auto_load_btn.pack(side='left', padx=10)

        self.continue_crop_btn = tk.Button(top_frame, text="继续到裁剪 →",
                                        font=('Microsoft YaHei', 11, 'bold'),
                                        bg='#FF9800', fg='black', padx=20, pady=10,
                                        command=self.continue_to_cropping,
                                        state='disabled')
        self.continue_crop_btn.pack(side='left', padx=10)
        
        self.sort_progress_label = tk.Label(top_frame, text="请选择包含关键帧的文件夹",
                                           bg='#1a1a1a', fg='#e0e0e0',
                                           font=('Microsoft YaHei', 11))
        self.sort_progress_label.pack(side='right')
        
        # Main content area
        content_frame = tk.Frame(main_container, bg='#1a1a1a')
        content_frame.pack(fill='both', expand=True, padx=15)
        
        # Left side - Image viewer
        left_frame = tk.Frame(content_frame, bg='#2d2d2d', relief='solid', bd=1)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0,8))
        
        # Current image display
        image_frame = tk.Frame(left_frame, bg='#2d2d2d')
        image_frame.pack(fill='both', expand=True, padx=15, pady=15)
        
        self.sort_image_label = tk.Label(image_frame, bg='#2d2d2d',
                                        text="选择文件夹后，图像将显示在这里\n支持格式: JPG, PNG, BMP, TIFF",
                                        fg='#b0b0b0', font=('Microsoft YaHei', 14))
        self.sort_image_label.pack(expand=True)
        
        # Navigation
        nav_frame = tk.Frame(left_frame, bg='#2d2d2d')
        nav_frame.pack(fill='x', padx=15, pady=(0,15))
        
        prev_btn = tk.Button(nav_frame, text="◀ 上一张",
                           font=('Microsoft YaHei', 11),
                           bg='#404040', fg='black', padx=20, pady=8,
                           command=self.previous_sort_image)
        prev_btn.pack(side='left')
        
        next_btn = tk.Button(nav_frame, text="下一张 ▶",
                           font=('Microsoft YaHei', 11),
                           bg='#404040', fg='black', padx=20, pady=8,
                           command=self.next_sort_image)
        next_btn.pack(side='right')
        
        self.sort_info_label = tk.Label(nav_frame, text="",
                                       bg='#2d2d2d', fg='#e0e0e0',
                                       font=('Microsoft YaHei', 10))
        self.sort_info_label.pack()

        # Add slider for quick navigation
        slider_frame = tk.Frame(left_frame, bg='#2d2d2d')
        slider_frame.pack(fill='x', padx=15, pady=10)

        tk.Label(slider_frame, text="快速导航:", bg='#2d2d2d', fg='white',
                font=('Microsoft YaHei', 10)).pack(side='left', padx=(0,10))

        self.nav_slider = tk.Scale(slider_frame, from_=1, to=1,
                                orient='horizontal', length=400,
                                bg='#2d2d2d', fg='white',
                                highlightthickness=0,
                                command=self.slider_changed)
        self.nav_slider.pack(side='left', fill='x', expand=True)

        self.slider_label = tk.Label(slider_frame, text="1/1",
                                    bg='#2d2d2d', fg='white',
                                    font=('Microsoft YaHei', 10))
        self.slider_label.pack(side='left', padx=(10,0))
        
        # Right side - Action buttons
        right_frame = tk.Frame(content_frame, bg='#2d2d2d', width=220, relief='solid', bd=1)
        right_frame.pack(side='right', fill='y', padx=(8,0))
        right_frame.pack_propagate(False)
        
        actions_frame = tk.Frame(right_frame, bg='#2d2d2d')
        actions_frame.pack(pady=25, padx=15, fill='x')
        
        tk.Label(actions_frame, text="保存选项",
                bg='#2d2d2d', fg='white',
                font=('Microsoft YaHei', 14, 'bold')).pack(pady=(0,20))
        
        # Save buttons
        bg_btn = tk.Button(actions_frame, text="背景文档",
                         font=('Microsoft YaHei', 12, 'bold'),
                         bg='#2196F3', fg='black', pady=12,
                         command=lambda: self.save_sorted_image('background'))
        bg_btn.pack(fill='x', pady=8)
        
        human_btn = tk.Button(actions_frame, text="人物文档",
                            font=('Microsoft YaHei', 12, 'bold'),
                            bg='#FF9800', fg='black', pady=12,
                            command=lambda: self.save_sorted_image('human'))
        human_btn.pack(fill='x', pady=8)
        
        both_btn = tk.Button(actions_frame, text="背景+人物",
                           font=('Microsoft YaHei', 12, 'bold'),
                           bg='#9C27B0', fg='black', pady=12,
                           command=lambda: self.save_sorted_image('both'))
        both_btn.pack(fill='x', pady=8)
        
        # Separator
        separator = tk.Frame(actions_frame, height=2, bg='#404040')
        separator.pack(fill='x', pady=(20,15))
        
        # Undo button
        self.sort_undo_btn = tk.Button(actions_frame, text="撤销上一步",
                                      font=('Microsoft YaHei', 11, 'bold'),
                                      bg='#FFC107', fg='#333', pady=10,
                                      state='disabled',
                                      command=self.undo_sort_action)
        self.sort_undo_btn.pack(fill='x', pady=8)
        
        skip_btn = tk.Button(actions_frame, text="⏭ 跳过",
                           font=('Microsoft YaHei', 11),
                           bg='#757575', fg='black', pady=10,
                           command=self.skip_sort_image)
        skip_btn.pack(fill='x', pady=8)
        
        # Keyboard shortcuts info
        info_frame = tk.Frame(actions_frame, bg='#353535', relief='solid', bd=1)
        info_frame.pack(fill='x', pady=(25,0))
        
        tk.Label(info_frame, text="快捷键",
                bg='#353535', fg='white',
                font=('Microsoft YaHei', 10, 'bold')).pack(pady=(8,5))
        
        shortcuts = """← → 导航图片
B 背景文档
H 人物文档
T 背景+人物
U 撤销上一步
S 跳过当前"""
        
        tk.Label(info_frame, text=shortcuts,
                bg='#353535', fg='#ccc',
                font=('Microsoft YaHei', 9),
                justify='left').pack(pady=(0,8))
        
        # Bottom - Thumbnail gallery (YOUR ORIGINAL FEATURE)
        self.setup_thumbnail_gallery(main_container)
        
        # Initialize sorting variables
        self.sort_images = []
        self.sort_current_index = 0
        self.sort_processed = set()
        self.sort_thumbnails = []
        self.sort_last_action = None
        self.background_count = 0
        self.human_count = 0
    
    def setup_thumbnail_gallery(self, parent):
        """Setup thumbnail gallery at bottom - from your original code"""
        # Separator
        separator = tk.Frame(parent, height=2, bg='#404040')
        separator.pack(fill='x', padx=15, pady=8)
        
        # Thumbnail section
        thumb_section = tk.Frame(parent, bg='#1a1a1a', height=180)
        thumb_section.pack(fill='x', padx=15, pady=(0,15))
        thumb_section.pack_propagate(False)
        
        # Title
        tk.Label(thumb_section, text="缩略图预览",
                bg='#1a1a1a', fg='white',
                font=('Microsoft YaHei', 12, 'bold')).pack(pady=(8,5))
        
        # Canvas container
        canvas_frame = tk.Frame(thumb_section, bg='#1a1a1a')
        canvas_frame.pack(fill='both', expand=True, padx=8, pady=5)
        
        # Canvas for thumbnails
        self.thumbnail_canvas = tk.Canvas(canvas_frame, bg='#2d2d2d', height=120,
                                         highlightthickness=0, relief='solid', bd=1)
        
        # Horizontal scrollbar
        h_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL,
                                  command=self.thumbnail_canvas.xview)
        self.thumbnail_canvas.configure(xscrollcommand=h_scrollbar.set)
        
        self.thumbnail_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Add drag scrolling for gallery
        self.gallery_drag_data = {"x": 0, "y": 0}

        def on_gallery_press(event):
            self.gallery_drag_data["x"] = event.x

        def on_gallery_drag(event):
            delta = event.x - self.gallery_drag_data["x"] 
            self.thumbnail_canvas.xview_scroll(int(-delta/10), "units")
            self.gallery_drag_data["x"] = event.x

        self.thumbnail_canvas.bind("<ButtonPress-1>", on_gallery_press)
        self.thumbnail_canvas.bind("<B1-Motion>", on_gallery_drag)
        
        # Frame inside canvas for thumbnails
        self.thumbnail_frame = tk.Frame(self.thumbnail_canvas, bg='#2d2d2d')
        self.thumbnail_canvas.create_window(0, 0, anchor=tk.NW, window=self.thumbnail_frame)
        
        # Bind scrolling events
        self.thumbnail_frame.bind('<Configure>',
                                 lambda e: self.thumbnail_canvas.configure(
                                     scrollregion=self.thumbnail_canvas.bbox("all")))
        
        # Mouse wheel scrolling
        # Enhanced mouse wheel scrolling
        def on_mousewheel(event):
            # Increase scroll speed
            if event.delta:
                # Windows/Mac
                self.thumbnail_canvas.xview_scroll(int(-3*(event.delta/120)), "units")
            elif event.num == 4:
                # Linux scroll up
                self.thumbnail_canvas.xview_scroll(-3, "units")
            elif event.num == 5:
                # Linux scroll down
                self.thumbnail_canvas.xview_scroll(3, "units")

        self.thumbnail_canvas.bind("<MouseWheel>", on_mousewheel)
        # Add support for horizontal scrolling (touchpad)
        self.thumbnail_canvas.bind("<Shift-MouseWheel>", on_mousewheel)
        # Add two-finger swipe support for Mac
        self.thumbnail_canvas.bind("<Button-4>", lambda e: self.thumbnail_canvas.xview_scroll(-3, "units"))
        self.thumbnail_canvas.bind("<Button-5>", lambda e: self.thumbnail_canvas.xview_scroll(3, "units"))
    
    def setup_cropper(self):
        """Setup cropping interface"""
        main_frame = tk.Frame(self.crop_frame, bg='#1a1a1a')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        title = tk.Label(main_frame, text="人物裁剪工具",
                        font=('Microsoft YaHei', 16, 'bold'),
                        bg='#1a1a1a', fg='white')
        title.pack(pady=(0, 20))
        
        # Control panel
        control_frame = tk.Frame(main_frame, bg='#2d2d2d', relief='solid', bd=1)
        control_frame.pack(fill='x', pady=10)
        
        load_btn = tk.Button(control_frame, text="选择人物文件夹",
                           font=('Microsoft YaHei', 11, 'bold'),
                           bg='#4CAF50', fg='black', padx=20, pady=8,
                           command=self.load_crop_folder)
        load_btn.pack(side='left', padx=10, pady=5)
        
        self.auto_load_human_btn = tk.Button(control_frame, text="加载当前项目人物",
                                            font=('Microsoft YaHei', 11, 'bold'),
                                            bg='#2196F3', fg='black', padx=20, pady=8,
                                            command=self.load_current_human_folder,
                                            state='disabled')
        self.auto_load_human_btn.pack(side='left', padx=10, pady=5)
        
        self.crop_info = tk.Label(control_frame, text="请选择包含人物图像的文件夹",
                                bg='#2d2d2d', fg='white',
                                font=('Microsoft YaHei', 10))
        self.crop_info.pack(side='left', padx=20)
        
        save_btn = tk.Button(control_frame, text="保存裁剪",
                           font=('Microsoft YaHei', 11, 'bold'),
                           bg='#FF9800', fg='black', padx=20, pady=8,
                           command=self.save_crop, state='disabled')
        save_btn.pack(side='right', padx=10, pady=5)
        self.crop_save_btn = save_btn
        
        # Canvas for image and cropping
        canvas_frame = tk.Frame(main_frame, bg='#2d2d2d', relief='solid', bd=1)
        canvas_frame.pack(fill='both', expand=True, pady=10)
        
        self.crop_canvas = tk.Canvas(canvas_frame, bg='#2d2d2d', cursor="cross")
        self.crop_canvas.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Bind mouse events
        self.crop_canvas.bind("<ButtonPress-1>", self.start_crop)
        self.crop_canvas.bind("<B1-Motion>", self.draw_crop)
        self.crop_canvas.bind("<ButtonRelease-1>", self.end_crop)
        
        # Instructions
        instructions = tk.Label(main_frame,
                              text="使用方法：点击并拖动鼠标来选择裁剪区域，然后点击保存裁剪。可以在同一图像上裁剪多个区域。",
                              bg='#1a1a1a', fg='#888',
                              font=('Microsoft YaHei', 9))
        instructions.pack(pady=5)
        
        # Navigation
        nav_frame = tk.Frame(main_frame, bg='#1a1a1a')
        nav_frame.pack(fill='x', pady=10)
        
        prev_btn = tk.Button(nav_frame, text="◀ 上一张",
                           font=('Microsoft YaHei', 11),
                           bg='#404040', fg='black', padx=20, pady=8,
                           command=self.prev_crop_image, state='disabled')
        prev_btn.pack(side='left', padx=5)
        
        self.crop_status = tk.Label(nav_frame, text="",
                                  bg='#1a1a1a', fg='white',
                                  font=('Microsoft YaHei', 10))
        self.crop_status.pack(side='left', expand=True)
        
        next_btn = tk.Button(nav_frame, text="下一张 ▶",
                           font=('Microsoft YaHei', 11),
                           bg='#404040', fg='black', padx=20, pady=8,
                           command=self.next_crop_image, state='disabled')
        next_btn.pack(side='right', padx=5)
        
        self.crop_prev_btn = prev_btn
        self.crop_next_btn = next_btn
        
        # Cropping variables
        self.crop_images = []
        self.crop_current_index = 0
        self.crop_start_x = None
        self.crop_start_y = None
        self.crop_rect = None
        self.current_crop_image = None
        self.crop_scale_factor = 1.0
        self.crop_count = 0
    
    # Extraction methods
    def select_video(self):
        """Select video file for extraction"""
        video_path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm *.m4v"),
                      ("All files", "*.*")]
        )
        if video_path:
            self.video_path_var.set(video_path)
            self.current_workflow['video_path'] = video_path
            self.current_workflow['video_name'] = Path(video_path).stem
            self.extract_btn.config(state='normal')
            self.update_workflow_status()
    
    def start_extraction(self):
        """Start keyframe extraction in a separate thread"""
        video_path = self.current_workflow['video_path']
        if not video_path or not os.path.exists(video_path):
            messagebox.showerror("错误", "视频文件不存在")
            return
        
        self.extract_btn.config(state='disabled')
        self.extraction_settings['scene_threshold'] = self.threshold_var.get()
        
        # Run extraction in thread
        thread = threading.Thread(target=self.extract_keyframes, args=(video_path,))
        thread.daemon = True
        thread.start()
    
    def extract_keyframes(self, video_path):
        """Extract keyframes from video using YOUR ORIGINAL ALGORITHM"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                self.root.after(0, lambda: messagebox.showerror("错误", "无法打开视频文件"))
                return
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            video_name = Path(video_path).stem
            duration_minutes = total_frames / fps / 60
            
            # Create output directory
            output_base = Path(video_path).parent / f"{video_name}_keyframes"
            output_base.mkdir(exist_ok=True)
            
            # Store in workflow
            self.current_workflow['keyframes_folder'] = str(output_base)
            
            # Update UI
            self.root.after(0, lambda: self.extract_status.config(
                text=f"正在处理: {video_name} ({total_frames:,} 帧, {duration_minutes:.1f} 分钟)"))
            
            # Calculate maximum allowed keyframes
            max_allowed = int(duration_minutes * self.extraction_settings['max_keyframes_per_minute'])
            
            keyframes_detected = 0
            frame_count = 0
            prev_frame = None
            frames_since_last = 0
            black_filtered = 0
            
            # Process first frame
            ret, first_frame = cap.read()
            if ret and not self.is_black_frame(first_frame):
                output_path = output_base / f"{video_name}_keyframe_{keyframes_detected:04d}.jpg"
                cv2.imwrite(str(output_path), first_frame,
                           [cv2.IMWRITE_JPEG_QUALITY, self.extraction_settings['jpeg_quality']])
                keyframes_detected += 1
                prev_frame = first_frame.copy()
            
            # Process remaining frames
            while True:
                ret, current_frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                frames_since_last += 1
                
                # Update progress
                if frame_count % 30 == 0:
                    progress = (frame_count / total_frames) * 100
                    self.root.after(0, lambda p=progress: self.extract_progress.config(value=p))
                
                # Check if reached max keyframes
                if keyframes_detected >= max_allowed:
                    continue
                
                # Skip if too soon after last keyframe
                if frames_since_last < self.extraction_settings['min_frames_between']:
                    continue
                
                # Skip black frames
                if self.is_black_frame(current_frame):
                    black_filtered += 1
                    continue
                
                # Calculate scene change
                if prev_frame is not None:
                    difference = self.calculate_frame_difference(prev_frame, current_frame)
                    
                    if difference >= self.extraction_settings['scene_threshold']:
                        # Save keyframe
                        timestamp = frame_count / fps
                        minutes = int(timestamp // 60)
                        seconds = int(timestamp % 60)
                        
                        filename = f"{video_name}_keyframe_{keyframes_detected:04d}_{minutes:02d}m{seconds:02d}s.jpg"
                        output_path = output_base / filename
                        
                        cv2.imwrite(str(output_path), current_frame,
                                   [cv2.IMWRITE_JPEG_QUALITY, self.extraction_settings['jpeg_quality']])
                        keyframes_detected += 1
                        frames_since_last = 0
                        
                        # Update status
                        self.root.after(0, lambda kf=keyframes_detected: 
                                      self.extract_status.config(text=f"已提取 {kf} 个关键帧"))
                
                prev_frame = current_frame.copy()
            
            cap.release()
            
            # Store stats
            self.current_workflow['extraction_stats'] = {
                'total_frames': total_frames,
                'keyframes_detected': keyframes_detected,
                'duration_minutes': duration_minutes,
                'black_filtered': black_filtered
            }
            
            # Update UI with results
            results = f"""✅ 提取完成！
视频: {video_name}
总帧数: {total_frames:,}
时长: {duration_minutes:.1f} 分钟
提取关键帧: {keyframes_detected}
每分钟关键帧: {keyframes_detected/duration_minutes:.1f}
过滤黑帧: {black_filtered}
输出目录: {output_base}"""
            
            self.root.after(0, lambda: self.results_text.delete('1.0', tk.END))
            self.root.after(0, lambda: self.results_text.insert('1.0', results))
            self.root.after(0, lambda: self.extract_btn.config(state='normal'))
            self.root.after(0, lambda: self.continue_sort_btn.config(state='normal'))
            self.root.after(0, lambda: self.auto_load_btn.config(state='normal'))
            self.root.after(0, lambda: self.extract_progress.config(value=100))
            self.root.after(0, lambda: self.update_workflow_status(step_completed=1))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"提取失败: {str(e)}"))
            self.root.after(0, lambda: self.extract_btn.config(state='normal'))
    
    def calculate_frame_difference(self, frame1, frame2):
        """Calculate difference between frames using YOUR ORIGINAL METHOD"""
        hsv1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2HSV)
        hsv2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2HSV)
        
        hist1 = cv2.calcHist([hsv1], [0, 1, 2], None, [50, 60, 60],
                            [0, 180, 0, 256, 0, 256])
        hist2 = cv2.calcHist([hsv2], [0, 1, 2], None, [50, 60, 60],
                            [0, 180, 0, 256, 0, 256])
        
        hist1 = cv2.normalize(hist1, hist1).flatten()
        hist2 = cv2.normalize(hist2, hist2).flatten()
        
        correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        return 1 - max(0, correlation)
    
    def is_black_frame(self, frame):
        """Check if frame is mostly black"""
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        black_pixels = np.sum(gray_frame < self.extraction_settings['black_threshold'])
        total_pixels = gray_frame.shape[0] * gray_frame.shape[1]
        black_ratio = black_pixels / total_pixels
        return black_ratio >= self.extraction_settings['black_ratio']
    
    def continue_to_sorting(self):
        """Automatically move to sorting tab with current project"""
        self.notebook.select(1)  # Switch to sorting tab
        self.load_current_project_for_sorting()

    def continue_to_cropping(self):
        """Automatically move to cropping tab with current project"""
        if self.current_workflow['human_folder'] and os.path.exists(self.current_workflow['human_folder']):
            human_files = [f for f in os.listdir(self.current_workflow['human_folder']) 
                        if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            if human_files:
                self.notebook.select(2)  # Switch to cropping tab
                self.load_current_human_folder()
            else:
                messagebox.showwarning("警告", "人物文件夹中没有图像，请先分类一些人物图像")
        else:
            messagebox.showwarning("警告", "请先将一些图像分类到人物文件夹")
    
    # Sorting methods
    def load_current_project_for_sorting(self):
        """Load the current project's keyframes for sorting"""
        if self.current_workflow['keyframes_folder']:
            self.load_sorting_folder(self.current_workflow['keyframes_folder'])
    
    def load_folder_for_sorting(self):
        """Manually select folder for sorting"""
        folder_path = filedialog.askdirectory(title="选择包含关键帧的文件夹")
        if folder_path:
            self.load_sorting_folder(folder_path)
    
    def load_sorting_folder(self, folder_path):
        """Load images from folder for sorting"""
        if not os.path.exists(folder_path):
            messagebox.showerror("错误", "文件夹不存在")
            return
        
        # Create output folders
        folder_name = os.path.basename(folder_path)
        parent_dir = os.path.dirname(folder_path)
        
        # Use consistent naming
        if folder_name.endswith('_keyframes'):
            base_name = folder_name.replace('_keyframes', '')
        else:
            base_name = folder_name

        
        output_base = os.path.join(parent_dir, f"{base_name}_sorted")
        os.makedirs(output_base, exist_ok=True)
        
        self.sort_background_folder = os.path.join(output_base, "Background")
        self.sort_human_folder = os.path.join(output_base, "Human")
        os.makedirs(self.sort_background_folder, exist_ok=True)
        os.makedirs(self.sort_human_folder, exist_ok=True)
        
        # Update workflow
        self.current_workflow['sorted_folder'] = output_base
        self.current_workflow['background_folder'] = self.sort_background_folder
        self.current_workflow['human_folder'] = self.sort_human_folder
        
        # Load images
        self.sort_images = []
        supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
        
        for filename in sorted(os.listdir(folder_path)):
            if filename.lower().endswith(supported_formats):
                self.sort_images.append(os.path.join(folder_path, filename))
        
        if not self.sort_images:
            messagebox.showwarning("警告", "未找到图像文件")
            return
        
        # Initialize sorting
        self.sort_current_index = 0
        self.sort_processed = set()
        self.sort_last_action = None
        
        # Load thumbnails
        self.load_thumbnails()
        
        # Display first image
        self.display_sort_image()
        self.update_sort_progress()

        if os.path.exists(self.sort_human_folder):
            human_files = [f for f in os.listdir(self.sort_human_folder) 
                        if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            if human_files:
                self.continue_crop_btn.config(state='normal')
        
        # Enable human folder button
        self.auto_load_human_btn.config(state='normal')
    
    def load_thumbnails(self):
        """Load and display thumbnails in gallery"""
        # Clear existing
        for widget in self.thumbnail_frame.winfo_children():
            widget.destroy()
        
        self.sort_thumbnails = []
        
        for i, image_path in enumerate(self.sort_images):
            try:
                img = Image.open(image_path)
                img.thumbnail((100, 80), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                
                thumb_btn = tk.Button(self.thumbnail_frame, image=photo,
                                    command=lambda idx=i: self.select_sort_image(idx),
                                    bg='#404040', relief='solid', borderwidth=2)
                thumb_btn.image = photo
                thumb_btn.pack(side='left', padx=3, pady=3)
                
                self.sort_thumbnails.append(thumb_btn)
                
            except Exception as e:
                print(f"Error loading thumbnail: {e}")
        
        # Update scroll region
        self.thumbnail_frame.update_idletasks()
        self.thumbnail_canvas.configure(scrollregion=self.thumbnail_canvas.bbox("all"))
    
    def select_sort_image(self, index):
        """Select image by clicking thumbnail"""
        if 0 <= index < len(self.sort_images):
            self.sort_current_index = index
            self.display_sort_image()

    def slider_changed(self, value):
        """Handle slider movement for quick navigation"""
        index = int(value) - 1
        if 0 <= index < len(self.sort_images):
            self.sort_current_index = index
            self.display_sort_image()
            # Scroll gallery to show current image
            self.scroll_gallery_to_current()
        
    def display_sort_image(self):
        """Display current image for sorting"""
        if not self.sort_images:
            return
        
        try:
            image_path = self.sort_images[self.sort_current_index]
            img = Image.open(image_path)
            
            # Resize for display
            display_width, display_height = 700, 450
            img.thumbnail((display_width, display_height), Image.Resampling.LANCZOS)
            
            photo = ImageTk.PhotoImage(img)
            self.sort_image_label.configure(image=photo, text="")
            self.sort_image_label.image = photo
            
            # Update info
            filename = os.path.basename(image_path)
            self.sort_info_label.configure(
                text=f"{filename}\n第 {self.sort_current_index + 1} / {len(self.sort_images)} 张")
            
            # Update slider position and range
            if hasattr(self, 'nav_slider'):
                self.nav_slider.config(to=len(self.sort_images))
                self.nav_slider.set(self.sort_current_index + 1)
                self.slider_label.config(text=f"{self.sort_current_index + 1}/{len(self.sort_images)}")
            
            # Highlight current thumbnail
            self.highlight_current_thumbnail()
            
        except Exception as e:
            messagebox.showerror("错误", f"无法显示图像: {str(e)}")
    
    def highlight_current_thumbnail(self):
        """Highlight current thumbnail in gallery"""
        for i, thumb in enumerate(self.sort_thumbnails):
            if i == self.sort_current_index:
                thumb.configure(relief='solid', borderwidth=3, bg='#2196F3')
            elif i in self.sort_processed:
                thumb.pack_forget()
            else:
                thumb.configure(relief='solid', borderwidth=2, bg='#404040')

    def scroll_gallery_to_current(self):
        """Scroll thumbnail gallery to show current image"""
        if not self.sort_thumbnails:
            return
        
        # Calculate position of current thumbnail
        thumb_width = 106  # 100px image + 6px padding
        current_position = self.sort_current_index * thumb_width
        
        # Get canvas viewport info
        canvas_width = self.thumbnail_canvas.winfo_width()
        
        # Calculate scroll position to center current thumbnail
        scroll_to = (current_position - canvas_width/2) / (len(self.sort_thumbnails) * thumb_width)
        scroll_to = max(0, min(1, scroll_to))  # Clamp between 0 and 1
        
        # Move scrollbar
        self.thumbnail_canvas.xview_moveto(scroll_to)
    
    def save_sorted_image(self, save_type):
        """Save image to specified folder(s)"""
        if not self.sort_images:
            return
        
        current_path = self.sort_images[self.sort_current_index]
        filename = os.path.basename(current_path)
        
        # Store for undo
        self.sort_last_action = {
            'index': self.sort_current_index,
            'filename': filename,
            'save_type': save_type,
            'saved_files': []
        }
        
        try:
            if save_type in ['background', 'both']:
                dest = os.path.join(self.sort_background_folder, filename)
                shutil.copy2(current_path, dest)
                self.sort_last_action['saved_files'].append(('background', dest))
            
            if save_type in ['human', 'both']:
                dest = os.path.join(self.sort_human_folder, filename)
                shutil.copy2(current_path, dest)
                self.sort_last_action['saved_files'].append(('human', dest))
                if hasattr(self, 'continue_crop_btn'):
                    self.continue_crop_btn.config(state='normal')
            
            self.sort_processed.add(self.sort_current_index)
            self.sort_undo_btn.config(state='normal')
            self.update_sort_progress()
            self.advance_to_next_unprocessed()
            
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")
    
    def skip_sort_image(self):
        """Skip current image"""
        self.sort_last_action = {
            'index': self.sort_current_index,
            'filename': os.path.basename(self.sort_images[self.sort_current_index]),
            'save_type': 'skip',
            'saved_files': []
        }
        
        self.sort_processed.add(self.sort_current_index)
        self.sort_undo_btn.config(state='normal')
        self.update_sort_progress()
        self.advance_to_next_unprocessed()
    
    def undo_sort_action(self):
        """Undo last sorting action"""
        if not self.sort_last_action:
            return
        
        try:
            # Remove saved files
            for folder_type, file_path in self.sort_last_action['saved_files']:
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            # Remove from processed
            if self.sort_last_action['index'] in self.sort_processed:
                self.sort_processed.remove(self.sort_last_action['index'])
            
            # Go back to that image
            self.sort_current_index = self.sort_last_action['index']
            self.display_sort_image()
            self.update_sort_progress()
            
            # Disable undo
            self.sort_undo_btn.config(state='disabled')
            self.sort_last_action = None
            
        except Exception as e:
            messagebox.showerror("错误", f"撤销失败: {str(e)}")
    
    def previous_sort_image(self):
        """Go to previous image"""
        if self.sort_current_index > 0:
            self.sort_current_index -= 1
            self.display_sort_image()
    
    def next_sort_image(self):
        """Go to next image"""
        if self.sort_current_index < len(self.sort_images) - 1:
            self.sort_current_index += 1
            self.display_sort_image()

    def refresh_gallery_visibility(self):
        """Hide processed thumbnails from gallery"""
        for i, thumb in enumerate(self.sort_thumbnails):
            if i in self.sort_processed:
                thumb.pack_forget()
        # Update scroll region after hiding
        self.thumbnail_frame.update_idletasks()
        self.thumbnail_canvas.configure(scrollregion=self.thumbnail_canvas.bbox("all"))
    
    def advance_to_next_unprocessed(self):
        """Move to next unprocessed image"""
        # Look forward
        for i in range(self.sort_current_index + 1, len(self.sort_images)):
            if i not in self.sort_processed:
                self.sort_current_index = i
                self.display_sort_image()
                self.refresh_gallery_visibility() 
                return
        
        # Look backward
        for i in range(self.sort_current_index - 1, -1, -1):
            if i not in self.sort_processed:
                self.sort_current_index = i
                self.display_sort_image()
                return
        
        # All done
        messagebox.showinfo("完成", 
            f"所有图像已处理完成！\n\n背景: {self.background_count} 张\n人物: {self.human_count} 张")
        self.update_workflow_status(step_completed=2)
        self.continue_crop_btn.config(state='normal') 
    
    def update_sort_progress(self):
        """Update sorting progress display"""
        if self.sort_images:
            processed = len(self.sort_processed)
            total = len(self.sort_images)
            remaining = total - processed
            
            # Count files
            self.background_count = len([f for f in os.listdir(self.sort_background_folder)
                                        if f.lower().endswith(('.jpg', '.jpeg', '.png'))]) \
                                        if os.path.exists(self.sort_background_folder) else 0
            
            self.human_count = len([f for f in os.listdir(self.sort_human_folder)
                                  if f.lower().endswith(('.jpg', '.jpeg', '.png'))]) \
                                  if os.path.exists(self.sort_human_folder) else 0
            
            if self.human_count > 0 and hasattr(self, 'continue_crop_btn'):
                self.continue_crop_btn.config(state='normal')
            
            self.sort_progress_label.config(
                text=f"总计: {total} | 已处理: {processed} | 剩余: {remaining} | 背景: {self.background_count} | 人物: {self.human_count}")
    
    # Cropping methods
    def load_current_human_folder(self):
        """Load current project's human folder for cropping"""
        if self.current_workflow['human_folder']:
            self.load_cropping_folder(self.current_workflow['human_folder'])
    
    def load_crop_folder(self):
        """Manually select folder for cropping"""
        folder_path = filedialog.askdirectory(title="选择人物图像文件夹")
        if folder_path:
            self.load_cropping_folder(folder_path)
    
    def load_cropping_folder(self, folder_path):
        """Load images for cropping"""
        if not os.path.exists(folder_path):
            messagebox.showerror("错误", "文件夹不存在")
            return
        
        # Create output folder
        # New code - puts cropped folder inside sorted folder
        if 'Human' in folder_path:
            # If we're in the Human folder, go up one level to sorted folder
            sorted_folder = os.path.dirname(folder_path)
            self.crop_output_folder = os.path.join(sorted_folder, "Cropped_Figures")
        else:
            # Fallback if structure is different
            parent_dir = os.path.dirname(folder_path)
            self.crop_output_folder = os.path.join(parent_dir, "Cropped_Figures")
        os.makedirs(self.crop_output_folder, exist_ok=True)
        
        # Update workflow
        self.current_workflow['cropped_folder'] = self.crop_output_folder
        
        # Load images
        self.crop_images = []
        for filename in sorted(os.listdir(folder_path)):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                self.crop_images.append(os.path.join(folder_path, filename))
        
        if not self.crop_images:
            messagebox.showwarning("警告", "未找到图像文件")
            return
        
        self.crop_current_index = 0
        self.crop_count = 0
        self.display_crop_image()
        
        # Enable controls
        self.crop_prev_btn.config(state='normal')
        self.crop_next_btn.config(state='normal')
        self.crop_save_btn.config(state='normal')
    
    def display_crop_image(self):
        """Display current image for cropping"""
        if not self.crop_images:
            return
        
        try:
            image_path = self.crop_images[self.crop_current_index]
            self.current_crop_image = Image.open(image_path)
            
            # Calculate display size
            canvas_width = self.crop_canvas.winfo_width()
            canvas_height = self.crop_canvas.winfo_height()
            
            if canvas_width <= 1:
                canvas_width = 800
                canvas_height = 600
            
            # Calculate scale
            scale_x = canvas_width / self.current_crop_image.width
            scale_y = canvas_height / self.current_crop_image.height
            self.crop_scale_factor = min(scale_x, scale_y, 1.0)
            
            new_width = int(self.current_crop_image.width * self.crop_scale_factor)
            new_height = int(self.current_crop_image.height * self.crop_scale_factor)
            
            # Resize for display
            display_image = self.current_crop_image.resize((new_width, new_height),
                                                          Image.Resampling.LANCZOS)
            
            self.crop_photo = ImageTk.PhotoImage(display_image)
            
            # Clear and display
            self.crop_canvas.delete("all")
            self.crop_canvas.create_image(0, 0, anchor='nw', image=self.crop_photo)
            
            # Update status
            filename = os.path.basename(image_path)
            self.crop_status.config(
                text=f"{filename} ({self.crop_current_index + 1}/{len(self.crop_images)})")
            self.crop_info.config(text=f"已裁剪: {self.crop_count} 张")
            
        except Exception as e:
            messagebox.showerror("错误", f"无法显示图像: {str(e)}")
    
    def start_crop(self, event):
        """Start drawing crop rectangle"""
        self.crop_start_x = event.x
        self.crop_start_y = event.y
        
        if self.crop_rect:
            self.crop_canvas.delete(self.crop_rect)
        
        self.crop_rect = self.crop_canvas.create_rectangle(
            event.x, event.y, event.x, event.y,
            outline='red', width=2
        )
    
    def draw_crop(self, event):
        """Update crop rectangle"""
        if self.crop_rect:
            self.crop_canvas.coords(
                self.crop_rect,
                self.crop_start_x, self.crop_start_y,
                event.x, event.y
            )
    
    def end_crop(self, event):
        """Finish drawing crop rectangle"""
        pass
    
    def save_crop(self):
        """Save cropped region"""
        if not self.crop_rect or not self.current_crop_image:
            messagebox.showwarning("警告", "请先选择裁剪区域")
            return
        
        coords = self.crop_canvas.coords(self.crop_rect)
        if len(coords) != 4:
            return
        
        x1, y1, x2, y2 = coords
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        
        # Convert to original coordinates
        orig_x1 = int(x1 / self.crop_scale_factor)
        orig_y1 = int(y1 / self.crop_scale_factor)
        orig_x2 = int(x2 / self.crop_scale_factor)
        orig_y2 = int(y2 / self.crop_scale_factor)
        
        try:
            cropped = self.current_crop_image.crop((orig_x1, orig_y1, orig_x2, orig_y2))
            
            # Generate filename
            original_name = Path(self.crop_images[self.crop_current_index]).stem
            output_path = os.path.join(self.crop_output_folder,
                                      f"{original_name}_crop_{self.crop_count:03d}.jpg")
            
            cropped.save(output_path, quality=95)
            self.crop_count += 1
            
            # Clear rectangle
            self.crop_canvas.delete(self.crop_rect)
            self.crop_rect = None
            
            # Update info
            self.crop_info.config(text=f"已裁剪: {self.crop_count} 张 - 保存成功!")
            
        except Exception as e:
            messagebox.showerror("错误", f"保存裁剪失败: {str(e)}")
    
    def prev_crop_image(self):
        """Go to previous image"""
        if self.crop_current_index > 0:
            self.crop_current_index -= 1
            self.display_crop_image()
    
    def next_crop_image(self):
        """Go to next image"""
        if self.crop_current_index < len(self.crop_images) - 1:
            self.crop_current_index += 1
            self.display_crop_image()
        else:
            messagebox.showinfo("完成", 
                f"所有图像已浏览完成！\n共裁剪: {self.crop_count} 张\n输出文件夹: {self.crop_output_folder}")
            self.update_workflow_status(step_completed=3)
    
    # Global keyboard shortcuts
    def on_global_key_press(self, event):
        """Handle global keyboard shortcuts"""
        # Only process if we're in sorting tab
        if self.notebook.index("current") == 1:  # Sorting tab
            key = event.keysym.lower()
            
            if key == 'left':
                self.previous_sort_image()
            elif key == 'right':
                self.next_sort_image()
            elif key == 'b':
                self.save_sorted_image('background')
            elif key == 'h':
                self.save_sorted_image('human')
            elif key == 't':
                self.save_sorted_image('both')
            elif key == 'u':
                self.undo_sort_action()
            elif key == 's':
                self.skip_sort_image()


def main():
    root = tk.Tk()
    app = HistoricalSceneApp(root)
    
    # Center window
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    root.mainloop()


if __name__ == "__main__":
    main()