# services/config_service.py
import json
from pathlib import Path
from typing import Optional
from datetime import datetime


class ConfigService:
    """配置服务"""

    DEFAULT_CONFIG = {
        "repo_path": "",
        "theme": "light",
        "last_sync": "",
        "update_remind_until": ""
    }

    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config_file = self.config_path / "config.json"
        self.config: dict = {}

    def load(self) -> bool:
        """加载配置"""
        if not self.config_file.exists():
            return False
        with open(self.config_file, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        return True

    def save(self):
        """保存配置"""
        self.config_path.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def init(self, repo_path: str):
        """初始化配置"""
        self.config = {
            "repo_path": repo_path,
            "theme": "light",
            "last_sync": "",
            "update_remind_until": ""
        }
        self.save()

    def get(self, key: str, default=None):
        return self.config.get(key, default)

    def set(self, key: str, value):
        self.config[key] = value
        self.save()

    def update_last_sync(self):
        self.config["last_sync"] = datetime.now().isoformat()
        self.save()

    def is_initialized(self) -> bool:
        return bool(self.config.get("repo_path"))

    def is_in_update_remind_period(self) -> bool:
        """检查是否在更新提醒期内"""
        remind_until = self.config.get("update_remind_until", "")
        if not remind_until:
            return False
        try:
            remind_date = datetime.fromisoformat(remind_until)
            return datetime.now() < remind_date
        except (ValueError, TypeError):
            return False

    def set_update_remind_until(self):
        """设置暂不提醒，截止时间为7天后"""
        from datetime import timedelta
        remind_date = datetime.now() + timedelta(days=7)
        self.config["update_remind_until"] = remind_date.isoformat()
        self.save()

    def set_latest_version(self, version: str):
        """保存最新版本号"""
        self.config["latest_version"] = version
        self.save()

    def get_latest_version(self) -> Optional[str]:
        """获取最新版本号"""
        return self.config.get("latest_version")

    def clear_latest_version_cache(self):
        """清除最新版本号缓存"""
        self.config["latest_version"] = ""
        self.save()
