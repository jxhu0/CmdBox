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
        on_reorder_boards: Callable[[List[str]], None],
        selected_board_id: Optional[str] = None,
        favorites_board_id: Optional[str] = None,
        tasks_board_id: Optional[str] = None
    ):
        super().__init__()
        self.boards = boards
        self.on_board_select = on_board_select
        self.on_add_board = on_add_board
        self.on_edit_board = on_edit_board
        self.on_delete_board = on_delete_board
        self.on_reorder_boards = on_reorder_boards
        self.selected_board_id = selected_board_id
        self.favorites_board_id = favorites_board_id
        self.tasks_board_id = tasks_board_id

        self.width = 180
        self.bgcolor = ft.Colors.WHITE
        self.padding = 5
        self.content = self._build_content()

    def _build_board_item(self, board: Board) -> ft.Container:
        """构建单个板块项"""
        is_selected = board.id == self.selected_board_id

        # 卡片内容
        card_content = ft.Row([
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
        ], spacing=4, tight=True)

        return ft.Container(
            key=board.id,
            content=ft.ReorderableDragHandle(
                content=ft.Container(
                    content=card_content,
                    padding=8,
                    border_radius=8,
                    bgcolor=ft.Colors.BLUE_50 if is_selected else ft.Colors.TRANSPARENT,
                    border=ft.border.only(left=ft.border.BorderSide(3, ft.Colors.BLUE_500)) if is_selected else None,
                    on_click=lambda e, bid=board.id: self.on_board_select(bid)
                )
            )
        )

    def _on_reorder(self, e):
        """处理拖拽重排序"""
        # 获取新的板块 ID 顺序
        board_ids = [board.id for board in self.boards]
        board_ids.insert(e.new_index, board_ids.pop(e.old_index))
        self.on_reorder_boards(board_ids)

    def _build_content(self) -> ft.Column:
        # 收藏板块（固定在最上方，不可拖动）
        fav_item = None
        if self.favorites_board_id:
            is_selected = self.selected_board_id == self.favorites_board_id
            fav_item = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(ft.Icons.STAR, size=16, color=ft.Colors.AMBER),
                        margin=ft.margin.only(left=-7)
                    ),
                    ft.Container(width=2),
                    ft.Text("收藏", size=13, weight=ft.FontWeight.W_600 if is_selected else ft.FontWeight.NORMAL,
                            color=ft.Colors.AMBER_700 if is_selected else ft.Colors.GREY_700),
                    ft.Container(content=None, expand=True)
                ], spacing=4, tight=True),
                padding=14,
                border_radius=8,
                bgcolor=ft.Colors.AMBER_50 if is_selected else ft.Colors.TRANSPARENT,
                border=ft.border.only(left=ft.border.BorderSide(3, ft.Colors.AMBER_500)) if is_selected else None,
                on_click=lambda e: self.on_board_select(self.favorites_board_id)
            )

        # 任务板块（固定，不可拖动）
        tasks_item = None
        if self.tasks_board_id:
            is_selected = self.selected_board_id == self.tasks_board_id
            tasks_item = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(ft.Icons.CHECKLIST, size=16, color=ft.Colors.GREEN),
                        margin=ft.margin.only(left=-7)
                    ),
                    ft.Container(width=2),
                    ft.Text("任务", size=13, weight=ft.FontWeight.W_600 if is_selected else ft.FontWeight.NORMAL,
                            color=ft.Colors.GREEN_700 if is_selected else ft.Colors.GREY_700),
                    ft.Container(content=None, expand=True)
                ], spacing=4, tight=True),
                padding=14,
                border_radius=8,
                bgcolor=ft.Colors.GREEN_50 if is_selected else ft.Colors.TRANSPARENT,
                border=ft.border.only(left=ft.border.BorderSide(3, ft.Colors.GREEN_500)) if is_selected else None,
                on_click=lambda e: self.on_board_select(self.tasks_board_id)
            )

        # 普通板块列表（可拖拽排序）
        board_items = [self._build_board_item(board) for board in self.boards]

        # 使用 ReorderableListView 实现拖拽排序
        reorderable_list = ft.ReorderableListView(
            controls=board_items,
            on_reorder=self._on_reorder,
            expand=True,
            show_default_drag_handles=False
        )

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

        # 构建完整布局
        content_items = [
            ft.Text("板块", size=10, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD),
        ]

        # 收藏板块在顶部
        if fav_item:
            content_items.append(fav_item)

        # 任务板块
        if tasks_item:
            content_items.append(tasks_item)

        # 可拖拽的普通板块列表
        content_items.append(ft.Container(
            content=reorderable_list,
            expand=True,
            padding=0
        ))

        # 新建按钮在底部
        content_items.append(add_btn)

        return ft.Column(content_items, tight=False, expand=True)

    def update_boards(self, boards: List[Board], selected_id: Optional[str] = None, favorites_id: Optional[str] = None, tasks_id: Optional[str] = None):
        self.boards = boards
        self.selected_board_id = selected_id
        if favorites_id:
            self.favorites_board_id = favorites_id
        if tasks_id:
            self.tasks_board_id = tasks_id
        self.content = self._build_content()
        self.update()
