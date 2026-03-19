# utils/helpers.py
from datetime import datetime


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
