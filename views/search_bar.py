# views/search_bar.py
import flet as ft
from views.isolated import IsolatedControl
import asyncio
from typing import List, Callable, Optional
from models.board import Board



class SearchBar(IsolatedControl, ft.Container):
    def is_isolated(self):
        return True

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
        self._search_generation = 0
        self._pending_search = None
        self._context = 'commands'
        self._narrow = False

        self.padding = 8
        self.content = self._build_content()
        self.on_size_change = self._on_width_changed

    def _on_width_changed(self, event):
        narrow = event.width < 560
        if narrow == self._narrow:
            return
        self._narrow = narrow
        self.board_dropdown.width = self.tag_dropdown.width = 100 if narrow else 130
        self.filters.update()

    def _build_content(self) -> ft.Row:
        # 搜索输入框
        self.search_input = ft.TextField(
            hint_text="搜索指令...",
            prefix_icon=ft.Icons.SEARCH,
            on_change=self._on_search_change,
            on_submit=self._on_submit,
            suffix=ft.IconButton(icon=ft.Icons.CLOSE, icon_size=16,
                                 tooltip='清空搜索', on_click=self._on_clear_click),
            expand=True,
            text_size=13,
            bgcolor=ft.Colors.WHITE,
            border_color=ft.Colors.GREY_200,
            focused_border_color=ft.Colors.BLUE_500,
            border_radius=8,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=8)
        )

        # 板块下拉选择
        board_options = [ft.dropdown.DropdownOption("all", "全部板块")]
        board_options.extend([
            ft.dropdown.DropdownOption(b.id, b.name)
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

        self.filters = ft.Row([
            self.board_dropdown,
            self.tag_dropdown,
        ], spacing=6)
        return ft.Row([
            self.search_input,
            self.filters,
        ], spacing=6)

    def set_context(self, context: str):
        self._context = context
        self.filters.visible = context == 'commands'
        self.search_input.hint_text = {
            'tasks': '搜索任务标题、描述...',
            'questions': '搜索问题、描述或解答...',
        }.get(context, '搜索指令...')
        self.update()

    def _on_search_change(self, e):
        self.cancel_pending_search()
        self._pending_search = self.page.run_task(self._debounced_search, self._search_generation)

    def cancel_pending_search(self):
        self._search_generation += 1
        if self._pending_search is not None:
            self._pending_search.cancel()
            self._pending_search = None

    async def _on_submit(self, e):
        self.cancel_pending_search()
        await self._run_search()

    async def _debounced_search(self, generation):
        await asyncio.sleep(0.2)
        if generation == self._search_generation:
            await self._run_search()

    async def _on_board_change(self, e):
        self.cancel_pending_search()
        await self._run_search()

    async def _on_tag_change(self, e):
        self.cancel_pending_search()
        await self._run_search()

    async def _run_search(self):
        import inspect
        result = self._do_search()
        if inspect.isawaitable(result):
            await result

    def _do_search(self):
        keyword = self.search_input.value or ""
        if self._context != 'commands':
            return self.on_search(keyword, None, None)
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

        return self.on_search(keyword, board_ids, selected_tag)

    def update_boards(self, boards: List[Board]):
        self.boards = boards
        snapshot = [(b.id, b.name) for b in boards]
        if snapshot == getattr(self, '_boards_snapshot', None):
            return False
        self._boards_snapshot = snapshot
        self.board_dropdown.options = [ft.dropdown.DropdownOption('all', '全部板块')] + [
            ft.dropdown.DropdownOption(b.id, b.name) for b in boards]
        cleared = self.board_dropdown.value not in {'all', *(b.id for b in boards)}
        if cleared:
            self.board_dropdown.value = 'all'
        self.board_dropdown.update()
        return cleared

    def update_tags(self, tags: List[str]):
        self.tags = tags
        snapshot = sorted(tags)
        if snapshot == getattr(self, '_tags_snapshot', None):
            return False
        self._tags_snapshot = snapshot
        self.tag_dropdown.options = [ft.dropdown.DropdownOption('all', '全部标签')] + [
            ft.dropdown.DropdownOption(tag, f'#{tag}') for tag in snapshot]
        cleared = self.tag_dropdown.value not in {'all', *tags}
        if cleared:
            self.tag_dropdown.value = 'all'
        self.tag_dropdown.update()
        return cleared

    def reset_filters(self, board_id=None):
        self.cancel_pending_search()
        self.search_input.value = ''
        self.board_dropdown.value = board_id or 'all'
        self.tag_dropdown.value = 'all'
        self.update()

    async def _on_clear_click(self, e):
        await self.clear_search()

    async def clear_search(self):
        """清空搜索框内容"""
        self.cancel_pending_search()
        if hasattr(self, 'search_input') and self.search_input.value:
            self.search_input.value = ""
            self.search_input.update()
            await self._run_search()
