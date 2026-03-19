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
        selected_board_id: Optional[str] = None
    ):
        super().__init__()
        self.boards = boards
        self.on_board_select = on_board_select
        self.on_add_board = on_add_board
        self.on_edit_board = on_edit_board
        self.on_delete_board = on_delete_board
        self.selected_board_id = selected_board_id

        self.width = 150
        self.bgcolor = ft.Colors.GREY_100
        self.padding = 5
        self.content = self._build_content()

    def _build_content(self) -> ft.Column:
        board_items = []
        for board in self.boards:
            is_selected = board.id == self.selected_board_id
            item = ft.Container(
                content=ft.Row([
                    ft.Text(board.icon, size=14),
                    ft.Text(board.name, size=12, weight=ft.FontWeight.BOLD if is_selected else ft.FontWeight.NORMAL),
                    ft.IconButton(
                        icon=ft.Icons.EDIT,
                        icon_size=9,
                        tooltip="编辑板块",
                        on_click=lambda e, bid=board.id: self.on_edit_board(bid)
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_size=9,
                        tooltip="删除板块",
                        on_click=lambda e, bid=board.id: self.on_delete_board(bid)
                    )
                ], spacing=1, tight=True),
                padding=2,
                border_radius=3,
                bgcolor=ft.Colors.BLUE_50 if is_selected else None,
                on_click=lambda e, bid=board.id: self.on_board_select(bid)
            )
            board_items.append(item)

        # 添加新建按钮
        add_btn = ft.TextButton(
            content=ft.Row([
                ft.Icon(ft.Icons.ADD, size=12),
                ft.Text("新建板块", size=11)
            ]),
            on_click=lambda e: self.on_add_board()
        )

        return ft.Column([
            ft.Text("板块", size=10, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD),
            ft.Divider(height=3, color="transparent"),
            *board_items,
            ft.Divider(height=5, color="transparent"),
            add_btn
        ])

    def update_boards(self, boards: List[Board], selected_id: Optional[str] = None):
        self.boards = boards
        self.selected_board_id = selected_id
        self.content = self._build_content()
        self.update()
