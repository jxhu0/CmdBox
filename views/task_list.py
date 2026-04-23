# views/task_list.py
import flet as ft
from typing import List, Callable
from models.task import Task
from views.task_card import TaskCard

# 排序模式：(mode_key, icon, tooltip)
SORT_MODES = [
    ("priority", ft.Icons.FLAG, "按优先级排序"),
    ("time", ft.Icons.SCHEDULE, "按时间排序"),
    ("status", ft.Icons.CHECKLIST, "按状态排序"),
]

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


class TaskList(ft.Column):
    """任务列表组件"""

    def __init__(
        self,
        on_toggle_complete: Callable[[Task], None],
        on_toggle_in_progress: Callable[[Task], None],
        on_edit: Callable[[Task], None],
        on_delete: Callable[[Task], None],
        on_add_task: Callable[[], None],
        on_clear_completed: Callable[[], None] = None
    ):
        super().__init__()
        self.on_toggle_complete = on_toggle_complete
        self.on_toggle_in_progress = on_toggle_in_progress
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_add_task = on_add_task
        self.on_clear_completed = on_clear_completed
        self.tasks: List[Task] = []
        self.completed_expanded = False
        self.sort_mode_index = 0  # 默认按优先级

        self.expand = True
        self.scroll = ft.ScrollMode.AUTO
        self.controls = self._build_empty_state()

    def _get_sorted_tasks(self) -> List[Task]:
        """根据当前排序模式排序任务"""
        mode = SORT_MODES[self.sort_mode_index][0]
        tasks = list(self.tasks)
        if mode == "priority":
            # 执行中优先，再按优先级，再按创建时间
            tasks.sort(key=lambda t: (not t.in_progress, PRIORITY_ORDER.get(t.priority, 1), t.created_at or ""), reverse=False)
        elif mode == "time":
            # 执行中优先，再按时间倒序
            tasks.sort(key=lambda t: (not t.in_progress, ""), reverse=False)
            in_progress_tasks = [t for t in tasks if t.in_progress]
            other_tasks = [t for t in tasks if not t.in_progress]
            other_tasks.sort(key=lambda t: t.created_at or "", reverse=True)
            tasks = in_progress_tasks + other_tasks
        elif mode == "status":
            # 执行中 > 待办 > 已完成
            tasks.sort(key=lambda t: (2 if t.completed else (0 if t.in_progress else 1), PRIORITY_ORDER.get(t.priority, 1)))
        return tasks

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
        self.controls = self._build_task_cards()
        self.update()

    def _build_empty_state(self) -> List[ft.Control]:
        return [
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.CHECKLIST_OUTLINED, size=48, color=ft.Colors.GREY_400),
                    ft.Text("暂无任务", color=ft.Colors.GREY_500),
                    ft.Text("点击下方按钮添加第一个任务", size=12, color=ft.Colors.GREY_400),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
                alignment=ft.Alignment(0.5, 0.5),
                expand=True
            )
        ]

    def _build_task_card(self, task: Task) -> TaskCard:
        return TaskCard(
            task=task,
            on_toggle_complete=self.on_toggle_complete,
            on_toggle_in_progress=self.on_toggle_in_progress,
            on_edit=self.on_edit,
            on_delete=self.on_delete
        )

    def _build_task_cards(self) -> List[ft.Control]:
        if not self.tasks:
            return self._build_empty_state()

        sorted_tasks = self._get_sorted_tasks()
        pending = [t for t in sorted_tasks if not t.completed]
        completed = [t for t in sorted_tasks if t.completed]

        cards = []

        # 排序切换栏
        cards.append(self._build_sort_bar())

        # 待办任务
        if pending:
            for task in pending:
                cards.append(self._build_task_card(task))
        else:
            # 无待办任务时显示空状态
            cards.append(ft.Container(
                content=ft.Text("暂无待办任务", size=13, color=ft.Colors.GREY_400),
                padding=ft.padding.symmetric(vertical=12),
            ))

        # 已完成任务（折叠区域）
        if completed:
            cards.append(ft.Divider(height=1))

            expand_icon = ft.Icons.EXPAND_MORE if self.completed_expanded else ft.Icons.CHEVRON_RIGHT
            header_row = [
                ft.Container(
                    content=ft.Row([
                        ft.Icon(expand_icon, size=16, color=ft.Colors.GREY_500),
                        ft.Text(f"已完成 ({len(completed)})", size=12, color=ft.Colors.GREY_500),
                    ], spacing=4, tight=True),
                    on_click=self._toggle_completed_section,
                ),
                ft.Container(expand=True),
            ]
            if self.on_clear_completed:
                header_row.append(
                    ft.IconButton(
                        icon=ft.Icons.DELETE_SWEEP,
                        icon_size=14,
                        icon_color=ft.Colors.GREY_400,
                        tooltip="清除已完成任务",
                        on_click=lambda e: self.on_clear_completed(),
                    )
                )
            completed_header = ft.Container(
                content=ft.Row(header_row, spacing=4, tight=True),
                padding=ft.padding.symmetric(vertical=6, horizontal=4),
            )
            cards.append(completed_header)

            if self.completed_expanded:
                for task in completed:
                    cards.append(self._build_task_card(task))

        # 底部占位，为 FAB 按钮预留空间
        cards.append(ft.Container(height=80))

        return cards

    def _toggle_completed_section(self, e):
        self.completed_expanded = not self.completed_expanded
        self.controls = self._build_task_cards()
        self.update()

    def update_tasks(self, tasks: List[Task]):
        self.tasks = tasks
        self.controls = self._build_task_cards()
        self.update()
