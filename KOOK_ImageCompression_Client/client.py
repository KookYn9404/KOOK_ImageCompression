#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KOOK Image Compression Client
一个简单的图片压缩客户端，支持拖拽上传、压缩和自动复制到剪贴板
"""

import os
import io
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
import torch
import win32clipboard
from io import BytesIO
from tkinterdnd2 import TkinterDnD, DND_FILES
import tempfile
import urllib.request
import re
import struct

class ImageCompressionClient:
    """
    图片压缩客户端类
    """
    
    def __init__(self, root):
        """
        初始化客户端
        
        参数:
            root: Tkinter根窗口
        """
        self.root = root
        self.root.title("KOOK Image Compression Client")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # 设置窗口图标（如果有）
        # self.root.iconbitmap("icon.ico")
        
        # 图片质量设置（固定为90，删除了质量选择栏）
        self.quality = 90
        
        # 初始化变量
        self.original_image = None
        self.compressed_image = None
        self.original_path = None
        
        # 创建主布局
        self.create_widgets()
        
        # 绑定拖拽事件
        self.bind_drag_events()
    
    def create_widgets(self):
        """
        创建窗口组件
        """
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建图片显示区域（上方）
        images_frame = ttk.Frame(main_frame)
        images_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 创建左侧框架（上传区域）
        left_frame = ttk.LabelFrame(images_frame, text="上传图片", padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 创建右侧框架（压缩结果区域）
        right_frame = ttk.LabelFrame(images_frame, text="压缩结果", padding="10")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 左侧Canvas用于显示图片 - 使用固定高度
        self.left_canvas = tk.Canvas(left_frame, bg='#f0f0f0', highlightthickness=1, highlightbackground='#cccccc', height=400)
        self.left_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 在Canvas上创建文本提示
        self.left_canvas_text = self.left_canvas.create_text(
            200, 200,
            text="请拖拽图片到此处或点击下方按钮选择",
            font=("Arial", 12),
            fill="#666666",
            anchor=tk.CENTER
        )
        
        # 右侧Canvas用于显示图片 - 使用固定高度
        self.right_canvas = tk.Canvas(right_frame, bg='#f0f0f0', highlightthickness=1, highlightbackground='#cccccc', height=400)
        self.right_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 在Canvas上创建文本提示
        self.right_canvas_text = self.right_canvas.create_text(
            200, 200,
            text="压缩后的图片将显示在这里",
            font=("Arial", 12),
            fill="#666666",
            anchor=tk.CENTER
        )
        
        # 图片信息
        self.info_label = ttk.Label(
            right_frame, 
            text="", 
            justify=tk.LEFT,
            font=("Arial", 10)
        )
        self.info_label.pack(pady=(10, 0), fill=tk.X)
        
        # 创建控制区域（下方）
        control_frame = ttk.LabelFrame(main_frame, text="控制选项", padding="10")
        control_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 控制按钮区域
        buttons_frame = ttk.Frame(control_frame)
        buttons_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 选择图片按钮
        select_btn = ttk.Button(
            buttons_frame, 
            text="选择图片", 
            command=self.select_image
        )
        select_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 从剪贴板粘贴按钮
        paste_btn = ttk.Button(
            buttons_frame, 
            text="从剪贴板粘贴", 
            command=self.paste_from_clipboard
        )
        paste_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 压缩按钮
        compress_btn = ttk.Button(
            buttons_frame, 
            text="压缩图片", 
            command=self.compress_image,
            style="Accent.TButton"
        )
        compress_btn.pack(side=tk.LEFT)
        
        # 设置样式
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Arial", 10, "bold"))
    
    def _display_image_on_canvas(self, canvas, image, text_item):
        """
        在Canvas上显示图片
        
        参数:
            canvas: Canvas对象
            image: PIL图像对象
            text_item: 文本对象ID
        """
        try:
            # 强制更新窗口布局
            self.root.update_idletasks()
            
            # 获取Canvas的尺寸
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()
            
            # 如果Canvas还没有尺寸，使用默认值
            if canvas_width < 50:
                canvas_width = 400
            if canvas_height < 50:
                canvas_height = 400
            
            # 设置Canvas的滚动区域
            canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))
            
            # 调整图片大小以适应Canvas
            img_width, img_height = image.size
            
            # 计算缩放比例，保持宽高比
            ratio = min((canvas_width - 40) / img_width, (canvas_height - 40) / img_height, 1.0)
            new_width = int(img_width * ratio)
            new_height = int(img_height * ratio)
            
            # 调整图片大小
            resized_image = image.resize((new_width, new_height), Image.LANCZOS)
            
            # 转换为Tkinter兼容格式
            tk_image = ImageTk.PhotoImage(resized_image)
            
            # 清除Canvas上的所有内容
            canvas.delete("all")
            
            # 在Canvas中心显示图片
            x = canvas_width // 2
            y = canvas_height // 2
            canvas.create_image(x, y, image=tk_image, anchor=tk.CENTER)
            
            # 保持引用，防止被垃圾回收
            canvas.image = tk_image
            
        except Exception as e:
            print(f"显示图片失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def bind_drag_events(self):
        """
        绑定拖拽事件
        """
        # 使用tkinterdnd2库绑定拖拽事件到左侧的Canvas
        self.left_canvas.drop_target_register(DND_FILES)
        self.left_canvas.dnd_bind('<<Drop>>', self.on_drop)
        
        # 同时绑定到根窗口，提高兼容性
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_drop)
    
    def on_drop(self, event):
        """
        拖拽放置事件处理
        """
        try:
            # 获取拖拽的数据
            data = event.data
            
            # 处理数据
            if not data:
                messagebox.showwarning("警告", "未检测到拖拽内容")
                return
            
            # 1. 检查是否是本地文件路径
            # 处理Windows路径格式
            file_path = data
            if file_path.startswith('{') and file_path.endswith('}'):
                file_path = file_path[1:-1]
            # 去除引号
            file_path = file_path.strip('"')
            
            # 检查是否是本地文件
            if os.path.isfile(file_path):
                # 检查文件扩展名是否为图片
                ext = os.path.splitext(file_path)[1].lower()
                if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
                    self.load_image(file_path)
                    return
            
            # 2. 检查是否是图片URL
            if self._is_image_url(data):
                self._load_image_from_url(data)
                return
            
            # 3. 尝试从HTML或其他格式中提取图片URL
            image_url = self._extract_image_url(data)
            if image_url:
                self._load_image_from_url(image_url)
                return
            
            # 4. 尝试处理可能的base64编码图片数据
            if 'base64' in data.lower():
                try:
                    self._load_image_from_base64(data)
                    return
                except:
                    pass
            
            # 5. 尝试处理剪贴板中的图片
            try:
                self._load_image_from_clipboard()
                return
            except:
                pass
            
            # 6. 其他情况
            messagebox.showwarning("警告", "请拖拽图片文件或图片URL")
            
        except Exception as e:
            messagebox.showerror("错误", f"拖拽上传失败: {str(e)}")
    
    def _is_image_url(self, url):
        """
        检查是否是图片URL
        """
        # 检查是否是URL格式
        if not (url.startswith('http://') or url.startswith('https://')):
            return False
        
        # 检查URL是否以图片扩展名结尾
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
        for ext in image_extensions:
            if url.lower().endswith(ext):
                return True
        
        # 检查URL中是否包含图片相关的参数
        image_patterns = ['image', 'img', 'jpg', 'jpeg', 'png', 'bmp', 'gif']
        url_lower = url.lower()
        for pattern in image_patterns:
            if pattern in url_lower:
                return True
        
        return False
    
    def _extract_image_url(self, data):
        """
        从数据中提取图片URL
        """
        try:
            # 尝试匹配URL模式
            url_pattern = r'https?://[^\s]+\.(?:jpg|jpeg|png|bmp|gif)'
            matches = re.findall(url_pattern, data, re.IGNORECASE)
            if matches:
                return matches[0]
        except:
            pass
        return None
    
    def _load_image_from_url(self, url):
        """
        从URL加载图片
        """
        try:
            self.left_canvas.delete("all")
            self.left_canvas.create_text(
                200, 200,
                text="正在从网络下载图片...",
                font=("Arial", 12),
                fill="#666666",
                anchor=tk.CENTER
            )
            self.root.update()
            
            # 下载图片到临时文件
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                temp_file_path = temp_file.name
            
            # 下载图片
            urllib.request.urlretrieve(url, temp_file_path)
            
            # 加载图片
            self.load_image(temp_file_path)
            
            # 清理临时文件
            try:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
            except:
                pass
                
        except Exception as e:
            messagebox.showerror("错误", f"下载图片失败: {str(e)}")
            self.left_canvas.delete("all")
            self.left_canvas.create_text(
                200, 200,
                text="请拖拽图片到此处或点击下方按钮选择",
                font=("Arial", 12),
                fill="#666666",
                anchor=tk.CENTER
            )
    
    def _load_image_from_clipboard(self):
        """
        尝试从剪贴板加载图片
        使用PIL的ImageGrab模块，这是更可靠的方法
        加载后转换为JPG格式存储
        """
        try:
            # 首先尝试使用PIL的ImageGrab.grabclipboard()
            from PIL import ImageGrab
            
            img = ImageGrab.grabclipboard()
            
            if img is not None:
                print(f"从剪贴板获取图片尺寸: {img.size}")
                
                # 转换为JPG格式（如果是RGBA则转为RGB）
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # 显示图片预览
                self._display_image_on_canvas(self.left_canvas, img, self.left_canvas_text)
                
                # 保存到实例变量
                self.original_image = img
                self.original_path = None
                
                return True
            
            # 如果ImageGrab失败，尝试win32clipboard方法
            win32clipboard.OpenClipboard()
            
            # 检查剪贴板是否有DIB数据
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIB):
                data = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)
                win32clipboard.CloseClipboard()
                
                # 使用PIL直接打开DIB数据
                img = self._dib_to_image(data)
                
                if img is not None:
                    print(f"从DIB数据获取图片尺寸: {img.size}")
                    
                    # 转换为JPG格式（如果是RGBA则转为RGB）
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGB')
                    
                    # 显示图片预览
                    self._display_image_on_canvas(self.left_canvas, img, self.left_canvas_text)
                    
                    # 保存到实例变量
                    self.original_image = img
                    self.original_path = None
                    
                    return True
            else:
                win32clipboard.CloseClipboard()
            
        except Exception as e:
            print(f"从剪贴板加载失败: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                win32clipboard.CloseClipboard()
            except:
                pass
            
            raise e
        
        return False
    
    def _dib_to_image(self, dib_data):
        """
        将DIB数据转换为PIL图像
        """
        try:
            # 解析BITMAPINFOHEADER
            if len(dib_data) < 40:
                return None
            
            # 读取头部信息
            biSize = struct.unpack('<I', dib_data[0:4])[0]
            biWidth = struct.unpack('<i', dib_data[4:8])[0]
            biHeight = struct.unpack('<i', dib_data[8:12])[0]
            biPlanes = struct.unpack('<H', dib_data[12:14])[0]
            biBitCount = struct.unpack('<H', dib_data[14:16])[0]
            biCompression = struct.unpack('<I', dib_data[16:20])[0]
            biSizeImage = struct.unpack('<I', dib_data[20:24])[0]
            
            print(f"DIB头部: 大小={biSize}, 宽度={biWidth}, 高度={biHeight}, 位深={biBitCount}")
            
            # 处理不同版本的BITMAPINFOHEADER
            header_size = biSize if biSize >= 40 else 40
            
            # 获取像素数据起始位置
            pixel_offset = header_size
            pixel_data = dib_data[pixel_offset:]
            
            # 计算每行字节数（4字节对齐）
            row_size = ((biWidth * biBitCount + 31) // 32) * 4
            actual_height = abs(biHeight)
            
            print(f"计算: 行大小={row_size}, 实际高度={actual_height}")
            
            # 创建BMP文件头
            bmp_header = b'BM'
            file_size = 14 + header_size + len(pixel_data)
            bmp_header += struct.pack('<I', file_size)
            bmp_header += struct.pack('<HH', 0, 0)
            bmp_header += struct.pack('<I', 14 + header_size)
            
            # 修改DIB头部中的高度为正数（BMP格式要求）
            modified_header = bytearray(dib_data[:header_size])
            struct.pack_into('<i', modified_header, 8, actual_height)
            
            # 组合完整的BMP数据
            bmp_data = bmp_header + bytes(modified_header) + pixel_data
            
            # 使用PIL打开
            img = Image.open(BytesIO(bmp_data))
            
            # 如果需要，翻转图像
            if biHeight > 0:
                img = img.transpose(Image.FLIP_TOP_BOTTOM)
            
            return img
            
        except Exception as e:
            print(f"DIB转换失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _load_image_from_base64(self, data):
        """
        尝试从base64数据加载图片
        """
        try:
            import base64
            
            # 提取base64数据
            import re
            base64_match = re.search(r'base64,(.*)', data)
            if base64_match:
                base64_data = base64_match.group(1)
                
                # 解码base64数据
                image_data = base64.b64decode(base64_data)
                
                # 创建临时文件
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                    temp_file_path = temp_file.name
                
                # 写入图片数据
                with open(temp_file_path, 'wb') as f:
                    f.write(image_data)
                
                # 加载图片
                self.load_image(temp_file_path)
                
                # 清理临时文件
                try:
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
                except:
                    pass
                
                return True
        except Exception as e:
            raise e
        
        return False
    
    def select_image(self):
        """
        选择图片文件
        """
        file_path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[
                ("图片文件", "*.jpg *.jpeg *.png *.bmp *.gif"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_path:
            self.load_image(file_path)
    
    def paste_from_clipboard(self):
        """
        从剪贴板粘贴图片
        """
        try:
            # 尝试从剪贴板加载图片
            success = self._load_image_from_clipboard()
            if not success:
                messagebox.showwarning("警告", "剪贴板中没有图片数据")
        except Exception as e:
            messagebox.showerror("错误", f"粘贴失败: {str(e)}")
    
    def load_image(self, file_path):
        """
        加载图片
        
        参数:
            file_path: 图片文件路径
        """
        try:
            # 打开图片
            self.original_image = Image.open(file_path)
            self.original_path = file_path
            
            # 显示图片预览
            self._display_image_on_canvas(self.left_canvas, self.original_image, self.left_canvas_text)
            
        except Exception as e:
            messagebox.showerror("错误", f"加载图片失败: {str(e)}")
            # 恢复提示文本
            self.left_canvas.delete("all")
            self.left_canvas.create_text(
                200, 200,
                text="请拖拽图片到此处或点击下方按钮选择",
                font=("Arial", 12),
                fill="#666666",
                anchor=tk.CENTER
            )
    
    def compress_image(self):
        """
        压缩图片
        """
        if not self.original_image:
            messagebox.showwarning("警告", "请先上传图片")
            return
        
        try:
            # 执行压缩
            self.compressed_image = self._compress_image(self.original_image, self.quality)
            
            # 显示压缩结果
            self._display_image_on_canvas(self.right_canvas, self.compressed_image, self.right_canvas_text)
            
            # 复制到剪贴板
            self.copy_to_clipboard()
            
            # 显示成功消息
            messagebox.showinfo("成功", "图片压缩完成并已复制到剪贴板")
            
        except Exception as e:
            messagebox.showerror("错误", f"压缩图片失败: {str(e)}")
    
    def _compress_image(self, image, quality):
        """
        执行图像压缩
        
        参数:
            image: PIL图像对象
            quality: 压缩质量 (0-100)
            
        返回:
            压缩后的PIL图像对象
        """
        # 确保图像是RGB格式
        if image.mode == 'RGBA':
            image = image.convert('RGB')
        
        # 使用内存中的BytesIO进行压缩
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=quality, optimize=True, subsampling=1)
        buffer.seek(0)
        
        # 读取压缩后的图像
        compressed_image = Image.open(buffer)
        return compressed_image
    
    def copy_to_clipboard(self):
        """
        复制压缩后的图片到剪贴板 (JPG格式)
        """
        if not self.compressed_image:
            return
        
        try:
            # 将图像转换为JPG格式的BytesIO
            buffer = BytesIO()
            # 确保图像是RGB格式
            img_to_save = self.compressed_image
            if img_to_save.mode in ('RGBA', 'LA', 'P'):
                img_to_save = img_to_save.convert('RGB')
            img_to_save.save(buffer, format="JPEG", quality=self.quality, optimize=True)
            jpg_data = buffer.getvalue()
            
            # 复制JPG数据到剪贴板 (使用CF_DIB格式需要先转换为DIB)
            # 这里我们同时提供多种格式
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            
            # 创建DIB格式数据用于兼容性
            buffer_dib = BytesIO()
            img_to_save.save(buffer_dib, format="BMP")
            dib_data = buffer_dib.getvalue()[14:]  # 去掉BMP文件头
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, dib_data)
            
            win32clipboard.CloseClipboard()
            
        except Exception as e:
            messagebox.showerror("错误", f"复制到剪贴板失败: {str(e)}")

def main():
    """
    主函数
    """
    root = TkinterDnD.Tk()
    app = ImageCompressionClient(root)
    root.mainloop()

if __name__ == "__main__":
    main()
