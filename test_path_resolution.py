#!/usr/bin/env python3
"""测试路径解析逻辑，验证相对路径和绝对路径在不同操作系统上的处理"""

from pathlib import Path
import os


def test_path_resolution():
    """测试路径解析功能"""
    print("=" * 60)
    print("路径解析测试")
    print("=" * 60)

    # 测试用例
    test_cases = [
        "./sample_data",           # 相对路径（当前目录）
        "../sample_data",          # 相对路径（上级目录）
        "sample_data",             # 相对路径（无前缀）
        "/absolute/path/data",     # 绝对路径（Unix风格）
    ]

    print(f"\n当前工作目录: {Path.cwd()}")
    print(f"操作系统: {os.name}")
    print()

    for test_path in test_cases:
        print(f"测试路径: '{test_path}'")
        base_dir = Path(test_path)
        print(f"  - 是否为绝对路径: {base_dir.is_absolute()}")

        # 如果是相对路径，转换为绝对路径
        if not base_dir.is_absolute():
            base_dir = Path.cwd() / base_dir
            print(f"  - 相对于 cwd 的路径: {base_dir}")

        # 解析路径（处理 . 和 .. 符号）
        resolved = base_dir.resolve()
        print(f"  - 解析后的绝对路径: {resolved}")
        print(f"  - 字符串表示: {str(resolved)}")
        print()

    # 测试实际的 sample.json 中的路径
    print("=" * 60)
    print("测试 sample.json 中的实际路径")
    print("=" * 60)
    sample_base_dir = "./sample_data"
    print(f"JSON 中的 base_dir: '{sample_base_dir}'")

    base_dir = Path(sample_base_dir)
    if not base_dir.is_absolute():
        base_dir = Path.cwd() / base_dir
    base_dir = base_dir.resolve()

    print(f"解析后的绝对路径: {base_dir}")
    print(f"路径是否存在: {base_dir.exists()}")
    if base_dir.exists():
        print(f"是否为目录: {base_dir.is_dir()}")
    print()


if __name__ == "__main__":
    test_path_resolution()
