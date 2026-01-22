import json
import streamlit as st
from pathlib import Path
from typing import Dict, Optional


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

        # 解析 base_dir 路径，将相对路径转换为绝对路径
        # 这样在 Windows 和 Mac 上都能正确工作
        base_dir = Path(config["base_dir"])
        if not base_dir.is_absolute():
            # 相对于当前工作目录解析
            base_dir = Path.cwd() / base_dir
        # 解析路径，处理 . 和 .. 等符号
        base_dir = base_dir.resolve()
        # 更新配置中的 base_dir 为绝对路径字符串
        config["base_dir"] = str(base_dir)
        
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
