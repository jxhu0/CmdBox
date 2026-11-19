# services/config_service.py
import json
import os
import tempfile
import threading
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
        self._lock = threading.RLock()

    def load(self) -> bool:
        """加载配置"""
        if not self.config_file.exists():
            return False
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or not isinstance(data.get('repo_path', ''), str):
                raise ValueError('配置格式无效')
            self.config = {**self.DEFAULT_CONFIG, **data}
            for key, default in {**self.DEFAULT_CONFIG, 'latest_version': ''}.items():
                if not isinstance(self.config.get(key, default), str):
                    self.config[key] = default
        except (ValueError, TypeError):
            # 留下原文件供恢复，重新显示初始化向导。
            from shutil import copy2
            copy2(self.config_file, self.config_file.with_suffix('.json.corrupted'))
            self.config = dict(self.DEFAULT_CONFIG)
            return False
        return True

    def save(self):
        """保存配置"""
        with self._lock:
            self.config_path.mkdir(parents=True, exist_ok=True)
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.config_path,
                                                 prefix='.config-', suffix='.tmp', delete=False) as f:
                    temporary = f.name
                    json.dump(self.config, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temporary, self.config_file)
            finally:
                if temporary and os.path.exists(temporary):
                    os.unlink(temporary)

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
        with self._lock:
            previous = dict(self.config)
            self.config[key] = value
            try:
                self.save()
            except OSError:
                self.config = previous
                raise

    def update_last_sync(self):
        self.set('last_sync', datetime.now().isoformat())

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
        self.set('update_remind_until', remind_date.isoformat())

    def set_latest_version(self, version: str):
        """保存最新版本号"""
        self.set('latest_version', version)

    def get_latest_version(self) -> Optional[str]:
        """获取最新版本号"""
        return self.config.get("latest_version")

    def clear_latest_version_cache(self):
        """清除最新版本号缓存"""
        self.set('latest_version', '')
