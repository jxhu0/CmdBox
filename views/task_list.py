# views/task_list.py
import flet as ft
from typing import List, Callable
from models.task import Task
from views.task_card import TaskCard


class TaskList(ft.Column):
    """任务列表组件"""

    def __init__(
        self,
        on_toggle_complete: Callable[[Task], None],
        on_edit: Callable[[Task], None],
        on_delete: Callable[[Task], None],
        on_add_task: Callable[[], None]
    ):
        super().__init__()
        self.on_toggle_complete = on_toggle_complete
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_add_task = on_add_task
        self.tasks: List[Task] = []

        self.expand = True
        self.scroll = ft.ScrollMode.AUTO
        self.controls = self._build_empty_state()

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

    def _build_task_cards(self) -> List[ft.Control]:
        if not self.tasks:
            return self._build_empty_state()

        cards = []
        for task in self.tasks:
            card = TaskCard(
                task=task,
                on_toggle_complete=self.on_toggle_complete,
                on_edit=self.on_edit,
                on_delete=self.on_delete
            )
            cards.append(card)

        # 添加底部占位，为 FAB 按钮预留空间
        cards.append(ft.Container(height=80))

        return cards

    def update_tasks(self, tasks: List[Task]):
        self.tasks = tasks
        self.controls = self._build_task_cards()
        self.update()
