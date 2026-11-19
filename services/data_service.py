# services/data_service.py
import json
import os
import shutil
import copy
import hashlib
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional
from pathlib import Path
from datetime import datetime
from models.board import Board
from models.command import Command
from models.task import Task
from models.question import Question
from services.data_schema import parse_data
from services.search_index import SearchIndex
from services.file_lock import data_file_lock


class ExternalDataChangeError(OSError):
    """当前内存版本落后于磁盘版本，不能覆盖写入。"""


class DataService:
    """数据读写服务"""

    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        self.data_file = self.data_path / "data.json"
        self._file_version = self._disk_version()
        self._file_digest = None
        self.backup_dir = self.data_path / "backups"
        self.boards: List[Board] = []
        self.commands: List[Command] = []
        self.tasks: List[Task] = []
        self.questions: List[Question] = []
        self.revision = 0
        self._save_lock = threading.Lock()
        self._save_ready = threading.Condition(self._save_lock)
        self._save_generation = 0
        self._flush_requested = False
        self._executor = None
        self._pending_save = None
        self._writing = False
        self._save_future = None
        self._save_error = None
        self._on_save_error = None
        self._snapshot_cache = {name: {} for name in ('boards', 'commands', 'tasks', 'questions')}
        self._search_indexes = {
            'commands': SearchIndex(('title', 'content', 'description', 'tags')),
            'tasks': SearchIndex(('title', 'description')),
            'questions': SearchIndex(('title', 'description', 'answer')),
        }

    def enable_background_saves(self, on_error=None):
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='cmdbox-save')
        self._on_save_error = on_error

    def flush(self):
        """Wait until queued data is persisted; never hide a failed write."""
        with self._save_ready:
            self._flush_requested = True
            self._save_ready.notify_all()
            future = self._save_future
        try:
            if future:
                future.result()
        finally:
            with self._save_ready:
                self._flush_requested = False
        if self._save_error:
            if isinstance(self._save_error, ExternalDataChangeError):
                raise self._save_error
            raise OSError(f'保存数据失败: {self._save_error}') from self._save_error

    def close(self):
        try:
            self.flush()
        except ExternalDataChangeError:
            # 保留本窗口的未保存修改，让用户能正常退出后重新打开最新数据。
            with self._save_lock:
                snapshot = self._pending_save
            if snapshot is None:
                raise
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S_%f')
            draft = self.backup_dir / f'data_local_{timestamp}.json'
            with draft.open('w', encoding='utf-8') as handle:
                json.dump(snapshot, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            with self._save_lock:
                self._pending_save = None
                self._save_error = None
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None

    def _disk_version(self):
        try:
            stat = self.data_file.stat()
            return stat.st_mtime_ns, stat.st_size, stat.st_ino
        except FileNotFoundError:
            return None

    def assert_current(self):
        if self._disk_version() != self._file_version:
            # Git 中止合并可能重写内容完全相同的文件；只在确实有变化时拒绝。
            if self._disk_digest() != self._file_digest:
                raise ExternalDataChangeError('数据文件已被其他窗口或程序修改，已停止写入。请重新打开应用以加载最新数据')
            self._file_version = self._disk_version()

    def _disk_digest(self):
        try:
            return self._digest(self.data_file.read_bytes())
        except FileNotFoundError:
            return None

    @staticmethod
    def _digest(raw):
        # Git 在 Windows 上可能把相同 JSON 的换行还原为 CRLF。
        return hashlib.sha256(raw.replace(b'\r\n', b'\n')).digest()

    def _write_snapshot(self, data):
        with data_file_lock(self.data_path):
            self.assert_current()
            self._write_snapshot_unlocked(data)
            self._file_version = self._disk_version()
            self._file_digest = self._disk_digest()

    def _write_snapshot_unlocked(self, data):
        self.data_path.mkdir(parents=True, exist_ok=True)
        path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.data_path,
                                             prefix='.cmdbox-', suffix='.tmp', delete=False) as f:
                path = f.name
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(path, self.data_file)
        finally:
            if path and os.path.exists(path):
                os.unlink(path)

    def _drain_saves(self):
        while True:
            with self._save_ready:
                # Coalesce bursts of edits; flush bypasses the short delay.
                generation = self._save_generation
                deadline = time.monotonic() + 0.1
                while self._pending_save is not None and not self._flush_requested:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    self._save_ready.wait(remaining)
                    if generation != self._save_generation:
                        generation = self._save_generation
                        deadline = time.monotonic() + 0.1
                snapshot = self._pending_save
                self._pending_save = None
                if snapshot is None:
                    self._writing = False
                    return
            try:
                self._write_snapshot(snapshot)
                self._save_error = None
            except Exception as error:
                with self._save_lock:
                    self._save_error = error
                    if self._pending_save is None:
                        self._pending_save = snapshot
                    self._writing = False
                if self._on_save_error:
                    self._on_save_error(error)
                return

    def load(self):
        """从文件加载数据"""
        self.flush()
        if not self.data_file.exists():
            if self._file_version is not None:
                raise ExternalDataChangeError('数据文件已被其他程序移除，请检查数据目录后重试')
            self._init_default_data()
            return

        try:
            with data_file_lock(self.data_path):
                raw = self.data_file.read_bytes()
                loaded_version = self._disk_version()
                loaded_digest = self._digest(raw)
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            previous_version = self._file_version
            previous_digest = self._file_digest
            self._file_version = loaded_version
            self._file_digest = loaded_digest
            # JSON 损坏时尝试恢复最新备份
            restored = self._try_restore_from_backup()
            if restored is not None:
                data = restored
            else:
                # 保留损坏文件；不能把无法读取误判为一套全新的空数据。
                self._backup_corrupted_file()
                self._file_version = previous_version
                self._file_digest = previous_digest
                raise ValueError('数据文件损坏且没有有效备份，请修复数据文件或选择其他数据目录')
            loaded_version = self._file_version
            loaded_digest = self._file_digest

        # 完整解析后再替换，避免某类数据加载失败造成内存处于半更新状态。
        records = self.parse_data(data)
        self._file_version = loaded_version
        self._file_digest = loaded_digest
        self._apply_records(records)

    def _apply_records(self, records):
        self.revision += 1
        for name, items in records.items():
            setattr(self, name, items)
        self._snapshot_cache = {name: {} for name in self._snapshot_cache}
        for index in self._search_indexes.values():
            index.clear()

    parse_data = staticmethod(parse_data)

    def restore_backup(self, backup_path):
        """先完整校验备份，再备份当前数据并原子替换，最后替换内存模型。"""
        self.flush()
        data = json.loads(Path(backup_path).read_text(encoding='utf-8'))
        records = self.parse_data(data)
        self.backup()
        self._write_snapshot(data)
        self._apply_records(records)

    def save(self):
        """保存数据到文件"""
        self.revision += 1
        data = {}
        for name in self._snapshot_cache:
            previous = self._snapshot_cache[name]
            current = {}
            rows = []
            for item in getattr(self, name):
                # A record's update timestamp changes on edits; object identity also
                # invalidates the cache after loading or replacing a record.
                signature = (id(item), item.updated_at)
                cached = previous.get(item.id)
                if cached is None or cached[0] != signature:
                    cached = (signature, copy.deepcopy(item.to_dict()))
                current[item.id] = cached
                rows.append(cached[1])
            self._snapshot_cache[name] = current
            data[name] = rows

        if self._executor is None:
            self._write_snapshot(data)
        else:
            with self._save_ready:
                self._pending_save = data
                self._save_generation += 1
                self._save_ready.notify_all()
                if not self._writing:
                    self._writing = True
                    self._save_future = self._executor.submit(self._drain_saves)

    def backup(self) -> str:
        """创建数据备份，返回备份文件路径"""
        self.flush()
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # 生成带时间戳的备份文件名
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
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

    def _try_restore_from_backup(self) -> Optional[dict]:
        """尝试从最新备份恢复，返回是否成功"""
        if not self.backup_dir.exists():
            return None
        backups = sorted(self.backup_dir.glob("data_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for backup in backups:
            try:
                with open(backup, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.parse_data(data)
                self._write_snapshot(data)
                return data
            except (ValueError, KeyError, TypeError):
                continue
        return None

    def _backup_corrupted_file(self):
        """将损坏的数据文件备份为 .corrupted 文件"""
        if self.data_file.exists():
            corrupted_path = self.data_file.with_suffix(".json.corrupted")
            shutil.copy2(self.data_file, corrupted_path)

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

    def reorder_boards(self, board_ids: List[str]):
        """根据给定的 ID 顺序重新排列板块"""
        # 创建 ID 到板块的映射
        board_map = {b.id: b for b in self.boards}
        # 按新顺序重建列表
        if len(board_ids) != len(set(board_ids)) or set(board_ids) != set(board_map):
            raise ValueError('板块排序必须包含全部板块且不能重复')
        self.boards = [board_map[bid] for bid in board_ids]
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

    def get_favorite_commands(self) -> List[Command]:
        """获取所有收藏的指令"""
        return [c for c in self.commands if c.is_favorite]

    def update_command(self, command: Command):
        self.save()

    def delete_command(self, command_id: str):
        self.commands = [c for c in self.commands if c.id != command_id]
        self.save()

    # Task CRUD
    def add_task(self, task: Task):
        self.tasks.append(task)
        self.save()

    def get_task(self, task_id: str) -> Optional[Task]:
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def get_sorted_tasks(self) -> List[Task]:
        """按优先级排序（高→中→低），同优先级按创建时间倒序"""
        priority_order = {"high": 0, "medium": 1, "low": 2}
        sorted_by_time = sorted(self.tasks, key=lambda t: t.created_at or "", reverse=True)
        return sorted(sorted_by_time, key=lambda t: priority_order.get(t.priority, 1))

    def update_task(self, task: Task):
        self.save()

    def delete_task(self, task_id: str):
        self.tasks = [t for t in self.tasks if t.id != task_id]
        self.save()

    def delete_completed_tasks(self):
        self.tasks = [t for t in self.tasks if not t.completed]
        self.save()

    # Question CRUD
    def add_question(self, question: Question):
        self.questions.append(question)
        self.save()

    def get_question(self, question_id: str) -> Optional[Question]:
        for question in self.questions:
            if question.id == question_id:
                return question
        return None

    def get_sorted_questions(self) -> List[Question]:
        """按优先级排序（高→中→低），同优先级按创建时间倒序"""
        priority_order = {"high": 0, "medium": 1, "low": 2}
        sorted_by_time = sorted(self.questions, key=lambda q: q.created_at or "", reverse=True)
        return sorted(sorted_by_time, key=lambda q: priority_order.get(q.priority, 1))

    def update_question(self, question: Question):
        self.save()

    def delete_question(self, question_id: str):
        self.questions = [q for q in self.questions if q.id != question_id]
        self.save()

    def delete_asked_questions(self):
        self.questions = [q for q in self.questions if not q.asked]
        self.save()

    def move_command_up(self, command_id: str, board_id: str = None):
        """将指令在当前板块内上移一位"""
        # 获取当前板块内的命令
        if board_id:
            board_commands = [(i, c) for i, c in enumerate(self.commands) if c.board_id == board_id]
        else:
            board_commands = [(i, c) for i, c in enumerate(self.commands)]

        for local_idx, (global_idx, cmd) in enumerate(board_commands):
            if cmd.id == command_id and local_idx > 0:
                # 获取前一个命令的全局索引
                prev_global_idx = board_commands[local_idx - 1][0]
                # 交换位置
                self.commands[global_idx], self.commands[prev_global_idx] = \
                    self.commands[prev_global_idx], self.commands[global_idx]
                self.save()
                return True
        return False

    def move_command_down(self, command_id: str, board_id: str = None):
        """将指令在当前板块内下移一位"""
        # 获取当前板块内的命令
        if board_id:
            board_commands = [(i, c) for i, c in enumerate(self.commands) if c.board_id == board_id]
        else:
            board_commands = [(i, c) for i, c in enumerate(self.commands)]

        for local_idx, (global_idx, cmd) in enumerate(board_commands):
            if cmd.id == command_id and local_idx < len(board_commands) - 1:
                # 获取后一个命令的全局索引
                next_global_idx = board_commands[local_idx + 1][0]
                # 交换位置
                self.commands[global_idx], self.commands[next_global_idx] = \
                    self.commands[next_global_idx], self.commands[global_idx]
                self.save()
                return True
        return False

    def search_commands(
        self,
        keyword: str,
        board_ids: Optional[List[str]] = None,
        tag: Optional[str] = None
    ) -> List[Command]:
        """搜索指令"""
        results = list(self.commands)

        # 按板块过滤
        if board_ids:
            results = [c for c in results if c.board_id in board_ids]

        # 按标签过滤
        if tag:
            results = [c for c in results if tag in c.tags]

        # 按关键词过滤
        if keyword:
            results = self._search_indexes['commands'].filter(results, keyword)

        # 有关键词或标签筛选时按更新时间降序排序
        if keyword or tag:
            results.sort(key=lambda c: c.updated_at or "", reverse=True)
        return results

    def search_tasks(self, keyword=''):
        return self._search_indexes['tasks'].filter(self.tasks, keyword)

    def search_questions(self, keyword=''):
        return self._search_indexes['questions'].filter(self.questions, keyword)

    def export_commands(self, board_id: Optional[str] = None, format: str = "json") -> str:
        """导出指令为 JSON 或 CSV 格式

        Args:
            board_id: 若指定，则只导出该板块的指令；若为 None，则导出所有
            format: "json" 或 "csv"

        Returns:
            序列化后的字符串
        """
        # 获取要导出的指令
        if board_id:
            commands = [c for c in self.commands if c.board_id == board_id]
        else:
            commands = self.commands

        # 获取板块名称映射
        board_names = {b.id: b.name for b in self.boards}

        if format == "json":
            return self._export_as_json(commands, board_names)
        else:
            return self._export_as_csv(commands, board_names)

    def _export_as_json(self, commands: List[Command], board_names: dict) -> str:
        """导出为 JSON 格式"""
        export_data = {
            "export_date": datetime.now().strftime("%Y-%m-%d"),
            "commands": []
        }
        for c in commands:
            export_data["commands"].append({
                "title": c.title,
                "description": c.description,
                "content": c.content,
                "board": board_names.get(c.board_id, ""),
                "tags": c.tags,
                "is_favorite": c.is_favorite,
                "created_at": c.created_at,
                "updated_at": c.updated_at
            })
        return json.dumps(export_data, ensure_ascii=False, indent=2)

    def _export_as_csv(self, commands: List[Command], board_names: dict) -> str:
        """导出为 CSV 格式（UTF-8 BOM）"""
        import csv
        import io

        output = io.StringIO()
        # UTF-8 BOM for Excel compatibility
        output.write("\ufeff")

        writer = csv.writer(output, quoting=csv.QUOTE_ALL, lineterminator='\n')
        writer.writerow(["title", "description", "content", "board", "tags", "is_favorite", "created_at", "updated_at"])

        for c in commands:
            writer.writerow([
                c.title,
                c.description,
                c.content,
                board_names.get(c.board_id, ""),
                ",".join(c.tags) if c.tags else "",
                1 if c.is_favorite else 0,
                c.created_at,
                c.updated_at
            ])

        return output.getvalue()

    def export_commands_list(self, commands: List[Command], format: str = "json", board_names=None) -> str:
        """直接导出一批指令（不通过 board_id 过滤）

        Args:
            commands: 要导出的指令列表
            format: "json" 或 "csv"

        Returns:
            序列化后的字符串
        """
        board_names = board_names if board_names is not None else {b.id: b.name for b in self.boards}
        if format == "json":
            return self._export_as_json(commands, board_names)
        else:
            return self._export_as_csv(commands, board_names)
