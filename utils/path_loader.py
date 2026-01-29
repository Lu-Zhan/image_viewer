"""
路径列表加载器：从多个文件夹路径生成图片配置
"""
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 支持的图片文件扩展名
SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'}


def is_image_file(file_path: Path) -> bool:
    """检查文件是否为支持的图片格式"""
    return file_path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS


def scan_folder_for_images(folder_path: Path) -> List[str]:
    """
    扫描文件夹中的所有图片文件，返回相对路径列表
    
    参数:
        folder_path: 要扫描的文件夹路径
    
    返回:
        图片文件的相对路径列表（相对于 folder_path）
    """
    image_files = []
    
    if not folder_path.exists() or not folder_path.is_dir():
        return image_files
    
    # 递归遍历文件夹
    for root, dirs, files in os.walk(folder_path):
        for file in sorted(files):  # 排序以保持一致的顺序
            file_path = Path(root) / file
            if is_image_file(file_path):
                # 计算相对于 folder_path 的路径
                rel_path = file_path.relative_to(folder_path)
                image_files.append(str(rel_path))
    
    return image_files


def parse_path_list(path_list_text: str) -> List[str]:
    """
    解析路径列表文本，每行一个路径
    
    参数:
        path_list_text: 包含路径的文本，每行一个路径
    
    返回:
        路径列表
    """
    paths = []
    for line in path_list_text.strip().split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):  # 忽略空行和注释
            paths.append(line)
    return paths


def validate_path_list(paths: List[str]) -> Tuple[bool, str, List[Path]]:
    """
    验证路径列表是否有效
    
    参数:
        paths: 路径字符串列表
    
    返回:
        (是否有效, 错误信息, 解析后的 Path 对象列表)
    """
    if not paths:
        return False, "路径列表为空", []
    
    resolved_paths = []
    for path_str in paths:
        path = Path(path_str)
        
        # 如果是相对路径，转换为绝对路径
        if not path.is_absolute():
            path = Path.cwd() / path
        path = path.resolve()
        
        if not path.exists():
            return False, f"路径不存在: {path_str}", []
        
        if not path.is_dir():
            return False, f"路径不是目录: {path_str}", []
        
        resolved_paths.append(path)
    
    return True, "", resolved_paths


def generate_config_from_paths(paths: List[Path]) -> Optional[Dict]:
    """
    从路径列表生成配置
    
    每个路径作为一个 method，第一个路径用于扫描图片文件列表，
    然后假设其他路径下有相同的相对路径结构。
    
    参数:
        paths: 已验证的文件夹路径列表
    
    返回:
        配置字典，格式与 JSON 配置相同
    """
    if not paths:
        return None
    
    # 扫描第一个路径获取图片列表
    first_path = paths[0]
    image_files = scan_folder_for_images(first_path)
    
    if not image_files:
        return None
    
    # 生成 methods 列表
    methods = []
    for i, path in enumerate(paths, start=1):
        methods.append({
            "name": f"Method {i}",
            "description": f"Description {i}"
        })
    
    # 生成 samples 列表
    # 每个图片文件作为一个 sample
    samples = []
    for i, image_rel_path in enumerate(image_files, start=1):
        # 为每个图片创建一个 sample
        images = {}
        for j, path in enumerate(paths, start=1):
            method_name = f"Method {j}"
            # 存储绝对路径，这样每个 method 可以有不同的 base_dir
            full_path = path / image_rel_path
            images[method_name] = str(full_path)
        
        # 使用图片文件名（不含扩展名）作为 sample 名称
        image_name = Path(image_rel_path).stem
        
        samples.append({
            "name": image_name,
            "text": f"Text {i}",
            "images": images
        })
    
    # 对于路径列表模式，使用空字符串作为 base_dir
    # 因为 sample 的 images 中存储的是绝对路径
    config = {
        "base_dir": "",  # 空字符串表示使用绝对路径模式
        "methods": methods,
        "samples": samples
    }
    
    return config


def load_path_list_config(path_list_text: str) -> Tuple[Optional[Dict], str]:
    """
    从路径列表文本加载配置
    
    参数:
        path_list_text: 包含路径的文本，每行一个路径
    
    返回:
        (配置字典或 None, 错误信息)
    """
    # 解析路径列表
    paths = parse_path_list(path_list_text)
    
    if not paths:
        return None, "请输入至少一个有效的文件夹路径"
    
    # 验证路径
    valid, error_msg, resolved_paths = validate_path_list(paths)
    if not valid:
        return None, error_msg
    
    # 生成配置
    config = generate_config_from_paths(resolved_paths)
    
    if config is None:
        return None, "在第一个文件夹中未找到图片文件"
    
    return config, ""
