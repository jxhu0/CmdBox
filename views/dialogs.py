# views/dialogs.py
import flet as ft
import subprocess
import platform
from typing import List, Optional, Callable
from models.board import Board
from models.command import Command


def _browse_folder(initial_dir: str) -> Optional[str]:
    """跨平台选择文件夹"""
    system = platform.system()

    if system == "Darwin":  # macOS
        escaped_path = initial_dir.replace('"', '\\"')
        script = f'''
set targetFolder to POSIX file "{escaped_path}"
set chosen to choose folder with prompt "选择数据存储文件夹" default location targetFolder
return POSIX path of chosen
'''
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, Exception):
            pass
        return None

    else:  # Windows / Linux - 使用 tkinter
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        root.update()
        try:
            folder = filedialog.askdirectory(initialdir=initial_dir)
        finally:
            root.destroy()
        return folder if folder else None


# 预设图标列表
BOARD_ICONS = [
    "📁", "📂", "📃", "📄", "📅", "📆", "📇", "📈", "📉", "📊",
    "📋", "📌", "📍", "📎", "📏", "📐", "📑", "📓", "📔", "📕",
    "📖", "📗", "📘", "📙", "📚", "📛", "📜", "📝", "📞", "📟",
    "💻", "🖥️", "🖱️", "⌨️", "📱", "📲", "☎️", "📠", "🔧", "🔨",
    "🔩", "💡", "🔔", "🔑", "🗝️", "🔒", "🌐", "🌍", "🌎", "🌏",
    "🗺️", "📡", "📶", "🔗", "🎯", "⭐", "💫", "✨", "⚡", "🔥"
]


class BoardDialog(ft.AlertDialog):
    """板块弹窗（新建/编辑）"""

    def __init__(
        self,
        title: str,
        board: Optional[Board] = None,
        on_save: Callable[[str, str, str], None] = None
    ):
        super().__init__()
        self.board = board
        self.on_save_callback = on_save
        self.selected_icon = board.icon if board else "📁"

        self.modal = True
        self.title = ft.Text(title)

        self.name_field = ft.TextField(
            label="板块名称",
            value=board.name if board else "",
            autofocus=True
        )

        self.desc_field = ft.TextField(
            label="板块描述（可选）",
            value=board.description if board else "",
            multiline=True,
            max_lines=3
        )

        # 创建图标按钮
        def make_icon_btn(icon):
            btn = ft.Container(
                content=ft.Text(icon, size=18),
                width=32,
                height=32,
                alignment=ft.Alignment(0, 0),
                border_radius=4,
                on_click=self._on_icon_select,
                data=icon
            )
            if icon == self.selected_icon:
                btn.border = ft.border.all(2, ft.Colors.BLUE_400)
                btn.bgcolor = ft.Colors.BLUE_50
            return btn

        self.icon_buttons = [make_icon_btn(icon) for icon in BOARD_ICONS]

        self.icon_preview = ft.Container(
            content=ft.Text(self.selected_icon, size=24),
            width=50,
            height=50,
            alignment=ft.Alignment(0, 0),
            border_radius=8,
            border=ft.border.all(1, ft.Colors.GREY_300)
        )

        self.content = ft.Column([
            self.name_field,
            self.desc_field,
            ft.Text("选择图标", size=12, color=ft.Colors.GREY_600),
            ft.Container(
                content=ft.Row(self.icon_buttons, wrap=True, spacing=2, run_spacing=2),
                height=120
            ),
            ft.Row([
                ft.Text("预览：", size=12),
                self.icon_preview
            ], alignment=ft.MainAxisAlignment.START)
        ], tight=True, scroll=ft.ScrollMode.AUTO)

        self.actions = [
            ft.TextButton("取消", on_click=self._on_cancel),
            ft.TextButton("保存", on_click=self._on_save)
        ]

    def _on_icon_select(self, e):
        """选择图标"""
        self.selected_icon = e.control.data
        # 更新预览
        self.icon_preview.content = ft.Text(self.selected_icon, size=24)
        # 更新所有按钮的样式
        for btn in self.icon_buttons:
            if btn.data == self.selected_icon:
                btn.border = ft.border.all(2, ft.Colors.BLUE_400)
                btn.bgcolor = ft.Colors.BLUE_50
            else:
                btn.border = None
                btn.bgcolor = None
        self.page.update()

    def _on_cancel(self, e):
        if self.page:
            self.page.pop_dialog()
            self.page.update()

    def _on_save(self, e):
        if self.on_save_callback:
            self.on_save_callback(self.name_field.value, self.selected_icon, self.desc_field.value)
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
        if self.page:
            self.page.pop_dialog()
        if self.on_confirm_callback:
            self.on_confirm_callback()
        if self.page:
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
        data_service=None,
        on_save: Callable[[str], None] = None,
        on_restore: Callable[[str], None] = None,
        on_path_save: Callable[[str], None] = None,
        latest_version: str = None
    ):
        import app as app_module
        super().__init__()
        self.on_save_callback = on_save
        self._version = app_module.__version__
        self._latest_version = latest_version
        self.on_restore_callback = on_restore
        self.on_path_save_callback = on_path_save
        self.data_service = data_service
        self.path_data = {"path": repo_path}

        self.modal = True
        self.title_padding = 0
        self.title = ft.Container(
            content=ft.Row([
                ft.Text("设置", weight=ft.FontWeight.BOLD, size=18),
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    icon_size=18,
                    tooltip="关闭",
                    on_click=self._on_cancel,
                    style=ft.ButtonStyle(color=ft.Colors.GREY_500)
                )
            ], alignment=ft.MainAxisAlignment.START),
            padding=ft.padding.only(left=24, right=5, top=16, bottom=8)
        )

        # 数据路径（可编辑）
        self.path_field = ft.TextField(
            label="数据存储路径",
            value=repo_path,
            on_change=self._on_path_change,
            dense=True
        )

        # 浏览按钮
        self.browse_btn = ft.IconButton(
            icon=ft.Icons.FOLDER_OPEN,
            tooltip="浏览",
            on_click=self._on_browse
        )

        # 远程仓库地址
        self.remote_field = ft.TextField(
            label="Git 远程仓库地址",
            value=remote_url,
            hint_text="例如: https://github.com/username/cmdbox-data.git",
            expand=True,
            on_change=self._on_remote_change
        )

        # 备份列表
        self.backup_list = ft.Column([], tight=True, scroll=ft.ScrollMode.AUTO)
        self._refresh_backups()

        # 说明文字
        self.help_text = ft.Column([
            ft.Text("配置说明：", size=12, weight=ft.FontWeight.BOLD),
            ft.Text("1. 在 GitHub/GitLab 创建一个私有仓库", size=11, color=ft.Colors.GREY_600),
            ft.Text("2. 复制仓库的 HTTPS 或 SSH 地址到上方输入框", size=11, color=ft.Colors.GREY_600),
            ft.Text("3. 点击保存后，使用同步功能推送数据", size=11, color=ft.Colors.GREY_600),
        ], spacing=2)

        self.tutorial_btn = ft.TextButton(
            "使用已有远程仓库？查看教程",
            icon=ft.Icons.MENU_BOOK,
            on_click=self._on_show_tutorial
        )

        self.content_padding = 24
        self.content = ft.Column([
            ft.Container(
                content=ft.Row([
                    self.path_field, self.browse_btn
                ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.only(top=10, bottom=10)
            ),
            self.remote_field,
            ft.Divider(height=10, color="transparent"),
            self.help_text,
            self.tutorial_btn,
            ft.Divider(height=10, color="transparent"),
            ft.Text("数据备份", size=12, weight=ft.FontWeight.BOLD),
            ft.Text("同步前会自动创建备份，最多保留10个", size=10, color=ft.Colors.GREY_600),
            self.backup_list,
            ft.Container(height=10),
            ft.Row([
                ft.Text(f"当前版本 v{self._version}" + (f"（最新版本 v{self._latest_version}）" if self._latest_version else ""), size=13, color=ft.Colors.BLUE_600),
                ft.TextButton(
                    "前往下载",
                    icon=ft.Icons.DOWNLOAD,
                    on_click=self._on_download,
                    style=ft.ButtonStyle(color=ft.Colors.BLUE_600)
                ),
            ], alignment=ft.MainAxisAlignment.START),
        ], scroll=ft.ScrollMode.AUTO)

        self.actions = [
            ft.TextButton("保存", on_click=self._on_save)
        ]

    def _on_download(self, e):
        """打开 GitHub releases 下载页面"""
        import webbrowser
        webbrowser.open("https://github.com/jxhu0/CmdBox/releases")

    def _on_browse(self, e):
        """浏览选择新路径"""
        folder = _browse_folder(self.path_data["path"])
        if folder:
            self.path_field.value = folder
            self.path_field.update()
            self.path_data["path"] = folder

    def _on_show_tutorial(self, e):
        """显示教程对话框"""
        page = self.page

        tutorial_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.MENU_BOOK, color=ft.Colors.BLUE_600),
                    ft.Text("使用教程", weight=ft.FontWeight.BOLD)
                ], spacing=10)
            ),
            content=ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Text("在新电脑使用已有数据初始化：", size=14, weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_GREY_800),
                        ft.Container(height=10),
                        ft.Text("1. 在本地 clone 远程仓库到指定文件夹", size=13, color=ft.Colors.GREY_700),
                        ft.Container(height=6),
                        ft.Text("2. 打开 CmdBox，在向导中选择该文件夹路径", size=13, color=ft.Colors.GREY_700),
                        ft.Container(height=6),
                        ft.Text("3. 进入应用后，点击右上角设置", size=13, color=ft.Colors.GREY_700),
                        ft.Container(height=6),
                        ft.Text("4. 在「Git 远程仓库地址」中填写远程仓库地址", size=13, color=ft.Colors.GREY_700),
                        ft.Container(height=6),
                        ft.Text("5. 点击「保存」即可同步数据", size=13, color=ft.Colors.GREY_700),
                    ], tight=True),
                    padding=15,
                    bgcolor=ft.Colors.BLUE_50,
                    border_radius=12
                )
            ], tight=True),
            actions=[
                ft.TextButton("我知道了", on_click=lambda e: close_tutorial(tutorial_dialog))
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )

        def close_tutorial(dialog):
            dialog.open = False
            page.update()

        page.show_dialog(tutorial_dialog)

    def _on_path_change(self, e):
        """路径文本变化"""
        self.path_data["path"] = e.control.value

    def _on_remote_change(self, e):
        """远程地址文本变化"""
        pass  # TextField.value 已自动更新

    def _refresh_backups(self):
        """刷新备份列表"""
        if not self.data_service:
            return

        backups = self.data_service.get_backups()
        self.backup_list.controls.clear()

        if not backups:
            self.backup_list.controls.append(
                ft.Text("暂无备份", size=11, color=ft.Colors.GREY_500)
            )
            return

        for backup in backups[:5]:  # 只显示最近5个
            row = ft.Row([
                ft.Text(backup["name"], size=11, expand=True),
                ft.Text(backup["created"], size=10, color=ft.Colors.GREY_500),
                ft.TextButton(
                    "恢复",
                    on_click=lambda e, path=backup["path"]: self._on_restore(path)
                )
            ])
            self.backup_list.controls.append(row)

    def _on_restore(self, backup_path: str):
        """恢复备份"""
        if self.on_restore_callback:
            self.on_restore_callback(backup_path)
        if self.page:
            self.page.pop_dialog()
            self.page.update()

    def _on_cancel(self, e):
        if self.page:
            self.page.pop_dialog()
            self.page.update()

    def _on_save(self, e):
        new_path = self.path_data["path"].strip()
        if self.on_save_callback:
            self.on_save_callback(self.remote_field.value)
        if self.on_path_save_callback and new_path:
            self.on_path_save_callback(new_path)
        if self.page:
            self.page.pop_dialog()
            self.page.update()
