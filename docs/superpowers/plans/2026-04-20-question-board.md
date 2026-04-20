# 问题板块实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增"问题"板块，记录待询问和已询问的问题，支持解答字段，参照任务板块架构实现。

**Architecture:** 完全复刻任务板块的 Model → Card → List → Dialog → Service → App 集成模式。新增 Question 模型、QuestionCard、QuestionList、QuestionDialog 四个独立组件，在 DataService 中新增 questions 数据存取，在 app.py 中集成三态内容切换（命令列表/任务列表/问题列表）。

**Tech Stack:** Python 3.10+, Flet 0.82.2, dataclasses

---

## Chunk 1: 数据层（模型 + 服务）

### Task 1: 创建 Question 数据模型

**Files:**
- Create: `models/question.py`

- [ ] **Step 1: 创建 `models/question.py`**

```python
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
```

- [ ] **Step 2: 验证模型可导入**

Run: `cd /Users/hujiaxi/Documents/projects/CmdBox && python3 -c "from models.question import Question; q = Question.create('测试问题', answer='测试解答'); print(q.to_dict())"`
Expected: 打印包含 id, title, description, answer, priority, asked, created_at, updated_at 的字典

- [ ] **Step 3: Commit**

```bash
git add models/question.py
git commit -m "feat: 新增 Question 数据模型"
```

---

### Task 2: DataService 新增 Question CRUD

**Files:**
- Modify: `services/data_service.py:1-10` (imports)
- Modify: `services/data_service.py:22` (tasks 属性后新增 questions 属性)
- Modify: `services/data_service.py:47` (load 方法)
- Modify: `services/data_service.py:53-57` (save 方法)
- Modify: `services/data_service.py:211-213` (delete_completed_tasks 后新增 question 方法)

- [ ] **Step 1: 添加 Question 导入**

在 `services/data_service.py` 第 10 行 `from models.task import Task` 后新增：
```python
from models.question import Question
```

- [ ] **Step 2: 新增 questions 属性**

在 `services/data_service.py` 第 22 行 `self.tasks: List[Task] = []` 后新增：
```python
        self.questions: List[Question] = []
```

- [ ] **Step 3: 修改 load 方法**

在 `services/data_service.py` 第 47 行 `self.tasks = ...` 后新增：
```python
        self.questions = [Question.from_dict(q) for q in data.get("questions", [])]
```

- [ ] **Step 4: 修改 save 方法**

在 `services/data_service.py` 的 save 方法中，将 data 字典从：
```python
        data = {
            "boards": [b.to_dict() for b in self.boards],
            "commands": [c.to_dict() for c in self.commands],
            "tasks": [t.to_dict() for t in self.tasks]
        }
```
改为：
```python
        data = {
            "boards": [b.to_dict() for b in self.boards],
            "commands": [c.to_dict() for c in self.commands],
            "tasks": [t.to_dict() for t in self.tasks],
            "questions": [q.to_dict() for q in self.questions]
        }
```

- [ ] **Step 5: 新增 Question CRUD 方法**

在 `services/data_service.py` 的 `delete_completed_tasks` 方法（第 211-213 行）后新增：
```python

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
```

- [ ] **Step 6: 验证 DataService 可导入**

Run: `cd /Users/hujiaxi/Documents/projects/CmdBox && python3 -c "from services.data_service import DataService; print('DataService 导入成功')"`
Expected: `DataService 导入成功`

- [ ] **Step 7: Commit**

```bash
git add services/data_service.py
git commit -m "feat: DataService 新增 Question CRUD 方法"
```

---

## Chunk 2: UI 组件（Card + List + Dialog）

### Task 3: 创建 QuestionCard 组件

**Files:**
- Create: `views/question_card.py`

- [ ] **Step 1: 创建 `views/question_card.py`**

```python
# views/question_card.py
import flet as ft
from typing import Callable
from models.question import Question

# 优先级颜色配置（复用任务卡片的配色）
PRIORITY_COLORS = {
    "high": (ft.Colors.RED_100, ft.Colors.RED_700, ft.Colors.RED_500),
    "medium": (ft.Colors.AMBER_100, ft.Colors.AMBER_700, ft.Colors.AMBER_500),
    "low": (ft.Colors.GREEN_100, ft.Colors.GREEN_700, ft.Colors.GREEN_500),
}

PRIORITY_LABELS = {"high": "高", "medium": "中", "low": "低"}


class QuestionCard(ft.Container):
    """问题卡片组件"""

    def __init__(
        self,
        question: Question,
        on_toggle_asked: Callable[[Question], None],
        on_edit: Callable[[Question], None],
        on_delete: Callable[[Question], None]
    ):
        super().__init__()
        self.question = question
        self.on_toggle_asked = on_toggle_asked
        self.on_edit = on_edit
        self.on_delete = on_delete

        _, _, border_color = PRIORITY_COLORS.get(question.priority, PRIORITY_COLORS["medium"])

        self.bgcolor = ft.Colors.GREY_50 if question.asked else ft.Colors.WHITE
        self.border = ft.border.only(left=ft.border.BorderSide(3, border_color))
        self.border_radius = 10
        self.padding = ft.padding.symmetric(horizontal=10, vertical=6)
        self.content = self._build_content()

    def _build_content(self) -> ft.Row:
        question = self.question
        _, label_color, _ = PRIORITY_COLORS.get(question.priority, PRIORITY_COLORS["medium"])
        priority_label = PRIORITY_LABELS.get(question.priority, "中")

        # 左侧：checkbox + 标题 + 描述 + 解答摘要
        text_controls = [
            ft.Text(
                question.title,
                size=15,
                weight=ft.FontWeight.W_600,
                color=ft.Colors.GREY_500 if question.asked else ft.Colors.GREY_800,
                overflow=ft.TextOverflow.ELLIPSIS,
                max_lines=1
            ),
        ]

        if question.description:
            text_controls.append(
                ft.Text(
                    "· " + question.description,
                    size=13,
                    color=ft.Colors.GREY_500 if question.asked else ft.Colors.GREY_600,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    max_lines=1
                )
            )

        if question.answer:
            text_controls.append(
                ft.Text(
                    "💬 " + question.answer,
                    size=12,
                    color=ft.Colors.GREY_400 if question.asked else ft.Colors.BLUE_400,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    max_lines=1
                )
            )

        left_content = ft.Row(
            [
                ft.IconButton(
                    icon=ft.Icons.CHECK_CIRCLE if question.asked else ft.Icons.RADIO_BUTTON_UNCHECKED,
                    icon_size=20,
                    icon_color=ft.Colors.PURPLE if question.asked else ft.Colors.GREY_400,
                    tooltip="切换询问状态",
                    on_click=lambda e: self.on_toggle_asked(self.question),
                    style=ft.ButtonStyle(padding=0)
                ),
                *text_controls,
            ],
            spacing=6,
            tight=True,
            expand=True
        )

        # 右侧：优先级标签 + 编辑 + 删除
        right_controls = ft.Row([
            ft.Container(
                content=ft.Text(priority_label, size=11, color=label_color, weight=ft.FontWeight.W_500),
                bgcolor=PRIORITY_COLORS.get(question.priority, PRIORITY_COLORS["medium"])[0],
                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                border_radius=8
            ),
            ft.IconButton(
                icon=ft.Icons.EDIT_OUTLINED,
                icon_size=14,
                icon_color=ft.Colors.GREY_500,
                tooltip="编辑",
                on_click=lambda e: self.on_edit(self.question)
            ),
            ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                icon_size=14,
                icon_color=ft.Colors.GREY_500,
                tooltip="删除",
                on_click=lambda e: self.on_delete(self.question)
            ),
        ], spacing=0, tight=True)

        return ft.Row(
            [left_content, right_controls],
            spacing=8,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
```

- [ ] **Step 2: 验证 QuestionCard 可导入**

Run: `cd /Users/hujiaxi/Documents/projects/CmdBox && python3 -c "from views.question_card import QuestionCard; print('QuestionCard 导入成功')"`
Expected: `QuestionCard 导入成功`

- [ ] **Step 3: Commit**

```bash
git add views/question_card.py
git commit -m "feat: 新增 QuestionCard 卡片组件"
```

---

### Task 4: 创建 QuestionList 组件

**Files:**
- Create: `views/question_list.py`

- [ ] **Step 1: 创建 `views/question_list.py`**

```python
# views/question_list.py
import flet as ft
from typing import List, Callable
from models.question import Question
from views.question_card import QuestionCard

# 排序模式：(mode_key, icon, tooltip)
SORT_MODES = [
    ("priority", ft.Icons.FLAG, "按优先级排序"),
    ("time", ft.Icons.SCHEDULE, "按时间排序"),
    ("status", ft.Icons.CHECKLIST, "按状态排序"),
]

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


class QuestionList(ft.Column):
    """问题列表组件"""

    def __init__(
        self,
        on_toggle_asked: Callable[[Question], None],
        on_edit: Callable[[Question], None],
        on_delete: Callable[[Question], None],
        on_add_question: Callable[[], None],
        on_clear_asked: Callable[[], None] = None
    ):
        super().__init__()
        self.on_toggle_asked = on_toggle_asked
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_add_question = on_add_question
        self.on_clear_asked = on_clear_asked
        self.questions: List[Question] = []
        self.asked_expanded = False
        self.sort_mode_index = 0  # 默认按优先级

        self.expand = True
        self.scroll = ft.ScrollMode.AUTO
        self.controls = self._build_empty_state()

    def _get_sorted_questions(self) -> List[Question]:
        """根据当前排序模式排序问题"""
        mode = SORT_MODES[self.sort_mode_index][0]
        questions = list(self.questions)
        if mode == "priority":
            questions.sort(key=lambda q: PRIORITY_ORDER.get(q.priority, 1))
        elif mode == "time":
            questions.sort(key=lambda q: q.created_at or "", reverse=True)
        elif mode == "status":
            # 待询问在前，已询问在后；同状态按优先级排序
            questions.sort(key=lambda q: (q.asked, PRIORITY_ORDER.get(q.priority, 1)))
        return questions

    def _build_sort_bar(self) -> ft.Control:
        """构建排序切换栏"""
        _, icon, tooltip = SORT_MODES[self.sort_mode_index]
        return ft.Container(
            content=ft.Row([
                ft.Container(expand=True),
                ft.IconButton(
                    icon=icon,
                    icon_size=16,
                    icon_color=ft.Colors.GREY_500,
                    tooltip=tooltip,
                    on_click=self._cycle_sort_mode,
                    style=ft.ButtonStyle(padding=4),
                ),
            ], spacing=0, tight=True),
            padding=ft.padding.only(right=4, top=2),
        )

    def _cycle_sort_mode(self, e):
        self.sort_mode_index = (self.sort_mode_index + 1) % len(SORT_MODES)
        self.controls = self._build_question_cards()
        self.update()

    def _build_empty_state(self) -> List[ft.Control]:
        return [
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.HELP_OUTLINE, size=48, color=ft.Colors.GREY_400),
                    ft.Text("暂无问题", color=ft.Colors.GREY_500),
                    ft.Text("点击下方按钮添加第一个问题", size=12, color=ft.Colors.GREY_400),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
                alignment=ft.Alignment(0.5, 0.5),
                expand=True
            )
        ]

    def _build_question_card(self, question: Question) -> QuestionCard:
        return QuestionCard(
            question=question,
            on_toggle_asked=self.on_toggle_asked,
            on_edit=self.on_edit,
            on_delete=self.on_delete
        )

    def _build_question_cards(self) -> List[ft.Control]:
        if not self.questions:
            return self._build_empty_state()

        sorted_questions = self._get_sorted_questions()
        pending = [q for q in sorted_questions if not q.asked]
        asked = [q for q in sorted_questions if q.asked]

        cards = []

        # 排序切换栏
        cards.append(self._build_sort_bar())

        # 待询问问题
        if pending:
            for question in pending:
                cards.append(self._build_question_card(question))
        else:
            cards.append(ft.Container(
                content=ft.Text("暂无待询问问题", size=13, color=ft.Colors.GREY_400),
                padding=ft.padding.symmetric(vertical=12),
            ))

        # 已询问问题（折叠区域）
        if asked:
            cards.append(ft.Divider(height=1))

            expand_icon = ft.Icons.EXPAND_MORE if self.asked_expanded else ft.Icons.CHEVRON_RIGHT
            header_row = [
                ft.Container(
                    content=ft.Row([
                        ft.Icon(expand_icon, size=16, color=ft.Colors.GREY_500),
                        ft.Text(f"已询问 ({len(asked)})", size=12, color=ft.Colors.GREY_500),
                    ], spacing=4, tight=True),
                    on_click=self._toggle_asked_section,
                ),
                ft.Container(expand=True),
            ]
            if self.on_clear_asked:
                header_row.append(
                    ft.IconButton(
                        icon=ft.Icons.DELETE_SWEEP,
                        icon_size=14,
                        icon_color=ft.Colors.GREY_400,
                        tooltip="清除已询问问题",
                        on_click=lambda e: self.on_clear_asked(),
                    )
                )
            asked_header = ft.Container(
                content=ft.Row(header_row, spacing=4, tight=True),
                padding=ft.padding.symmetric(vertical=6, horizontal=4),
            )
            cards.append(asked_header)

            if self.asked_expanded:
                for question in asked:
                    cards.append(self._build_question_card(question))

        # 底部占位，为 FAB 按钮预留空间
        cards.append(ft.Container(height=80))

        return cards

    def _toggle_asked_section(self, e):
        self.asked_expanded = not self.asked_expanded
        self.controls = self._build_question_cards()
        self.update()

    def update_questions(self, questions: List[Question]):
        self.questions = questions
        self.controls = self._build_question_cards()
        self.update()
```

- [ ] **Step 2: 验证 QuestionList 可导入**

Run: `cd /Users/hujiaxi/Documents/projects/CmdBox && python3 -c "from views.question_list import QuestionList; print('QuestionList 导入成功')"`
Expected: `QuestionList 导入成功`

- [ ] **Step 3: Commit**

```bash
git add views/question_list.py
git commit -m "feat: 新增 QuestionList 列表组件"
```

---

### Task 5: 新增 QuestionDialog

**Files:**
- Modify: `views/dialogs.py:8` (import)
- Modify: `views/dialogs.py:723` (TaskDialog 类结束后新增 QuestionDialog)

- [ ] **Step 1: 添加 Question 导入**

在 `views/dialogs.py` 第 8 行 `from models.task import Task` 后新增：
```python
from models.question import Question
```

- [ ] **Step 2: 在 TaskDialog 类后新增 QuestionDialog**

在 `views/dialogs.py` 文件末尾（第 723 行 `TaskDialog` 类结束后）新增：

```python

class QuestionDialog(ft.AlertDialog):
    """问题新建/编辑对话框"""

    def __init__(
        self,
        title: str,
        question: Optional[Question] = None,
        on_save: Callable[[str, str, str, str], None] = None
    ):
        super().__init__()
        self.modal = True
        self.title = ft.Text(title)
        self.on_save_callback = on_save

        self.title_field = ft.TextField(
            label="问题标题",
            value=question.title if question else "",
            autofocus=True,
            text_size=13
        )
        self.desc_field = ft.TextField(
            label="问题描述（可选）",
            value=question.description if question else "",
            multiline=True,
            max_lines=3,
            text_size=13
        )
        self.answer_field = ft.TextField(
            label="解答（可选）",
            value=question.answer if question else "",
            multiline=True,
            min_lines=2,
            max_lines=4,
            text_size=13
        )
        self.priority_dropdown = ft.Dropdown(
            label="优先级",
            options=[
                ft.dropdown.DropdownOption("high", "高优先级"),
                ft.dropdown.DropdownOption("medium", "中优先级"),
                ft.dropdown.DropdownOption("low", "低优先级"),
            ],
            value=question.priority if question else "medium",
            text_size=13
        )

        self.content = ft.Container(
            content=ft.Column([
                self.title_field,
                self.desc_field,
                self.answer_field,
                self.priority_dropdown
            ], tight=True, spacing=12),
            width=350
        )
        self.actions = [
            ft.TextButton("取消", on_click=self._on_cancel),
            ft.TextButton("保存", on_click=self._on_save)
        ]

    def _on_cancel(self, e):
        if self.page:
            self.page.pop_dialog()
            self.page.update()

    def _on_save(self, e):
        title = (self.title_field.value or "").strip()
        description = (self.desc_field.value or "").strip()
        answer = (self.answer_field.value or "").strip()
        priority = self.priority_dropdown.value or "medium"
        if self.on_save_callback:
            self.on_save_callback(title, description, answer, priority)
        if self.page:
            self.page.pop_dialog()
            self.page.update()
```

- [ ] **Step 3: 验证 QuestionDialog 可导入**

Run: `cd /Users/hujiaxi/Documents/projects/CmdBox && python3 -c "from views.dialogs import QuestionDialog; print('QuestionDialog 导入成功')"`
Expected: `QuestionDialog 导入成功`

- [ ] **Step 4: Commit**

```bash
git add views/dialogs.py
git commit -m "feat: 新增 QuestionDialog 对话框"
```

---

## Chunk 3: 应用集成（Sidebar + App）

### Task 6: 侧边栏新增问题板块入口

**Files:**
- Modify: `views/sidebar.py:11-146` (构造函数和 _build_content)
- Modify: `views/sidebar.py:198-207` (update_boards)

- [ ] **Step 1: 修改 Sidebar 构造函数，新增 questions 相关参数**

将 `views/sidebar.py` 的 `__init__` 方法（第 11-34 行）替换为：

```python
    def __init__(
        self,
        boards: List[Board],
        on_board_select: Callable[[str], None],
        on_add_board: Callable[[], None],
        on_edit_board: Callable[[str], None],
        on_delete_board: Callable[[str], None],
        on_reorder_boards: Callable[[List[str]], None],
        selected_board_id: Optional[str] = None,
        favorites_board_id: Optional[str] = None,
        tasks_board_id: Optional[str] = None,
        questions_board_id: Optional[str] = None,
        pending_task_count: int = 0,
        pending_question_count: int = 0
    ):
        super().__init__()
        self.boards = boards
        self.on_board_select = on_board_select
        self.on_add_board = on_add_board
        self.on_edit_board = on_edit_board
        self.on_delete_board = on_delete_board
        self.on_reorder_boards = on_reorder_boards
        self.selected_board_id = selected_board_id
        self.favorites_board_id = favorites_board_id
        self.tasks_board_id = tasks_board_id
        self.questions_board_id = questions_board_id
        self.pending_task_count = pending_task_count
        self.pending_question_count = pending_question_count

        self.width = 180
        self.bgcolor = ft.Colors.WHITE
        self.padding = 5
        self.content = self._build_content()
```

- [ ] **Step 2: 在 `_build_content` 方法中，在任务板块构建（第 146 行 `tasks_item` 块结束）和收藏板块构建（第 89 行 `fav_item` 块开始）之间插入问题板块**

在 `views/sidebar.py` 的 `_build_content` 方法中，找到这段注释和代码：

```python
        # 普通板块列表（可拖拽排序）
```

在它之前（即 `tasks_item` 构建块结束后，`# 普通板块列表` 注释之前），插入问题板块构建代码：

```python
        # 问题板块（固定，不可拖动）
        questions_item = None
        if self.questions_board_id:
            is_selected = self.selected_board_id == self.questions_board_id
            # 待询问数量徽章
            q_badge = None
            if self.pending_question_count > 0:
                q_badge = ft.Container(
                    content=ft.Text(
                        str(self.pending_question_count),
                        size=10, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER
                    ),
                    bgcolor=ft.Colors.PURPLE_500,
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=5, vertical=1),
                )
            questions_row_controls = [
                ft.Container(
                    content=ft.Icon(ft.Icons.HELP_OUTLINE, size=16, color=ft.Colors.PURPLE),
                    margin=ft.margin.only(left=-7)
                ),
                ft.Container(width=2),
                ft.Text("问题", size=13, weight=ft.FontWeight.W_600 if is_selected else ft.FontWeight.NORMAL,
                        color=ft.Colors.PURPLE_700 if is_selected else ft.Colors.GREY_700),
                ft.Container(content=None, expand=True),
            ]
            if q_badge:
                questions_row_controls.append(q_badge)
            questions_item = ft.Container(
                content=ft.Row(questions_row_controls, spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=14,
                border_radius=8,
                bgcolor=ft.Colors.PURPLE_50 if is_selected else ft.Colors.TRANSPARENT,
                border=ft.border.only(left=ft.border.BorderSide(3, ft.Colors.PURPLE_500)) if is_selected else None,
                on_click=lambda e: self.on_board_select(self.questions_board_id)
            )

```

- [ ] **Step 3: 在布局构建中加入问题板块**

在 `_build_content` 方法的布局构建部分（第 174-195 行），找到：

```python
        # 任务板块在顶部
        if tasks_item:
            content_items.append(tasks_item)

        # 收藏板块
        if fav_item:
            content_items.append(fav_item)
```

替换为：

```python
        # 任务板块在顶部
        if tasks_item:
            content_items.append(tasks_item)

        # 问题板块
        if questions_item:
            content_items.append(questions_item)

        # 收藏板块
        if fav_item:
            content_items.append(fav_item)
```

- [ ] **Step 4: 修改 `update_boards` 方法**

将 `update_boards` 方法（第 198-207 行）替换为：

```python
    def update_boards(self, boards: List[Board], selected_id: Optional[str] = None, favorites_id: Optional[str] = None, tasks_id: Optional[str] = None, questions_id: Optional[str] = None, pending_task_count: int = 0, pending_question_count: int = 0):
        self.boards = boards
        self.selected_board_id = selected_id
        if favorites_id:
            self.favorites_board_id = favorites_id
        if tasks_id:
            self.tasks_board_id = tasks_id
        if questions_id:
            self.questions_board_id = questions_id
        self.pending_task_count = pending_task_count
        self.pending_question_count = pending_question_count
        self.content = self._build_content()
        self.update()
```

- [ ] **Step 5: 验证 Sidebar 可导入**

Run: `cd /Users/hujiaxi/Documents/projects/CmdBox && python3 -c "from views.sidebar import Sidebar; print('Sidebar 导入成功')"`
Expected: `Sidebar 导入成功`

- [ ] **Step 6: Commit**

```bash
git add views/sidebar.py
git commit -m "feat: 侧边栏新增问题板块入口"
```

---

### Task 7: app.py 集成问题板块

**Files:**
- Modify: `app.py:17` (import)
- Modify: `app.py:23` (dialogs import)
- Modify: `app.py:45` (常量)
- Modify: `app.py:262-268` (QuestionList 实例)
- Modify: `app.py:295-304` (main_content)
- Modify: `app.py:341-355` (_refresh_sidebar)
- Modify: `app.py:357-376` (_on_board_select)
- Modify: `app.py:378-386` (_on_search)
- Modify: `app.py:443-456` (_refresh_board_desc)
- Modify: `app.py:626-631` (_show_task_list)
- Modify: `app.py:641-646` (_on_fab_click)

- [ ] **Step 1: 添加 Question 相关导入**

在 `app.py` 第 17 行 `from models.task import Task` 后新增：
```python
from models.question import Question
```

在第 21 行 `from views.task_list import TaskList` 后新增：
```python
from views.question_list import QuestionList
```

在第 23 行 dialogs 导入末尾，将：
```python
from views.dialogs import BoardDialog, CommandDialog, ConfirmDialog, EditAndCopyDialog, SettingsDialog, TaskDialog
```
改为：
```python
from views.dialogs import BoardDialog, CommandDialog, ConfirmDialog, EditAndCopyDialog, SettingsDialog, TaskDialog, QuestionDialog
```

- [ ] **Step 2: 新增 QUESTIONS_BOARD_ID 常量**

在 `app.py` 第 45 行 `self.TASKS_BOARD_ID = "__tasks__"` 后新增：
```python
        # 问题板块ID（虚拟板块，不存储在数据中）
        self.QUESTIONS_BOARD_ID = "__questions__"
```

- [ ] **Step 3: 新增 QuestionList 实例**

在 `app.py` 的 TaskList 实例化后（第 268 行后），新增：
```python

        # 问题列表
        self.question_list = QuestionList(
            on_toggle_asked=self._on_toggle_question_asked,
            on_edit=self._on_edit_question,
            on_delete=self._on_delete_question,
            on_add_question=self._on_add_question,
            on_clear_asked=self._on_clear_asked_questions
        )
```

- [ ] **Step 4: 新增 question_list_container 并修改 main_content**

在 `app.py` 的 `task_list_container` 定义后（第 299 行后），新增：
```python
        self.question_list_container = ft.Container(
            content=self.question_list, expand=True,
            padding=ft.padding.only(left=5, right=5, top=4, bottom=5),
            visible=False
        )
```

将 `main_content` 从：
```python
        main_content = ft.Column([
            self.board_desc_container,
            self.command_list_container,
            self.task_list_container,
        ], expand=True, spacing=0)
```
改为：
```python
        main_content = ft.Column([
            self.board_desc_container,
            self.command_list_container,
            self.task_list_container,
            self.question_list_container,
        ], expand=True, spacing=0)
```

- [ ] **Step 5: 修改 `_refresh_sidebar` 方法**

将 `_refresh_sidebar` 方法（第 341-355 行）中的计算和调用更新：

```python
    def _refresh_sidebar(self):
        """刷新侧边栏"""
        pending_count = len([t for t in self.data_service.tasks if not t.completed])
        pending_question_count = len([q for q in self.data_service.questions if not q.asked])
        self.sidebar.update_boards(
            self.data_service.boards,
            self.selected_board_id,
            self.FAVORITES_BOARD_ID,
            tasks_id=self.TASKS_BOARD_ID,
            questions_id=self.QUESTIONS_BOARD_ID,
            pending_task_count=pending_count,
            pending_question_count=pending_question_count
        )
        self.search_bar.update_boards(self.data_service.boards)
        self.search_bar.update_tags(self._get_all_tags())
        # 同时更新指令列表的板块字典
        boards_dict = {b.id: b for b in self.data_service.boards}
        self.command_list.update_boards(boards_dict)
```

- [ ] **Step 6: 修改 `_on_board_select` 方法，新增问题板块分支**

将 `_on_board_select` 方法（第 357-376 行）中，在 `elif board_id == self.TASKS_BOARD_ID:` 块之后、`else:` 之前，新增：

```python
        elif board_id == self.QUESTIONS_BOARD_ID:
            # 问题板块
            self.show_favorites_only = False
            self.search_board_ids = None
            self._show_question_list()
```

- [ ] **Step 7: 修改 `_on_search` 方法，新增问题板块搜索分支**

将 `_on_search` 方法（第 378-386 行）中的条件判断更新：

```python
    def _on_search(self, keyword: str, board_ids: Optional[List[str]], tag: Optional[str] = None):
        """搜索"""
        self.search_keyword = keyword
        self.search_board_ids = board_ids
        self.search_tag = tag
        if self.selected_board_id == self.TASKS_BOARD_ID:
            self._refresh_tasks()
        elif self.selected_board_id == self.QUESTIONS_BOARD_ID:
            self._refresh_questions()
        else:
            self._refresh_commands()
```

- [ ] **Step 8: 修改 `_refresh_board_desc` 方法，排除问题板块**

将 `_refresh_board_desc` 方法（第 443-456 行）中的排除条件更新：

```python
    def _refresh_board_desc(self):
        """刷新板块描述卡片"""
        # 收藏板块、任务板块和问题板块不显示描述卡片
        if self.selected_board_id in (self.FAVORITES_BOARD_ID, self.TASKS_BOARD_ID, self.QUESTIONS_BOARD_ID):
            self.board_desc_card.update_board(None)
            self.board_desc_container.visible = False
        elif self.selected_board_id:
            board = self.data_service.get_board(self.selected_board_id)
            self.board_desc_card.update_board(board)
            self.board_desc_container.visible = bool(board and board.description)
        else:
            self.board_desc_card.update_board(None)
            self.board_desc_container.visible = False
        self.page.update()
```

- [ ] **Step 9: 修改 `_show_task_list` 方法，处理三态切换**

将 `_show_task_list` 方法（第 626-631 行）替换为：

```python
    def _show_task_list(self, show_tasks: bool):
        """切换右侧内容区：指令列表 / 任务列表"""
        self.command_list_container.visible = not show_tasks
        self.task_list_container.visible = show_tasks
        self.question_list_container.visible = False
        if show_tasks:
            self._refresh_tasks()
```

- [ ] **Step 10: 新增 `_show_question_list` 方法**

在 `_show_task_list` 方法后新增：

```python

    def _show_question_list(self):
        """切换右侧内容区：问题列表"""
        self.command_list_container.visible = False
        self.task_list_container.visible = False
        self.question_list_container.visible = True
        self._refresh_questions()
```

- [ ] **Step 11: 修改 `_on_fab_click`，新增问题板块分发**

将 `_on_fab_click` 方法（第 641-646 行）替换为：

```python
    def _on_fab_click(self, e):
        """FAB 按钮点击分发"""
        if self.selected_board_id == self.TASKS_BOARD_ID:
            self._on_add_task()
        elif self.selected_board_id == self.QUESTIONS_BOARD_ID:
            self._on_add_question()
        else:
            self._on_add_command()
```

- [ ] **Step 12: 新增 `_refresh_questions` 方法**

在 `_refresh_tasks` 方法后新增：

```python

    def _refresh_questions(self):
        """刷新问题列表"""
        questions = self.data_service.get_sorted_questions()
        if self.search_keyword:
            keyword = self.search_keyword.lower()
            questions = [q for q in questions if keyword in q.title.lower() or keyword in q.description.lower() or keyword in q.answer.lower()]
        self.question_list.update_questions(questions)
```

- [ ] **Step 13: 新增问题相关回调方法**

在 `_on_clear_completed_tasks` 方法后（任务相关方法区块结束处），新增：

```python

    # ==================== 问题相关 ====================

    def _on_add_question(self):
        """添加问题"""
        def on_save(title: str, description: str, answer: str, priority: str):
            if title:
                question = Question.create(title=title, description=description, answer=answer, priority=priority)
                self.data_service.add_question(question)
                self._refresh_questions()
                self._refresh_sidebar()
            self.page.pop_dialog()
            self.page.update()

        dialog = QuestionDialog("新建问题", on_save=on_save)
        self.page.show_dialog(dialog)
        self.page.update()

    def _on_edit_question(self, question: Question):
        """编辑问题"""
        def on_save(title: str, description: str, answer: str, priority: str):
            if title:
                question.update(title=title, description=description, answer=answer, priority=priority)
                self.data_service.update_question(question)
                self._refresh_questions()
                self._refresh_sidebar()
            self.page.pop_dialog()
            self.page.update()

        dialog = QuestionDialog("编辑问题", question=question, on_save=on_save)
        self.page.show_dialog(dialog)
        self.page.update()

    def _on_delete_question(self, question: Question):
        """删除问题"""
        def on_confirm():
            self.data_service.delete_question(question.id)
            self._refresh_questions()
            self._refresh_sidebar()
            self.page.pop_dialog()
            self.page.update()

        dialog = ConfirmDialog(
            "确认删除",
            f"确定要删除问题「{question.title}」吗？",
            on_confirm=on_confirm
        )
        self.page.show_dialog(dialog)
        self.page.update()

    def _on_toggle_question_asked(self, question: Question):
        """切换问题询问状态"""
        question.update(asked=not question.asked)
        self.data_service.update_question(question)
        self._refresh_questions()
        self._refresh_sidebar()

    def _on_clear_asked_questions(self):
        """清除所有已询问问题"""
        def on_confirm():
            self.data_service.delete_asked_questions()
            self._refresh_questions()
            self._refresh_sidebar()
            self.page.pop_dialog()
            self.page.update()

        asked_count = len([q for q in self.data_service.questions if q.asked])
        dialog = ConfirmDialog(
            "确认清除",
            f"确定要清除 {asked_count} 个已询问的问题吗？",
            on_confirm=on_confirm
        )
        self.page.show_dialog(dialog)
        self.page.update()
```

- [ ] **Step 14: 运行应用进行端到端验证**

Run: `cd /Users/hujiaxi/Documents/projects/CmdBox && python3 main.py`

验证清单：
1. 侧边栏显示顺序：任务 → 问题（紫色）→ 收藏 → 普通板块
2. 点击"问题"板块，右侧显示空状态"暂无问题"
3. 点击 FAB 按钮，弹出新建问题对话框（标题、描述、解答、优先级）
4. 创建问题后卡片正常显示（标题、描述、解答摘要、优先级标签）
5. 点击勾选按钮可切换"已询问/待询问"状态
6. 已询问问题在折叠区域显示
7. 搜索功能可搜索问题标题、描述和解答
8. 重启应用后问题数据保持

- [ ] **Step 15: Commit**

```bash
git add app.py
git commit -m "feat: 集成问题板块到主应用"
```
