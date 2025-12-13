# -*- coding: utf-8 -*-
"""
JPG图片压缩节点实现
"""

import io
import numpy as np
from PIL import Image
import torch

class JPGImageCompression:
    """
    JPG图片压缩节点
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
                    "display": "number"
                }),
            },
        }
    
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "compress"
    CATEGORY = "image"
    
    # 确保节点能被正确搜索
    DESCRIPTION = "KOOK JPG Image Compression Node"
    
    def compress(self, image, quality):
        """
        执行JPG压缩
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
            },
        }
    
    RETURN_TYPES = ()
    RETURN_NAMES = ()
    FUNCTION = "save_jpg"
    CATEGORY = "image"
    OUTPUT_NODE = True
    
    # 确保节点能被正确搜索
    DESCRIPTION = "KOOK Save JPG Image Node"
    
    def save_jpg(self, images):
        """
        保存图像为JPG格式（默认质量90）
        """
        import os
        from datetime import datetime
        
        # 创建输出目录
        output_dir = "output"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
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
            filename = f"comfyui_jpg_{timestamp}_{i+1}.jpg"
            file_path = os.path.join(output_dir, filename)
            
            # 保存JPG文件（默认质量90）
            pil_img.save(file_path, format="JPEG", quality=90, optimize=True)
            
            # 记录保存的图像信息，用于预览
            saved_images.append({
                "filename": filename,
                "subfolder": "",
                "type": "output"
            })
        
        # 按照ComfyUI官方OUTPUT_NODE规范返回结果
        # 必须包含images字段的ui字典，用于前端显示预览
        return {
            "ui": {
                "images": saved_images
            },
            "result": ()
        }
