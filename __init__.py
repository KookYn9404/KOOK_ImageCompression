# -*- coding: utf-8 -*-
"""
图片压缩节点
"""

from .nodes import ImageCompression, SaveJPGImage

# 注册节点
NODE_CLASS_MAPPINGS = {
    "KOOK_ImageCompression": ImageCompression,
    "KOOK_SaveJPGImage": SaveJPGImage
}

# 节点显示名称
NODE_DISPLAY_NAME_MAPPINGS = {
    "KOOK_ImageCompression": "高质量图片压缩",
    "KOOK_SaveJPGImage": "保存JPG图像"
}

# 导出必要的变量
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
