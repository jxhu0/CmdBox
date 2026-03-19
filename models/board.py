# models/board.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class Board:
    """板块数据模型"""
    id: str
    name: str
    icon: str = "📁"
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @classmethod
    def create(cls, name: str, icon: str = "📁", description: str = "") -> "Board":
        """创建新板块"""
        now = datetime.now().isoformat()
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            icon=icon,
            description=description,
            created_at=now,
            updated_at=now
        )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Board":
        """从字典创建"""
        return cls(
            id=data["id"],
            name=data["name"],
            icon=data.get("icon", "📁"),
            description=data.get("description", ""),
            created_at=data["created_at"],
            updated_at=data["updated_at"]
        )

    def update(self, name: Optional[str] = None, icon: Optional[str] = None, description: Optional[str] = None):
        """更新板块信息"""
        if name is not None:
            self.name = name
        if icon is not None:
            self.icon = icon
        if description is not None:
            self.description = description
        self.updated_at = datetime.now().isoformat()
