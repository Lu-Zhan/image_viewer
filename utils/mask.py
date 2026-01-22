from pathlib import Path
from PIL import Image
import numpy as np
from typing import Dict, List, Tuple, Optional


def check_masks_available(samples: List[Dict], base_dir: Path) -> bool:
    """检查是否至少有一个 sample 有有效的 mask 图片"""
    for sample in samples:
        if "mask" in sample and sample["mask"]:
            mask_path = base_dir / sample["mask"]
            if mask_path.exists() and mask_path.is_file():
                return True
    return False


def load_mask(mask_path: Path, target_size: Tuple[int, int]) -> Optional[Image.Image]:
    """
    加载 mask 图片并调整到目标尺寸
    参数:
        mask_path: mask 图片路径
        target_size: 目标尺寸 (width, height)
    返回:
        处理后的 mask 图片（灰度），如果加载失败返回 None
    """
    try:
        mask = Image.open(mask_path)
        # 转换为灰度图
        if mask.mode != 'L':
            mask = mask.convert('L')
        # 调整到目标尺寸
        if mask.size != target_size:
            mask = mask.resize(target_size, Image.Resampling.LANCZOS)
        return mask
    except Exception as e:
        # 静默失败，不在UI显示错误
        return None


def apply_mask_to_image(image: Image.Image, mask: Image.Image, overlay_opacity: float = 0.5) -> Image.Image:
    """
    对图片应用 mask 效果：mask > 0 的区域正常显示，其余区域应用半透明黑色叠加层
    参数:
        image: 要处理的 PIL Image 对象
        mask: mask 图片（灰度）
        overlay_opacity: 叠加层不透明度（默认 0.5，即变暗 50%）
    返回:
        应用 mask 后的图片
    """
    try:
        # 确保 mask 尺寸与图片匹配
        if mask.size != image.size:
            mask = mask.resize(image.size, Image.Resampling.LANCZOS)
        
        # 转换为 numpy 数组进行处理
        img_array = np.array(image).astype(np.float32)
        mask_array = np.array(mask).astype(np.float32)
        
        # 创建 mask 条件：mask > 0 为 True
        mask_condition = mask_array > 0
        
        # 对于 mask <= 0 的区域，应用半透明黑色叠加
        # 效果：将像素值乘以 (1 - overlay_opacity)，即变暗
        darkened = img_array * (1 - overlay_opacity)
        
        # 根据 mask 条件选择：mask > 0 保持原样，mask <= 0 变暗
        if len(img_array.shape) == 3:  # RGB/RGBA 图片
            # 扩展 mask 维度以匹配彩色图片
            mask_condition_3d = np.stack([mask_condition] * img_array.shape[2], axis=2)
            result = np.where(mask_condition_3d, img_array, darkened)
        else:  # 灰度图片
            result = np.where(mask_condition, img_array, darkened)
        
        # 转换回 PIL Image
        result = np.clip(result, 0, 255).astype(np.uint8)
        return Image.fromarray(result, mode=image.mode)
    
    except Exception as e:
        # 如果应用失败，返回原始图片
        return image
