# utils/helpers.py
import os
import sys
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


def _get_assets_dir():
    """获取 assets 目录路径，兼容 PyInstaller 打包环境"""
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, "assets")
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")


def _resolve_icon_path(icon_value: str) -> str:
    """解析图标路径，SVG 自动回退到 PNG（跨平台兼容）"""
    if icon_value.endswith('.svg'):
        png_path = icon_value.replace('.svg', '.png')
        if os.path.exists(os.path.join(_get_assets_dir(), png_path)):
            return png_path
    return icon_value


def create_icon_widget(icon_value: str, size: int = 16):
    """根据图标值创建对应的 Flet 控件

    统一返回固定尺寸的 Container，确保 emoji 和图片图标尺寸一致。

    Args:
        icon_value: emoji 字符串（如 "📁"）或图片路径（如 "icons/tux.svg"）
        size: 图标显示尺寸

    Returns:
        ft.Container，内容为 ft.Text（emoji）或 ft.Image（图片）
    """
    if is_image_icon(icon_value):
        resolved = _resolve_icon_path(icon_value)
        inner = ft.Image(
            src=resolved,
            width=size,
            height=size,
            fit=ft.BoxFit.CONTAIN,
        )
    else:
        inner = ft.Text(icon_value, size=size)
    return ft.Container(
        content=inner,
        width=size + 4,
        height=size + 4,
        alignment=ft.Alignment(-1, 0),
    )


def get_icon_display_text(icon_value: str) -> str:
    """获取下拉菜单等纯文本场景的图标显示文字

    对于图片图标，返回文件名（如 'git'）
    对于 emoji，原样返回
    """
    if is_image_icon(icon_value):
        basename = os.path.basename(icon_value)
        return basename.replace('.svg', '').replace('.png', '')
    return icon_value
