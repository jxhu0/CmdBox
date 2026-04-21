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

        # 左侧文本区：标题 + 描述 + 解答（纵向排列）
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
                    question.description,
                    size=13,
                    color=ft.Colors.GREY_500 if question.asked else ft.Colors.GREY_600,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    max_lines=1
                )
            )

        if question.answer:
            text_controls.append(
                ft.Text(
                    "\U0001f4ac " + question.answer,
                    size=12,
                    color=ft.Colors.GREY_400 if question.asked else ft.Colors.BLUE_400,
                )
            )

        # 底部行：时间戳
        bottom_controls = []
        if question.asked and question.asked_at:
            bottom_controls.append(
                ft.Text(question.asked_at, size=11, color=ft.Colors.GREY_400)
            )

        left_column_controls = [
            ft.Column(text_controls, spacing=2, expand=True),
        ]
        if bottom_controls:
            left_column_controls.append(ft.Row(bottom_controls, spacing=6))

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
                ft.Column(
                    left_column_controls,
                    spacing=2,
                    expand=True
                ),
            ],
            spacing=6,
            tight=True,
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
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
