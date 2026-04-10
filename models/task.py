# models/task.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class Task:
    """任务数据模型"""
    id: str
    title: str
    description: str = ""
    priority: str = "medium"  # high / medium / low
    completed: bool = False
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def create(
        cls,
        title: str,
        description: str = "",
        priority: str = "medium"
    ) -> "Task":
        """创建新任务"""
        now = datetime.now().isoformat()
        return cls(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            priority=priority,
            completed=False,
            created_at=now,
            updated_at=now
        )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "completed": self.completed,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """从字典创建"""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            priority=data.get("priority", "medium"),
            completed=data.get("completed", False),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", "")
        )

    def update(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        completed: Optional[bool] = None
    ):
        """更新任务信息"""
        if title is not None:
            self.title = title
        if description is not None:
            self.description = description
        if priority is not None:
            self.priority = priority
        if completed is not None:
            self.completed = completed
        self.updated_at = datetime.now().isoformat()
