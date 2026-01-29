import streamlit as st
import json
from pathlib import Path

from config.languages import LANGUAGES
from utils.json_loader import load_json_config
from utils.folder_loader import parse_folder_list, build_config_from_folders
from utils.mask import check_masks_available
from services.crop_manager import migrate_crop_data_if_needed
from services.pdf_export import generate_pdf_from_current_view
from ui.styles import apply_custom_styles
from ui.sidebar import render_sidebar
from ui.main_view import render_main_view
from ui.crop_editor import render_crop_editor


def main():
    # Initialize language in session state BEFORE set_page_config
    if "language" not in st.session_state:
        st.session_state.language = "zh"  # Default to Chinese

    lang = LANGUAGES[st.session_state.language]

    st.set_page_config(page_title=lang["page_title"], page_icon="🖼️", layout="wide")

    # 初始化 session state
    if "selected_sample_idx" not in st.session_state:
        st.session_state.selected_sample_idx = 0
    if "show_text" not in st.session_state:
        st.session_state.show_text = True
    if "show_descriptions" not in st.session_state:
        st.session_state.show_descriptions = False
    if "show_sample_name" not in st.session_state:
        st.session_state.show_sample_name = True
    if "show_method_name" not in st.session_state:
        st.session_state.show_method_name = True
    if "visible_methods" not in st.session_state:
        st.session_state.visible_methods = []

    # Input mode session state
    if "input_mode" not in st.session_state:
        st.session_state.input_mode = "json"  # 默认使用JSON模式

    # Close view session state
    if "close_view_enabled" not in st.session_state:
        st.session_state.close_view_enabled = False
    if "show_edit_crop_button" not in st.session_state:
        st.session_state.show_edit_crop_button = True
    if "crop_data" not in st.session_state:
        st.session_state.crop_data = {}
    if "current_cropping_sample" not in st.session_state:
        st.session_state.current_cropping_sample = None
    if "cropper_reference_method" not in st.session_state:
        st.session_state.cropper_reference_method = None
    if "current_editing_crop_id" not in st.session_state:
        st.session_state.current_editing_crop_id = None
    if "next_crop_id_counter" not in st.session_state:
        st.session_state.next_crop_id_counter = 0
    if "config_hash" not in st.session_state:
        st.session_state.config_hash = None
    if "text_size" not in st.session_state:
        st.session_state.text_size = 16
    if "method_text_size" not in st.session_state:
        st.session_state.method_text_size = 18
    if "preserve_aspect_ratio" not in st.session_state:
        st.session_state.preserve_aspect_ratio = True

    # Mask session state
    if "use_mask" not in st.session_state:
        st.session_state.use_mask = False
    if "darken_factor" not in st.session_state:
        st.session_state.darken_factor = 1.0

    # 迁移旧的crop数据格式到新格式
    migrate_crop_data_if_needed()

    # 固定图片宽度
    image_width = 800

    # 侧边栏：文件上传（在没有config之前先显示）
    with st.sidebar:
        # Language toggle button
        if st.button(
            "中/En",
            key="lang_toggle_init",
            help="Switch language / 切换语言",
            use_container_width=True,
        ):
            st.session_state.language = (
                "en" if st.session_state.language == "zh" else "zh"
            )
            st.rerun()

        # 输入模式选择
        input_mode = st.radio(
            lang["input_mode_label"],
            options=["json", "folders"],
            format_func=lambda x: lang["input_mode_json"]
            if x == "json"
            else lang["input_mode_folders"],
            key="input_mode",
            horizontal=True,
        )

        # 根据输入模式显示不同的输入控件
        uploaded_file = None
        folder_text = None

        if st.session_state.input_mode == "json":
            # JSON 文件上传
            uploaded_file = st.file_uploader(
                lang["upload_label"], type=["json"], help=lang["upload_help"]
            )
        else:
            # 文件夹列表输入
            folder_text = st.text_area(
                lang["folder_list_label"],
                height=150,
                help=lang["folder_list_help"],
                placeholder=lang["folder_list_placeholder"],
            )

    # 主界面 - 未输入时显示提示
    has_input = (
        st.session_state.input_mode == "json" and uploaded_file is not None
    ) or (
        st.session_state.input_mode == "folders" and folder_text and folder_text.strip()
    )

    if not has_input:
        st.title(lang["sidebar_title"])

        if st.session_state.input_mode == "json":
            st.info(lang["no_file_msg"])
            # 显示示例 JSON 格式
            with st.expander(lang["json_example_title"]):
                st.code(
                    """{
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
}""",
                    language="json",
                )
        else:
            st.info(lang["no_folder_msg"])
            # 显示文件夹列表示例
            with st.expander(lang["folder_example_title"]):
                st.code(
                    """./images/method_A
./images/method_B
./images/method_C

# 或使用绝对路径：
/Users/username/project/results/baseline
/Users/username/project/results/improved""",
                    language="bash",
                )
                st.markdown("---")
                st.markdown("**说明 / Instructions:**")
                st.markdown(
                    "- "
                    + (
                        "每个文件夹代表一个方法"
                        if st.session_state.language == "zh"
                        else "Each folder represents a method"
                    )
                )
                st.markdown(
                    "- "
                    + (
                        "文件夹名即为方法名"
                        if st.session_state.language == "zh"
                        else "Folder name is the method name"
                    )
                )
                st.markdown(
                    "- "
                    + (
                        "从第一个文件夹扫描所有图片"
                        if st.session_state.language == "zh"
                        else "Scan all images from the first folder"
                    )
                )
                st.markdown(
                    "- "
                    + (
                        "其他文件夹使用相同相对路径查找对应图片"
                        if st.session_state.language == "zh"
                        else "Other folders use the same relative paths to find images"
                    )
                )
        return

    # 加载配置
    config = None
    stats = None

    if st.session_state.input_mode == "json":
        # JSON 模式
        config = load_json_config(uploaded_file)
        if config is None:
            return
    else:
        # Folder List 模式
        if not folder_text or not folder_text.strip():
            st.error(lang["error_no_folders"])
            return

        try:
            folders = parse_folder_list(folder_text)
            config, stats = build_config_from_folders(folders)

            # 处理错误
            if config is None and stats and stats.get("errors"):
                for error in stats["errors"]:
                    if error == "error_no_folders":
                        st.error(lang["error_no_folders"])
                    elif error.startswith("error_folder_not_exist|"):
                        folder_path = error.split("|", 1)[1]
                        st.error(f"{lang['error_folder_not_exist']}: {folder_path}")
                    elif error.startswith("error_no_images_in_folder|"):
                        folder_path = error.split("|", 1)[1]
                        st.error(f"{lang['error_no_images_in_folder']}: {folder_path}")
                return
        except Exception as e:
            st.error(f"Error parsing folder list: {e}")
            return

    if config is None:
        return

    base_dir = Path(config["base_dir"])
    methods = config["methods"]
    samples = config["samples"]

    # 显示加载摘要（仅Folder List模式）
    if st.session_state.input_mode == "folders" and stats:
        with st.sidebar:
            st.markdown("---")
            with st.expander(lang["loading_summary_title"], expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(lang["num_methods_label"], stats["num_methods"])
                    st.metric(lang["num_samples_label"], stats["num_samples"])
                with col2:
                    if stats["num_missing"] > 0:
                        st.metric(
                            lang["num_missing_label"],
                            stats["num_missing"],
                            delta=None,
                            delta_color="off",
                        )
                    else:
                        st.metric(lang["num_missing_label"], "0 ✓")

    # Check if any sample has mask images available
    has_masks = check_masks_available(samples, base_dir)

    # Check if config has changed (clear crops if new config)
    current_config_hash = hash(json.dumps(config, sort_keys=True))
    if st.session_state.config_hash != current_config_hash:
        st.session_state.config_hash = current_config_hash
        st.session_state.crop_data = {}
        st.session_state.current_cropping_sample = None

    # 渲染侧边栏（返回用户配置）
    sidebar_config = render_sidebar(
        lang=lang, samples=samples, methods=methods, has_masks=has_masks
    )
    num_rows = sidebar_config["num_rows"]

    # 应用自定义样式
    apply_custom_styles()

    # 右上角添加保存PDF按钮
    header_col1, header_col2 = st.columns([0.9, 0.1])
    with header_col2:
        # 检查是否正在编辑crop
        is_editing_crop = st.session_state.current_cropping_sample is not None

        if is_editing_crop:
            # 正在编辑时禁用按钮
            st.button(
                "📥 Export",
                disabled=True,
                help=lang["save_pdf_disabled_tooltip"],
                key="save_pdf_btn",
            )
        else:
            # 生成PDF
            try:
                pdf_bytes = generate_pdf_from_current_view(
                    samples=samples,
                    methods=methods,
                    base_dir=base_dir,
                    start_idx=st.session_state.selected_sample_idx,
                    num_rows=num_rows,
                    show_method_name=st.session_state.show_method_name,
                    show_text=st.session_state.show_text,
                    show_sample_name=st.session_state.show_sample_name,
                    show_descriptions=st.session_state.show_descriptions,
                    close_view_enabled=st.session_state.close_view_enabled,
                    crop_data=st.session_state.crop_data,
                    preserve_aspect_ratio=st.session_state.preserve_aspect_ratio,
                    lang=lang,
                    use_mask=st.session_state.use_mask,
                    darken_factor=st.session_state.darken_factor,
                    image_width=image_width,
                    visible_methods=st.session_state.visible_methods,
                )

                # 生成文件名
                sample_name = (
                    samples[st.session_state.selected_sample_idx]["name"]
                    if samples
                    else "export"
                )
                safe_name = "".join(
                    c for c in sample_name if c.isalnum() or c in (" ", "-", "_")
                ).strip()
                filename = f"{lang['save_pdf_filename']}_{safe_name}.pdf"

                st.download_button(
                    label="📥 Export",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                    help=lang["save_pdf_tooltip"],
                    key="save_pdf_btn",
                )
            except Exception as e:
                st.button(
                    "📥", disabled=True, help=f"Error: {str(e)}", key="save_pdf_btn"
                )

    # Crop 编辑界面
    if st.session_state.current_cropping_sample is not None:
        render_crop_editor(
            samples=samples,
            methods=methods,
            base_dir=base_dir,
            image_width=image_width,
            lang=lang,
        )

    # 主视图
    render_main_view(
        samples=samples,
        methods=methods,
        base_dir=base_dir,
        start_idx=st.session_state.selected_sample_idx,
        num_rows=num_rows,
        image_width=image_width,
        lang=lang,
    )


if __name__ == "__main__":
    main()
