import streamlit as st
import json
from pathlib import Path
from PIL import Image, ImageDraw
import io
from typing import Dict, List, Tuple, Optional
from streamlit_cropper import st_cropper
import time


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


def load_and_process_image(image_path: Path, target_width: int = 512) -> Tuple[Optional[Image.Image], float, bool]:
    """
    加载并处理图片
    返回: (处理后的图片, 原始宽高比, 是否被裁剪)
    """
    try:
        img = Image.open(image_path)
        original_ratio = get_aspect_ratio(img)
        
        # 检查是否需要裁剪（宽高比偏离 1:1 超过 5%）
        needs_crop = abs(original_ratio - 1.0) > 0.05
        
        if needs_crop:
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
                         base_dir: Path, target_width: int) -> bool:
    """
    对样本的所有方法图片应用相同的裁剪框
    参数:
        sample_idx: 样本索引
        box: 裁剪框坐标 (left, top, right, bottom)
        samples: 样本列表
        methods: 方法列表
        base_dir: 图片基础路径
        target_width: 目标宽度
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
            image_path = base_dir / image_rel_path

            # 加载原始图片
            img = Image.open(image_path)
            original_sizes[method_name] = img.size

            # 应用裁剪
            cropped = apply_crop_to_image(img, box, target_width)
            cropped_images[method_name] = cropped

        # 存储裁剪数据
        st.session_state.crop_data[sample_idx] = {
            'box': box,
            'cropped_images': cropped_images,
            'original_sizes': original_sizes
        }

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


def draw_crop_box_on_image(image: Image.Image, box: Tuple[int, int, int, int],
                           original_size: Tuple[int, int], display_size: Tuple[int, int]) -> Image.Image:
    """
    在图片上绘制绿色裁剪框
    参数:
        image: 要绘制的图片（已处理过的显示版本）
        box: 原始图片上的裁剪框坐标 (left, top, right, bottom)
        original_size: 原始图片尺寸 (width, height)
        display_size: 显示图片尺寸 (width, height)
    返回:
        绘制了绿色框的图片
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

    # 绘制绿色矩形框（3像素宽）
    for i in range(3):
        draw.rectangle(
            [(left + i, top + i), (right - i, bottom - i)],
            outline='#00ff00',
            width=1
        )

    return img_with_box


def main():
    st.set_page_config(
        page_title="图片比较可视化工具",
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
    if 'config_hash' not in st.session_state:
        st.session_state.config_hash = None

    # 固定图片宽度，自动撑满页面
    image_width = 800
    
    # 侧边栏：配置选项
    with st.sidebar:
        st.title("🖼️ 图片比较可视化工具")

        # 文件上传
        uploaded_file = st.file_uploader(
            "上传 JSON 配置文件",
            type=["json"],
            help="上传包含图片路径和方法信息的 JSON 文件"
        )
    
    # 主界面
    if uploaded_file is None:
        st.info("👈 请在左侧上传 JSON 配置文件开始使用")
        
        # 显示示例 JSON 格式
        with st.expander("📄 查看 JSON 格式示例"):
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
        st.divider()
        st.subheader("📂 样本选择")

        # 显示行数控制
        num_rows = st.number_input(
            "显示行数",
            min_value=1,
            max_value=len(samples),
            value=1,
            step=1,
            help="选择同时显示多少行样本"
        )

        sample_names = [s["name"] for s in samples]
        max_start_idx = max(0, len(samples) - num_rows)

        # 回调函数 - 在widget实例化之前执行
        def go_prev():
            st.session_state.selected_sample_idx = max(0, st.session_state.selected_sample_idx - 1)

        def go_next():
            st.session_state.selected_sample_idx = min(max_start_idx, st.session_state.selected_sample_idx + 1)

        # 样本选择下拉框 - selectbox会自动更新session_state的key
        st.selectbox(
            "起始样本",
            range(len(samples)),
            index=st.session_state.selected_sample_idx,
            format_func=lambda i: sample_names[i],
            key="selected_sample_idx"
        )

        # 翻页按钮 - 使用on_click回调
        col_prev, col_next = st.columns(2)
        with col_prev:
            st.button(
                "⬅️ 上一个",
                disabled=(st.session_state.selected_sample_idx == 0),
                use_container_width=True,
                key="prev_btn",
                on_click=go_prev
            )

        with col_next:
            st.button(
                "下一个 ➡️",
                disabled=(st.session_state.selected_sample_idx >= max_start_idx),
                use_container_width=True,
                key="next_btn",
                on_click=go_next
            )

        # 显示当前范围
        end_idx = min(st.session_state.selected_sample_idx + num_rows, len(samples))
        if num_rows == 1:
            st.caption(f"📍 当前: {sample_names[st.session_state.selected_sample_idx]} ({st.session_state.selected_sample_idx + 1}/{len(samples)})")
        else:
            st.caption(f"📍 显示范围: {st.session_state.selected_sample_idx + 1}-{end_idx} / {len(samples)}")

        st.divider()
        st.markdown("**🔍 Close View**")

        close_view_enabled = st.checkbox(
            "启用",
            value=st.session_state.close_view_enabled,
            help="启用裁剪功能以查看所有方法的详细区域"
        )
        st.session_state.close_view_enabled = close_view_enabled

        if st.session_state.close_view_enabled:
            st.session_state.show_edit_crop_button = st.checkbox(
                "显示 Edit Crop 按钮",
                value=st.session_state.show_edit_crop_button,
                help="控制是否显示编辑裁剪按钮"
            )

        if st.session_state.crop_data:
            if st.button("Clear All Crops", use_container_width=True):
                st.session_state.crop_data = {}
                st.rerun()

        st.divider()

        # 将显示选项放在 expander 中
        with st.expander("🎨 显示选项", expanded=False):
            # 控制是否显示样本标题
            st.session_state.show_sample_name = st.checkbox(
                "显示样本标题 (Sample Name)",
                value=st.session_state.show_sample_name,
                key="show_sample_name_checkbox"
            )

            # 控制是否显示方法名称
            st.session_state.show_method_name = st.checkbox(
                "显示方法名称 (Method Name)",
                value=st.session_state.show_method_name,
                key="show_method_name_checkbox"
            )

            # 控制是否显示 text 和 descriptions
            st.session_state.show_text = st.checkbox(
                "显示样本文本 (Text)",
                value=st.session_state.show_text,
                key="show_text_checkbox"
            )

            st.session_state.show_descriptions = st.checkbox(
                "显示方法说明 (Descriptions)",
                value=st.session_state.show_descriptions,
                key="show_descriptions_checkbox"
            )

        # 将使用说明放在 expander 中
        with st.expander("📖 使用说明", expanded=False):
            st.caption("""
            1. 上传 JSON 配置文件
            2. 选择显示行数（多样本对比）
            3. 使用翻页按钮或下拉框切换样本
            4. 启用 Close View 查看图片细节
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

        st.markdown(f"### 🔍 Select Crop Area: {sample['name']}")
        st.divider()

        # Method selection for reference image
        method_names = [m["name"] for m in methods if m["name"] in sample["images"]]

        if not method_names:
            st.error("No valid images found for this sample")
            st.session_state.current_cropping_sample = None
            st.rerun()

        # Initialize reference method if not set
        if st.session_state.cropper_reference_method is None or st.session_state.cropper_reference_method not in method_names:
            st.session_state.cropper_reference_method = method_names[0]

        # Display method selection
        st.write("Select reference image:")
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

            # Display cropper
            cropped_img = st_cropper(
                reference_img,
                realtime_update=True,
                box_color='#00ff00',
                aspect_ratio=None,
                return_type='box'
            )

            # Save/Cancel buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Save Crop", use_container_width=True):
                    if cropped_img:
                        # cropped_img is the box coordinates
                        box = (int(cropped_img['left']), int(cropped_img['top']),
                               int(cropped_img['left'] + cropped_img['width']),
                               int(cropped_img['top'] + cropped_img['height']))

                        # Save crop for all methods in this sample
                        if save_crop_for_sample(sample_idx, box, samples, methods, base_dir, image_width):
                            st.success("Crop saved successfully!")
                            st.session_state.current_cropping_sample = None
                            st.session_state.cropper_reference_method = None
                            time.sleep(0.5)
                            st.rerun()
                    else:
                        st.error("Please draw a crop box first")

            with col2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.current_cropping_sample = None
                    st.session_state.cropper_reference_method = None
                    st.rerun()

        except Exception as e:
            st.error(f"Error loading reference image: {e}")
            st.session_state.current_cropping_sample = None
            st.rerun()

        st.divider()
        st.info("👆 Draw a rectangle on the image above to select the crop area")
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
            processed_img, original_ratio, was_cropped = load_and_process_image(image_path, image_width)

            if processed_img is not None:
                # 如果有crop data且close view启用，在图片上绘制绿色框
                if st.session_state.close_view_enabled and crop_data and method_name in crop_data.get('original_sizes', {}):
                    try:
                        # 加载原始图片以获取正确的尺寸
                        original_img = Image.open(image_path)
                        original_size = original_img.size
                        display_size = processed_img.size

                        # 在processed_img上绘制绿色框
                        processed_img = draw_crop_box_on_image(
                            processed_img,
                            crop_data['box'],
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
                        st.caption(data["method_name"])
                    st.image(
                        data["image"],
                        use_container_width=True
                    )

            # Display cropped images if crop exists and close view is enabled
            if st.session_state.close_view_enabled and crop_data:
                crop_cols = st.columns(len(images_data))

                for idx, (col, data) in enumerate(zip(crop_cols, images_data)):
                    with col:
                        method_name = data["method_name"]
                        if method_name in crop_data['cropped_images']:
                            cropped_img = crop_data['cropped_images'][method_name]
                            st.image(cropped_img, use_container_width=True)

            # Add Edit Crop button at the bottom if close view is enabled and button is set to show
            if st.session_state.close_view_enabled and st.session_state.show_edit_crop_button:
                button_label = "✏️ Edit Crop" if crop_data else "➕ Add Crop"

                if st.button(button_label, key=f"crop_btn_{actual_sample_idx}", use_container_width=True):
                    st.session_state.current_cropping_sample = actual_sample_idx
                    st.session_state.cropper_reference_method = None
                    st.rerun()
        else:
            st.error(f"样本 '{sample['name']}' 没有成功加载任何图片")
        
        # 显示样本的 text 字段（如果启用）
        if st.session_state.show_text and "text" in sample and sample["text"]:
            if st.session_state.show_sample_name:
                # 显示加粗的样本名称 + text
                st.markdown(f"<small><b>{sample['name']}</b> ｜ Text: {sample['text']}</small>", unsafe_allow_html=True)
            else:
                # 只显示text
                st.caption(f"Text: {sample['text']}")
        
        # 只在最后一行样本之后显示 method descriptions（如果启用）
        if row_idx == len(selected_samples) - 1 and st.session_state.show_descriptions:
            st.divider()
            st.markdown("#### 方法说明")
            method_cols = st.columns(len(methods))
            for col, method in zip(method_cols, methods):
                with col:
                    st.markdown(f"**{method['name']}**")
                    if method.get("description"):
                        st.caption(method['description'])
        
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
            with st.expander("⚠️ 宽高比警告 - 点击查看详情"):
                st.warning("检测到部分图片宽高比存在差异：")
                for sample_name, method_name, ratio in inconsistent:
                    st.write(f"- {sample_name} - {method_name}: {ratio:.3f} (宽:高 = {ratio:.2f}:1)")


if __name__ == "__main__":
    main()
