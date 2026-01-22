import streamlit as st


def apply_custom_styles():
    """应用自定义 CSS 样式"""
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
