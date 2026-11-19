# views/task_card.py
import flet as ft
from views.isolated import IsolatedControl
from typing import Callable
from models.task import Task

# 优先级颜色配置
PRIORITY_COLORS = {
    "high": (ft.Colors.RED_100, ft.Colors.RED_700, ft.Colors.RED_500),
    "medium": (ft.Colors.AMBER_100, ft.Colors.AMBER_700, ft.Colors.AMBER_500),
    "low": (ft.Colors.GREEN_100, ft.Colors.GREEN_700, ft.Colors.GREEN_500),
}

PRIORITY_LABELS = {"high": "高", "medium": "中", "low": "低"}


class TaskCard(IsolatedControl, ft.Container):
    """任务卡片组件"""

    def __init__(
        self,
        task: Task,
        on_toggle_complete: Callable[[Task], None],
        on_toggle_in_progress: Callable[[Task], None],
        on_edit: Callable[[Task], None],
        on_delete: Callable[[Task], None]
    ):
        super().__init__()
        self.task = task
        self.on_toggle_complete = on_toggle_complete
        self.on_toggle_in_progress = on_toggle_in_progress
        self.on_edit = on_edit
        self.on_delete = on_delete

        _, _, border_color = PRIORITY_COLORS.get(task.priority, PRIORITY_COLORS["medium"])

        if task.completed:
            self.bgcolor = ft.Colors.GREY_50
        elif task.in_progress:
            self.bgcolor = ft.Colors.BLUE_50
        else:
            self.bgcolor = ft.Colors.WHITE
        self.border = ft.border.only(left=ft.border.BorderSide(3, border_color))
        self.border_radius = 10
        self.padding = ft.padding.symmetric(horizontal=10, vertical=6)
        self.content = self._build_content()

    def _build_content(self) -> ft.Row:
        task = self.task
        _, label_color, _ = PRIORITY_COLORS.get(task.priority, PRIORITY_COLORS["medium"])
        priority_label = PRIORITY_LABELS.get(task.priority, "中")

        # 左侧：checkbox + 标题 + 描述
        title = ft.Text(
            task.title,
            size=15,
            weight=ft.FontWeight.W_600,
            color=ft.Colors.GREY_500 if task.completed else ft.Colors.GREY_800,
            expand=True,
            expand_loose=True,
            overflow=ft.TextOverflow.ELLIPSIS,
            max_lines=1,
            tooltip=task.title
        )
        text_content = title

        if task.description:
            description = ft.Text(
                "· " + task.description,
                size=13,
                color=ft.Colors.GREY_500 if task.completed else ft.Colors.GREY_600,
                expand=True,
                expand_loose=True,
                overflow=ft.TextOverflow.ELLIPSIS,
                max_lines=1
            )
            self._title_text = title
            self._description_text = description
            self._title_natural_width = None
            self._text_available_width = None
            # Row 中两个 Flexible 会平分空间。使用同字体的原生测量值，
            # 先给标题自然宽度，再把剩余空间交给描述。
            text_content = ft.Stack([
                ft.Row([title, description], spacing=6, tight=True),
                ft.Row([
                    ft.Text(task.title, size=title.size, weight=title.weight,
                            no_wrap=True, on_size_change=self._on_title_measured)
                ], left=0, top=0, right=0, height=0, opacity=0),
            ], expand=True, on_size_change=self._on_text_area_resized)

        left_row_controls = [
            ft.IconButton(
                icon=ft.Icons.CHECK_CIRCLE if task.completed else ft.Icons.RADIO_BUTTON_UNCHECKED,
                icon_size=20,
                icon_color=ft.Colors.GREEN if task.completed else ft.Colors.GREY_400,
                tooltip="切换完成状态",
                on_click=lambda e: self.on_toggle_complete(self.task),
                style=ft.ButtonStyle(padding=0)
            ),
            ft.IconButton(
                icon=ft.Icons.PLAY_CIRCLE_FILL if task.in_progress else ft.Icons.PLAY_CIRCLE_OUTLINE,
                icon_size=20,
                icon_color=ft.Colors.BLUE if task.in_progress else ft.Colors.GREY_400,
                tooltip="切换执行中状态",
                on_click=lambda e: self.on_toggle_in_progress(self.task),
                style=ft.ButtonStyle(padding=0)
            ),
            text_content,
        ]
        if task.completed and task.completed_at:
            completed_controls = [
                ft.Text(task.completed_at, size=11, color=ft.Colors.GREY_400)
            ]
            if task.recurring:
                completed_controls.append(
                    ft.Icon(ft.Icons.REPLAY, size=12, color=ft.Colors.GREY_400)
                )
            left_row_controls.append(
                ft.Row(completed_controls, spacing=4, tight=True)
            )

        left_content = ft.Row(
            left_row_controls,
            spacing=6,
            tight=True,
            expand=True
        )

        # 右侧：优先级标签 + 编辑 + 删除
        right_controls = ft.Row([
            ft.Container(
                content=ft.Text(priority_label, size=11, color=label_color, weight=ft.FontWeight.W_500),
                bgcolor=PRIORITY_COLORS.get(task.priority, PRIORITY_COLORS["medium"])[0],
                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                border_radius=8
            ),
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
        ], spacing=0, tight=True)

        return ft.Row(
            [left_content, right_controls],
            spacing=8,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

    def _on_title_measured(self, event):
        self._title_natural_width = event.width
        self._resize_inline_text()

    def _on_text_area_resized(self, event):
        self._text_available_width = event.width
        self._resize_inline_text()

    def _resize_inline_text(self):
        if self._title_natural_width is None or self._text_available_width is None:
            return
        available = max(0, self._text_available_width)
        width = min(self._title_natural_width, available)
        show_description = self._title_natural_width + 6 < available
        title, description = self._title_text, self._description_text
        if title.width == width and description.visible == show_description:
            return
        title.expand = None
        title.expand_loose = False
        title.width = width
        description.visible = show_description
        self.update()
