# -*- coding: utf-8 -*-
"""
图片压缩节点实现
"""

import io
import os
import time
import numpy as np
from PIL import Image
import torch

try:
    import folder_paths
except ImportError:
    folder_paths = None


def get_output_directory():
    """
    获取 ComfyUI 输出目录，缺失时回退到相对 output 目录。
    """
    if folder_paths is not None and hasattr(folder_paths, "get_output_directory"):
        return folder_paths.get_output_directory()
    return "output"


def get_temp_directory():
    """
    获取 ComfyUI 临时目录，缺失时回退到 output 目录。
    """
    if folder_paths is not None and hasattr(folder_paths, "get_temp_directory"):
        return folder_paths.get_temp_directory()
    return get_output_directory()


def unwrap_quoted_path(path_value):
    """
    去掉路径首尾空白和成对包裹引号。
    """
    unwrapped = (path_value or "").strip()
    if len(unwrapped) >= 2 and unwrapped[0] == unwrapped[-1] and unwrapped[0] in {"'", '"'}:
        unwrapped = unwrapped[1:-1].strip()
    return unwrapped


def normalize_directory_path(directory_path):
    """
    规范化目录路径，兼容包裹引号、环境变量和用户目录。
    """
    normalized = unwrap_quoted_path(directory_path)
    normalized = os.path.expandvars(os.path.expanduser(normalized))
    return os.path.abspath(os.path.normpath(normalized))


def tensor_image_to_uint8_numpy(image_tensor):
    """
    将 ComfyUI 图像张量安全转换为 uint8 numpy 数组。
    """
    img_np = image_tensor.cpu().numpy()
    img_np = np.clip(np.rint(img_np * 255.0), 0, 255).astype(np.uint8)
    return img_np


def sanitize_filename_prefix(filename_prefix):
    """
    清理文件名前缀，避免路径穿越和非法目录写入。
    """
    if not filename_prefix:
        return "Comfyui_"

    invalid_chars = '<>:"/\\|?*'
    sanitized = "".join("_" if ch in invalid_chars or ord(ch) < 32 else ch for ch in filename_prefix)
    sanitized = sanitized.strip().rstrip(".")
    sanitized = sanitized[:120]
    return sanitized or "Comfyui_"


def build_unique_output_path(directory, filename_prefix, timestamp, index, extension):
    """
    生成不会覆盖已有文件的输出路径。
    """
    base_filename = f"{filename_prefix}{timestamp}_{index}{extension}"
    file_path = os.path.join(directory, base_filename)
    duplicate_index = 1

    while os.path.exists(file_path):
        base_filename = f"{filename_prefix}{timestamp}_{index}_{duplicate_index}{extension}"
        file_path = os.path.join(directory, base_filename)
        duplicate_index += 1

    return base_filename, file_path


def prepare_image_for_jpeg_pipeline(img_np):
    """
    规范化图像通道，生成可进入 JPEG 流程的 RGB 图像，并按需保留 alpha。
    """
    if img_np.ndim == 2:
        rgb_np = np.stack([img_np] * 3, axis=-1)
        return Image.fromarray(rgb_np, mode="RGB"), None

    channel_count = img_np.shape[-1]

    if channel_count == 1:
        rgb_np = np.repeat(img_np, 3, axis=-1)
        return Image.fromarray(rgb_np, mode="RGB"), None

    if channel_count == 2:
        gray_channel = img_np[..., :1]
        alpha_channel = img_np[..., 1:2]
        rgb_np = np.repeat(gray_channel, 3, axis=-1)
        return Image.fromarray(rgb_np, mode="RGB"), alpha_channel

    if channel_count >= 4:
        alpha_channel = img_np[..., 3:4]
        return Image.fromarray(img_np[..., :3], mode="RGB"), alpha_channel

    return Image.fromarray(img_np[..., :3], mode="RGB"), None


def prepare_image_for_save(img_np):
    """
    生成保存用的 RGB/JPG 图像。
    """
    if img_np.ndim == 2:
        img_rgb = np.stack([img_np] * 3, axis=-1)
        return Image.fromarray(img_rgb, mode="RGB"), ".jpg", "JPEG", {"quality": 90, "optimize": True}, False

    channel_count = img_np.shape[-1]

    if channel_count == 1:
        img_rgb = np.repeat(img_np, 3, axis=-1)
        return Image.fromarray(img_rgb, mode="RGB"), ".jpg", "JPEG", {"quality": 90, "optimize": True}, False

    if channel_count == 2:
        gray_channel = img_np[..., :1]
        img_rgb = np.repeat(gray_channel, 3, axis=-1)
        return Image.fromarray(img_rgb, mode="RGB"), ".jpg", "JPEG", {"quality": 90, "optimize": True}, False

    if channel_count == 3:
        return Image.fromarray(img_np, mode="RGB"), ".jpg", "JPEG", {"quality": 90, "optimize": True}, False

    if channel_count >= 4:
        rgb = img_np[..., :3]
        return Image.fromarray(rgb, mode="RGB"), ".jpg", "JPEG", {"quality": 90, "optimize": True}, False

    return Image.fromarray(img_np[..., :3], mode="RGB"), ".jpg", "JPEG", {"quality": 90, "optimize": True}, False


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
            img_np = tensor_image_to_uint8_numpy(img)
            pil_img, _ = prepare_image_for_jpeg_pipeline(img_np)
            
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
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
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
    
    def save_jpg(self, images, filename_prefix, save_path="", prompt=None, extra_pnginfo=None):
        """
        保存图像为JPG格式（默认质量90）
        """
        from datetime import datetime
        
        # 仅在未指定自定义路径时使用默认 output 目录。
        # 指定 save_path 后，以 save_path 为唯一正式保存位置；节点预览写入 temp。
        preview_dir = normalize_directory_path(get_output_directory())
        temp_preview_dir = normalize_directory_path(get_temp_directory())
        custom_save_path = unwrap_quoted_path(save_path)
        actual_dir = normalize_directory_path(custom_save_path) if custom_save_path else preview_dir
        safe_filename_prefix = sanitize_filename_prefix(filename_prefix)
        
        # 确保实际保存目录存在
        if not os.path.exists(actual_dir):
            os.makedirs(actual_dir, exist_ok=True)
        if custom_save_path and not os.path.exists(temp_preview_dir):
            os.makedirs(temp_preview_dir, exist_ok=True)
        
        batch_size = images.shape[0]
        saved_images = []
        saved_paths = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        
        # 处理每张图像
        for i in range(batch_size):
            # 获取单张图像
            img = images[i]
            
            # 转换为[0, 255]范围的numpy数组
            img_np = tensor_image_to_uint8_numpy(img)

            pil_img, _ = prepare_image_for_jpeg_pipeline(img_np)
            file_extension = ".jpg"
            file_format = "JPEG"
            save_kwargs = {"quality": 90, "optimize": True, "subsampling": 1}
            
            # 生成唯一文件名
            filename, actual_file_path = build_unique_output_path(
                actual_dir,
                safe_filename_prefix,
                timestamp,
                i + 1,
                file_extension,
            )

            # 保存到实际目录
            pil_img.save(actual_file_path, format=file_format, **save_kwargs)
            saved_paths.append(actual_file_path)
            
            if custom_save_path:
                preview_filename, preview_file_path = build_unique_output_path(
                    temp_preview_dir,
                    f"{safe_filename_prefix}preview_",
                    timestamp,
                    i + 1,
                    file_extension,
                )
                pil_img.save(preview_file_path, format=file_format, **save_kwargs)
                saved_images.append({
                    "filename": preview_filename,
                    "subfolder": "",
                    "type": "temp"
                })
            else:
                subfolder = os.path.relpath(actual_dir, preview_dir)
                if subfolder == ".":
                    subfolder = ""

                saved_images.append({
                    "filename": filename,
                    "subfolder": subfolder,
                    "type": "output"
                })
        
        if custom_save_path:
            return {
                "ui": {
                    "images": saved_images,
                    "text": saved_paths
                },
                "result": ()
            }

        return {
            "ui": {
                "images": saved_images
            },
            "result": ()
        }

    @classmethod
    def IS_CHANGED(s, images, filename_prefix, save_path="", prompt=None, extra_pnginfo=None):
        """
        让保存节点每次都重新执行，避免同输入时被 ComfyUI 缓存跳过。
        """
        return time.time()
