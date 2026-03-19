# views/command_card.py
import flet as ft
from typing import Callable
from models.command import Command
from models.board import Board
from utils.helpers import truncate_text


class CommandCard(ft.Container):
    """指令卡片组件 - 紧凑布局设计，    """

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

        # 状态
        self._is_expanded = False
        self._is_truncated = len(command.content) > 100

        self.padding = 8
        self.border_radius = 8
        self.border = ft.border.all(1, ft.Colors.GREY_300)
        self.margin = ft.margin.only(bottom=6)

        self.content = self._build_content()

    def _toggle_expand(self, e):
        """切换展开/收起状态"""
        self._is_expanded = not self._is_expanded
        self.content = self._build_content()
        self.update()

    def _build_content(self) -> ft.Column:
        # 标题行（包含描述）
        title_controls = [
            ft.Icon(ft.Icons.STAR if self.command.is_favorite else ft.Icons.STAR_BORDER,
                    color=ft.Colors.AMBER if self.command.is_favorite else ft.Colors.GREY,
                    size=16),
            ft.Text(self.command.title, size=14, weight=ft.FontWeight.BOLD),
        ]

        # 如果有描述，添加到标题行
        if self.command.description:
            title_controls.append(
                ft.Text(" - " + self.command.description, size=12, color=ft.Colors.GREY_600)
            )

        title_row = ft.Row(title_controls, wrap=True)

        # 内容文本（根据展开状态决定是否截断）
        display_content = self.command.content if self._is_expanded else truncate_text(self.command.content, 100)
        content_text = ft.Text(
            display_content,
            size=13,
            color=ft.Colors.GREY_700
        )

        # 构建内容和标签的控件列表
        content_and_tags_controls = [content_text]

        # 添加标签
        for tag in self.command.tags[:3]:
            content_and_tags_controls.append(
                ft.Container(
                    content=ft.Text(tag, size=11, color=ft.Colors.BLUE_700),
                    bgcolor=ft.Colors.BLUE_50,
                    padding=4,
                    border_radius=4
                )
            )

        # "显示全部/收起"按钮（仅在内容被截断时显示）- 放在省略号同一行
        if self._is_truncated:
            content_and_tags_controls.append(
                ft.GestureDetector(
                    content=ft.Container(
                        content=ft.Row([
                            ft.Text("显示全部" if not self._is_expanded else "收起", size=10, color=ft.Colors.BLUE_700),
                            ft.Icon(ft.Icons.EXPAND_MORE if not self._is_expanded else ft.Icons.EXPAND_LESS, size=12, color=ft.Colors.BLUE_700),
                        ], spacing=2, tight=True),
                        padding=4,
                    ),
                    on_tap=self._toggle_expand
                )
            )

        # 内容和标签放在 Row 中，标签紧跟文本
        content_and_tags = ft.Row(
            content_and_tags_controls,
            spacing=6,
            wrap=True,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

        # 操作按钮行
        actions_row = ft.Row([
            ft.IconButton(
                icon=ft.Icons.CONTENT_COPY,
                icon_size=14,
                tooltip="复制",
                on_click=lambda e: self.on_copy(self.command)
            ),
            ft.IconButton(
                icon=ft.Icons.EDIT,
                icon_size=14,
                tooltip="编辑",
                on_click=lambda e: self.on_edit(self.command)
            ),
            ft.IconButton(
                icon=ft.Icons.STAR if self.command.is_favorite else ft.Icons.STAR_BORDER,
                icon_color=ft.Colors.AMBER if self.command.is_favorite else None,
                icon_size=14,
                tooltip="取消收藏" if self.command.is_favorite else "收藏",
                on_click=lambda e: self.on_toggle_favorite(self.command)
            ),
            ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                icon_size=14,
                tooltip="删除",
                on_click=lambda e: self.on_delete(self.command)
            )
        ], alignment=ft.MainAxisAlignment.END, spacing=0)

        # 构建内容列的子控件列表
        column_controls = [
            title_row,
            ft.Divider(height=2, color="transparent"),
            content_and_tags,
            ft.Divider(height=2, color="transparent"),
            actions_row
        ]

        return ft.Column(column_controls, spacing=0)