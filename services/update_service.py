# services/update_service.py
import requests
from typing import Optional, Tuple

__version__ = "1.0.0"

GITHUB_REPO = "jxhu0/CmdBox"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


class UpdateService:
    """检查更新的服务"""

    @staticmethod
    def check_for_updates() -> Tuple[bool, Optional[str], Optional[str]]:
        """检查是否有新版本

        Returns:
            Tuple[有新版本, 最新版本号, 更新说明]
            - (False, None, None) 表示无新版本或检查失败
            - (True, "v1.1.0", "更新内容...") 表示有新版本
        """
        try:
            response = requests.get(API_URL, timeout=5)
            if response.status_code != 200:
                return False, None, None

            data = response.json()
            latest_version = data.get("tag_name", "")
            release_notes = data.get("body", "")

            # 去除 tag_name 的 'v' 前缀进行比较
            latest_ver = latest_version.lstrip("v")
            current_ver = __version__

            if latest_ver != current_ver:
                return True, latest_version, release_notes
            return False, None, None
        except Exception:
            return False, None, None
