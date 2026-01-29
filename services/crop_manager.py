from pathlib import Path
from PIL import Image
import streamlit as st
from typing import Dict, List, Tuple, Optional

from config.constants import CROP_COLORS
from utils.image_processing import apply_crop_to_image, check_image_exists, filter_visible_methods


def save_crop_for_sample(sample_idx: int, box: Tuple[int, int, int, int],
                         samples: List[Dict], methods: List[Dict],
                         base_dir: Path, target_width: int,
                         crop_id: str, color: str, visible_methods: Optional[List[str]] = None) -> bool:
    """
    对样本的所有方法图片应用相同的裁剪框（支持多crop）
    参数:
        sample_idx: 样本索引
        box: 裁剪框坐标 (left, top, right, bottom)
        samples: 样本列表
        methods: 方法列表
        base_dir: 图片基础路径
        target_width: 目标宽度
        crop_id: crop的唯一标识符
        color: crop的颜色
        visible_methods: 可见方法列表
    返回:
        是否成功
    """
    def get_image_path(rel_path):
        """Helper to handle both absolute and relative paths"""
        if Path(rel_path).is_absolute():
            return Path(rel_path)
        return base_dir / rel_path
    
    def image_exists(rel_path):
        """Helper to check if image exists for both path types"""
        path = get_image_path(rel_path)
        return path.exists() and path.is_file()
    
    try:
        sample = samples[sample_idx]
        cropped_images = {}
        original_sizes = {}

        # 使用过滤后的方法列表
        visible_methods_list = filter_visible_methods(methods, visible_methods) if visible_methods else methods

        for method in visible_methods_list:
            method_name = method["name"]

            if method_name not in sample["images"]:
                continue

            image_rel_path = sample["images"][method_name]

            # 跳过不存在的图片文件
            if not image_exists(image_rel_path):
                continue

            image_path = get_image_path(image_rel_path)

            # 加载原始图片
            img = Image.open(image_path)
            original_sizes[method_name] = img.size

            # 应用裁剪
            cropped = apply_crop_to_image(img, box, target_width)
            cropped_images[method_name] = cropped

        # 创建新的crop对象
        new_crop = {
            'id': crop_id,
            'color': color,
            'box': box,
            'cropped_images': cropped_images,
            'original_sizes': original_sizes
        }

        # 初始化或更新crop_data
        if sample_idx not in st.session_state.crop_data:
            st.session_state.crop_data[sample_idx] = {'crops': []}

        if 'crops' not in st.session_state.crop_data[sample_idx]:
            st.session_state.crop_data[sample_idx]['crops'] = []

        # 检查是否是更新已有crop
        crop_list = st.session_state.crop_data[sample_idx]['crops']
        crop_found = False

        for i, crop in enumerate(crop_list):
            if crop['id'] == crop_id:
                # 更新已有crop
                crop_list[i] = new_crop
                crop_found = True
                break

        # 如果是新crop，添加到列表
        if not crop_found:
            crop_list.append(new_crop)

        return True
    except Exception as e:
        st.error(f"保存裁剪数据时出错: {e}")
        return False


def get_crop_data(sample_idx: int) -> Optional[Dict]:
    """
    获取样本的裁剪数据
    参数:
        sample_idx: 样本索引
    返回:
        裁剪数据字典，如果不存在则返回None
    """
    return st.session_state.crop_data.get(sample_idx, None)


def migrate_crop_data_if_needed():
    """
    将旧的单crop格式迁移到新的多crop格式
    旧格式: {sample_idx: {'box': ..., 'cropped_images': {...}, 'original_sizes': {...}}}
    新格式: {sample_idx: {'crops': [{'id': ..., 'color': ..., 'box': ..., ...}, ...]}}
    """
    if not hasattr(st.session_state, 'crop_data'):
        return

    for sample_idx in list(st.session_state.crop_data.keys()):
        data = st.session_state.crop_data[sample_idx]

        # 检查是否是旧格式（直接有'box'键，而不是'crops'）
        if 'box' in data and 'crops' not in data:
            # 迁移到新格式
            st.session_state.crop_data[sample_idx] = {
                'crops': [{
                    'id': 'crop_0',
                    'color': CROP_COLORS[0],  # Green
                    'box': data['box'],
                    'cropped_images': data.get('cropped_images', {}),
                    'original_sizes': data.get('original_sizes', {})
                }]
            }


def get_next_crop_color(sample_idx: int) -> str:
    """
    获取下一个可用的crop颜色
    参数:
        sample_idx: 样本索引
    返回:
        下一个可用的颜色（从CROP_COLORS中选择未使用的）
    """
    crop_data = get_crop_data(sample_idx)

    if not crop_data or 'crops' not in crop_data:
        # 没有crops，返回第一个颜色
        return CROP_COLORS[0]

    # 获取已使用的颜色
    used_colors = {crop['color'] for crop in crop_data['crops']}

    # 找到第一个未使用的颜色
    for color in CROP_COLORS:
        if color not in used_colors:
            return color

    # 如果所有颜色都被使用（不应该发生，因为有MAX_CROPS_PER_SAMPLE限制）
    # 返回第一个颜色
    return CROP_COLORS[0]


def get_crop_by_id(sample_idx: int, crop_id: str) -> Optional[Dict]:
    """
    根据crop ID获取crop数据
    参数:
        sample_idx: 样本索引
        crop_id: crop ID
    返回:
        crop数据字典，如果不存在则返回None
    """
    crop_data = get_crop_data(sample_idx)

    if not crop_data or 'crops' not in crop_data:
        return None

    for crop in crop_data['crops']:
        if crop['id'] == crop_id:
            return crop

    return None


def delete_crop_from_sample(sample_idx: int, crop_id: str):
    """
    从样本中删除指定的crop
    参数:
        sample_idx: 样本索引
        crop_id: 要删除的crop ID
    """
    if sample_idx not in st.session_state.crop_data:
        return

    crop_data = st.session_state.crop_data[sample_idx]

    if 'crops' not in crop_data:
        return

    # 过滤掉要删除的crop
    crop_data['crops'] = [crop for crop in crop_data['crops'] if crop['id'] != crop_id]

    # 如果没有crops了，删除整个sample的crop_data
    if not crop_data['crops']:
        del st.session_state.crop_data[sample_idx]
