import streamlit as st
from streamlit_cropper import st_cropper
from pathlib import Path
from PIL import Image
import time
from typing import Dict, List

from utils.image_processing import check_image_exists, apply_crop_to_image
from utils.mask import load_mask, apply_mask_to_image
from services.crop_manager import (
    get_crop_data,
    get_crop_by_id,
    get_next_crop_color,
    save_crop_for_sample,
)


def render_crop_editor(
    samples: List[Dict],
    methods: List[Dict],
    base_dir: Path,
    image_width: int,
    lang: Dict,
):
    """
    渲染 Crop 编辑器界面
    
    当 st.session_state.current_cropping_sample 不为 None 时调用
    """
    sample_idx = st.session_state.current_cropping_sample
    sample = samples[sample_idx]

    # Determine if adding new crop or editing existing
    is_editing = st.session_state.current_editing_crop_id is not None
    crop_id = ""
    crop_color = ""

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
    # 收集可用的方法名称
    all_method_names = [m["name"] for m in methods if m["name"] in sample["images"]]
    
    def get_image_path(rel_path):
        """Helper to handle both absolute and relative paths"""
        if Path(rel_path).is_absolute():
            return Path(rel_path)
        return base_dir / rel_path
    
    def image_exists(rel_path):
        """Helper to check if image exists for both path types"""
        path = get_image_path(rel_path)
        return path.exists() and path.is_file()
    
    method_names = [
        name for name in all_method_names
        if image_exists(sample["images"][name])
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
    selected_idx = st.radio(
        "Method",
        range(len(method_names)),
        index=method_names.index(st.session_state.cropper_reference_method),
        format_func=lambda i: method_names[i],
        horizontal=True,
        label_visibility="collapsed"
    )
    selected_method = method_names[selected_idx]
    st.session_state.cropper_reference_method = selected_method

    # Load reference image
    try:
        image_rel_path = sample["images"][selected_method]
        image_path = get_image_path(image_rel_path)
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
            
            # Apply mask to reference image in cropper if enabled
            if st.session_state.use_mask and "mask" in sample and sample["mask"]:
                mask_path = get_image_path(sample["mask"])
                if mask_path.exists() and mask_path.is_file():
                    mask_img = load_mask(mask_path, display_ref_img.size)
                    if mask_img is not None:
                        display_ref_img = apply_mask_to_image(display_ref_img, mask_img, st.session_state.darken_factor)

            # Display cropper with crop's color
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
                
                # Apply mask to preview if enabled
                if st.session_state.use_mask and "mask" in sample and sample["mask"]:
                    mask_path = get_image_path(sample["mask"])
                    if mask_path.exists() and mask_path.is_file():
                        mask_img = load_mask(mask_path, preview_img.size)
                        if mask_img is not None:
                            preview_img = apply_mask_to_image(preview_img, mask_img, st.session_state.darken_factor)
                
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
                    if save_crop_for_sample(sample_idx, box, samples, methods, base_dir, image_width, crop_id, crop_color, st.session_state.visible_methods):
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
