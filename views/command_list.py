# views/command_list.py
import flet as ft
from typing import List, Callable, Dict
from models.command import Command
from models.board import Board
from views.command_card import CommandCard
from views.isolated import IsolatedControl
from views.list_helpers import empty_state, scroll_to_top


class CommandStack(IsolatedControl, ft.Stack):
    def is_isolated(self):
        return True


class CommandList(IsolatedControl, ft.ListView):
    """指令列表组件"""

    def is_isolated(self):
        return True

    def __init__(
        self,
        boards: Dict[str, Board],
        on_copy: Callable[[Command], None],
        on_edit: Callable[[Command], None],
        on_delete: Callable[[Command], None],
        on_toggle_favorite: Callable[[Command], None],
        on_add_command: Callable[[], None],
        on_move_up: Callable[[Command], None] = None,
        on_move_down: Callable[[Command], None] = None,
        show_move_buttons: bool = True
    ):
        super().__init__()
        self.boards = boards
        self.on_copy = on_copy
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_toggle_favorite = on_toggle_favorite
        self.on_add_command = on_add_command
        self.on_move_up = on_move_up
        self.on_move_down = on_move_down
        self.show_move_buttons = show_move_buttons
        self.commands: List[Command] = []
        self._card_cache = {}
        self._visible_limit = 20
        self._page_start = 0
        self._query_ids = ()
        self.empty_filtered = False
        self._render_signature = None

        self.expand = True
        self.controls = self._build_empty_state()

    def _build_empty_state(self) -> List[ft.Control]:
        return empty_state('指令', ft.Icons.INBOX_OUTLINED, self.empty_filtered)

    def _card_signature(self, command, board):
        # 正文是不可变字符串，直接比较即可；repr 会复制整段长正文。
        snapshot = command.to_dict()
        snapshot['tags'] = tuple(command.tags)
        return (id(command), snapshot, id(board), board.to_dict(), self.show_move_buttons)

    def _build_command_cards(self) -> List[ft.Control]:
        if not self.commands:
            return self._build_empty_state()

        cards = []
        for cmd in self.commands[self._page_start:self._page_start + self._visible_limit]:
            board = self.boards.get(cmd.board_id)
            if not board:
                continue
            signature = self._card_signature(cmd, board)
            cached = self._card_cache.get(cmd.id)
            if cached and cached[0] == signature:
                cards.append(cached[1])
                continue
            card = CommandCard(
                command=cmd,
                board=board,
                on_copy=self.on_copy,
                on_edit=self.on_edit,
                on_delete=self.on_delete,
                on_toggle_favorite=self.on_toggle_favorite,
                on_move_up=self.on_move_up,
                on_move_down=self.on_move_down,
                show_move_buttons=self.show_move_buttons
            )
            cards.append(card)
            self._card_cache[cmd.id] = (signature, card)

        # Keep only controls on the current page, including during repeated paging.
        visible_ids = {cmd.id for cmd in self.commands[self._page_start:self._page_start + self._visible_limit]}
        self._card_cache = {key: value for key, value in self._card_cache.items() if key in visible_ids}

        if self._page_start:
            cards.append(ft.TextButton('上一页', on_click=self._previous_page))
        if len(self.commands) > self._page_start + self._visible_limit:
            cards.append(ft.TextButton(
                f'下一页（{self._page_start + self._visible_limit}/{len(self.commands)}）',
                on_click=self._load_more))
        # 添加底部占位，为 FAB 按钮预留空间
        cards.append(ft.Container(height=80))

        return cards

    def update_commands(self, commands: List[Command], update=True):
        ids = tuple(command.id for command in commands)
        if ids != self._query_ids:
            self._visible_limit = 20
            self._page_start = 0
            self._query_ids = ids
        self.commands = commands
        signature = (ids, self._visible_limit, self._page_start, self.show_move_buttons, self.empty_filtered,
                     [self._card_signature(cmd, self.boards[cmd.board_id])
                      for cmd in commands[self._page_start:self._page_start + self._visible_limit] if cmd.board_id in self.boards])
        if signature == self._render_signature:
            return
        self._render_signature = signature
        self.controls = self._build_command_cards()
        if update:
            self.update()

    def _load_more(self, e):
        self._page_start += self._visible_limit
        self._render_signature = None
        self.update_commands(self.commands)
        scroll_to_top(self)

    def _previous_page(self, e):
        self._page_start = max(0, self._page_start - self._visible_limit)
        self._render_signature = None
        self.update_commands(self.commands)
        scroll_to_top(self)

    def update_boards(self, boards: Dict[str, Board]):
        self.boards = boards

    def set_show_move_buttons(self, show: bool):
        """设置是否显示移动按钮"""
        self.show_move_buttons = show
