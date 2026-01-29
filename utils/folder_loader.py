import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple


# 支持的图片格式
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


def parse_folder_list(folder_text: str) -> List[Path]:
    """
    解析文件夹列表文本，返回路径列表

    Args:
        folder_text: 多行文本，每行一个文件夹路径

    Returns:
        文件夹路径列表（Path对象）
    """
    lines = folder_text.strip().split("\n")
    folders = []

    for line in lines:
        line = line.strip()
        if not line:  # 跳过空行
            continue

        folder_path = Path(line)

        # 如果是相对路径，转换为绝对路径
        if not folder_path.is_absolute():
            folder_path = Path.cwd() / folder_path

        # 解析路径（处理 . 和 .. 等符号）
        folder_path = folder_path.resolve()
        folders.append(folder_path)

    return folders


def scan_images_in_folder(folder: Path) -> List[Path]:
    """
    扫描文件夹中的所有图片文件（递归）

    Args:
        folder: 文件夹路径

    Returns:
        图片文件相对于folder的相对路径列表
    """
    images = []

    if not folder.exists() or not folder.is_dir():
        return images

    # 递归遍历文件夹
    for root, dirs, files in os.walk(folder):
        root_path = Path(root)
        for file in files:
            file_path = root_path / file

            # 检查文件扩展名
            if file_path.suffix.lower() in IMAGE_EXTENSIONS:
                # 计算相对路径
                relative_path = file_path.relative_to(folder)
                images.append(relative_path)

    # 按路径排序
    images.sort()
    return images


def find_common_parent(folders: List[Path]) -> Path:
    """
    找到所有文件夹的公共父目录

    Args:
        folders: 文件夹路径列表

    Returns:
        公共父目录路径
    """
    if not folders:
        return Path.cwd()

    if len(folders) == 1:
        return folders[0].parent

    # 获取所有路径的parts
    all_parts = [folder.parts for folder in folders]

    # 找到最短路径的长度
    min_length = min(len(parts) for parts in all_parts)

    # 找到公共前缀
    common_parts = []
    for i in range(min_length):
        part = all_parts[0][i]
        if all(parts[i] == part for parts in all_parts):
            common_parts.append(part)
        else:
            break

    if not common_parts:
        # 如果没有公共路径，返回根目录
        return Path(folders[0].anchor)

    return Path(*common_parts)


def build_config_from_folders(folders: List[Path]) -> Tuple[Optional[Dict], Dict]:
    """
    根据文件夹列表生成配置字典

    Args:
        folders: 文件夹路径列表

    Returns:
        (config_dict, stats_dict)
        - config_dict: 配置字典，如果出错则返回None
        - stats_dict: 统计信息字典 {
            'num_methods': int,
            'num_samples': int,
            'num_missing': int,
            'errors': List[str]
          }
    """
    stats = {"num_methods": 0, "num_samples": 0, "num_missing": 0, "errors": []}

    # 验证输入
    if not folders:
        stats["errors"].append("error_no_folders")
        return None, stats

    # 检查文件夹是否存在
    for folder in folders:
        if not folder.exists():
            stats["errors"].append(f"error_folder_not_exist|{folder}")
            return None, stats
        if not folder.is_dir():
            stats["errors"].append(f"error_folder_not_exist|{folder}")
            return None, stats

    # 找到公共父目录作为 base_dir
    base_dir = find_common_parent(folders)

    # 构建 methods 列表
    methods = []
    for folder in folders:
        method_name = folder.name  # 使用文件夹basename作为method名称
        methods.append({"name": method_name, "description": ""})
    stats["num_methods"] = len(methods)

    # 从第一个文件夹扫描图片
    reference_folder = folders[0]
    image_files = scan_images_in_folder(reference_folder)

    if not image_files:
        stats["errors"].append(f"error_no_images_in_folder|{reference_folder}")
        return None, stats

    stats["num_samples"] = len(image_files)

    # 构建 samples 列表
    samples = []
    for image_rel_path in image_files:
        # Sample 名称 = 文件名（不含扩展名）
        sample_name = image_rel_path.stem

        # 构建 images 字典
        images_dict = {}
        for folder in folders:
            method_name = folder.name
            image_abs_path = folder / image_rel_path

            if image_abs_path.exists():
                # 计算相对于base_dir的路径
                try:
                    relative_to_base = image_abs_path.relative_to(base_dir)
                    images_dict[method_name] = str(relative_to_base)
                except ValueError:
                    # 如果无法计算相对路径，使用绝对路径
                    images_dict[method_name] = str(image_abs_path)
            else:
                # 图片不存在，标记为None
                images_dict[method_name] = None
                stats["num_missing"] += 1

        samples.append({"name": sample_name, "text": "", "images": images_dict})

    # 构建最终配置
    config = {"base_dir": str(base_dir), "methods": methods, "samples": samples}

    return config, stats
