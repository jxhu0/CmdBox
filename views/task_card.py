# views/task_card.py
import flet as ft
from typing import Callable
from models.task import Task

# 优先级颜色配置
PRIORITY_COLORS = {
    "high": (ft.Colors.RED_100, ft.Colors.RED_700, ft.Colors.RED_500),
    "medium": (ft.Colors.AMBER_100, ft.Colors.AMBER_700, ft.Colors.AMBER_500),
    "low": (ft.Colors.GREEN_100, ft.Colors.GREEN_700, ft.Colors.GREEN_500),
}

PRIORITY_LABELS = {"high": "高", "medium": "中", "low": "低"}


class TaskCard(ft.Container):
    """任务卡片组件"""

    def __init__(
        self,
        task: Task,
        on_toggle_complete: Callable[[Task], None],
        on_edit: Callable[[Task], None],
        on_delete: Callable[[Task], None]
    ):
        super().__init__()
        self.task = task
        self.on_toggle_complete = on_toggle_complete
        self.on_edit = on_edit
        self.on_delete = on_delete

        _, _, border_color = PRIORITY_COLORS.get(task.priority, PRIORITY_COLORS["medium"])

        self.bgcolor = ft.Colors.GREY_50 if task.completed else ft.Colors.WHITE
        self.border = ft.border.only(left=ft.border.BorderSide(3, border_color))
        self.border_radius = 10
        self.padding = ft.padding.symmetric(horizontal=12, vertical=10)
        self.content = self._build_content()

    def _build_content(self) -> ft.Column:
        task = self.task
        _, label_color, _ = PRIORITY_COLORS.get(task.priority, PRIORITY_COLORS["medium"])
        priority_label = PRIORITY_LABELS.get(task.priority, "中")

        # 标题行：checkbox + 标题 + 优先级标签
        title_controls = [
            ft.IconButton(
                icon=ft.Icons.CHECK_CIRCLE if task.completed else ft.Icons.RADIO_BUTTON_UNCHECKED,
                icon_size=20,
                icon_color=ft.Colors.GREEN if task.completed else ft.Colors.GREY_400,
                tooltip="切换完成状态",
                on_click=lambda e: self.on_toggle_complete(self.task),
                style=ft.ButtonStyle(padding=0)
            ),
            ft.Text(
                task.title,
                size=13,
                weight=ft.FontWeight.W_600,
                color=ft.Colors.GREY_500 if task.completed else ft.Colors.GREY_800,
                expand=True,
                overflow=ft.TextOverflow.ELLIPSIS,
                max_lines=1
            ),
            ft.Container(
                content=ft.Text(priority_label, size=10, color=label_color, weight=ft.FontWeight.W_500),
                bgcolor=PRIORITY_COLORS.get(task.priority, PRIORITY_COLORS["medium"])[0],
                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                border_radius=8
            ),
        ]

        content_controls = [
            ft.Row(title_controls, spacing=4, alignment=ft.MainAxisAlignment.START)
        ]

        # 描述行
        if task.description:
            content_controls.append(
                ft.Container(
                    content=ft.Text(
                        task.description,
                        size=11,
                        color=ft.Colors.GREY_500 if task.completed else ft.Colors.GREY_600,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS
                    ),
                    margin=ft.margin.only(left=38)
                )
            )

        # 操作按钮行
        action_row = ft.Row([
            ft.IconButton(
                icon=ft.Icons.EDIT_OUTLINED,
                icon_size=14,
                icon_color=ft.Colors.GREY_500,
                tooltip="编辑",
                on_click=lambda e: self.on_edit(self.task)
            ),
            ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                icon_size=14,
                icon_color=ft.Colors.GREY_500,
                tooltip="删除",
                on_click=lambda e: self.on_delete(self.task)
            ),
        ], spacing=0, alignment=ft.MainAxisAlignment.END)

        content_controls.append(action_row)

        return ft.Column(content_controls, spacing=6, tight=True)
