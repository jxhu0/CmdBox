# utils/helpers.py
import os
from datetime import datetime

import flet as ft


def format_datetime(iso_str: str) -> str:
    """格式化 ISO 时间为可读格式"""
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso_str


def truncate_text(text: str, max_len: int = 50) -> str:
    """截断文本"""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def is_image_icon(icon_value: str) -> bool:
    """判断图标值是否为图片路径（以 icons/ 开头）"""
    return isinstance(icon_value, str) and icon_value.startswith("icons/")


def create_icon_widget(icon_value: str, size: int = 16):
    """根据图标值创建对应的 Flet 控件

    Args:
        icon_value: emoji 字符串（如 "📁"）或图片路径（如 "icons/tux.svg"）
        size: 图标显示尺寸

    Returns:
        ft.Text（emoji）或 ft.Image（图片）
    """
    if is_image_icon(icon_value):
        return ft.Image(
            src=icon_value,
            width=size,
            height=size,
            fit=ft.BoxFit.CONTAIN,
        )
    return ft.Text(icon_value, size=size)


def get_icon_display_text(icon_value: str) -> str:
    """获取下拉菜单等纯文本场景的图标显示文字

    对于图片图标，返回文件名（如 'git'）
    对于 emoji，原样返回
    """
    if is_image_icon(icon_value):
        basename = os.path.basename(icon_value)
        return basename.replace('.svg', '').replace('.png', '')
    return icon_value
