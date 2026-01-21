import streamlit as st
import json
from pathlib import Path
from PIL import Image, ImageDraw
import io
from typing import Dict, List, Tuple, Optional
from streamlit_cropper import st_cropper
import time


# Language configurations
LANGUAGES = {
    'zh': {
        'page_title': '图片查看器',
        'sidebar_title': '🖼️ 图片查看器',
        'upload_label': '上传 JSON 配置文件',
        'upload_help': '上传包含图片路径和方法信息的 JSON 文件',
        'no_file_msg': '👈 请在左侧上传 JSON 配置文件开始使用',
        'json_example_title': '📄 查看 JSON 格式示例',
        'sample_selection': '📂 样本选择',
        'num_rows_label': '显示行数',
        'num_rows_help': '选择同时显示多少行样本',
        'starting_sample': '起始样本',
        'prev_button': '上一个',
        'next_button': '下一个',
        'current_label': '📍 当前',
        'range_label': '📍 显示范围',
        'close_view': '🔍 Close View',
        'enable': '启用',
        'close_view_help': '启用裁剪功能以查看所有方法的详细区域',
        'show_edit_button': '显示 Edit Crop 按钮',
        'show_edit_help': '控制是否显示编辑裁剪按钮',
        'clear_all_crops': 'Clear All Crops',
        'display_options': '🎨 显示选项',
        'show_sample_name': '显示样本标题 (Sample Name)',
        'show_method_name': '显示方法名称 (Method Name)',
        'show_text': '显示样本文本 (Text)',
        'show_descriptions': '显示方法说明 (Descriptions)',
        'instructions': '📖 使用说明',
        'edit_crop': '✏️ Edit',
        'delete_crop': '🗑️ Delete',
        'add_crop': '➕ Add Crop',
        'max_crops_msg': '最多支持 {n} 个Close Views',
        'method_desc_title': '方法说明',
        'aspect_ratio_warning': '⚠️ 宽高比警告 - 点击查看详情',
        'aspect_ratio_msg': '检测到部分图片宽高比存在差异：',
        'select_reference_image': '选择参考图片：',
        'error_no_images': '未找到有效的图片',
        'draw_crop_hint': '👆 在上方图片上绘制矩形以选择裁剪区域',
        'reference_image': '参考图片',
        'close_view_preview': 'Close View 预览',
        'draw_crop_to_preview': '在左侧绘制裁剪框以查看预览',
        'crop_size_label': '裁剪尺寸',
        'valid_methods_count': '可用参考图片: {n}/{total}',
        'no_valid_reference': '没有可用的参考图片',
        'text_size_label': 'Prompt文本大小',
        'text_size_help': '调整样本文本显示大小（10-24px）',
        'method_text_size_label': '方法文本大小',
        'method_text_size_help': '调整方法名称和说明显示大小（10-24px）',
        'preserve_aspect_ratio': '保持原始比例',
        'preserve_aspect_ratio_help': '不裁剪为正方形，完整显示图片',
    },
    'en': {
        'page_title': 'ImageViewer',
        'sidebar_title': '🖼️ ImageViewer',
        'upload_label': 'Upload JSON Configuration',
        'upload_help': 'Upload a JSON file containing image paths and method information',
        'no_file_msg': '👈 Please upload a JSON configuration file in the sidebar',
        'json_example_title': '📄 View JSON Format Example',
        'sample_selection': '📂 Sample Selection',
        'num_rows_label': 'Number of Rows',
        'num_rows_help': 'Select how many rows of samples to display simultaneously',
        'starting_sample': 'Starting Sample',
        'prev_button': 'Previous',
        'next_button': 'Next',
        'current_label': '📍 Current',
        'range_label': '📍 Range',
        'close_view': '🔍 Close View',
        'enable': 'Enable',
        'close_view_help': 'Enable cropping feature to view detailed regions across all methods',
        'show_edit_button': 'Show Edit Crop Button',
        'show_edit_help': 'Control whether to show edit crop buttons',
        'clear_all_crops': 'Clear All Crops',
        'display_options': '🎨 Display Options',
        'show_sample_name': 'Show Sample Name',
        'show_method_name': 'Show Method Name',
        'show_text': 'Show Sample Text',
        'show_descriptions': 'Show Method Descriptions',
        'instructions': '📖 Instructions',
        'edit_crop': '✏️ Edit',
        'delete_crop': '🗑️ Delete',
        'add_crop': '➕ Add Crop',
        'max_crops_msg': 'Maximum {n} Close Views supported',
        'method_desc_title': 'Method Descriptions',
        'aspect_ratio_warning': '⚠️ Aspect Ratio Warning - Click for details',
        'aspect_ratio_msg': 'Detected aspect ratio differences in some images:',
        'select_reference_image': 'Select reference image:',
        'error_no_images': 'No valid images found',
        'draw_crop_hint': '👆 Draw a rectangle on the image above to select the crop area',
        'reference_image': 'Reference Image',
        'close_view_preview': 'Close View Preview',
        'draw_crop_to_preview': 'Draw a crop box on the left to see preview',
        'crop_size_label': 'Crop size',
        'valid_methods_count': 'Available images: {n}/{total}',
        'no_valid_reference': 'No valid reference images available',
        'text_size_label': 'Prompt Text Size',
        'text_size_help': 'Adjust sample text display size (10-24px)',
        'method_text_size_label': 'Method Text Size',
        'method_text_size_help': 'Adjust method name and description display size (10-24px)',
        'preserve_aspect_ratio': 'Preserve aspect ratio',
        'preserve_aspect_ratio_help': 'Display full image without cropping to square',
    }
}

# Color palette for multiple close views
CROP_COLORS = [
    '#00ff00',  # Green
    '#ff0000',  # Red
    '#0000ff',  # Blue
    '#ffff00',  # Yellow
    '#ff00ff',  # Magenta
]
MAX_CROPS_PER_SAMPLE = 5


def load_json_config(uploaded_file) -> Optional[Dict]:
    """加载并验证 JSON 配置文件"""
    try:
        content = uploaded_file.read()
        config = json.loads(content)
        
        # 验证必需字段
        required_fields = ["base_dir", "methods", "samples"]
        for field in required_fields:
            if field not in config:
                st.error(f"JSON 配置缺少必需字段: {field}")
                return None
        
        # 验证 methods 结构
        if not isinstance(config["methods"], list) or len(config["methods"]) == 0:
            st.error("methods 字段必须是非空列表")
            return None
        
        for method in config["methods"]:
            if "name" not in method:
                st.error("每个 method 必须包含 'name' 字段")
                return None
        
        # 验证 samples 结构
        if not isinstance(config["samples"], list) or len(config["samples"]) == 0:
            st.error("samples 字段必须是非空列表")
            return None
        
        for sample in config["samples"]:
            if "name" not in sample or "images" not in sample:
                st.error("每个 sample 必须包含 'name' 和 'images' 字段")
                return None
        
        return config
    except json.JSONDecodeError as e:
        st.error(f"JSON 解析错误: {e}")
        return None
    except Exception as e:
        st.error(f"加载配置文件时出错: {e}")
        return None


def get_aspect_ratio(image: Image.Image) -> float:
    """获取图片宽高比"""
    width, height = image.size
    return width / height


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


def load_and_process_image(image_path: Path, target_width: int = 512,
                           preserve_aspect_ratio: bool = False) -> Tuple[Optional[Image.Image], float, bool]:
    """
    加载并处理图片
    参数:
        image_path: 图片路径
        target_width: 目标宽度
        preserve_aspect_ratio: 是否保持原始比例（不裁剪为正方形）
    返回: (处理后的图片, 原始宽高比, 是否被裁剪)
    """
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
        st.error(f"找不到图片文件: {image_path}")
        return None, 0.0, False
    except Exception as e:
        st.error(f"加载图片 {image_path} 时出错: {e}")
        return None, 0.0, False


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


def apply_crop_to_image(image: Image.Image, box: Tuple[int, int, int, int], target_width: int) -> Image.Image:
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


def save_crop_for_sample(sample_idx: int, box: Tuple[int, int, int, int],
                         samples: List[Dict], methods: List[Dict],
                         base_dir: Path, target_width: int,
                         crop_id: str, color: str) -> bool:
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
    返回:
        是否成功
    """
    try:
        sample = samples[sample_idx]
        cropped_images = {}
        original_sizes = {}

        for method in methods:
            method_name = method["name"]

            if method_name not in sample["images"]:
                continue

            image_rel_path = sample["images"][method_name]

            # 跳过不存在的图片文件
            if not check_image_exists(base_dir, image_rel_path):
                continue

            image_path = base_dir / image_rel_path

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


def draw_crop_box_on_image(image: Image.Image, box: Tuple[int, int, int, int],
                           original_size: Tuple[int, int], display_size: Tuple[int, int],
                           color: str = '#00ff00') -> Image.Image:
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
            [(left + i, top + i), (right - i, bottom - i)],
            outline=color,
            width=1
        )

    return img_with_box


def draw_all_crop_boxes_on_image(image: Image.Image, crops: List[Dict],
                                  original_size: Tuple[int, int], display_size: Tuple[int, int]) -> Image.Image:
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
            result_img,
            crop['box'],
            original_size,
            display_size,
            crop['color']
        )

    return result_img


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


def main():
    # Initialize language in session state BEFORE set_page_config
    if 'language' not in st.session_state:
        st.session_state.language = 'zh'  # Default to Chinese

    lang = LANGUAGES[st.session_state.language]

    st.set_page_config(
        page_title=lang['page_title'],
        page_icon="🖼️",
        layout="wide"
    )

    # 初始化 session state
    if 'selected_sample_idx' not in st.session_state:
        st.session_state.selected_sample_idx = 0
    if 'show_text' not in st.session_state:
        st.session_state.show_text = True
    if 'show_descriptions' not in st.session_state:
        st.session_state.show_descriptions = False
    if 'show_sample_name' not in st.session_state:
        st.session_state.show_sample_name = True
    if 'show_method_name' not in st.session_state:
        st.session_state.show_method_name = True

    # Close view session state
    if 'close_view_enabled' not in st.session_state:
        st.session_state.close_view_enabled = False
    if 'show_edit_crop_button' not in st.session_state:
        st.session_state.show_edit_crop_button = True
    if 'crop_data' not in st.session_state:
        st.session_state.crop_data = {}  # {sample_idx: {'box': ..., 'cropped_images': {...}}}
    if 'current_cropping_sample' not in st.session_state:
        st.session_state.current_cropping_sample = None
    if 'cropper_reference_method' not in st.session_state:
        st.session_state.cropper_reference_method = None
    if 'current_editing_crop_id' not in st.session_state:
        st.session_state.current_editing_crop_id = None
    if 'next_crop_id_counter' not in st.session_state:
        st.session_state.next_crop_id_counter = 0
    if 'config_hash' not in st.session_state:
        st.session_state.config_hash = None
    if 'text_size' not in st.session_state:
        st.session_state.text_size = 16  # 默认 16px
    if 'method_text_size' not in st.session_state:
        st.session_state.method_text_size = 18  # 默认 18px
    if 'preserve_aspect_ratio' not in st.session_state:
        st.session_state.preserve_aspect_ratio = True

    # 迁移旧的crop数据格式到新格式
    migrate_crop_data_if_needed()

    # 固定图片宽度，自动撑满页面
    image_width = 800

    # 侧边栏：配置选项
    with st.sidebar:
        # Language toggle button in top-left with title
        # title_col, toggle_col = st.columns([0.7, 0.3])
        # with title_col:
        #     st.title(lang['sidebar_title'])
        # with toggle_col:
        # Compact language toggle button
        if st.button("中/En", key="lang_toggle", help="Switch language / 切换语言", use_container_width=True):
            st.session_state.language = 'en' if st.session_state.language == 'zh' else 'zh'
            st.rerun()

        # 文件上传
        uploaded_file = st.file_uploader(
            lang['upload_label'],
            type=["json"],
            help=lang['upload_help']
        )

    # 主界面
    if uploaded_file is None:
        st.title(lang['sidebar_title'])
        st.info(lang['no_file_msg'])

        # 显示示例 JSON 格式
        with st.expander(lang['json_example_title']):
            st.code('''{
  "base_dir": "./images",
  "methods": [
    {
      "name": "方法A",
      "description": "方法A的描述"
    },
    {
      "name": "方法B",
      "description": "方法B的描述"
    }
  ],
  "samples": [
    {
      "name": "样本1",
      "text": "样本1的文本说明",
      "images": {
        "方法A": "sample1_methodA.jpg",
        "方法B": "sample1_methodB.jpg"
      }
    }
  ]
}''', language="json")
        return
    
    # 加载配置
    config = load_json_config(uploaded_file)
    if config is None:
        return

    base_dir = Path(config["base_dir"])
    methods = config["methods"]
    samples = config["samples"]

    # Check if config has changed (clear crops if new config)
    current_config_hash = hash(json.dumps(config, sort_keys=True))
    if st.session_state.config_hash != current_config_hash:
        st.session_state.config_hash = current_config_hash
        st.session_state.crop_data = {}
        st.session_state.current_cropping_sample = None
    
    # 侧边栏：样本选择和显示行数控制
    with st.sidebar:
        # st.divider()
        # st.subheader(lang['sample_selection'])

        # num_col, col_prev, col_next = st.columns([0.5, 0.25, 0.25])

        # 1. 显示行数控制 (moved up)
        # with num_col:
        num_rows = st.number_input(
            lang['num_rows_label'],
            min_value=1,
            max_value=len(samples),
            value=1,
            step=1,
            help=lang['num_rows_help']
        )

        sample_names = [s["name"] for s in samples]
        max_start_idx = max(0, len(samples) - num_rows)

        # 回调函数 - 在widget实例化之前执行
        def go_prev():
            st.session_state.selected_sample_idx = max(0, st.session_state.selected_sample_idx - 1)

        def go_next():
            st.session_state.selected_sample_idx = min(max_start_idx, st.session_state.selected_sample_idx + 1)

        # 2. 翻页按钮 - 使用on_click回调 (moved before selectbox)
        col_prev, col_next = st.columns(2)
        with col_prev:
            # add blank space to align buttons
            st.button(
                lang['prev_button'],
                disabled=(st.session_state.selected_sample_idx == 0),
                use_container_width=True,
                key="prev_btn",
                on_click=go_prev
            )
            
        with col_next:
            st.button(
                lang['next_button'],
                disabled=(st.session_state.selected_sample_idx >= max_start_idx),
                use_container_width=True,
                key="next_btn",
                on_click=go_next
            )

        # 3. 样本选择下拉框 - selectbox会自动更新session_state的key (moved to end)
        st.selectbox(
            lang['starting_sample'],
            range(len(samples)),
            index=st.session_state.selected_sample_idx,
            format_func=lambda i: sample_names[i],
            key="selected_sample_idx"
        )

        # 显示当前范围
        end_idx = min(st.session_state.selected_sample_idx + num_rows, len(samples))
        if num_rows == 1:
            st.caption(f"{lang['current_label']}: {sample_names[st.session_state.selected_sample_idx]} ({st.session_state.selected_sample_idx + 1}/{len(samples)})")
        else:
            st.caption(f"{lang['range_label']}: {st.session_state.selected_sample_idx + 1}-{end_idx} / {len(samples)}")

        # st.divider()
        # st.markdown(f"**{lang['close_view']}**")

        close_view_enabled = st.checkbox(
            lang['close_view'],
            value=st.session_state.close_view_enabled,
            help=lang['close_view_help']
        )
        st.session_state.close_view_enabled = close_view_enabled

        if st.session_state.close_view_enabled:
            st.session_state.show_edit_crop_button = st.checkbox(
                lang['show_edit_button'],
                value=st.session_state.show_edit_crop_button,
                help=lang['show_edit_help']
            )

        if st.session_state.crop_data:
            if st.button(lang['clear_all_crops'], use_container_width=True):
                st.session_state.crop_data = {}
                st.rerun()

        st.divider()

        # 将显示选项放在 expander 中
        with st.expander(lang['display_options'], expanded=False):
            # 控制是否显示样本标题
            st.session_state.show_sample_name = st.checkbox(
                lang['show_sample_name'],
                value=st.session_state.show_sample_name,
                key="show_sample_name_checkbox"
            )

            # 控制是否显示方法名称
            st.session_state.show_method_name = st.checkbox(
                lang['show_method_name'],
                value=st.session_state.show_method_name,
                key="show_method_name_checkbox"
            )

            # 控制是否显示 text 和 descriptions
            st.session_state.show_text = st.checkbox(
                lang['show_text'],
                value=st.session_state.show_text,
                key="show_text_checkbox"
            )

            st.session_state.show_descriptions = st.checkbox(
                lang['show_descriptions'],
                value=st.session_state.show_descriptions,
                key="show_descriptions_checkbox"
            )

            st.session_state.preserve_aspect_ratio = st.checkbox(
                lang['preserve_aspect_ratio'],
                value=st.session_state.preserve_aspect_ratio,
                help=lang['preserve_aspect_ratio_help'],
                key="preserve_aspect_ratio_checkbox"
            )

            st.session_state.text_size = st.slider(
                lang['text_size_label'],
                min_value=10,
                max_value=24,
                step=2,
                value=st.session_state.text_size,
                help=lang['text_size_help'],
                key="text_size_slider"
            )

            st.session_state.method_text_size = st.slider(
                lang['method_text_size_label'],
                min_value=10,
                max_value=24,
                step=2,
                value=st.session_state.method_text_size,
                help=lang['method_text_size_help'],
                key="method_text_size_slider"
            )

        # 将使用说明放在 expander 中
        with st.expander(lang['instructions'], expanded=False):
            if st.session_state.language == 'zh':
                st.caption("""
            1. 上传 JSON 配置文件
            2. 选择显示行数（多样本对比）
            3. 使用翻页按钮或下拉框切换样本
            4. 启用 Close View 查看图片细节
                """)
            else:
                st.caption("""
            1. Upload JSON configuration file
            2. Select number of rows (multi-sample comparison)
            3. Use navigation buttons or dropdown to switch samples
            4. Enable Close View to inspect image details
                """)
    
    # 主界面 - 加载并显示图片
    # 确定要显示的样本范围
    start_idx = st.session_state.selected_sample_idx
    end_idx = min(start_idx + num_rows, len(samples))
    selected_samples = samples[start_idx:end_idx]
    
    # 添加 CSS 去除图片圆角和调整间距
    st.markdown(
        """
        <style>
        img {
            border-radius: 0 !important;
        }
        /* 减小样本之间的间距 */
        .stMarkdown {
            margin-bottom: 0.2rem !important;
            margin-top: 0.2rem !important;
        }
        /* 减小标题间距 */
        h3 {
            margin-top: 0.2rem !important;
            margin-bottom: 0.2rem !important;
        }
        /* 减小分隔线间距 */
        hr {
            margin-top: 0.5rem !important;
            margin-bottom: 0.5rem !important;
        }
        /* 减小列间距 */
        [data-testid="column"] {
            padding-left: 2px !important;
            padding-right: 2px !important;
        }
        /* 减小图片容器间距 */
        [data-testid="element-container"] {
            margin-bottom: 0.2rem !important;
            margin-top: 0.2rem !important;
        }
        /* 减小侧边栏间距 */
        .css-1d391kg, [data-testid="stSidebar"] {
            padding-top: 1rem !important;
        }
        section[data-testid="stSidebar"] .element-container {
            margin-bottom: 0.5rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Crop selection interface
    if st.session_state.current_cropping_sample is not None:
        sample_idx = st.session_state.current_cropping_sample
        sample = samples[sample_idx]

        # Determine if adding new crop or editing existing
        is_editing = st.session_state.current_editing_crop_id is not None

        if is_editing:
            # Editing existing crop
            existing_crop = get_crop_by_id(sample_idx, st.session_state.current_editing_crop_id)
            if existing_crop:
                crop_id = existing_crop['id']
                crop_color = existing_crop['color']
                crop_number = None
                # Find crop number for display
                crop_data = get_crop_data(sample_idx)
                if crop_data and 'crops' in crop_data:
                    for idx, c in enumerate(crop_data['crops']):
                        if c['id'] == crop_id:
                            crop_number = idx + 1
                            break

                title = f"### 🔍 Edit Crop for: {sample['name']}"
                if crop_number:
                    st.markdown(
                        f"{title}\n\n"
                        f'<div style="margin-bottom: 10px;"><span style="display: inline-block; '
                        f'width: 16px; height: 16px; background-color: {crop_color}; '
                        f'border: 1px solid #333; margin-right: 8px;"></span>'
                        f'<b>Close View #{crop_number}</b></div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(title)
            else:
                # Crop not found, treat as new
                is_editing = False
                st.session_state.current_editing_crop_id = None

        if not is_editing:
            # Adding new crop
            crop_id = f"crop_{st.session_state.next_crop_id_counter}"
            crop_color = get_next_crop_color(sample_idx)
            st.markdown(f"### 🔍 Add Crop for: {sample['name']}")

        st.divider()

        # Method selection for reference image
        # 过滤掉图片不存在的方法
        all_method_names = [m["name"] for m in methods if m["name"] in sample["images"]]
        method_names = [
            name for name in all_method_names
            if check_image_exists(base_dir, sample["images"][name])
        ]

        # 显示可用图片数量
        if len(method_names) < len(all_method_names):
            st.info(lang['valid_methods_count'].format(n=len(method_names), total=len(all_method_names)))

        if not method_names:
            st.error(lang['no_valid_reference'])
            st.session_state.current_cropping_sample = None
            st.session_state.current_editing_crop_id = None
            st.rerun()

        # Initialize reference method if not set
        if st.session_state.cropper_reference_method is None or st.session_state.cropper_reference_method not in method_names:
            st.session_state.cropper_reference_method = method_names[0]

        # Display method selection
        st.write(lang['select_reference_image'])
        selected_method = st.radio(
            "Method",
            method_names,
            index=method_names.index(st.session_state.cropper_reference_method),
            horizontal=True,
            label_visibility="collapsed"
        )
        st.session_state.cropper_reference_method = selected_method

        # Load reference image
        try:
            image_rel_path = sample["images"][selected_method]
            image_path = base_dir / image_rel_path
            reference_img = Image.open(image_path)

            # Create two columns for cropper and preview (1:1 ratio)
            col_cropper, col_preview = st.columns([1, 1], gap="medium")

            with col_cropper:
                st.markdown(f"**{lang['reference_image']}**")

                # Fixed display size for editing mode
                max_display_size = 420

                ref_w, ref_h = reference_img.size
                scale = min(max_display_size / ref_w, max_display_size / ref_h)
                display_size = int(max_display_size)
                display_ref_img = reference_img.resize(
                    (int(ref_w * scale), int(ref_h * scale)),
                    Image.Resampling.LANCZOS
                )

                # Display cropper with crop's color
                # Ensure reference image is fully displayed
                cropped_img_scaled = st_cropper(
                    display_ref_img,
                    realtime_update=True,
                    box_color=crop_color,
                    aspect_ratio=None,
                    return_type='box',
                    key=f"cropper_{sample_idx}_{crop_id}"
                )

                # Store display_size for height consistency in preview
                st.session_state[f"display_size_{sample_idx}_{crop_id}"] = display_size

                # Scale crop coordinates back to original image size
                cropped_img = None
                if cropped_img_scaled and cropped_img_scaled.get('width', 0) > 0:
                    cropped_img = {
                        'left': cropped_img_scaled['left'] / scale,
                        'top': cropped_img_scaled['top'] / scale,
                        'width': cropped_img_scaled['width'] / scale,
                        'height': cropped_img_scaled['height'] / scale
                    }

            with col_preview:
                st.markdown(f"**{lang['close_view_preview']}**")

                # Get display size to maintain height consistency
                display_size = st.session_state.get(f"display_size_{sample_idx}_{crop_id}", display_size)

                # Display crop size and aspect ratio
                if cropped_img and cropped_img.get('width', 0) > 0:
                    crop_w = cropped_img['width']
                    crop_h = cropped_img['height']
                    crop_ar = crop_w / crop_h
                    st.caption(f"Crop: {int(crop_w)}×{int(crop_h)}px (比例: {crop_ar:.2f}:1)")

                # Generate real-time preview
                if cropped_img and cropped_img.get('width', 0) > 0 and cropped_img.get('height', 0) > 0:
                    # Convert box format
                    box = (
                        int(cropped_img['left']),
                        int(cropped_img['top']),
                        int(cropped_img['left'] + cropped_img['width']),
                        int(cropped_img['top'] + cropped_img['height'])
                    )

                    # Apply crop and show preview (resized to 1:1)
                    preview_img = apply_crop_to_image(reference_img, box, image_width)
                    st.image(preview_img, width=display_size)
                else:
                    # Show placeholder when no crop is drawn
                    st.info("👆 " + lang['draw_crop_to_preview'])

            # Save/Cancel buttons below both columns
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Save", use_container_width=True):
                    if cropped_img and cropped_img.get('width', 0) > 0 and cropped_img.get('height', 0) > 0:
                        # cropped_img is the box coordinates
                        box = (int(cropped_img['left']), int(cropped_img['top']),
                               int(cropped_img['left'] + cropped_img['width']),
                               int(cropped_img['top'] + cropped_img['height']))

                        # Save crop for all methods in this sample
                        if save_crop_for_sample(sample_idx, box, samples, methods, base_dir, image_width, crop_id, crop_color):
                            st.success("Crop saved successfully!")

                            # Increment counter if this was a new crop
                            if not is_editing:
                                st.session_state.next_crop_id_counter += 1

                            # Clear editing state
                            st.session_state.current_cropping_sample = None
                            st.session_state.current_editing_crop_id = None
                            st.session_state.cropper_reference_method = None
                            time.sleep(0.5)
                            st.rerun()
                    else:
                        st.error("Please draw a crop box first")

            with col2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.current_cropping_sample = None
                    st.session_state.current_editing_crop_id = None
                    st.session_state.cropper_reference_method = None
                    st.rerun()

        except Exception as e:
            st.error(f"Error loading reference image: {e}")
            st.session_state.current_cropping_sample = None
            st.session_state.current_editing_crop_id = None
            st.rerun()

        st.divider()
        st.info(lang['draw_crop_hint'])
        st.divider()

    # 收集所有样本的图片信息
    all_aspect_ratios = []
    
    for row_idx, sample in enumerate(selected_samples):
        # 每个样本一行
        # 样本名称将显示在text前面（加粗）

        # 收集当前样本的所有图片信息
        images_data = []
        aspect_ratios = []
        actual_sample_idx = start_idx + row_idx
        crop_data = get_crop_data(actual_sample_idx)

        for method in methods:
            method_name = method["name"]
            method_desc = method.get("description", "")

            if method_name not in sample["images"]:
                st.warning(f"样本 '{sample['name']}' 中缺少方法 '{method_name}' 的图片")
                continue

            image_rel_path = sample["images"][method_name]
            image_path = base_dir / image_rel_path

            # 加载并处理图片
            processed_img, original_ratio, was_cropped = load_and_process_image(
                image_path, image_width, st.session_state.preserve_aspect_ratio
            )

            if processed_img is not None:
                # 如果有crop data且close view启用，在图片上绘制所有crop框
                if st.session_state.close_view_enabled and crop_data:
                    try:
                        # 加载原始图片以获取正确的尺寸
                        original_img = Image.open(image_path)
                        original_size = original_img.size
                        display_size = processed_img.size

                        # 获取crops列表并绘制所有框
                        crops = crop_data.get('crops', [])
                        if crops:
                            processed_img = draw_all_crop_boxes_on_image(
                                processed_img,
                                crops,
                                original_size,
                                display_size
                            )
                    except Exception as e:
                        pass  # 如果绘制失败，使用原始图片

                images_data.append({
                    "method_name": method_name,
                    "description": method_desc,
                    "image": processed_img,
                    "original_ratio": original_ratio,
                    "was_cropped": was_cropped,
                    "path": image_rel_path
                })
                aspect_ratios.append((method_name, original_ratio))
                all_aspect_ratios.append((sample['name'], method_name, original_ratio))

        # 并排显示图片
        if images_data:
            cols = st.columns(len(images_data))

            # 渲染主图片
            for idx, (col, data) in enumerate(zip(cols, images_data)):
                with col:
                    # 在图片上方显示方法名称（只在第一个样本显示，如果启用）
                    if st.session_state.show_method_name and row_idx == 0:
                        method_size = st.session_state.method_text_size
                        st.markdown(f"<span style='font-size: {method_size}px; font-weight: bold;'>{data['method_name']}</span>", unsafe_allow_html=True)
                    st.image(
                        data["image"],
                        use_container_width=True
                    )

            # Display multiple cropped close views vertically
            if st.session_state.close_view_enabled and crop_data:
                crops = crop_data.get('crops', [])

                for crop_idx, crop in enumerate(crops):
                    color = crop['color']

                    # Close View title with color indicator and Edit/Delete buttons if enabled
                    title_cols = st.columns([1, 5])
                    with title_cols[0]:
                        st.markdown(
                            f'<div style="margin-bottom: 5px;"><span style="display: inline-block; '
                            f'width: 14px; height: 14px; background-color: {color}; '
                            f'border: 1px solid #333; margin-right: 6px; vertical-align: middle;"></span>'
                            f'<b style="vertical-align: middle;">Close View #{crop_idx + 1}</b></div>',
                            unsafe_allow_html=True
                        )

                    # Only show Edit/Delete buttons if show_edit_crop_button is enabled
                    if st.session_state.show_edit_crop_button:
                        with title_cols[1]:
                            button_cols = st.columns([1, 1, 4])
                            with button_cols[0]:
                                if st.button(lang['edit_crop'], key=f"edit_crop_{actual_sample_idx}_{crop['id']}", use_container_width=True):
                                    st.session_state.current_cropping_sample = actual_sample_idx
                                    st.session_state.current_editing_crop_id = crop['id']
                                    st.session_state.cropper_reference_method = None
                                    st.rerun()

                            with button_cols[1]:
                                if st.button(lang['delete_crop'], key=f"delete_crop_{actual_sample_idx}_{crop['id']}", use_container_width=True):
                                    delete_crop_from_sample(actual_sample_idx, crop['id'])
                                    st.rerun()

                    # Cropped images in columns
                    crop_cols = st.columns(len(images_data))
                    for col_idx, (col, data) in enumerate(zip(crop_cols, images_data)):
                        with col:
                            method_name = data["method_name"]
                            if method_name in crop['cropped_images']:
                                st.image(crop['cropped_images'][method_name], use_container_width=True)

            # Add Crop button at the bottom if close view is enabled and button is set to show
            if st.session_state.close_view_enabled and st.session_state.show_edit_crop_button:
                # Check if max crops reached
                crops = crop_data.get('crops', []) if crop_data else []
                num_crops = len(crops)

                if num_crops < MAX_CROPS_PER_SAMPLE:
                    if st.button(lang['add_crop'], key=f"add_crop_btn_{actual_sample_idx}", use_container_width=True):
                        st.session_state.current_cropping_sample = actual_sample_idx
                        st.session_state.current_editing_crop_id = None  # None means new crop
                        st.session_state.cropper_reference_method = None
                        st.rerun()
                else:
                    st.info(lang['max_crops_msg'].format(n=MAX_CROPS_PER_SAMPLE))
        else:
            if st.session_state.language == 'zh':
                st.error(f"样本 '{sample['name']}' 没有成功加载任何图片")
            else:
                st.error(f"Sample '{sample['name']}' failed to load any images")
        
        # 显示样本的 text 字段（如果启用）
        if st.session_state.show_text and "text" in sample and sample["text"]:
            text_label = "文本:" if st.session_state.language == 'zh' else "Text:"
            text_size = st.session_state.text_size
            if st.session_state.show_sample_name:
                # 显示加粗的样本名称 + text
                st.markdown(f"<span style='font-size: {text_size}px;'><b>{sample['name']}</b> ｜ {text_label} {sample['text']}</span>", unsafe_allow_html=True)
            else:
                # 只显示text
                st.markdown(f"<span style='font-size: {text_size}px;'>{text_label} {sample['text']}</span>", unsafe_allow_html=True)
        
        # 只在最后一行样本之后显示 method descriptions（如果启用）
        if row_idx == len(selected_samples) - 1 and st.session_state.show_descriptions:
            st.divider()
            method_size = st.session_state.method_text_size
            st.markdown(f"<span style='font-size: {method_size + 2}px; font-weight: bold;'>{lang['method_desc_title']}</span>", unsafe_allow_html=True)
            method_cols = st.columns(len(methods))
            for col, method in zip(method_cols, methods):
                with col:
                    st.markdown(f"<span style='font-size: {method_size}px; font-weight: bold;'>{method['name']}</span>", unsafe_allow_html=True)
                    if method.get("description"):
                        st.markdown(f"<span style='font-size: {method_size - 2}px; color: gray;'>{method['description']}</span>", unsafe_allow_html=True)
        
        # 添加分隔线（除了最后一个样本）
        if row_idx < len(selected_samples) - 1:
            st.divider()
    
    # 检查宽高比一致性（所有显示的样本）
    if len(all_aspect_ratios) > 1:
        ratios = [ratio for _, _, ratio in all_aspect_ratios]
        avg_ratio = sum(ratios) / len(ratios)

        inconsistent = []
        for sample_name, method_name, ratio in all_aspect_ratios:
            if abs(ratio - avg_ratio) / avg_ratio > 0.05:
                inconsistent.append((sample_name, method_name, ratio))

        if inconsistent:
            with st.expander(lang['aspect_ratio_warning']):
                st.warning(lang['aspect_ratio_msg'])
                for sample_name, method_name, ratio in inconsistent:
                    st.write(f"- {sample_name} - {method_name}: {ratio:.3f} (宽:高 = {ratio:.2f}:1)")


if __name__ == "__main__":
    main()
