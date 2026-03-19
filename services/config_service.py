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
        "last_sync": ""
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
            "last_sync": ""
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
