# views/search_bar.py
import flet as ft
from typing import List, Callable, Optional
from models.board import Board


class SearchBar(ft.Container):
    """搜索栏组件"""

    def __init__(
        self,
        boards: List[Board],
        tags: List[str],
        on_search: Callable[[str, Optional[List[str]], Optional[str]], None]
    ):
        super().__init__()
        self.boards = boards
        self.tags = tags
        self.on_search = on_search

        self.padding = 8
        self.content = self._build_content()

    def _build_content(self) -> ft.Row:
        # 搜索输入框
        self.search_input = ft.TextField(
            hint_text="搜索指令...",
            prefix_icon=ft.Icons.SEARCH,
            on_change=self._on_search_change,
            expand=True,
            text_size=13,
            bgcolor=ft.Colors.GREY_50,
            border_color=ft.Colors.GREY_300,
            focused_border_color=ft.Colors.BLUE_500,
            border_radius=8,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=8)
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
            on_select=self._on_board_change,
            bgcolor=ft.Colors.GREY_50,
            border_color=ft.Colors.GREY_300,
            border_radius=8,
            content_padding=ft.padding.symmetric(horizontal=8, vertical=8)
        )

        # 标签下拉选择
        tag_options = [ft.dropdown.DropdownOption("all", "全部标签")]
        tag_options.extend([
            ft.dropdown.DropdownOption(tag, f"#{tag}")
            for tag in sorted(self.tags)
        ])

        self.tag_dropdown = ft.Dropdown(
            options=tag_options,
            value="all",
            width=130,
            on_select=self._on_tag_change,
            bgcolor=ft.Colors.GREY_50,
            border_color=ft.Colors.GREY_300,
            border_radius=8,
            content_padding=ft.padding.symmetric(horizontal=8, vertical=8)
        )

        return ft.Row([
            self.search_input,
            ft.Container(width=6),
            self.board_dropdown,
            ft.Container(width=6),
            self.tag_dropdown
        ], spacing=0)

    def _on_search_change(self, e):
        self._do_search()

    def _on_board_change(self, e):
        self._do_search()

    def _on_tag_change(self, e):
        self._do_search()

    def _do_search(self):
        keyword = self.search_input.value or ""
        board_value = self.board_dropdown.value
        tag_value = self.tag_dropdown.value

        if board_value == "all":
            board_ids = None
        else:
            board_ids = [board_value]

        if tag_value == "all":
            selected_tag = None
        else:
            selected_tag = tag_value

        self.on_search(keyword, board_ids, selected_tag)

    def update_boards(self, boards: List[Board]):
        self.boards = boards
        self.content = self._build_content()
        self.update()

    def update_tags(self, tags: List[str]):
        self.tags = tags
        self.content = self._build_content()
        self.update()
