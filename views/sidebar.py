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
        on_edit_board: Callable[[str], None],
        on_delete_board: Callable[[str], None],
        selected_board_id: Optional[str] = None,
        favorites_board_id: Optional[str] = None
    ):
        super().__init__()
        self.boards = boards
        self.on_board_select = on_board_select
        self.on_add_board = on_add_board
        self.on_edit_board = on_edit_board
        self.on_delete_board = on_delete_board
        self.selected_board_id = selected_board_id
        self.favorites_board_id = favorites_board_id

        self.width = 180
        self.bgcolor = ft.Colors.WHITE
        self.padding = 5
        self.content = self._build_content()

    def _build_content(self) -> ft.Column:
        board_items = []

        # 收藏板块（固定在最上方）
        if self.favorites_board_id:
            is_selected = self.selected_board_id == self.favorites_board_id
            fav_item = ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.STAR, size=16, color=ft.Colors.AMBER),
                    ft.Container(width=2),  # 替代 emoji 占位
                    ft.Text("收藏", size=13, weight=ft.FontWeight.W_600 if is_selected else ft.FontWeight.NORMAL,
                            color=ft.Colors.AMBER_700 if is_selected else ft.Colors.GREY_700),
                    ft.Container(content=None, expand=True)  # 空置位，保持对齐
                ], spacing=4, tight=True),
                padding=14,
                border_radius=8,
                bgcolor=ft.Colors.AMBER_50 if is_selected else ft.Colors.TRANSPARENT,
                border=ft.border.only(left=ft.border.BorderSide(3, ft.Colors.AMBER_500)) if is_selected else None,
                on_click=lambda e: self.on_board_select(self.favorites_board_id)
            )
            board_items.append(fav_item)

        # 普通板块列表
        for board in self.boards:
            is_selected = board.id == self.selected_board_id
            item = ft.Container(
                content=ft.Row([
                    ft.Text(board.icon, size=16),
                    ft.Text(board.name, size=13, weight=ft.FontWeight.W_600 if is_selected else ft.FontWeight.NORMAL,
                            color=ft.Colors.BLUE_700 if is_selected else ft.Colors.GREY_700),
                    ft.Row([
                        ft.IconButton(
                            icon=ft.Icons.EDIT_OUTLINED,
                            icon_size=12,
                            tooltip="编辑板块",
                            on_click=lambda e, bid=board.id: self.on_edit_board(bid)
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_size=12,
                            tooltip="删除板块",
                            on_click=lambda e, bid=board.id: self.on_delete_board(bid)
                        )
                    ], spacing=0)
                ], spacing=4, tight=True),
                padding=8,
                border_radius=8,
                bgcolor=ft.Colors.BLUE_50 if is_selected else ft.Colors.TRANSPARENT,
                border=ft.border.only(left=ft.border.BorderSide(3, ft.Colors.BLUE_500)) if is_selected else None,
                on_click=lambda e, bid=board.id: self.on_board_select(bid)
            )
            board_items.append(item)

        # 新建按钮（固定在底部）
        add_btn = ft.Container(
            content=ft.TextButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.ADD, size=14, color=ft.Colors.BLUE_600),
                    ft.Text("新建板块", size=12, color=ft.Colors.BLUE_600)
                ]),
                on_click=lambda e: self.on_add_board()
            ),
            bgcolor=ft.Colors.BLUE_50,
            border_radius=8,
            padding=8
        )

        # 使用 Column 布局：标题 + 可滚动列表 + 固定底部按钮
        return ft.Column([
            ft.Text("板块", size=10, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD),
            ft.Container(
                content=ft.ListView(controls=board_items, expand=True),
                expand=True,
                padding=0
            ),
            add_btn
        ], tight=False, expand=True)

    def update_boards(self, boards: List[Board], selected_id: Optional[str] = None, favorites_id: Optional[str] = None):
        self.boards = boards
        self.selected_board_id = selected_id
        if favorites_id:
            self.favorites_board_id = favorites_id
        self.content = self._build_content()
        self.update()
