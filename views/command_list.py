# views/command_list.py
import flet as ft
from typing import List, Callable, Dict
from models.command import Command
from models.board import Board
from views.command_card import CommandCard


class CommandList(ft.Column):
    """指令列表组件"""

    def __init__(
        self,
        boards: Dict[str, Board],
        on_copy: Callable[[Command], None],
        on_edit: Callable[[Command], None],
        on_delete: Callable[[Command], None],
        on_toggle_favorite: Callable[[Command], None],
        on_add_command: Callable[[], None]
    ):
        super().__init__()
        self.boards = boards
        self.on_copy = on_copy
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_toggle_favorite = on_toggle_favorite
        self.on_add_command = on_add_command
        self.commands: List[Command] = []

        self.expand = True
        self.scroll = ft.ScrollMode.AUTO
        self.controls = self._build_empty_state()

    def _build_empty_state(self) -> List[ft.Control]:
        return [
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.INBOX_OUTLINED, size=48, color=ft.Colors.GREY_400),
                    ft.Text("暂无指令", color=ft.Colors.GREY_500),
                    ft.Text("点击下方按钮添加第一条指令", size=12, color=ft.Colors.GREY_400),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
                alignment=ft.Alignment(0.5, 0.5),
                expand=True
            )
        ]

    def _build_command_cards(self) -> List[ft.Control]:
        if not self.commands:
            return self._build_empty_state()

        cards = []
        for cmd in self.commands:
            board = self.boards.get(cmd.board_id)
            if not board:
                continue
            card = CommandCard(
                command=cmd,
                board=board,
                on_copy=self.on_copy,
                on_edit=self.on_edit,
                on_delete=self.on_delete,
                on_toggle_favorite=self.on_toggle_favorite
            )
            cards.append(card)

        return cards

    def update_commands(self, commands: List[Command]):
        self.commands = commands
        self.controls = self._build_command_cards()
        self.update()

    def update_boards(self, boards: Dict[str, Board]):
        self.boards = boards
        self.controls = self._build_command_cards()
        self.update()
