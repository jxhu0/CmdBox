# services/data_service.py
import json
import os
import shutil
from typing import List, Optional
from pathlib import Path
from datetime import datetime
from models.board import Board
from models.command import Command


class DataService:
    """数据读写服务"""

    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        self.data_file = self.data_path / "data.json"
        self.backup_dir = self.data_path / "backups"
        self.boards: List[Board] = []
        self.commands: List[Command] = []

    def load(self):
        """从文件加载数据"""
        if not self.data_file.exists():
            self._init_default_data()
            return

        with open(self.data_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.boards = [Board.from_dict(b) for b in data.get("boards", [])]
        self.commands = [Command.from_dict(c) for c in data.get("commands", [])]

    def save(self):
        """保存数据到文件"""
        self.data_path.mkdir(parents=True, exist_ok=True)

        data = {
            "boards": [b.to_dict() for b in self.boards],
            "commands": [c.to_dict() for c in self.commands]
        }

        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def backup(self) -> str:
        """创建数据备份，返回备份文件路径"""
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # 生成带时间戳的备份文件名
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_file = self.backup_dir / f"data_{timestamp}.json"

        # 复制当前数据文件到备份目录
        shutil.copy2(self.data_file, backup_file)

        # 清理旧备份，只保留最近10个
        self._cleanup_old_backups()

        return str(backup_file)

    def _cleanup_old_backups(self):
        """清理旧备份，只保留最近10个"""
        if not self.backup_dir.exists():
            return

        backups = sorted(self.backup_dir.glob("data_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old_backup in backups[10:]:
            old_backup.unlink()

    def get_backups(self) -> List[dict]:
        """获取所有备份文件列表"""
        if not self.backup_dir.exists():
            return []

        backups = []
        for f in sorted(self.backup_dir.glob("data_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            stat = f.stat()
            backups.append({
                "path": str(f),
                "name": f.name,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
        return backups

    def _init_default_data(self):
        """初始化默认数据"""
        self.boards = [
            Board.create("Commands", "💻"),
            Board.create("Prompts", "🤖")
        ]
        self.save()

    # Board CRUD
    def add_board(self, board: Board):
        self.boards.append(board)
        self.save()

    def get_board(self, board_id: str) -> Optional[Board]:
        for board in self.boards:
            if board.id == board_id:
                return board
        return None

    def update_board(self, board: Board):
        self.save()

    def delete_board(self, board_id: str) -> int:
        """删除板块，返回被删除的指令数量"""
        self.boards = [b for b in self.boards if b.id != board_id]
        deleted_commands = [c for c in self.commands if c.board_id == board_id]
        self.commands = [c for c in self.commands if c.board_id != board_id]
        self.save()
        return len(deleted_commands)

    # Command CRUD
    def add_command(self, command: Command):
        self.commands.append(command)
        self.save()

    def get_command(self, command_id: str) -> Optional[Command]:
        for cmd in self.commands:
            if cmd.id == command_id:
                return cmd
        return None

    def get_commands_by_board(self, board_id: str) -> List[Command]:
        return [c for c in self.commands if c.board_id == board_id]

    def update_command(self, command: Command):
        self.save()

    def delete_command(self, command_id: str):
        self.commands = [c for c in self.commands if c.id != command_id]
        self.save()

    def search_commands(
        self,
        keyword: str,
        board_ids: Optional[List[str]] = None,
        tag: Optional[str] = None
    ) -> List[Command]:
        """搜索指令"""
        results = self.commands

        # 按板块过滤
        if board_ids:
            results = [c for c in results if c.board_id in board_ids]

        # 按标签过滤
        if tag:
            results = [c for c in results if tag in c.tags]

        # 按关键词过滤
        if keyword:
            keyword = keyword.lower()
            results = [
                c for c in results
                if keyword in c.title.lower()
                or keyword in c.content.lower()
                or (c.description and keyword in c.description.lower())
                or any(keyword in t.lower() for t in c.tags)
            ]

        # 收藏置顶，然后按更新时间降序
        results.sort(key=lambda c: (c.is_favorite, c.updated_at or ""), reverse=True)
        return results
