"""
文件操作工具模块
提供常用的文件和目录操作函数
"""
import os
import glob
from pathlib import Path
from typing import List


def ensure_dir(path: str) -> None:
    """确保目录存在,不存在则创建"""
    os.makedirs(path, exist_ok=True)


def find_files(directory: str, pattern: str = "*.pdf") -> List[str]:
    """
    查找目录下匹配模式的所有文件
    
    Args:
        directory: 目录路径
        pattern: 文件名模式
        
    Returns:
        文件路径列表
    """
    search_pattern = os.path.join(directory, pattern)
    return glob.glob(search_pattern)


def get_file_size_kb(file_path: str) -> float:
    """获取文件大小(KB)"""
    return os.path.getsize(file_path) / 1024


def get_file_size_mb(file_path: str) -> float:
    """获取文件大小(MB)"""
    return os.path.getsize(file_path) / (1024 * 1024)


def read_text_file(file_path: str, encoding: str = 'utf-8') -> str:
    """读取文本文件"""
    with open(file_path, 'r', encoding=encoding) as f:
        return f.read()


def write_text_file(file_path: str, content: str, encoding: str = 'utf-8') -> None:
    """写入文本文件"""
    ensure_dir(os.path.dirname(file_path))
    with open(file_path, 'w', encoding=encoding) as f:
        f.write(content)


def file_exists(file_path: str) -> bool:
    """检查文件是否存在"""
    return os.path.exists(file_path) and os.path.isfile(file_path)


def dir_exists(dir_path: str) -> bool:
    """检查目录是否存在"""
    return os.path.exists(dir_path) and os.path.isdir(dir_path)
