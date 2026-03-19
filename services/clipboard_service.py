# services/clipboard_service.py
import pyperclip


class ClipboardService:
    """剪贴板服务"""

    @staticmethod
    def copy(text: str) -> bool:
        """复制文本到剪贴板"""
        try:
            pyperclip.copy(text)
            return True
        except Exception:
            return False

    @staticmethod
    def paste() -> str:
        """从剪贴板获取文本"""
        try:
            return pyperclip.paste()
        except Exception:
            return ""
