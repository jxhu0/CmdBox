# views/board_desc_card.py
import flet as ft
from typing import Callable, Optional
from models.board import Board


class BoardDescCard(ft.Container):
    """板块描述卡片组件"""

    def __init__(
        self,
        board: Optional[Board] = None,
        on_edit: Callable[[Board], None] = None
    ):
        super().__init__()
        self.board = board
        self.on_edit = on_edit
        self.padding = 12
        self.border_radius = 10
        self.margin = ft.margin.only(bottom=4)
        self.content = self._build_content()

    def _build_content(self):
        if not self.board or not self.board.description:
            return ft.Container()  # 空容器

        return ft.Container(
            bgcolor=ft.Colors.BLUE_50,
            border_radius=10,
            padding=12,
            border=ft.border.all(1, ft.Colors.BLUE_100),
            content=ft.Row([
                ft.Text(self.board.icon, size=16),
                ft.Text(self.board.name, size=14, weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_800),
                ft.Text("·", size=14, color=ft.Colors.GREY_400),
                ft.Text(self.board.description, size=13, color=ft.Colors.GREY_700, expand=True),
                ft.IconButton(
                    icon=ft.Icons.EDIT_OUTLINED,
                    icon_size=16,
                    tooltip="编辑描述",
                    on_click=lambda e: self.on_edit(self.board) if self.on_edit else None
                )
            ], spacing=8, alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        )

    def update_board(self, board: Optional[Board]):
        """更新板块信息"""
        self.board = board
        self.content = self._build_content()
        self.update()
