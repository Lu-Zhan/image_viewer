from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import streamlit as st
from typing import Dict, List, Tuple, Optional


def filter_visible_methods(
    methods: List[Dict], visible_methods: List[str]
) -> List[Dict]:
    """根据用户选择过滤可见方法"""
    return [m for m in methods if m["name"] in visible_methods]


def get_aspect_ratio(image: Image.Image) -> float:
    """获取图片宽高比"""
    width, height = image.size
    return width / height


def create_placeholder_image(
    width: int, height: int, text: str = "Image Missing"
) -> Image.Image:
    """
    创建占位符图片

    Args:
        width: 图片宽度
        height: 图片高度
        text: 显示的文本

    Returns:
        占位符图片
    """
    # 创建灰色背景图片
    img = Image.new("RGB", (width, height), color=(200, 200, 200))
    draw = ImageDraw.Draw(img)

    # 尝试使用默认字体
    try:
        # 计算合适的字体大小（根据图片大小）
        font_size = max(20, min(width, height) // 10)
        # 尝试加载系统字体（这里使用默认字体）
        font = ImageFont.load_default()
    except Exception:
        font = None

    # 计算文本位置（居中）
    if font:
        # 使用 textbbox 获取文本边界框
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    else:
        # 如果没有字体，粗略估计
        text_width = len(text) * 8
        text_height = 15

    x = (width - text_width) // 2
    y = (height - text_height) // 2

    # 绘制文本
    draw.text((x, y), text, fill=(100, 100, 100), font=font)

    return img


def find_closest_square_crop(image: Image.Image) -> Tuple[int, int, int, int]:
    """
    找到最接近 1:1 比例的裁剪区域（中心裁剪）
    返回: (left, top, right, bottom)
    """
    width, height = image.size

    # 使用较小的边作为正方形边长
    crop_size = min(width, height)

    # 计算中心裁剪的坐标
    left = (width - crop_size) // 2
    top = (height - crop_size) // 2
    right = left + crop_size
    bottom = top + crop_size

    return (left, top, right, bottom)


def load_and_process_image(
    image_path: Optional[Path],
    target_width: int = 512,
    preserve_aspect_ratio: bool = False,
    placeholder_text: str = "Image Missing",
) -> Tuple[Optional[Image.Image], float, bool]:
    """
    加载并处理图片
    参数:
        image_path: 图片路径（如果为None，则生成占位符）
        target_width: 目标宽度
        preserve_aspect_ratio: 是否保持原始比例（不裁剪为正方形）
        placeholder_text: 占位符文本
    返回: (处理后的图片, 原始宽高比, 是否被裁剪)
    """
    # 如果图片路径为None，生成占位符图片
    if image_path is None:
        placeholder = create_placeholder_image(
            target_width, target_width, placeholder_text
        )
        return placeholder, 1.0, False

    try:
        img = Image.open(image_path)
        original_ratio = get_aspect_ratio(img)

        # 检查是否需要裁剪（宽高比偏离 1:1 超过 5%）
        needs_crop = abs(original_ratio - 1.0) > 0.05

        # 如果不保持原始比例，且需要裁剪，则裁剪到正方形
        if needs_crop and not preserve_aspect_ratio:
            # 裁剪到接近 1:1
            crop_box = find_closest_square_crop(img)
            img = img.crop(crop_box)

        # 调整大小到目标宽度，保持宽高比
        aspect_ratio = get_aspect_ratio(img)
        new_height = int(target_width / aspect_ratio)
        img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)

        return img, original_ratio, needs_crop
    except FileNotFoundError:
        # 文件不存在，生成占位符
        placeholder = create_placeholder_image(
            target_width, target_width, placeholder_text
        )
        return placeholder, 1.0, False
    except Exception as e:
        st.error(f"加载图片 {image_path} 时出错: {e}")
        # 出错时也生成占位符
        placeholder = create_placeholder_image(
            target_width, target_width, placeholder_text
        )
        return placeholder, 1.0, False


def check_image_exists(base_dir: Path, image_rel_path: str) -> bool:
    """检查图片文件是否存在"""
    try:
        image_path = base_dir / image_rel_path
        return image_path.exists() and image_path.is_file()
    except Exception:
        return False


def check_aspect_ratio_consistency(images_info: List[Tuple[str, float]]) -> bool:
    """
    检查所有图片的宽高比是否一致
    images_info: [(方法名, 宽高比), ...]
    返回: 是否一致
    """
    if len(images_info) < 2:
        return True

    ratios = [ratio for _, ratio in images_info]
    avg_ratio = sum(ratios) / len(ratios)

    # 如果任何图片的宽高比偏离平均值超过 5%，则认为不一致
    for method_name, ratio in images_info:
        if abs(ratio - avg_ratio) / avg_ratio > 0.05:
            return False

    return True


def apply_crop_to_image(
    image: Image.Image, box: Tuple[int, int, int, int], target_width: int
) -> Image.Image:
    """
    对图片应用裁剪框并调整大小
    参数:
        image: PIL Image对象
        box: 裁剪框坐标 (left, top, right, bottom)
        target_width: 目标宽度
    返回:
        裁剪并调整大小后的图片
    """
    # 裁剪图片
    cropped = image.crop(box)

    # 调整大小到目标宽度，保持宽高比
    aspect_ratio = get_aspect_ratio(cropped)
    new_height = int(target_width / aspect_ratio)
    resized = cropped.resize((target_width, new_height), Image.Resampling.LANCZOS)

    return resized


def draw_crop_box_on_image(
    image: Image.Image,
    box: Tuple[int, int, int, int],
    original_size: Tuple[int, int],
    display_size: Tuple[int, int],
    color: str = "#00ff00",
) -> Image.Image:
    """
    在图片上绘制裁剪框
    参数:
        image: 要绘制的图片（已处理过的显示版本）
        box: 原始图片上的裁剪框坐标 (left, top, right, bottom)
        original_size: 原始图片尺寸 (width, height)
        display_size: 显示图片尺寸 (width, height)
        color: 框的颜色 (默认: '#00ff00' 绿色)
    返回:
        绘制了指定颜色框的图片
    """
    # 创建图片副本
    img_with_box = image.copy()
    draw = ImageDraw.Draw(img_with_box)

    # 计算缩放比例
    scale_x = display_size[0] / original_size[0]
    scale_y = display_size[1] / original_size[1]

    # 将原始坐标缩放到显示尺寸
    left = int(box[0] * scale_x)
    top = int(box[1] * scale_y)
    right = int(box[2] * scale_x)
    bottom = int(box[3] * scale_y)

    # 绘制指定颜色的矩形框（3像素宽）
    for i in range(3):
        draw.rectangle(
            [(left + i, top + i), (right - i, bottom - i)], outline=color, width=1
        )

    return img_with_box


def draw_all_crop_boxes_on_image(
    image: Image.Image,
    crops: List[Dict],
    original_size: Tuple[int, int],
    display_size: Tuple[int, int],
) -> Image.Image:
    """
    在图片上绘制多个裁剪框
    参数:
        image: 要绘制的图片
        crops: 裁剪数据列表，每个包含 'box' 和 'color'
        original_size: 原始图片尺寸 (width, height)
        display_size: 显示图片尺寸 (width, height)
    返回:
        绘制了所有裁剪框的图片
    """
    result_img = image.copy()

    for crop in crops:
        result_img = draw_crop_box_on_image(
            result_img, crop["box"], original_size, display_size, crop["color"]
        )

    return result_img
