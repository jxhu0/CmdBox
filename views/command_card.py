# views/command_card.py
import flet as ft
from typing import Callable
from models.command import Command
from models.board import Board
from utils.helpers import truncate_text


# 标签颜色配置
TAG_COLORS = {
    "python": (ft.Colors.YELLOW_100, ft.Colors.YELLOW_800),
    "git": (ft.Colors.ORANGE_100, ft.Colors.ORANGE_800),
    "docker": (ft.Colors.CYAN_100, ft.Colors.CYAN_800),
    "linux": (ft.Colors.PURPLE_100, ft.Colors.PURPLE_800),
    "bash": (ft.Colors.GREEN_100, ft.Colors.GREEN_800),
    "shell": (ft.Colors.GREEN_100, ft.Colors.GREEN_800),
    "npm": (ft.Colors.RED_100, ft.Colors.RED_800),
    "node": (ft.Colors.GREEN_100, ft.Colors.GREEN_800),
    "react": (ft.Colors.CYAN_100, ft.Colors.CYAN_800),
    "vue": (ft.Colors.GREEN_100, ft.Colors.GREEN_800),
    "rust": (ft.Colors.ORANGE_100, ft.Colors.ORANGE_800),
    "go": (ft.Colors.CYAN_100, ft.Colors.CYAN_800),
    "java": (ft.Colors.RED_100, ft.Colors.RED_800),
    "sql": (ft.Colors.BLUE_100, ft.Colors.BLUE_800),
    "aws": (ft.Colors.YELLOW_100, ft.Colors.YELLOW_800),
    "api": (ft.Colors.PURPLE_100, ft.Colors.PURPLE_800),
    "web": (ft.Colors.BLUE_100, ft.Colors.BLUE_800),
    "http": (ft.Colors.GREEN_100, ft.Colors.GREEN_800),
    "json": (ft.Colors.YELLOW_100, ft.Colors.YELLOW_800),
    "yaml": (ft.Colors.PINK_100, ft.Colors.PINK_800),
    "mac": (ft.Colors.GREY_200, ft.Colors.GREY_800),
    "windows": (ft.Colors.BLUE_100, ft.Colors.BLUE_800),
    "ios": (ft.Colors.GREY_200, ft.Colors.GREY_800),
    "android": (ft.Colors.GREEN_100, ft.Colors.GREEN_800),
    "k8s": (ft.Colors.BLUE_100, ft.Colors.BLUE_800),
    "kubernetes": (ft.Colors.BLUE_100, ft.Colors.BLUE_800),
    "devops": (ft.Colors.PURPLE_100, ft.Colors.PURPLE_800),
    "ci": (ft.Colors.GREEN_100, ft.Colors.GREEN_800),
    "cd": (ft.Colors.BLUE_100, ft.Colors.BLUE_800),
    "test": (ft.Colors.GREEN_100, ft.Colors.GREEN_800),
    "security": (ft.Colors.RED_100, ft.Colors.RED_800),
    "network": (ft.Colors.CYAN_100, ft.Colors.CYAN_800),
    "ssh": (ft.Colors.YELLOW_100, ft.Colors.YELLOW_800),
    "vim": (ft.Colors.GREEN_100, ft.Colors.GREEN_800),
    "tmux": (ft.Colors.CYAN_100, ft.Colors.CYAN_800),
    "regex": (ft.Colors.PINK_100, ft.Colors.PINK_800),
    "csv": (ft.Colors.GREEN_100, ft.Colors.GREEN_800),
    "gy": (ft.Colors.TEAL_100, ft.Colors.TEAL_800),
    "self": (ft.Colors.INDIGO_100, ft.Colors.INDIGO_800),
    "cc": (ft.Colors.LIME_100, ft.Colors.LIME_800),
    "claw": (ft.Colors.AMBER_100, ft.Colors.AMBER_800),
    "tool": (ft.Colors.PINK_100, ft.Colors.PINK_800),
}


def get_tag_colors(tag: str) -> tuple:
    """根据标签名称获取颜色配置"""
    tag_lower = tag.lower()
    if tag_lower in TAG_COLORS:
        return TAG_COLORS[tag_lower]
    # 默认颜色
    return (ft.Colors.BLUE_50, ft.Colors.BLUE_700)


class CommandCard(ft.Container):
    """指令卡片组件 - 紧凑布局设计，    """

    def __init__(
        self,
        command: Command,
        board: Board,
        on_copy: Callable[[Command], None],
        on_edit: Callable[[Command], None],
        on_delete: Callable[[Command], None],
        on_toggle_favorite: Callable[[Command], None],
        on_move_up: Callable[[Command], None] = None,
        on_move_down: Callable[[Command], None] = None
    ):
        super().__init__()
        self.command = command
        self.board = board
        self.on_copy = on_copy
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_toggle_favorite = on_toggle_favorite
        self.on_move_up = on_move_up
        self.on_move_down = on_move_down

        # 状态
        self._is_expanded = False
        self._is_truncated = len(command.content) > 100

        self.padding = 12
        self.border_radius = 12
        self.border = None
        self.margin = ft.margin.only(bottom=8)
        self.shadow = ft.BoxShadow(
            spread_radius=1,
            blur_radius=6,
            color=ft.Colors.with_opacity(0.15, ft.Colors.GREY_400),
            offset=(0, 2)
        )
        self.bgcolor = ft.Colors.WHITE

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
                    color=ft.Colors.AMBER if self.command.is_favorite else ft.Colors.GREY_400,
                    size=18),
            ft.Text(self.command.title, size=15, weight=ft.FontWeight.W_600, color=ft.Colors.GREY_800),
        ]

        # 如果有描述，添加到标题行
        if self.command.description:
            title_controls.append(
                ft.Text("· " + self.command.description, size=12, color=ft.Colors.GREY_500)
            )

        title_row = ft.Row(title_controls, wrap=True, spacing=4)

        # 内容文本（根据展开状态决定是否截断）
        display_content = self.command.content if self._is_expanded else truncate_text(self.command.content, 100)
        content_text = ft.Text(
            display_content,
            size=13,
            color=ft.Colors.GREY_600,
            font_family="monospace"
        )

        # 构建内容和标签的控件列表
        content_and_tags_controls = [content_text]

        # 添加标签
        for tag in self.command.tags[:3]:
            bg_color, text_color = get_tag_colors(tag)
            content_and_tags_controls.append(
                ft.Container(
                    content=ft.Text(tag, size=11, color=text_color, weight=ft.FontWeight.W_500),
                    bgcolor=bg_color,
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=12
                )
            )

        # "显示全部/收起"按钮（仅在内容被截断时显示）- 放在省略号同一行
        if self._is_truncated:
            content_and_tags_controls.append(
                ft.GestureDetector(
                    content=ft.Container(
                        content=ft.Row([
                            ft.Text("显示全部" if not self._is_expanded else "收起", size=11, color=ft.Colors.BLUE_600, weight=ft.FontWeight.W_500),
                            ft.Icon(ft.Icons.EXPAND_MORE if not self._is_expanded else ft.Icons.EXPAND_LESS, size=14, color=ft.Colors.BLUE_600),
                        ], spacing=2, tight=True),
                        padding=4,
                        bgcolor=ft.Colors.BLUE_50,
                        border_radius=6
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
            ft.Container(
                content=ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.KEYBOARD_ARROW_UP,
                        icon_size=16,
                        tooltip="上移",
                        on_click=lambda e: self.on_move_up(self.command) if self.on_move_up else None
                    ),
                    ft.IconButton(
                        icon=ft.Icons.KEYBOARD_ARROW_DOWN,
                        icon_size=16,
                        tooltip="下移",
                        on_click=lambda e: self.on_move_down(self.command) if self.on_move_down else None
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CONTENT_COPY,
                        icon_size=16,
                        tooltip="复制",
                        on_click=lambda e: self.on_copy(self.command)
                    ),
                    ft.IconButton(
                        icon=ft.Icons.EDIT_OUTLINED,
                        icon_size=16,
                        tooltip="编辑",
                        on_click=lambda e: self.on_edit(self.command)
                    ),
                    ft.IconButton(
                        icon=ft.Icons.STAR if self.command.is_favorite else ft.Icons.STAR_OUTLINE,
                        icon_color=ft.Colors.AMBER if self.command.is_favorite else ft.Colors.GREY_500,
                        icon_size=16,
                        tooltip="取消收藏" if self.command.is_favorite else "收藏",
                        on_click=lambda e: self.on_toggle_favorite(self.command)
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_size=16,
                        tooltip="删除",
                        on_click=lambda e: self.on_delete(self.command)
                    )
                ], spacing=0),
                bgcolor=ft.Colors.GREY_50,
                border_radius=8,
                padding=2
            )
        ], alignment=ft.MainAxisAlignment.END)

        # 构建内容列的子控件列表
        column_controls = [
            title_row,
            ft.Divider(height=2, color="transparent"),
            content_and_tags,
            ft.Divider(height=2, color="transparent"),
            actions_row
        ]

        return ft.Column(column_controls, spacing=0)