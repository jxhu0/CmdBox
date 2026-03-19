# views/dialogs.py
import flet as ft
from typing import List, Optional, Callable
from models.board import Board
from models.command import Command


class BoardDialog(ft.AlertDialog):
    """板块弹窗（新建/编辑）"""

    def __init__(
        self,
        title: str,
        board: Optional[Board] = None,
        on_save: Callable[[str, str], None] = None
    ):
        super().__init__()
        self.board = board
        self.on_save_callback = on_save

        self.modal = True
        self.title = ft.Text(title)

        self.name_field = ft.TextField(
            label="板块名称",
            value=board.name if board else "",
            autofocus=True
        )

        self.icon_field = ft.TextField(
            label="图标 (emoji)",
            value=board.icon if board else "📁",
            max_length=2
        )

        self.content = ft.Column([
            self.name_field,
            self.icon_field
        ], tight=True)

        self.actions = [
            ft.TextButton("取消", on_click=self._on_cancel),
            ft.TextButton("保存", on_click=self._on_save)
        ]

    def _on_cancel(self, e):
        if self.page:
            self.page.pop_dialog()
            self.page.update()

    def _on_save(self, e):
        if self.on_save_callback:
            self.on_save_callback(self.name_field.value, self.icon_field.value)
        if self.page:
            self.page.pop_dialog()
            self.page.update()


class CommandDialog(ft.AlertDialog):
    """指令弹窗（新建/编辑）"""

    def __init__(
        self,
        title: str,
        boards: List[Board],
        command: Optional[Command] = None,
        selected_board_id: Optional[str] = None,
        on_save: Callable = None
    ):
        super().__init__()
        self.command = command
        self.boards = boards
        self.on_save_callback = on_save

        self.modal = True
        self.title = ft.Text(title)

        # 表单字段
        self.title_field = ft.TextField(
            label="标题",
            value=command.title if command else ""
        )

        board_options = [
            ft.dropdown.DropdownOption(b.id, f"{b.icon} {b.name}")
            for b in boards
        ]
        self.board_dropdown = ft.Dropdown(
            label="所属板块",
            options=board_options,
            value=command.board_id if command else (selected_board_id if selected_board_id else (boards[0].id if boards else None))
        )

        self.content_field = ft.TextField(
            label="指令内容",
            value=command.content if command else "",
            multiline=True,
            min_lines=3,
            max_lines=10
        )

        self.description_field = ft.TextField(
            label="描述（可选）",
            value=command.description if command else "",
            multiline=True,
            min_lines=2,
            max_lines=5
        )

        self.tags_field = ft.TextField(
            label="标签（逗号分隔）",
            value=", ".join(command.tags) if command and command.tags else ""
        )

        self.favorite_checkbox = ft.Checkbox(
            label="添加到收藏",
            value=command.is_favorite if command else False
        )

        self.content = ft.Column([
            self.title_field,
            self.board_dropdown,
            self.content_field,
            self.description_field,
            self.tags_field,
            self.favorite_checkbox
        ], tight=True, scroll=ft.ScrollMode.AUTO)

        self.actions = [
            ft.TextButton("取消", on_click=self._on_cancel),
            ft.TextButton("保存", on_click=self._on_save)
        ]

    def _on_cancel(self, e):
        if self.page:
            self.page.pop_dialog()
            self.page.update()

    def _on_save(self, e):
        if self.on_save_callback:
            tags_str = self.tags_field.value or ""
            tags = [t.strip() for t in tags_str.split(",") if t.strip()]

            self.on_save_callback(
                title=self.title_field.value,
                board_id=self.board_dropdown.value,
                content=self.content_field.value,
                description=self.description_field.value,
                tags=tags,
                is_favorite=self.favorite_checkbox.value
            )
        if self.page:
            self.page.pop_dialog()
            self.page.update()


class ConfirmDialog(ft.AlertDialog):
    """确认弹窗"""

    def __init__(
        self,
        title: str,
        content: str,
        on_confirm: Callable = None
    ):
        super().__init__()
        self.on_confirm_callback = on_confirm

        self.modal = True
        self.title = ft.Text(title)
        self.content = ft.Text(content)

        self.actions = [
            ft.TextButton("取消", on_click=self._on_cancel),
            ft.TextButton("确认", on_click=self._on_confirm)
        ]

    def _on_cancel(self, e):
        if self.page:
            self.page.pop_dialog()
            self.page.update()

    def _on_confirm(self, e):
        if self.on_confirm_callback:
            self.on_confirm_callback()
        if self.page:
            self.page.pop_dialog()
            self.page.update()


class EditAndCopyDialog(ft.AlertDialog):
    """编辑后复制弹窗"""

    def __init__(self, command: Command, on_copy: Callable[[str], None]):
        super().__init__()
        self.command = command
        self.on_copy_callback = on_copy

        self.modal = True
        self.title = ft.Text("编辑后复制")

        self.edit_field = ft.TextField(
            value=command.content,
            multiline=True,
            min_lines=5,
            max_lines=15,
            expand=True
        )

        self.content = ft.Column([self.edit_field], tight=True)

        self.actions = [
            ft.TextButton("取消", on_click=self._on_cancel),
            ft.TextButton("复制", on_click=self._on_copy)
        ]

    def _on_cancel(self, e):
        if self.page:
            self.page.pop_dialog()
            self.page.update()

    def _on_copy(self, e):
        self.on_copy_callback(self.edit_field.value)
        if self.page:
            self.page.pop_dialog()
            self.page.update()


class SettingsDialog(ft.AlertDialog):
    """设置弹窗"""

    def __init__(
        self,
        repo_path: str,
        remote_url: str,
        on_save: Callable[[str], None] = None
    ):
        super().__init__()
        self.on_save_callback = on_save

        self.modal = True
        self.title = ft.Text("设置")

        # 数据路径（只读显示）
        self.path_field = ft.TextField(
            label="数据存储路径",
            value=repo_path,
            read_only=True,
            border_color=ft.Colors.GREY_400
        )

        # 远程仓库地址
        self.remote_field = ft.TextField(
            label="Git 远程仓库地址",
            value=remote_url,
            hint_text="例如: https://github.com/username/cmdbox-data.git",
            expand=True
        )

        # 说明文字
        self.help_text = ft.Column([
            ft.Text("配置说明：", size=12, weight=ft.FontWeight.BOLD),
            ft.Text("1. 在 GitHub/GitLab 创建一个私有仓库", size=11, color=ft.Colors.GREY_600),
            ft.Text("2. 复制仓库的 HTTPS 或 SSH 地址到上方输入框", size=11, color=ft.Colors.GREY_600),
            ft.Text("3. 点击保存后，使用同步功能推送数据", size=11, color=ft.Colors.GREY_600),
        ], spacing=2)

        self.content = ft.Column([
            self.path_field,
            ft.Divider(height=10, color="transparent"),
            self.remote_field,
            ft.Divider(height=10, color="transparent"),
            self.help_text,
        ], tight=True, scroll=ft.ScrollMode.AUTO)

        self.actions = [
            ft.TextButton("取消", on_click=self._on_cancel),
            ft.TextButton("保存", on_click=self._on_save)
        ]

    def _on_cancel(self, e):
        if self.page:
            self.page.pop_dialog()
            self.page.update()

    def _on_save(self, e):
        if self.on_save_callback:
            self.on_save_callback(self.remote_field.value)
        if self.page:
            self.page.pop_dialog()
            self.page.update()
