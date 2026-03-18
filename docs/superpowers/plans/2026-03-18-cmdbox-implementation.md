# CmdBox 实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个桌面应用，用于保存和管理命令行指令及大模型 Prompt，支持 Git 同步。

**Architecture:** Python + Flet 桌面应用，数据存储为 JSON 文件，通过 Git 仓库实现跨设备同步。采用 MVC 模式：models 定义数据结构，services 处理业务逻辑，views 负责 UI 组件。

**Tech Stack:** Python 3.10+, Flet, GitPython, pyperclip

---

## Chunk 1: 项目初始化与数据模型

### Task 1: 创建项目结构

**Files:**
- Create: `requirements.txt`
- Create: `models/__init__.py`
- Create: `models/board.py`
- Create: `models/command.py`
- Create: `services/__init__.py`
- Create: `views/__init__.py`
- Create: `utils/__init__.py`

- [ ] **Step 1: 创建目录结构**

```bash
mkdir -p models services views utils
```

- [ ] **Step 2: 创建 requirements.txt**

```
flet>=0.21.0
gitpython>=3.1.40
pyperclip>=1.8.2
```

- [ ] **Step 3: 创建空的 `__init__.py` 文件**

```bash
touch models/__init__.py services/__init__.py views/__init__.py utils/__init__.py
```

- [ ] **Step 4: 提交**

```bash
git add . && git commit -m "chore: initialize project structure"
```

---

### Task 2: 实现 Board 数据模型

**Files:**
- Create: `models/board.py`

- [ ] **Step 1: 编写 Board 模型**

```python
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
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @classmethod
    def create(cls, name: str, icon: str = "📁") -> "Board":
        """创建新板块"""
        now = datetime.now().isoformat()
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            icon=icon,
            created_at=now,
            updated_at=now
        )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
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
            created_at=data["created_at"],
            updated_at=data["updated_at"]
        )

    def update(self, name: Optional[str] = None, icon: Optional[str] = None):
        """更新板块信息"""
        if name is not None:
            self.name = name
        if icon is not None:
            self.icon = icon
        self.updated_at = datetime.now().isoformat()
```

- [ ] **Step 2: 提交**

```bash
git add models/board.py && git commit -m "feat: add Board data model"
```

---

### Task 3: 实现 Command 数据模型

**Files:**
- Create: `models/command.py`

- [ ] **Step 1: 编写 Command 模型**

```python
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
```

- [ ] **Step 2: 提交**

```bash
git add models/command.py && git commit -m "feat: add Command data model"
```

---

### Task 4: 实现数据服务

**Files:**
- Create: `services/data_service.py`

- [ ] **Step 1: 编写 DataService**

```python
# services/data_service.py
import json
import os
from typing import List, Optional
from pathlib import Path
from models.board import Board
from models.command import Command


class DataService:
    """数据读写服务"""

    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        self.data_file = self.data_path / "data.json"
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
        board_ids: Optional[List[str]] = None
    ) -> List[Command]:
        """搜索指令"""
        results = self.commands

        # 按板块过滤
        if board_ids:
            results = [c for c in results if c.board_id in board_ids]

        # 按关键词过滤
        if keyword:
            keyword = keyword.lower()
            results = [
                c for c in results
                if keyword in c.title.lower()
                or keyword in c.content.lower()
                or any(keyword in tag.lower() for tag in c.tags)
            ]

        # 收藏置顶
        results.sort(key=lambda c: (not c.is_favorite, c.updated_at), reverse=True)
        return results
```

- [ ] **Step 2: 提交**

```bash
git add services/data_service.py && git commit -m "feat: add DataService for JSON operations"
```

---

## Chunk 2: 核心服务

### Task 5: 实现剪贴板服务

**Files:**
- Create: `services/clipboard_service.py`

- [ ] **Step 1: 编写 ClipboardService**

```python
# services/clipboard_service.py
import pyperclip


class ClipboardService:
    """剪贴板服务"""

    @staticmethod
    def copy(text: str) -> bool:
        """复制文本到剪贴板"""
        try:
            pyperclip.copy(text)
            return True
        except Exception:
            return False

    @staticmethod
    def paste() -> str:
        """从剪贴板获取文本"""
        try:
            return pyperclip.paste()
        except Exception:
            return ""
```

- [ ] **Step 2: 提交**

```bash
git add services/clipboard_service.py && git commit -m "feat: add ClipboardService"
```

---

### Task 6: 实现 Git 服务

**Files:**
- Create: `services/git_service.py`

- [ ] **Step 1: 编写 GitService**

```python
# services/git_service.py
import os
from typing import Optional, Tuple
from pathlib import Path
from datetime import datetime


class GitService:
    """Git 同步服务"""

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self._git = None

    @property
    def git(self):
        """延迟加载 gitpython"""
        if self._git is None:
            import git
            self._git = git
        return self._git

    def is_repo(self) -> bool:
        """检查是否是 Git 仓库"""
        return (self.repo_path / ".git").exists()

    def init_repo(self) -> bool:
        """初始化 Git 仓库"""
        try:
            self.repo_path.mkdir(parents=True, exist_ok=True)
            self.git.Repo.init(self.repo_path)
            return True
        except Exception as e:
            print(f"Init repo error: {e}")
            return False

    def has_remote(self) -> bool:
        """检查是否配置了远程仓库"""
        if not self.is_repo():
            return False
        try:
            repo = self.git.Repo(self.repo_path)
            return len(repo.remotes) > 0
        except Exception:
            return False

    def get_status(self) -> Tuple[bool, str]:
        """获取仓库状态，返回 (有更改, 状态信息)"""
        try:
            repo = self.git.Repo(self.repo_path)
            if repo.is_dirty():
                return True, "有未提交的更改"
            return False, "工作目录干净"
        except Exception as e:
            return False, f"获取状态失败: {e}"

    def commit(self, message: str = "Update data") -> Tuple[bool, str]:
        """提交更改"""
        try:
            repo = self.git.Repo(self.repo_path)
            repo.git.add(A=True)
            if repo.is_dirty():
                repo.index.commit(message)
                return True, "提交成功"
            return True, "没有需要提交的更改"
        except Exception as e:
            return False, f"提交失败: {e}"

    def pull(self) -> Tuple[bool, str]:
        """拉取远程更改"""
        try:
            repo = self.git.Repo(self.repo_path)
            if not repo.remotes:
                return True, "没有配置远程仓库"
            origin = repo.remotes.origin
            origin.pull()
            return True, "拉取成功"
        except Exception as e:
            return False, f"拉取失败: {e}"

    def push(self) -> Tuple[bool, str]:
        """推送到远程"""
        try:
            repo = self.git.Repo(self.repo_path)
            if not repo.remotes:
                return True, "没有配置远程仓库"
            origin = repo.remotes.origin
            origin.push()
            return True, "推送成功"
        except Exception as e:
            return False, f"推送失败: {e}"

    def sync(self) -> Tuple[bool, str]:
        """同步：拉取 -> 提交 -> 推送"""
        # 先拉取
        success, msg = self.pull()
        if not success:
            return False, msg

        # 提交本地更改
        success, msg = self.commit(f"Sync at {datetime.now().isoformat()}")
        if not success:
            return False, msg

        # 推送
        success, msg = self.push()
        if not success:
            return False, msg

        return True, "同步完成"
```

- [ ] **Step 2: 提交**

```bash
git add services/git_service.py && git commit -m "feat: add GitService for sync operations"
```

---

### Task 7: 实现配置服务

**Files:**
- Create: `services/config_service.py`

- [ ] **Step 1: 编写 ConfigService**

```python
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
```

- [ ] **Step 2: 提交**

```bash
git add services/config_service.py && git commit -m "feat: add ConfigService"
```

---

## Chunk 3: UI 组件 - 基础

### Task 8: 实现工具函数

**Files:**
- Create: `utils/helpers.py`

- [ ] **Step 1: 编写 helpers**

```python
# utils/helpers.py
from datetime import datetime


def format_datetime(iso_str: str) -> str:
    """格式化 ISO 时间为可读格式"""
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso_str


def truncate_text(text: str, max_len: int = 50) -> str:
    """截断文本"""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."
```

- [ ] **Step 2: 提交**

```bash
git add utils/helpers.py && git commit -m "feat: add helper utilities"
```

---

### Task 9: 实现侧边栏组件

**Files:**
- Create: `views/sidebar.py`

- [ ] **Step 1: 编写 Sidebar**

```python
# views/sidebar.py
import flet as ft
from typing import List, Callable, Optional
from models.board import Board


class Sidebar(ft.Container):
    """左侧板块列表"""

    def __init__(
        self,
        boards: List[Board],
        on_board_select: Callable[[str], None],
        on_add_board: Callable[[], None],
        selected_board_id: Optional[str] = None
    ):
        super().__init__()
        self.boards = boards
        self.on_board_select = on_board_select
        self.on_add_board = on_add_board
        self.selected_board_id = selected_board_id

        self.width = 200
        self.bgcolor = ft.colors.GREY_100
        self.padding = 10
        self.content = self._build_content()

    def _build_content(self) -> ft.Column:
        board_items = []
        for board in self.boards:
            is_selected = board.id == self.selected_board_id
            item = ft.Container(
                content=ft.Row([
                    ft.Text(board.icon, size=16),
                    ft.Text(board.name, size=14, weight=ft.FontWeight.BOLD if is_selected else ft.FontWeight.NORMAL)
                ]),
                padding=10,
                border_radius=5,
                bgcolor=ft.colors.BLUE_50 if is_selected else None,
                on_click=lambda e, bid=board.id: self.on_board_select(bid)
            )
            board_items.append(item)

        # 添加新建按钮
        add_btn = ft.TextButton(
            content=ft.Row([
                ft.Icon(ft.icons.ADD, size=16),
                ft.Text("新建板块", size=12)
            ]),
            on_click=lambda e: self.on_add_board()
        )

        return ft.Column([
            ft.Text("板块", size=12, color=ft.colors.GREY_500, weight=ft.FontWeight.BOLD),
            ft.Divider(height=10, color="transparent"),
            *board_items,
            ft.Divider(height=20, color="transparent"),
            add_btn
        ])

    def update_boards(self, boards: List[Board], selected_id: Optional[str] = None):
        self.boards = boards
        self.selected_board_id = selected_id
        self.content = self._build_content()
        self.update()
```

- [ ] **Step 2: 提交**

```bash
git add views/sidebar.py && git commit -m "feat: add Sidebar component"
```

---

### Task 10: 实现搜索栏组件

**Files:**
- Create: `views/search_bar.py`

- [ ] **Step 1: 编写 SearchBar**

```python
# views/search_bar.py
import flet as ft
from typing import List, Callable, Optional
from models.board import Board


class SearchBar(ft.Container):
    """搜索栏组件"""

    def __init__(
        self,
        boards: List[Board],
        on_search: Callable[[str, Optional[List[str]]], None]
    ):
        super().__init__()
        self.boards = boards
        self.on_search = on_search

        self.padding = 10
        self.content = self._build_content()

    def _build_content(self) -> ft.Row:
        # 搜索输入框
        self.search_input = ft.TextField(
            hint_text="搜索指令...",
            prefix_icon=ft.icons.SEARCH,
            on_change=self._on_search_change,
            expand=True
        )

        # 板块下拉选择
        board_options = [ft.dropdown.Option("all", "全部板块")]
        board_options.extend([
            ft.dropdown.Option(b.id, f"{b.icon} {b.name}")
            for b in self.boards
        ])

        self.board_dropdown = ft.Dropdown(
            options=board_options,
            value="all",
            width=150,
            on_change=self._on_board_change
        )

        return ft.Row([
            self.search_input,
            self.board_dropdown
        ])

    def _on_search_change(self, e):
        self._do_search()

    def _on_board_change(self, e):
        self._do_search()

    def _do_search(self):
        keyword = self.search_input.value or ""
        board_value = self.board_dropdown.value

        if board_value == "all":
            board_ids = None
        else:
            board_ids = [board_value]

        self.on_search(keyword, board_ids)

    def update_boards(self, boards: List[Board]):
        self.boards = boards
        self.content = self._build_content()
        self.update()
```

- [ ] **Step 2: 提交**

```bash
git add views/search_bar.py && git commit -m "feat: add SearchBar component"
```

---

### Task 11: 实现指令卡片组件

**Files:**
- Create: `views/command_card.py`

- [ ] **Step 1: 编写 CommandCard**

```python
# views/command_card.py
import flet as ft
from typing import Callable
from models.command import Command
from models.board import Board
from utils.helpers import truncate_text


class CommandCard(ft.Container):
    """指令卡片组件"""

    def __init__(
        self,
        command: Command,
        board: Board,
        on_copy: Callable[[Command], None],
        on_edit: Callable[[Command], None],
        on_delete: Callable[[Command], None],
        on_toggle_favorite: Callable[[Command], None]
    ):
        super().__init__()
        self.command = command
        self.board = board
        self.on_copy = on_copy
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_toggle_favorite = on_toggle_favorite

        self.padding = 15
        self.border_radius = 8
        self.border = ft.border.all(1, ft.colors.GREY_300)
        self.margin = ft.margin.only(bottom=10)
        self.content = self._build_content()

    def _build_content(self) -> ft.Column:
        # 标题行
        title_row = ft.Row([
            ft.Icon(ft.icons.STAR if self.command.is_favorite else ft.icons.STAR_BORDER,
                    color=ft.colors.AMBER if self.command.is_favorite else ft.colors.GREY,
                    size=18),
            ft.Text(self.command.title, size=16, weight=ft.FontWeight.BOLD, expand=True),
        ])

        # 内容预览
        content_text = ft.Text(
            truncate_text(self.command.content, 100),
            size=12,
            color=ft.colors.GREY_700
        )

        # 标签行
        tags_row = ft.Row([
            ft.Container(
                content=ft.Text(tag, size=10, color=ft.colors.BLUE_700),
                bgcolor=ft.colors.BLUE_50,
                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                border_radius=10
            )
            for tag in self.command.tags[:3]
        ]) if self.command.tags else ft.Row()

        # 操作按钮行
        actions_row = ft.Row([
            ft.IconButton(
                icon=ft.icons.CONTENT_COPY,
                icon_size=18,
                tooltip="复制",
                on_click=lambda e: self.on_copy(self.command)
            ),
            ft.IconButton(
                icon=ft.icons.EDIT,
                icon_size=18,
                tooltip="编辑",
                on_click=lambda e: self.on_edit(self.command)
            ),
            ft.IconButton(
                icon=ft.icons.STAR if self.command.is_favorite else ft.icons.STAR_BORDER,
                icon_size=18,
                icon_color=ft.colors.AMBER if self.command.is_favorite else None,
                tooltip="取消收藏" if self.command.is_favorite else "收藏",
                on_click=lambda e: self.on_toggle_favorite(self.command)
            ),
            ft.IconButton(
                icon=ft.icons.DELETE_OUTLINE,
                icon_size=18,
                tooltip="删除",
                on_click=lambda e: self.on_delete(self.command)
            )
        ], alignment=ft.MainAxisAlignment.END)

        return ft.Column([
            title_row,
            ft.Divider(height=5, color="transparent"),
            content_text,
            ft.Divider(height=5, color="transparent"),
            tags_row,
            actions_row
        ])
```

- [ ] **Step 2: 提交**

```bash
git add views/command_card.py && git commit -m "feat: add CommandCard component"
```

---

### Task 12: 实现指令列表组件

**Files:**
- Create: `views/command_list.py`

- [ ] **Step 1: 编写 CommandList**

```python
# views/command_list.py
import flet as ft
from typing import List, Callable, Dict
from models.command import Command
from models.board import Board
from views.command_card import CommandCard


class CommandList(ft.Column):
    """指令列表组件"""

    def __init__(
        self,
        boards: Dict[str, Board],
        on_copy: Callable[[Command], None],
        on_edit: Callable[[Command], None],
        on_delete: Callable[[Command], None],
        on_toggle_favorite: Callable[[Command], None],
        on_add_command: Callable[[], None]
    ):
        super().__init__()
        self.boards = boards
        self.on_copy = on_copy
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_toggle_favorite = on_toggle_favorite
        self.on_add_command = on_add_command
        self.commands: List[Command] = []

        self.scroll = ft.ScrollMode.AUTO
        self.expand = True
        self.controls = self._build_empty_state()

    def _build_empty_state(self) -> List[ft.Control]:
        return [
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.INBOX_OUTLINED, size=48, color=ft.colors.GREY_400),
                    ft.Text("暂无指令", color=ft.colors.GREY_500),
                    ft.Text("点击下方按钮添加第一条指令", size=12, color=ft.colors.GREY_400),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.alignment.center,
                expand=True
            )
        ]

    def _build_command_cards(self) -> List[ft.Control]:
        if not self.commands:
            return self._build_empty_state()

        cards = []
        for cmd in self.commands:
            board = self.boards.get(cmd.board_id)
            if not board:
                continue
            card = CommandCard(
                command=cmd,
                board=board,
                on_copy=self.on_copy,
                on_edit=self.on_edit,
                on_delete=self.on_delete,
                on_toggle_favorite=self.on_toggle_favorite
            )
            cards.append(card)

        return cards

    def update_commands(self, commands: List[Command]):
        self.commands = commands
        self.controls = self._build_command_cards()
        self.update()

    def update_boards(self, boards: Dict[str, Board]):
        self.boards = boards
        self.controls = self._build_command_cards()
        self.update()
```

- [ ] **Step 2: 提交**

```bash
git add views/command_list.py && git commit -m "feat: add CommandList component"
```

---

## Chunk 4: 弹窗与主应用

### Task 13: 实现弹窗组件

**Files:**
- Create: `views/dialogs.py`

- [ ] **Step 1: 编写 Dialogs**

```python
# views/dialogs.py
import flet as ft
from typing import List, Optional, Callable
from models.board import Board
from models.command import Command


class BoardDialog(ft.AlertDialog):
    """板块弹窗（新建/编辑）"""

    def __init__(
        self,
        title: str,
        board: Optional[Board] = None,
        on_save: Callable[[str, str], None] = None
    ):
        super().__init__()
        self.board = board
        self.on_save = on_save

        self.modal = True
        self.title = ft.Text(title)

        self.name_field = ft.TextField(
            label="板块名称",
            value=board.name if board else "",
            autofocus=True
        )

        self.icon_field = ft.TextField(
            label="图标 (emoji)",
            value=board.icon if board else "📁",
            max_length=2
        )

        self.content = ft.Column([
            self.name_field,
            self.icon_field
        ], tight=True)

        self.actions = [
            ft.TextButton("取消", on_click=self._on_cancel),
            ft.TextButton("保存", on_click=self._on_save)
        ]

    def _on_cancel(self, e):
        self.open = False
        self.update()

    def _on_save(self, e):
        if self.on_save:
            self.on_save(self.name_field.value, self.icon_field.value)
        self.open = False
        self.update()


class CommandDialog(ft.AlertDialog):
    """指令弹窗（新建/编辑）"""

    def __init__(
        self,
        title: str,
        boards: List[Board],
        command: Optional[Command] = None,
        selected_board_id: Optional[str] = None,
        on_save: Callable = None
    ):
        super().__init__()
        self.command = command
        self.boards = boards
        self.on_save = on_save

        self.modal = True
        self.title = ft.Text(title)

        # 表单字段
        self.title_field = ft.TextField(
            label="标题",
            value=command.title if command else ""
        )

        board_options = [
            ft.dropdown.Option(b.id, f"{b.icon} {b.name}")
            for b in boards
        ]
        self.board_dropdown = ft.Dropdown(
            label="所属板块",
            options=board_options,
            value=command.board_id if command else selected_board_id
        )

        self.content_field = ft.TextField(
            label="指令内容",
            value=command.content if command else "",
            multiline=True,
            min_lines=3,
            max_lines=10
        )

        self.description_field = ft.TextField(
            label="描述（可选）",
            value=command.description if command else "",
            multiline=True,
            min_lines=2,
            max_lines=5
        )

        self.tags_field = ft.TextField(
            label="标签（逗号分隔）",
            value=", ".join(command.tags) if command and command.tags else ""
        )

        self.favorite_checkbox = ft.Checkbox(
            label="添加到收藏",
            value=command.is_favorite if command else False
        )

        self.content = ft.Column([
            self.title_field,
            self.board_dropdown,
            self.content_field,
            self.description_field,
            self.tags_field,
            self.favorite_checkbox
        ], tight=True, scroll=ft.ScrollMode.AUTO)

        self.actions = [
            ft.TextButton("取消", on_click=self._on_cancel),
            ft.TextButton("保存", on_click=self._on_save)
        ]

    def _on_cancel(self, e):
        self.open = False
        self.update()

    def _on_save(self, e):
        if self.on_save:
            tags_str = self.tags_field.value or ""
            tags = [t.strip() for t in tags_str.split(",") if t.strip()]

            self.on_save(
                title=self.title_field.value,
                board_id=self.board_dropdown.value,
                content=self.content_field.value,
                description=self.description_field.value,
                tags=tags,
                is_favorite=self.favorite_checkbox.value
            )
        self.open = False
        self.update()


class ConfirmDialog(ft.AlertDialog):
    """确认弹窗"""

    def __init__(
        self,
        title: str,
        content: str,
        on_confirm: Callable = None
    ):
        super().__init__()
        self.on_confirm = on_confirm

        self.modal = True
        self.title = ft.Text(title)
        self.content = ft.Text(content)

        self.actions = [
            ft.TextButton("取消", on_click=self._on_cancel),
            ft.TextButton("确认", on_click=self._on_confirm)
        ]

    def _on_cancel(self, e):
        self.open = False
        self.update()

    def _on_confirm(self, e):
        if self.on_confirm:
            self.on_confirm()
        self.open = False
        self.update()


class EditAndCopyDialog(ft.AlertDialog):
    """编辑后复制弹窗"""

    def __init__(self, command: Command, on_copy: Callable[[str], None]):
        super().__init__()
        self.command = command
        self.on_copy = on_copy

        self.modal = True
        self.title = ft.Text("编辑后复制")

        self.edit_field = ft.TextField(
            value=command.content,
            multiline=True,
            min_lines=5,
            max_lines=15,
            expand=True
        )

        self.content = ft.Column([self.edit_field], tight=True)

        self.actions = [
            ft.TextButton("取消", on_click=self._on_cancel),
            ft.TextButton("复制", on_click=self._on_copy)
        ]

    def _on_cancel(self, e):
        self.open = False
        self.update()

    def _on_copy(self, e):
        self.on_copy(self.edit_field.value)
        self.open = False
        self.update()
```

- [ ] **Step 2: 提交**

```bash
git add views/dialogs.py && git commit -m "feat: add dialog components"
```

---

### Task 14: 实现首次启动向导

**Files:**
- Create: `views/setup_wizard.py`

- [ ] **Step 1: 编写 SetupWizard**

```python
# views/setup_wizard.py
import flet as ft
from pathlib import Path
from typing import Callable


class SetupWizard(ft.Container):
    """首次启动向导"""

    def __init__(self, on_complete: Callable[[str], None]):
        super().__init__()
        self.on_complete = on_complete

        self.expand = True
        self.alignment = ft.alignment.center
        self.content = self._build_content()

    def _build_content(self) -> ft.Column:
        return ft.Column([
            ft.Icon(ft.icons.FOLDER_OPEN, size=64, color=ft.colors.BLUE),
            ft.Text("欢迎使用 CmdBox", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(height=20, color="transparent"),
            ft.Text("请选择数据存储目录", size=14, color=ft.colors.GREY_600),
            ft.Divider(height=20, color="transparent"),

            ft.Row([
                self._build_path_input(),
                self._build_browse_button()
            ]),

            ft.Divider(height=30, color="transparent"),

            ft.ElevatedButton(
                "开始使用",
                on_click=self._on_start,
                style=ft.ButtonStyle(
                    padding=ft.padding.symmetric(horizontal=40, vertical=15)
                )
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    def _build_path_input(self) -> ft.TextField:
        self.path_input = ft.TextField(
            hint_text="选择或输入目录路径",
            width=400,
            value=str(Path.home() / "cmdbox-data")
        )
        return self.path_input

    def _build_browse_button(self) -> ft.IconButton:
        return ft.IconButton(
            icon=ft.icons.FOLDER_OPEN,
            tooltip="浏览",
            on_click=self._on_browse
        )

    def _on_browse(self, e):
        # Flet 不支持原生文件对话框，使用输入框
        # 用户可以手动输入或粘贴路径
        self.path_input.focus()

    def _on_start(self, e):
        path = self.path_input.value.strip()
        if path:
            self.on_complete(path)
```

- [ ] **Step 2: 提交**

```bash
git add views/setup_wizard.py && git commit -m "feat: add SetupWizard"
```

---

### Task 15: 实现主应用

**Files:**
- Create: `app.py`

- [ ] **Step 1: 编写主应用**

```python
# app.py
import flet as ft
from pathlib import Path
from typing import Optional, List, Dict

from services.config_service import ConfigService
from services.data_service import DataService
from services.git_service import GitService
from services.clipboard_service import ClipboardService
from models.board import Board
from models.command import Command
from views.sidebar import Sidebar
from views.search_bar import SearchBar
from views.command_list import CommandList
from views.dialogs import BoardDialog, CommandDialog, ConfirmDialog, EditAndCopyDialog
from views.setup_wizard import SetupWizard


class CmdBoxApp:
    """CmdBox 主应用"""

    def __init__(self, page: ft.Page):
        self.page = page
        self._setup_page()

        # 服务
        self.config_service: Optional[ConfigService] = None
        self.data_service: Optional[DataService] = None
        self.git_service: Optional[GitService] = None
        self.clipboard_service = ClipboardService()

        # 状态
        self.selected_board_id: Optional[str] = None
        self.search_keyword: str = ""
        self.search_board_ids: Optional[List[str]] = None

        # 检查是否已初始化
        config_path = Path.home() / ".cmdbox"
        self.config_service = ConfigService(str(config_path))

        if self.config_service.load() and self.config_service.is_initialized():
            self._init_app()
        else:
            self._show_setup_wizard()

    def _setup_page(self):
        """设置页面属性"""
        self.page.title = "CmdBox"
        self.page.window.width = 900
        self.page.window.height = 600
        self.page.theme_mode = ft.ThemeMode.LIGHT

    def _show_setup_wizard(self):
        """显示设置向导"""
        self.page.clean()
        wizard = SetupWizard(on_complete=self._on_setup_complete)
        self.page.add(wizard)

    def _on_setup_complete(self, repo_path: str):
        """设置向导完成"""
        # 初始化配置
        self.config_service.init(repo_path)

        # 初始化 Git 仓库
        self.git_service = GitService(repo_path)
        self.git_service.init_repo()

        # 初始化数据服务
        self.data_service = DataService(repo_path)
        self.data_service.load()

        # 初始提交
        self.git_service.commit("Initial commit")

        self._init_app()

    def _init_app(self):
        """初始化应用"""
        repo_path = self.config_service.get("repo_path")

        # 初始化服务
        self.git_service = GitService(repo_path)
        self.data_service = DataService(repo_path)
        self.data_service.load()

        # 构建界面
        self._build_ui()

    def _build_ui(self):
        """构建界面"""
        self.page.clean()

        # 获取板块字典
        boards_dict = {b.id: b for b in self.data_service.boards}

        # 顶部栏
        self.header = ft.Container(
            content=ft.Row([
                ft.Text("CmdBox", size=20, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.IconButton(
                        icon=ft.icons.SYNC,
                        tooltip="同步",
                        on_click=self._on_sync
                    ),
                    ft.IconButton(
                        icon=ft.icons.SETTINGS,
                        tooltip="设置",
                        on_click=self._on_settings
                    )
                ])
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=10,
            bgcolor=ft.colors.BLUE_50
        )

        # 侧边栏
        self.sidebar = Sidebar(
            boards=self.data_service.boards,
            on_board_select=self._on_board_select,
            on_add_board=self._on_add_board,
            selected_board_id=self.selected_board_id
        )

        # 搜索栏
        self.search_bar = SearchBar(
            boards=self.data_service.boards,
            on_search=self._on_search
        )

        # 指令列表
        self.command_list = CommandList(
            boards=boards_dict,
            on_copy=self._on_copy_command,
            on_edit=self._on_edit_command,
            on_delete=self._on_delete_command,
            on_toggle_favorite=self._on_toggle_favorite,
            on_add_command=self._on_add_command
        )

        # 新建指令按钮
        self.add_btn = ft.FloatingActionButton(
            icon=ft.icons.ADD,
            on_click=lambda e: self._on_add_command()
        )

        # 主内容区
        main_content = ft.Column([
            ft.Container(content=self.search_bar, padding=10),
            ft.Divider(height=1),
            ft.Container(content=self.command_list, expand=True)
        ], expand=True)

        # 布局
        layout = ft.Row([
            ft.Container(content=self.sidebar, width=200),
            ft.VerticalDivider(width=1),
            ft.Container(content=main_content, expand=True)
        ], expand=True)

        # 添加到页面
        self.page.add(ft.Column([
            self.header,
            ft.Divider(height=1),
            layout
        ], expand=True))

        self.page.floating_action_button = self.add_btn

        # 加载初始数据
        self._refresh_commands()

    def _refresh_commands(self):
        """刷新指令列表"""
        commands = self.data_service.search_commands(
            self.search_keyword,
            self.search_board_ids
        )
        self.command_list.update_commands(commands)

    def _refresh_sidebar(self):
        """刷新侧边栏"""
        self.sidebar.update_boards(
            self.data_service.boards,
            self.selected_board_id
        )
        self.search_bar.update_boards(self.data_service.boards)

    def _on_board_select(self, board_id: str):
        """选择板块"""
        self.selected_board_id = board_id
        self.search_board_ids = [board_id]
        self._refresh_commands()
        self._refresh_sidebar()

    def _on_search(self, keyword: str, board_ids: Optional[List[str]]):
        """搜索"""
        self.search_keyword = keyword
        self.search_board_ids = board_ids
        self._refresh_commands()

    def _on_add_board(self):
        """添加板块"""
        def on_save(name: str, icon: str):
            if name:
                board = Board.create(name, icon)
                self.data_service.add_board(board)
                self._refresh_sidebar()

        dialog = BoardDialog("新建板块", on_save=on_save)
        self.page.open(dialog)

    def _on_add_command(self):
        """添加指令"""
        if not self.data_service.boards:
            self.page.snack_bar = ft.SnackBar(ft.Text("请先创建板块"))
            self.page.snack_bar.open = True
            self.page.update()
            return

        def on_save(**kwargs):
            command = Command.create(
                board_id=kwargs["board_id"],
                title=kwargs["title"],
                content=kwargs["content"],
                description=kwargs.get("description", ""),
                tags=kwargs.get("tags", []),
                is_favorite=kwargs.get("is_favorite", False)
            )
            self.data_service.add_command(command)
            self._refresh_commands()

        dialog = CommandDialog(
            "新建指令",
            boards=self.data_service.boards,
            selected_board_id=self.selected_board_id,
            on_save=on_save
        )
        self.page.open(dialog)

    def _on_copy_command(self, command: Command):
        """复制指令"""
        if self.clipboard_service.copy(command.content):
            self.page.snack_bar = ft.SnackBar(ft.Text("已复制到剪贴板"))
        else:
            self.page.snack_bar = ft.SnackBar(ft.Text("复制失败"))
        self.page.snack_bar.open = True
        self.page.update()

    def _on_edit_command(self, command: Command):
        """编辑指令"""
        def on_save(**kwargs):
            command.update(
                title=kwargs["title"],
                board_id=kwargs["board_id"],
                content=kwargs["content"],
                description=kwargs.get("description", ""),
                tags=kwargs.get("tags", []),
                is_favorite=kwargs.get("is_favorite", False)
            )
            self.data_service.update_command(command)
            self._refresh_commands()

        dialog = CommandDialog(
            "编辑指令",
            boards=self.data_service.boards,
            command=command,
            on_save=on_save
        )
        self.page.open(dialog)

    def _on_delete_command(self, command: Command):
        """删除指令"""
        def on_confirm():
            self.data_service.delete_command(command.id)
            self._refresh_commands()

        dialog = ConfirmDialog(
            "确认删除",
            f"确定要删除指令「{command.title}」吗？",
            on_confirm=on_confirm
        )
        self.page.open(dialog)

    def _on_toggle_favorite(self, command: Command):
        """切换收藏"""
        command.update(is_favorite=not command.is_favorite)
        self.data_service.update_command(command)
        self._refresh_commands()

    def _on_sync(self, e):
        """同步"""
        success, msg = self.git_service.sync()
        self.config_service.update_last_sync()

        self.page.snack_bar = ft.SnackBar(ft.Text(msg))
        self.page.snack_bar.open = True
        self.page.update()

    def _on_settings(self, e):
        """设置"""
        # TODO: 实现设置界面
        self.page.snack_bar = ft.SnackBar(ft.Text("设置功能开发中..."))
        self.page.snack_bar.open = True
        self.page.update()


def main(page: ft.Page):
    CmdBoxApp(page)


if __name__ == "__main__":
    ft.app(target=main)
```

- [ ] **Step 2: 提交**

```bash
git add app.py && git commit -m "feat: add main application"
```

---

### Task 16: 创建入口文件

**Files:**
- Create: `main.py`

- [ ] **Step 1: 编写入口**

```python
# main.py
"""CmdBox - 命令和 Prompt 管理工具"""

import flet as ft
from app import main

if __name__ == "__main__":
    ft.app(target=main)
```

- [ ] **Step 2: 提交**

```bash
git add main.py && git commit -m "feat: add entry point"
```

---

### Task 17: 创建 README

**Files:**
- Create: `README.md`

- [ ] **Step 1: 编写 README**

```markdown
# CmdBox

一款用于保存和管理命令行指令及大模型 Prompt 的桌面应用。

## 功能

- 📁 自定义板块分类
- 📋 指令增删查改
- 🔍 实时搜索过滤
- ⭐ 收藏置顶
- 🏷️ 标签系统
- 🔄 Git 仓库同步
- 📋 一键复制到剪贴板

## 安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
python main.py
```

## 技术栈

- Python 3.10+
- Flet (UI 框架)
- GitPython (Git 操作)
- pyperclip (剪贴板)
```

- [ ] **Step 2: 提交**

```bash
git add README.md && git commit -m "docs: add README"
```

---

### Task 18: 最终验证

- [ ] **Step 1: 安装依赖**

```bash
pip install -r requirements.txt
```

- [ ] **Step 2: 运行应用**

```bash
python main.py
```

Expected: 应用启动，显示欢迎向导

- [ ] **Step 3: 最终提交**

```bash
git add . && git commit -m "chore: finalize implementation"
```

---

## 完成标志

- [ ] 应用可正常启动
- [ ] 首次启动显示向导
- [ ] 可创建板块
- [ ] 可创建/编辑/删除指令
- [ ] 搜索功能正常
- [ ] 复制到剪贴板正常
- [ ] Git 同步功能正常
