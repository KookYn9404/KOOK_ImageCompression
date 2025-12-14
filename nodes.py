# -*- coding: utf-8 -*-
"""
图片压缩节点实现
"""

import io
import numpy as np
from PIL import Image
import torch

class ImageCompression:
    """
    高质量图片压缩节点
    """
    
    @classmethod
    def INPUT_TYPES(s):
        """
        定义节点的输入类型
        """
        return {
            "required": {
                "image": ("IMAGE",),
                "quality": ("INT", {
                    "default": 90,
                    "min": 0,
                    "max": 100,
                    "step": 1,
                    "display": "number",
                    "description": "压缩质量（0-100，默认90，如果图像较大例如10MB，可以设置为85左右，具体设置多少看你需要压缩成多大的文件大小，数值越低压缩越狠，质量就会有所下降，最低80左右就差不多，只会非常轻微的压缩图片质量，85往上图片压缩后，没有明显的质量下降，但是文件大小明显缩小。）"
                }),
            },
        }
    
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "compress"
    CATEGORY = "image"
    
    # 确保节点能被正确搜索
    DESCRIPTION = "KOOK Image Compression Node"
    
    def compress(self, image, quality):
        """
        执行图像压缩
        """
        # 转换ComfyUI图像格式到PIL图像
        # ComfyUI的图像格式是：[batch, height, width, channels]，值范围是[0, 1]
        
        # 获取原始图像数据
        batch_size = image.shape[0]
        compressed_images = []
        
        for i in range(batch_size):
            # 获取单张图像
            img = image[i]
            
            # 转换为[0, 255]范围的numpy数组
            img_np = (img.cpu().numpy() * 255).astype(np.uint8)
            
            # 转换为PIL图像（确保是RGB格式）
            if img_np.shape[-1] == 4:
                # 处理RGBA图像，转换为RGB
                pil_img = Image.fromarray(img_np).convert("RGB")
            else:
                pil_img = Image.fromarray(img_np)
            
            # 执行JPG压缩（使用内存中的BytesIO，避免磁盘IO）
            buffer_compressed = io.BytesIO()
            pil_img.save(buffer_compressed, format="JPEG", quality=quality, optimize=True, subsampling=1)
            
            # 转换回PIL图像
            buffer_compressed.seek(0)
            pil_img_compressed = Image.open(buffer_compressed)
            
            # 转换回numpy数组
            img_compressed_np = np.array(pil_img_compressed)
            
            # 确保通道数正确（如果是灰度图，转换为RGB）
            if len(img_compressed_np.shape) == 2:  # 灰度图
                img_compressed_np = np.stack([img_compressed_np] * 3, axis=-1)
            elif img_compressed_np.shape[-1] == 1:  # 单通道图
                img_compressed_np = np.repeat(img_compressed_np, 3, axis=-1)
            
            # 转换回ComfyUI图像格式
            img_compressed_np = img_compressed_np.astype(np.float32) / 255.0
            img_compressed_tensor = torch.from_numpy(img_compressed_np)
            compressed_images.append(img_compressed_tensor)
        
        # 堆叠压缩后的图像
        compressed_images_tensor = torch.stack(compressed_images)
        
        return (compressed_images_tensor,)

class SaveJPGImage:
    """
    保存JPG图像节点
    """
    
    @classmethod
    def INPUT_TYPES(s):
        """
        定义节点的输入类型
        """
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "Comfyui_"}),
            },
            "optional": {
                "save_path": ("STRING", {"default": ""}),
            },
        }
    
    RETURN_TYPES = ()
    RETURN_NAMES = ()
    FUNCTION = "save_jpg"
    CATEGORY = "image"
    OUTPUT_NODE = True
    
    # 确保节点能被正确搜索
    DESCRIPTION = "KOOK Save JPG Image Node"
    
    def save_jpg(self, images, filename_prefix, save_path=""):
        """
        保存图像为JPG格式（默认质量90）
        """
        import os
        from datetime import datetime
        
        # 确保output目录存在，用于预览
        preview_dir = "output"
        if not os.path.exists(preview_dir):
            os.makedirs(preview_dir, exist_ok=True)
        
        # 确定实际保存目录
        actual_dir = save_path.strip() if save_path and save_path.strip() else preview_dir
        
        # 确保实际保存目录存在
        if not os.path.exists(actual_dir):
            os.makedirs(actual_dir, exist_ok=True)
        
        batch_size = images.shape[0]
        saved_images = []
        
        # 处理每张图像
        for i in range(batch_size):
            # 获取单张图像
            img = images[i]
            
            # 转换为[0, 255]范围的numpy数组
            img_np = (img.cpu().numpy() * 255).astype(np.uint8)
            
            # 转换为PIL图像（确保是RGB格式）
            if img_np.shape[-1] == 4:
                # 处理RGBA图像，转换为RGB
                pil_img = Image.fromarray(img_np).convert("RGB")
            else:
                pil_img = Image.fromarray(img_np)
            
            # 生成唯一文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename_prefix}{timestamp}_{i+1}.jpg"
            
            # 保存到实际目录
            actual_file_path = os.path.join(actual_dir, filename)
            pil_img.save(actual_file_path, format="JPEG", quality=90, optimize=True)
            
            # 对于预览，确保图片在output目录中
            preview_file_path = os.path.join(preview_dir, filename)
            if actual_dir != preview_dir:
                # 如果保存到自定义目录，也复制一份到preview目录用于预览
                pil_img.save(preview_file_path, format="JPEG", quality=90, optimize=True)
            
            # 记录保存的图像信息，用于预览
            # ComfyUI预览需要图片在output目录中，subfolder为空
            saved_images.append({
                "filename": filename,
                "subfolder": "",
                "type": "output"
            })
        
        # 按照ComfyUI官方OUTPUT_NODE规范返回结果
        # 必须包含ui字典和result元组
        # 这是ComfyUI OUTPUT_NODE的标准返回格式
        return {
            "ui": {
                "images": saved_images
            },
            "result": ()
        }
