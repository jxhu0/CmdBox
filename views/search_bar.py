# views/search_bar.py
import flet as ft
from typing import List, Callable, Optional
from models.board import Board


class SearchBar(ft.Container):
    """搜索栏组件"""

    def __init__(
        self,
        boards: List[Board],
        on_search: Callable[[str, Optional[List[str]]], None]
    ):
        super().__init__()
        self.boards = boards
        self.on_search = on_search

        self.padding = 5
        self.content = self._build_content()

    def _build_content(self) -> ft.Row:
        # 搜索输入框
        self.search_input = ft.TextField(
            hint_text="搜索指令...",
            prefix_icon=ft.Icons.SEARCH,
            on_change=self._on_search_change,
            expand=True,
            text_size=12
        )

        # 板块下拉选择
        board_options = [ft.dropdown.DropdownOption("all", "全部板块")]
        board_options.extend([
            ft.dropdown.DropdownOption(b.id, f"{b.icon} {b.name}")
            for b in self.boards
        ])

        self.board_dropdown = ft.Dropdown(
            options=board_options,
            value="all",
            width=130,
            on_select=self._on_board_change
        )

        return ft.Row([
            self.search_input,
            self.board_dropdown
        ])

    def _on_search_change(self, e):
        self._do_search()

    def _on_board_change(self, e):
        self._do_search()

    def _do_search(self):
        keyword = self.search_input.value or ""
        board_value = self.board_dropdown.value

        if board_value == "all":
            board_ids = None
        else:
            board_ids = [board_value]

        self.on_search(keyword, board_ids)

    def update_boards(self, boards: List[Board]):
        self.boards = boards
        self.content = self._build_content()
        self.update()
