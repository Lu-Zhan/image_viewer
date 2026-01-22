import streamlit as st
from pathlib import Path
from typing import Dict, List

from config.languages import LANGUAGES


def render_sidebar(
    lang: Dict,
    samples: List[Dict],
    methods: List[Dict],
    has_masks: bool
) -> Dict:
    """
    渲染侧边栏并返回用户选择的配置
    
    返回:
        包含各项配置的字典
    """
    with st.sidebar:
        # Language toggle button
        if st.button("中/En", key="lang_toggle", help="Switch language / 切换语言", use_container_width=True):
            st.session_state.language = 'en' if st.session_state.language == 'zh' else 'zh'
            st.rerun()

        # 显示行数控制
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

        # 回调函数
        def go_prev():
            st.session_state.selected_sample_idx = max(0, st.session_state.selected_sample_idx - 1)

        def go_next():
            st.session_state.selected_sample_idx = min(max_start_idx, st.session_state.selected_sample_idx + 1)

        # 翻页按钮
        col_prev, col_next = st.columns(2)
        with col_prev:
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

        # 样本选择下拉框
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

        # Close View 选项
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

        # 显示选项 expander
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

            st.divider()
            st.markdown(f"**{lang['method_display']}**")

            # 初始化为所有方法（如果还没有初始化）
            if not st.session_state.visible_methods:
                st.session_state.visible_methods = [m["name"] for m in methods]

            # 为每个方法创建复选框
            for method in methods:
                method_name = method["name"]
                is_visible = method_name in st.session_state.visible_methods

                if st.checkbox(
                    method_name,
                    value=is_visible,
                    key=f"method_visible_{method_name}",
                    help=method.get("description", None)
                ):
                    if method_name not in st.session_state.visible_methods:
                        st.session_state.visible_methods.append(method_name)
                else:
                    if method_name in st.session_state.visible_methods:
                        st.session_state.visible_methods.remove(method_name)

            st.divider()

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
            
            # Mask controls (only show if masks are available)
            if has_masks:
                st.session_state.use_mask = st.checkbox(
                    lang['use_mask'],
                    value=st.session_state.use_mask,
                    help=lang['use_mask_help'],
                    key="use_mask_checkbox"
                )
                
                if st.session_state.use_mask:
                    st.session_state.darken_factor = st.slider(
                        lang['darken_factor_label'],
                        min_value=0.0,
                        max_value=1.0,
                        step=0.1,
                        value=st.session_state.darken_factor,
                        help=lang['darken_factor_help'],
                        key="darken_factor_slider"
                    )

        # 使用说明 expander
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
    
    return {
        'num_rows': num_rows,
    }
