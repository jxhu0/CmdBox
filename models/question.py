# models/question.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class Question:
    """问题数据模型"""
    id: str
    title: str
    description: str = ""
    answer: str = ""
    priority: str = "medium"  # high / medium / low
    asked: bool = False
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def create(
        cls,
        title: str,
        description: str = "",
        answer: str = "",
        priority: str = "medium"
    ) -> "Question":
        """创建新问题"""
        now = datetime.now().isoformat()
        return cls(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            answer=answer,
            priority=priority,
            asked=False,
            created_at=now,
            updated_at=now
        )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "answer": self.answer,
            "priority": self.priority,
            "asked": self.asked,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Question":
        """从字典创建"""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            answer=data.get("answer", ""),
            priority=data.get("priority", "medium"),
            asked=data.get("asked", False),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", "")
        )

    def update(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        answer: Optional[str] = None,
        priority: Optional[str] = None,
        asked: Optional[bool] = None
    ):
        """更新问题信息"""
        if title is not None:
            self.title = title
        if description is not None:
            self.description = description
        if answer is not None:
            self.answer = answer
        if priority is not None:
            self.priority = priority
        if asked is not None:
            self.asked = asked
        self.updated_at = datetime.now().isoformat()
