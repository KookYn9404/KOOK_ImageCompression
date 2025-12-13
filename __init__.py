# -*- coding: utf-8 -*-
"""
JPG图片压缩节点
"""

from .nodes import JPGImageCompression, SaveJPGImage

# 注册节点
NODE_CLASS_MAPPINGS = {
    "KOOK_JPGImageCompression": JPGImageCompression,
    "KOOK_SaveJPGImage": SaveJPGImage
}

# 节点显示名称
NODE_DISPLAY_NAME_MAPPINGS = {
    "KOOK_JPGImageCompression": "JPG图片压缩",
    "KOOK_SaveJPGImage": "保存JPG图像"
}

# 导出必要的变量
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
