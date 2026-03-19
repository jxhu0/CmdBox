# app.py
import flet as ft
from pathlib import Path
from typing import Optional, List, Dict

from services.config_service import ConfigService
from services.data_service import DataService
from services.git_service import GitService
from services.clipboard_service import ClipboardService
from models.board import Board
from models.command import Command
from views.sidebar import Sidebar
from views.search_bar import SearchBar
from views.command_list import CommandList
from views.dialogs import BoardDialog, CommandDialog, ConfirmDialog, EditAndCopyDialog, SettingsDialog
from views.setup_wizard import create_setup_wizard


class CmdBoxApp:
    """CmdBox 主应用"""

    def __init__(self, page: ft.Page):
        self.page = page
        self._setup_page()

        # 服务
        self.config_service: Optional[ConfigService] = None
        self.data_service: Optional[DataService] = None
        self.git_service: Optional[GitService] = None
        self.clipboard_service = ClipboardService()

        # 状态
        self.selected_board_id: Optional[str] = None
        self.search_keyword: str = ""
        self.search_board_ids: Optional[List[str]] = None

        # 检查是否已初始化
        config_path = Path.home() / ".cmdbox"
        self.config_service = ConfigService(str(config_path))

        if self.config_service.load() and self.config_service.is_initialized():
            self._init_app()
        else:
            self._show_setup_wizard()

    def _setup_page(self):
        """设置页面属性"""
        self.page.title = "CmdBox"
        self.page.window.width = 900
        self.page.window.height = 600
        self.page.theme_mode = ft.ThemeMode.LIGHT

    def _show_setup_wizard(self):
        """显示设置向导"""
        self.page.clean()
        wizard = create_setup_wizard(self.page, on_complete=self._on_setup_complete)
        self.page.add(wizard)

    def _on_setup_complete(self, repo_path: str):
        """设置向导完成"""
        # 初始化配置
        self.config_service.init(repo_path)

        # 初始化 Git 仓库
        self.git_service = GitService(repo_path)
        self.git_service.init_repo()

        # 初始化数据服务
        self.data_service = DataService(repo_path)
        self.data_service.load()

        # 初始提交
        self.git_service.commit("Initial commit")

        self._init_app()

    def _init_app(self):
        """初始化应用"""
        repo_path = self.config_service.get("repo_path")

        # 初始化服务
        self.git_service = GitService(repo_path)
        self.data_service = DataService(repo_path)
        self.data_service.load()

        # 构建界面
        self._build_ui()

    def _build_ui(self):
        """构建界面"""
        self.page.clean()

        # 获取板块字典
        boards_dict = {b.id: b for b in self.data_service.boards}

        # 顶部栏（紧凑设计）
        self.header = ft.Container(
            content=ft.Row([
                ft.Text("CmdBox", size=16, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.SYNC,
                        tooltip="同步",
                        on_click=self._on_sync
                    ),
                    ft.IconButton(
                        icon=ft.Icons.SETTINGS,
                        tooltip="设置",
                        on_click=self._on_settings
                    )
                ])
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=5,
            bgcolor=ft.Colors.BLUE_50
        )

        # 侧边栏（宽度减小）
        self.sidebar = Sidebar(
            boards=self.data_service.boards,
            on_board_select=self._on_board_select,
            on_add_board=self._on_add_board,
            on_delete_board=self._on_delete_board,
            selected_board_id=self.selected_board_id
        )

        # 搜索栏
        self.search_bar = SearchBar(
            boards=self.data_service.boards,
            on_search=self._on_search
        )

        # 指令列表
        self.command_list = CommandList(
            boards=boards_dict,
            on_copy=self._on_copy_command,
            on_edit=self._on_edit_command,
            on_delete=self._on_delete_command,
            on_toggle_favorite=self._on_toggle_favorite,
            on_add_command=self._on_add_command
        )

        # 新建指令按钮
        self.add_btn = ft.FloatingActionButton(
            icon=ft.Icons.ADD,
            on_click=lambda e: self._on_add_command()
        )

        # 主内容区（搜索栏紧凑）
        main_content = ft.Column([
            ft.Container(content=self.search_bar, padding=5),
            ft.Divider(height=1),
            ft.Container(content=self.command_list, expand=True, padding=5)
        ], expand=True)

        # 布局（侧边栏宽度减小）
        layout = ft.Row([
            ft.Container(content=self.sidebar, width=150),
            ft.VerticalDivider(width=1),
            ft.Container(content=main_content, expand=True)
        ], expand=True)

        # 添加到页面
        self.page.add(ft.Column([
            self.header,
            ft.Divider(height=1),
            layout
        ], expand=True))

        self.page.floating_action_button = self.add_btn

        # 加载初始数据
        self._refresh_commands()

    def _refresh_commands(self):
        """刷新指令列表"""
        commands = self.data_service.search_commands(
            self.search_keyword,
            self.search_board_ids
        )
        self.command_list.update_commands(commands)

    def _refresh_sidebar(self):
        """刷新侧边栏"""
        self.sidebar.update_boards(
            self.data_service.boards,
            self.selected_board_id
        )
        self.search_bar.update_boards(self.data_service.boards)
        # 同时更新指令列表的板块字典
        boards_dict = {b.id: b for b in self.data_service.boards}
        self.command_list.update_boards(boards_dict)

    def _on_board_select(self, board_id: str):
        """选择板块"""
        self.selected_board_id = board_id
        self.search_board_ids = [board_id]
        self._refresh_commands()
        self._refresh_sidebar()

    def _on_search(self, keyword: str, board_ids: Optional[List[str]]):
        """搜索"""
        self.search_keyword = keyword
        self.search_board_ids = board_ids
        self._refresh_commands()

    def _on_add_board(self):
        """添加板块"""
        def on_save(name: str, icon: str):
            if name:
                board = Board.create(name, icon)
                self.data_service.add_board(board)
                self._refresh_sidebar()
            self.page.pop_dialog()
            self.page.update()

        dialog = BoardDialog("新建板块", on_save=on_save)
        self.page.show_dialog(dialog)
        self.page.update()

    def _on_delete_board(self, board_id: str):
        """删除板块"""
        board = next((b for b in self.data_service.boards if b.id == board_id), None)
        if not board:
            return

        def on_confirm():
            deleted_count = self.data_service.delete_board(board_id)
            # 如果删除的是当前选中的板块，清除选择
            if self.selected_board_id == board_id:
                self.selected_board_id = None
                self.search_board_ids = None
            self._refresh_sidebar()
            self._refresh_commands()
            self._show_snack_bar(f"已删除板块「{board.name}」及 {deleted_count} 条指令")

        dialog = ConfirmDialog(
            "确认删除",
            f"确定要删除板块「{board.name}」吗？该板块下的所有指令也会被删除。",
            on_confirm=on_confirm
        )
        self.page.show_dialog(dialog)
        self.page.update()

    def _on_add_command(self):
        """添加指令"""
        if not self.data_service.boards:
            self.page.snack_bar = ft.SnackBar(ft.Text("请先创建板块"))
            self.page.snack_bar.open = True
            self.page.update()
            return

        def on_save(**kwargs):
            command = Command.create(
                board_id=kwargs["board_id"],
                title=kwargs["title"],
                content=kwargs["content"],
                description=kwargs.get("description", ""),
                tags=kwargs.get("tags", []),
                is_favorite=kwargs.get("is_favorite", False)
            )
            self.data_service.add_command(command)
            self._refresh_commands()

        dialog = CommandDialog(
            "新建指令",
            boards=self.data_service.boards,
            selected_board_id=self.selected_board_id,
            on_save=on_save
        )
        self.page.show_dialog(dialog)
        self.page.update()

    def _on_copy_command(self, command: Command):
        """复制指令"""
        if self.clipboard_service.copy(command.content):
            self.page.snack_bar = ft.SnackBar(ft.Text("已复制到剪贴板"))
        else:
            self.page.snack_bar = ft.SnackBar(ft.Text("复制失败"))
        self.page.snack_bar.open = True
        self.page.update()

    def _on_edit_command(self, command: Command):
        """编辑指令"""
        def on_save(**kwargs):
            command.update(
                title=kwargs["title"],
                board_id=kwargs["board_id"],
                content=kwargs["content"],
                description=kwargs.get("description", ""),
                tags=kwargs.get("tags", []),
                is_favorite=kwargs.get("is_favorite", False)
            )
            self.data_service.update_command(command)
            self._refresh_commands()

        dialog = CommandDialog(
            "编辑指令",
            boards=self.data_service.boards,
            command=command,
            on_save=on_save
        )
        self.page.show_dialog(dialog)
        self.page.update()

    def _on_delete_command(self, command: Command):
        """删除指令"""
        def on_confirm():
            self.data_service.delete_command(command.id)
            self._refresh_commands()

        dialog = ConfirmDialog(
            "确认删除",
            f"确定要删除指令「{command.title}」吗？",
            on_confirm=on_confirm
        )
        self.page.show_dialog(dialog)
        self.page.update()

    def _on_toggle_favorite(self, command: Command):
        """切换收藏"""
        command.update(is_favorite=not command.is_favorite)
        self.data_service.update_command(command)
        self._refresh_commands()

    def _on_sync(self, e):
        """同步"""
        try:
            # 先保存当前数据
            self.data_service.save()

            # 检查是否有远程仓库
            if not self.git_service.has_remote():
                self._show_snack_bar("未配置远程仓库，请在设置中配置 Git 远程地址")
                return

            # 执行同步
            success, msg = self.git_service.sync()

            if success:
                self.config_service.update_last_sync()

            self._show_snack_bar(msg)
        except Exception as ex:
            self._show_snack_bar(f"同步失败: {str(ex)}")

    def _show_snack_bar(self, message: str):
        """显示 SnackBar"""
        snack_bar = ft.SnackBar(ft.Text(message))
        self.page.show_dialog(snack_bar)

    def _on_settings(self, e):
        """设置"""
        # 获取当前远程仓库地址
        current_remote_url = self.git_service.get_remote_url() or ""

        def on_save(remote_url: str):
            if remote_url:
                success, msg = self.git_service.set_remote_url(remote_url)
                if success:
                    self._show_snack_bar(msg)
                else:
                    self._show_snack_bar(f"设置失败: {msg}")
            else:
                self._show_snack_bar("远程地址已清除")

        dialog = SettingsDialog(
            repo_path=self.config_service.get("repo_path"),
            remote_url=current_remote_url,
            on_save=on_save
        )
        self.page.show_dialog(dialog)
        self.page.update()


def main(page: ft.Page):
    CmdBoxApp(page)


if __name__ == "__main__":
    ft.app(target=main)
