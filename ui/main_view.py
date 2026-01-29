import streamlit as st
from pathlib import Path
from PIL import Image
from typing import Dict, List

from config.constants import MAX_CROPS_PER_SAMPLE
from utils.image_processing import (
    load_and_process_image,
    check_image_exists,
    draw_all_crop_boxes_on_image,
    filter_visible_methods,
)
from utils.mask import load_mask, apply_mask_to_image
from services.crop_manager import get_crop_data, delete_crop_from_sample


def render_main_view(
    samples: List[Dict],
    methods: List[Dict],
    base_dir: Path,
    start_idx: int,
    num_rows: int,
    image_width: int,
    lang: Dict,
):
    """
    渲染主视图，显示图片网格
    """
    end_idx = min(start_idx + num_rows, len(samples))
    selected_samples = samples[start_idx:end_idx]

    # 收集所有样本的图片信息
    all_aspect_ratios = []

    for row_idx, sample in enumerate(selected_samples):
        # 收集当前样本的所有图片信息
        images_data = []
        aspect_ratios = []
        actual_sample_idx = start_idx + row_idx
        crop_data = get_crop_data(actual_sample_idx)

        # 使用过滤后的方法列表
        visible_methods_list = filter_visible_methods(
            methods, st.session_state.visible_methods
        )

        for method in visible_methods_list:
            method_name = method["name"]
            method_desc = method.get("description", "")

            if method_name not in sample["images"]:
                st.warning(f"样本 '{sample['name']}' 中缺少方法 '{method_name}' 的图片")
                continue

            image_rel_path = sample["images"][method_name]

            # 处理图片路径为None的情况（缺失的图片）
            if image_rel_path is None:
                image_path = None
            else:
                image_path = base_dir / image_rel_path

            # 加载并处理图片（如果路径为None，会生成占位符）
            processed_img, original_ratio, was_cropped = load_and_process_image(
                image_path,
                image_width,
                st.session_state.preserve_aspect_ratio,
                placeholder_text=lang.get("image_missing_placeholder", "Image Missing"),
            )

            if processed_img is not None:
                # 应用 mask（如果启用且存在，且图片路径不为None）
                if (
                    image_path is not None
                    and st.session_state.use_mask
                    and "mask" in sample
                    and sample["mask"]
                ):
                    mask_path = base_dir / sample["mask"]
                    if check_image_exists(base_dir, sample["mask"]):
                        mask_img = load_mask(mask_path, processed_img.size)
                        if mask_img is not None:
                            processed_img = apply_mask_to_image(
                                processed_img, mask_img, st.session_state.darken_factor
                            )

                # 如果有crop data且close view启用，在图片上绘制所有crop框（仅当图片路径不为None）
                if (
                    image_path is not None
                    and st.session_state.close_view_enabled
                    and crop_data
                ):
                    try:
                        # 加载原始图片以获取正确的尺寸
                        original_img = Image.open(image_path)
                        original_size = original_img.size
                        display_size = processed_img.size

                        # 获取crops列表并绘制所有框
                        crops = crop_data.get("crops", [])
                        if crops:
                            processed_img = draw_all_crop_boxes_on_image(
                                processed_img, crops, original_size, display_size
                            )
                    except Exception as e:
                        pass  # 如果绘制失败，使用原始图片

                images_data.append(
                    {
                        "method_name": method_name,
                        "description": method_desc,
                        "image": processed_img,
                        "original_ratio": original_ratio,
                        "was_cropped": was_cropped,
                        "path": image_rel_path,
                    }
                )
                aspect_ratios.append((method_name, original_ratio))
                all_aspect_ratios.append((sample["name"], method_name, original_ratio))

        # 并排显示图片
        if images_data:
            # 计算总列数
            num_cols = len(images_data)
            cols = st.columns(num_cols)

            # 渲染主图片
            for idx, (col, data) in enumerate(
                zip(cols[: len(images_data)], images_data)
            ):
                with col:
                    # 在图片上方显示方法名称（只在第一个样本显示，如果启用）
                    if st.session_state.show_method_name and row_idx == 0:
                        method_size = st.session_state.method_text_size
                        st.markdown(
                            f"<span style='font-size: {method_size}px; font-weight: bold;'>{data['method_name']}</span>",
                            unsafe_allow_html=True,
                        )
                    st.image(data["image"], use_container_width=True)

            # Display multiple cropped close views vertically
            if st.session_state.close_view_enabled and crop_data:
                crops = crop_data.get("crops", [])

                for crop_idx, crop in enumerate(crops):
                    color = crop["color"]
                    crop_id = crop["id"]

                    # Close View title with color indicator and Edit/Delete buttons if enabled
                    title_cols = st.columns([1, 5])
                    with title_cols[0]:
                        st.markdown(
                            f'<div style="margin-bottom: 5px;"><span style="display: inline-block; '
                            f"width: 14px; height: 14px; background-color: {color}; "
                            f'border: 1px solid #333; margin-right: 6px; vertical-align: middle;"></span>'
                            f'<b style="vertical-align: middle;">Close View #{crop_idx + 1}</b></div>',
                            unsafe_allow_html=True,
                        )

                    # Only show Edit/Delete buttons if show_edit_crop_button is enabled
                    if st.session_state.show_edit_crop_button:
                        with title_cols[1]:
                            button_cols = st.columns([1, 1, 4])
                            with button_cols[0]:
                                if st.button(
                                    lang["edit_crop"],
                                    key=f"edit_crop_{actual_sample_idx}_{crop_id}",
                                    use_container_width=True,
                                ):
                                    st.session_state.current_cropping_sample = (
                                        actual_sample_idx
                                    )
                                    st.session_state.current_editing_crop_id = crop_id
                                    st.session_state.cropper_reference_method = None
                                    st.rerun()

                            with button_cols[1]:
                                if st.button(
                                    lang["delete_crop"],
                                    key=f"delete_crop_{actual_sample_idx}_{crop_id}",
                                    use_container_width=True,
                                ):
                                    delete_crop_from_sample(actual_sample_idx, crop_id)
                                    st.rerun()

                    # Cropped images in columns (保持与主显示相同的列数)
                    crop_cols = st.columns(num_cols)
                    for col_idx, (col, data) in enumerate(
                        zip(crop_cols[: len(images_data)], images_data)
                    ):
                        with col:
                            method_name = data["method_name"]
                            if method_name in crop["cropped_images"]:
                                cropped_img = crop["cropped_images"][method_name]
                                st.image(cropped_img, use_container_width=True)

            # Add Crop button at the bottom if close view is enabled and button is set to show
            if (
                st.session_state.close_view_enabled
                and st.session_state.show_edit_crop_button
            ):
                # Check if max crops reached
                crops = crop_data.get("crops", []) if crop_data else []
                num_crops = len(crops)

                if num_crops < MAX_CROPS_PER_SAMPLE:
                    if st.button(
                        lang["add_crop"],
                        key=f"add_crop_btn_{actual_sample_idx}",
                        use_container_width=True,
                    ):
                        st.session_state.current_cropping_sample = actual_sample_idx
                        st.session_state.current_editing_crop_id = (
                            None  # None means new crop
                        )
                        st.session_state.cropper_reference_method = None
                        st.rerun()
                else:
                    st.info(lang["max_crops_msg"].format(n=MAX_CROPS_PER_SAMPLE))
        else:
            if st.session_state.language == "zh":
                st.error(f"样本 '{sample['name']}' 没有成功加载任何图片")
            else:
                st.error(f"Sample '{sample['name']}' failed to load any images")

        # 显示样本的 text 字段（如果启用）
        if st.session_state.show_text and "text" in sample and sample["text"]:
            text_label = "文本:" if st.session_state.language == "zh" else "Text:"
            text_size = st.session_state.text_size
            if st.session_state.show_sample_name:
                # 显示加粗的样本名称 + text
                st.markdown(
                    f"<span style='font-size: {text_size}px;'><b>{sample['name']}</b> ｜ {text_label} {sample['text']}</span>",
                    unsafe_allow_html=True,
                )
            else:
                # 只显示text
                st.markdown(
                    f"<span style='font-size: {text_size}px;'>{text_label} {sample['text']}</span>",
                    unsafe_allow_html=True,
                )

        # 只在最后一行样本之后显示 method descriptions（如果启用）
        if row_idx == len(selected_samples) - 1 and st.session_state.show_descriptions:
            st.divider()
            method_size = st.session_state.method_text_size
            st.markdown(
                f"<span style='font-size: {method_size + 2}px; font-weight: bold;'>{lang['method_desc_title']}</span>",
                unsafe_allow_html=True,
            )

            # 计算列数（使用过滤后的方法）
            visible_methods_desc = filter_visible_methods(
                methods, st.session_state.visible_methods
            )
            num_desc_cols = len(visible_methods_desc)
            method_cols = st.columns(num_desc_cols)

            # 显示 methods 描述
            for col, method in zip(method_cols, visible_methods_desc):
                with col:
                    st.markdown(
                        f"<span style='font-size: {method_size}px; font-weight: bold;'>{method['name']}</span>",
                        unsafe_allow_html=True,
                    )
                    if method.get("description"):
                        st.markdown(
                            f"<span style='font-size: {method_size - 2}px; color: gray;'>{method['description']}</span>",
                            unsafe_allow_html=True,
                        )

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
            with st.expander(lang["aspect_ratio_warning"]):
                st.warning(lang["aspect_ratio_msg"])
                for sample_name, method_name, ratio in inconsistent:
                    st.write(
                        f"- {sample_name} - {method_name}: {ratio:.3f} (宽:高 = {ratio:.2f}:1)"
                    )
