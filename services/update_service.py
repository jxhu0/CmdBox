# services/update_service.py
import requests
import re
from typing import Optional, Tuple

GITHUB_REPO = "jxhu0/CmdBox"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


class UpdateService:
    """检查更新的服务"""

    @staticmethod
    def is_newer_version(candidate: str, current: str) -> bool:
        """按数字比较发布版本；忽略未知格式和预发布版本。"""
        def parse(version):
            match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)(?:\+[0-9A-Za-z.-]+)?", version or "")
            return tuple(map(int, match.groups())) if match else None

        candidate_parts, current_parts = parse(candidate), parse(current)
        return (candidate_parts is not None and current_parts is not None
                and candidate_parts > current_parts)

    @staticmethod
    def check_for_updates(current_version: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """检查是否有新版本

        Args:
            current_version: 当前版本号，如 "1.0.0"

        Returns:
            Tuple[有新版本, 最新版本号, 更新说明]
            - (False, "v1.1.0", "") 表示无新版本（但会返回最新版本号）
            - (True, "v1.1.0", "更新内容...") 表示有新版本
            - (False, None, None) 表示检查失败
        """
        try:
            response = requests.get(API_URL, timeout=5)
            if response.status_code != 200:
                return False, None, None

            data = response.json()
            latest_version = data.get("tag_name", "")
            release_notes = data.get("body", "")

            if (not data.get('draft') and not data.get('prerelease')
                    and UpdateService.is_newer_version(latest_version, current_version)):
                return True, latest_version, release_notes
            return False, latest_version, release_notes
        except Exception:
            return False, None, None
