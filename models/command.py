# models/command.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
import uuid


@dataclass
class Command:
    """指令数据模型"""
    id: str
    board_id: str
    title: str
    content: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    is_favorite: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @classmethod
    def create(
        cls,
        board_id: str,
        title: str,
        content: str,
        description: str = "",
        tags: List[str] = None,
        is_favorite: bool = False
    ) -> "Command":
        """创建新指令"""
        now = datetime.now().isoformat()
        return cls(
            id=str(uuid.uuid4()),
            board_id=board_id,
            title=title,
            content=content,
            description=description,
            tags=tags or [],
            is_favorite=is_favorite,
            created_at=now,
            updated_at=now
        )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "board_id": self.board_id,
            "title": self.title,
            "content": self.content,
            "description": self.description,
            "tags": self.tags,
            "is_favorite": self.is_favorite,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Command":
        """从字典创建"""
        return cls(
            id=data["id"],
            board_id=data["board_id"],
            title=data["title"],
            content=data["content"],
            description=data.get("description", ""),
            tags=data.get("tags", []),
            is_favorite=data.get("is_favorite", False),
            created_at=data["created_at"],
            updated_at=data["updated_at"]
        )

    def update(
        self,
        title: Optional[str] = None,
        content: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_favorite: Optional[bool] = None,
        board_id: Optional[str] = None
    ):
        """更新指令信息"""
        if title is not None:
            self.title = title
        if content is not None:
            self.content = content
        if description is not None:
            self.description = description
        if tags is not None:
            self.tags = tags
        if is_favorite is not None:
            self.is_favorite = is_favorite
        if board_id is not None:
            self.board_id = board_id
        self.updated_at = datetime.now().isoformat()
