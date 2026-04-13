# app.py
__version__ = "1.3.8"

import os
import sys
import flet as ft
from pathlib import Path
from typing import Optional, List, Dict

from services.config_service import ConfigService
from services.data_service import DataService
from services.git_service import GitService
from services.clipboard_service import ClipboardService
from services.update_service import UpdateService
from models.board import Board
from models.command import Command
from models.task import Task
from views.sidebar import Sidebar
from views.search_bar import SearchBar
from views.command_list import CommandList
from views.task_list import TaskList
from views.board_desc_card import BoardDescCard
from views.dialogs import BoardDialog, CommandDialog, ConfirmDialog, EditAndCopyDialog, SettingsDialog, TaskDialog
from views.export_dialog import ExportDialog
from views.setup_wizard import create_setup_wizard
from views.update_dialog import UpdateDialog


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

        # 收藏板块ID（虚拟板块，不存储在数据中）
        self.FAVORITES_BOARD_ID = "__favorites__"
        # 任务板块ID（虚拟板块，不存储在数据中）
        self.TASKS_BOARD_ID = "__tasks__"

        # 状态
        self.selected_board_id: Optional[str] = self.FAVORITES_BOARD_ID
        self.show_favorites_only: bool = True  # 初始显示收藏板块
        self.search_keyword: str = ""
        self.search_board_ids: Optional[List[str]] = None
        self.search_tag: Optional[str] = None

        # 移动指令时的防重复点击标志
        self._is_moving: bool = False

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

        # 根据操作系统设置字体
        import platform
        system = platform.system()
        if system == "Darwin":
            # macOS 使用苹方字体
            font_family = "PingFang SC"
        elif system == "Windows":
            # Windows 使用微软雅黑
            font_family = "Microsoft YaHei"
        else:
            # Linux 等其他系统
            font_family = "Source Han Sans SC"
        self.page.theme = ft.Theme(font_family=font_family)

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

        # 异步检查更新（不阻塞 UI）
        self._check_for_updates()

    def _check_for_updates(self):
        """异步检查更新"""
        import threading

        def check():
            # 如果当前版本高于缓存的最新版本，清除缓存以强制刷新
            cached = self.config_service.get_latest_version()
            if cached:
                # 去掉 v 前缀比较
                cached_ver = cached.lstrip("v")
                current_ver = __version__.lstrip("v")
                if current_ver > cached_ver:
                    self.config_service.clear_latest_version_cache()

            # 总是检测最新版本并保存到配置
            has_update, latest_ver, notes = UpdateService.check_for_updates(__version__)
            if latest_ver:
                self.config_service.set_latest_version(latest_ver)

            # 只有在免提醒期内才跳过弹窗
            if has_update and not self.config_service.is_in_update_remind_period():
                self.page.run_task(self._show_update_dialog, latest_ver, notes or "")

        thread = threading.Thread(target=check, daemon=True)
        thread.start()

    def _get_latest_version_sync(self):
        """同步获取最新版本（用于打开设置对话框时）"""
        try:
            has_update, latest_ver, notes = UpdateService.check_for_updates(__version__)
            if latest_ver:
                self.config_service.set_latest_version(latest_ver)
                return latest_ver
        except Exception:
            pass
        return self.config_service.get_latest_version()

    async def _show_update_dialog(self, version, notes):
        """显示更新对话框"""
        def on_remind_later():
            self.config_service.set_update_remind_until()

        dialog = UpdateDialog(version, notes, on_remind_later=on_remind_later)
        self.page.show_dialog(dialog)

    def _build_ui(self):
        """构建界面"""
        self.page.clean()

        # 获取板块字典
        boards_dict = {b.id: b for b in self.data_service.boards}

        # 搜索栏（先创建，供顶部栏使用）
        self.search_bar = SearchBar(
            boards=self.data_service.boards,
            tags=self._get_all_tags(),
            on_search=self._on_search
        )

        # 导出对话框
        self.export_dialog = ExportDialog(on_export=self._on_export_confirmed)

        # 顶部栏（简洁现代风格）
        # Logo 区域：深蓝背景 + CmdBox 文字（d和B连在一起）
        self.logo = ft.Container(
            content=ft.Row([
                ft.Text("Cmd", size=20, weight=ft.FontWeight.W_800, color=ft.Colors.WHITE),
                ft.Text("Box", size=20, weight=ft.FontWeight.W_800, color=ft.Colors.CYAN_200),
            ], spacing=-3, tight=True),
            bgcolor=ft.Colors.BLUE_GREY_800,
            padding=ft.padding.symmetric(horizontal=16, vertical=9),
            border_radius=9,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=7,
                color=ft.Colors.with_opacity(0.25, ft.Colors.BLUE_GREY_900),
                offset=(0, 2)
            )
        )

        self.header = ft.Container(
            content=ft.Row([
                self.logo,
                ft.Container(content=self.search_bar, expand=True, padding=ft.padding.only(left=10, right=10)),
                ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.DOWNLOAD,
                        icon_size=20,
                        tooltip="导出指令",
                        on_click=self._on_export_click
                    ),
                    ft.IconButton(
                        icon=ft.Icons.SYNC,
                        icon_size=20,
                        tooltip="同步",
                        on_click=self._on_sync
                    ),
                    ft.IconButton(
                        icon=ft.Icons.SETTINGS_OUTLINED,
                        icon_size=20,
                        tooltip="设置",
                        on_click=self._on_settings
                    )
                ], spacing=0)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, tight=False),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            bgcolor=ft.Colors.WHITE,
            border=ft.border.only(bottom=ft.border.BorderSide(1, ft.Colors.GREY_200))
        )

        # 侧边栏（宽度减小）
        self.sidebar = Sidebar(
            boards=self.data_service.boards,
            on_board_select=self._on_board_select,
            on_add_board=self._on_add_board,
            on_edit_board=self._on_edit_board,
            on_delete_board=self._on_delete_board,
            on_reorder_boards=self._on_reorder_boards,
            selected_board_id=self.selected_board_id,
            favorites_board_id=self.FAVORITES_BOARD_ID,
            tasks_board_id=self.TASKS_BOARD_ID
        )

        # 指令列表
        self.command_list = CommandList(
            boards=boards_dict,
            on_copy=self._on_copy_command,
            on_edit=self._on_edit_command,
            on_delete=self._on_delete_command,
            on_toggle_favorite=self._on_toggle_favorite,
            on_add_command=self._on_add_command,
            on_move_up=self._on_move_up,
            on_move_down=self._on_move_down
        )

        # 任务列表
        self.task_list = TaskList(
            on_toggle_complete=self._on_toggle_task_complete,
            on_edit=self._on_edit_task,
            on_delete=self._on_delete_task,
            on_add_task=self._on_add_task,
            on_clear_completed=self._on_clear_completed_tasks
        )

        # 板块描述卡片
        self.board_desc_card = BoardDescCard(
            board=None,
            on_edit=self._on_edit_board_desc
        )

        # 新建按钮
        self.add_btn = ft.FloatingActionButton(
            icon=ft.Icons.ADD,
            on_click=self._on_fab_click
        )

        # 主内容区
        self.board_desc_container = ft.Container(
            content=self.board_desc_card,
            padding=ft.padding.only(left=5, right=5, top=4, bottom=0),
            visible=False
        )

        # 内容区：指令列表 / 任务列表切换
        self.command_list_container = ft.Container(
            content=self.command_list, expand=True,
            padding=ft.padding.only(left=5, right=5, top=4, bottom=5),
            visible=True
        )
        self.task_list_container = ft.Container(
            content=self.task_list, expand=True,
            padding=ft.padding.only(left=5, right=5, top=4, bottom=5),
            visible=False
        )
        main_content = ft.Column([
            self.board_desc_container,
            self.command_list_container,
            self.task_list_container,
        ], expand=True, spacing=0)

        # 布局（侧边栏宽度减小）
        layout = ft.Row([
            ft.Container(content=self.sidebar, width=200),
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
        self._refresh_sidebar()

    def _refresh_commands(self):
        """刷新指令列表"""
        if self.show_favorites_only:
            # 收藏板块：显示所有收藏指令，隐藏移动按钮
            commands = self.data_service.get_favorite_commands()
            self.command_list.set_show_move_buttons(False)
        else:
            commands = self.data_service.search_commands(
                self.search_keyword,
                self.search_board_ids,
                self.search_tag
            )
            self.command_list.set_show_move_buttons(True)
        self.command_list.update_commands(commands)

    def _refresh_sidebar(self):
        """刷新侧边栏"""
        pending_count = len([t for t in self.data_service.tasks if not t.completed])
        self.sidebar.update_boards(
            self.data_service.boards,
            self.selected_board_id,
            self.FAVORITES_BOARD_ID,
            tasks_id=self.TASKS_BOARD_ID,
            pending_task_count=pending_count
        )
        self.search_bar.update_boards(self.data_service.boards)
        self.search_bar.update_tags(self._get_all_tags())
        # 同时更新指令列表的板块字典
        boards_dict = {b.id: b for b in self.data_service.boards}
        self.command_list.update_boards(boards_dict)

    def _on_board_select(self, board_id: str):
        """选择板块"""
        self.selected_board_id = board_id
        if board_id == self.FAVORITES_BOARD_ID:
            # 收藏板块
            self.show_favorites_only = True
            self.search_board_ids = None
            self._show_task_list(False)
        elif board_id == self.TASKS_BOARD_ID:
            # 任务板块
            self.show_favorites_only = False
            self.search_board_ids = None
            self._show_task_list(True)
        else:
            self.show_favorites_only = False
            self.search_board_ids = [board_id]
            self._show_task_list(False)
        self._refresh_commands()
        self._refresh_sidebar()
        self._refresh_board_desc()

    def _on_search(self, keyword: str, board_ids: Optional[List[str]], tag: Optional[str] = None):
        """搜索"""
        self.search_keyword = keyword
        self.search_board_ids = board_ids
        self.search_tag = tag
        if self.selected_board_id == self.TASKS_BOARD_ID:
            self._refresh_tasks()
        else:
            self._refresh_commands()

    def _get_all_tags(self) -> List[str]:
        """获取所有已使用的标签"""
        tags = set()
        for cmd in self.data_service.commands:
            tags.update(cmd.tags)
        return list(tags)

    def _on_add_board(self):
        """添加板块"""
        def on_save(name: str, icon: str, description: str = ""):
            if name:
                board = Board.create(name, icon, description)
                self.data_service.add_board(board)
                self._refresh_sidebar()
            self.page.pop_dialog()
            self.page.update()

        dialog = BoardDialog("新建板块", on_save=on_save)
        self.page.show_dialog(dialog)
        self.page.update()

    def _on_edit_board(self, board_id: str):
        """编辑板块"""
        board = self.data_service.get_board(board_id)
        if not board:
            return

        def on_save(name: str, icon: str, description: str = ""):
            if name:
                board.update(name=name, icon=icon, description=description)
                self.data_service.update_board(board)
                self._refresh_sidebar()
                self._refresh_board_desc()
            self.page.pop_dialog()
            self.page.update()

        dialog = BoardDialog("编辑板块", board=board, on_save=on_save)
        self.page.show_dialog(dialog)
        self.page.update()

    def _on_edit_board_desc(self, board: Board):
        """编辑板块描述（从描述卡片）"""
        def on_save(name: str, icon: str, description: str = ""):
            if name:
                board.update(name=name, icon=icon, description=description)
                self.data_service.update_board(board)
                self._refresh_sidebar()
                self._refresh_board_desc()
            self.page.pop_dialog()
            self.page.update()

        dialog = BoardDialog("编辑板块", board=board, on_save=on_save)
        self.page.show_dialog(dialog)
        self.page.update()

    def _refresh_board_desc(self):
        """刷新板块描述卡片"""
        # 收藏板块和任务板块不显示描述卡片
        if self.selected_board_id in (self.FAVORITES_BOARD_ID, self.TASKS_BOARD_ID):
            self.board_desc_card.update_board(None)
            self.board_desc_container.visible = False
        elif self.selected_board_id:
            board = self.data_service.get_board(self.selected_board_id)
            self.board_desc_card.update_board(board)
            self.board_desc_container.visible = bool(board and board.description)
        else:
            self.board_desc_card.update_board(None)
            self.board_desc_container.visible = False
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

    def _on_reorder_boards(self, board_ids: list):
        """处理板块拖拽重排序"""
        self.data_service.reorder_boards(board_ids)
        self._refresh_sidebar()

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
            existing_tags=self._get_all_tags(),
            on_save=on_save
        )
        self.page.show_dialog(dialog)
        self.page.update()

    def _on_copy_command(self, command: Command):
        """复制指令"""
        success = self.clipboard_service.copy(command.content)

        # 创建悬浮提示
        toast = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE if success else ft.Icons.ERROR,
                        color=ft.Colors.GREEN_600 if success else ft.Colors.RED_600, size=18),
                ft.Text("已复制到剪贴板" if success else "复制失败",
                        size=13, color=ft.Colors.GREY_800),
            ], tight=True, spacing=6),
            bgcolor=ft.Colors.WHITE,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border_radius=8,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=6,
                color=ft.Colors.with_opacity(0.15, ft.Colors.GREY_500),
                offset=(0, 2)
            )
        )

        # 添加到overlay
        self.page.overlay.append(toast)
        self.page.update()

        # 使用 page.run_task 延迟移除
        async def remove_toast():
            import asyncio
            await asyncio.sleep(2)
            if toast in self.page.overlay:
                self.page.overlay.remove(toast)
                self.page.update()

        self.page.run_task(remove_toast)

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
            existing_tags=self._get_all_tags(),
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

    def _on_move_up(self, command: Command):
        """上移指令"""
        if self._is_moving:
            return
        self._is_moving = True
        try:
            # 获取当前板块 ID（如果不是收藏板块）
            board_id = None if self.show_favorites_only else self.selected_board_id
            self.data_service.move_command_up(command.id, board_id)
            self._refresh_commands()
        finally:
            self._is_moving = False

    def _on_move_down(self, command: Command):
        """下移指令"""
        if self._is_moving:
            return
        self._is_moving = True
        try:
            # 获取当前板块 ID（如果不是收藏板块）
            board_id = None if self.show_favorites_only else self.selected_board_id
            self.data_service.move_command_down(command.id, board_id)
            self._refresh_commands()
        finally:
            self._is_moving = False

    # ==================== 任务相关 ====================

    def _show_task_list(self, show_tasks: bool):
        """切换右侧内容区：指令列表 / 任务列表"""
        self.command_list_container.visible = not show_tasks
        self.task_list_container.visible = show_tasks
        if show_tasks:
            self._refresh_tasks()

    def _refresh_tasks(self):
        """刷新任务列表"""
        tasks = self.data_service.get_sorted_tasks()
        if self.search_keyword:
            keyword = self.search_keyword.lower()
            tasks = [t for t in tasks if keyword in t.title.lower() or keyword in t.description.lower()]
        self.task_list.update_tasks(tasks)

    def _on_fab_click(self, e):
        """FAB 按钮点击分发"""
        if self.selected_board_id == self.TASKS_BOARD_ID:
            self._on_add_task()
        else:
            self._on_add_command()

    def _on_add_task(self):
        """添加任务"""
        def on_save(title: str, description: str, priority: str):
            if title:
                task = Task.create(title=title, description=description, priority=priority)
                self.data_service.add_task(task)
                self._refresh_tasks()
                self._refresh_sidebar()
            self.page.pop_dialog()
            self.page.update()

        dialog = TaskDialog("新建任务", on_save=on_save)
        self.page.show_dialog(dialog)
        self.page.update()

    def _on_edit_task(self, task: Task):
        """编辑任务"""
        def on_save(title: str, description: str, priority: str):
            if title:
                task.update(title=title, description=description, priority=priority)
                self.data_service.update_task(task)
                self._refresh_tasks()
                self._refresh_sidebar()
            self.page.pop_dialog()
            self.page.update()

        dialog = TaskDialog("编辑任务", task=task, on_save=on_save)
        self.page.show_dialog(dialog)
        self.page.update()

    def _on_delete_task(self, task: Task):
        """删除任务"""
        def on_confirm():
            self.data_service.delete_task(task.id)
            self._refresh_tasks()
            self._refresh_sidebar()
            self.page.pop_dialog()
            self.page.update()

        dialog = ConfirmDialog(
            "确认删除",
            f"确定要删除任务「{task.title}」吗？",
            on_confirm=on_confirm
        )
        self.page.show_dialog(dialog)
        self.page.update()

    def _on_toggle_task_complete(self, task: Task):
        """切换任务完成状态"""
        task.update(completed=not task.completed)
        self.data_service.update_task(task)
        self._refresh_tasks()
        self._refresh_sidebar()

    def _on_clear_completed_tasks(self):
        """清除所有已完成任务"""
        def on_confirm():
            self.data_service.delete_completed_tasks()
            self._refresh_tasks()
            self._refresh_sidebar()
            self.page.pop_dialog()
            self.page.update()

        completed_count = len([t for t in self.data_service.tasks if t.completed])
        dialog = ConfirmDialog(
            "确认清除",
            f"确定要清除 {completed_count} 个已完成的任务吗？",
            on_confirm=on_confirm
        )
        self.page.show_dialog(dialog)
        self.page.update()

    def _on_sync(self, e):
        """同步"""
        syncing_snack = None
        try:
            # 先保存当前数据
            self.data_service.save()

            # 检查是否有远程仓库
            if not self.git_service.has_remote():
                self._show_snack_bar("未配置远程仓库，请在设置中配置 Git 远程地址", 6000)
                return

            # 显示同步中提示
            syncing_snack = ft.SnackBar(
                content=ft.Row([
                    ft.ProgressRing(width=16, height=16, stroke_width=2, color=ft.Colors.WHITE),
                    ft.Text("正在同步...", size=14)
                ], spacing=10),
                duration=60000
            )
            self.page.overlay.append(syncing_snack)
            syncing_snack.open = True
            self.page.update()

            # 执行同步
            success, msg = self.git_service.sync(self.data_service)

            # 关闭同步中提示
            syncing_snack.open = False
            if syncing_snack in self.page.overlay:
                self.page.overlay.remove(syncing_snack)
            self.page.update()

            if success:
                self.config_service.update_last_sync()
                self._show_snack_bar("同步成功，重启应用后生效")
            else:
                self._show_snack_bar(msg, 8000)
        except Exception as ex:
            # 确保关闭同步中提示
            if syncing_snack:
                syncing_snack.open = False
                if syncing_snack in self.page.overlay:
                    self.page.overlay.remove(syncing_snack)
                self.page.update()
            self._show_snack_bar(f"同步失败: {str(ex)}", 8000)

    def _on_export_click(self, e):
        """点击导出按钮"""
        if self.export_dialog not in self.page.overlay:
            self.page.overlay.append(self.export_dialog)
        self.export_dialog.open = True
        self.page.update()

    def _on_export_confirmed(self, scope: str, fmt: str, filename: str):
        """确认导出"""
        # 确定板块 ID 和计数方式
        is_favorites = (self.selected_board_id == self.FAVORITES_BOARD_ID)

        if scope == "current":
            if is_favorites:
                # 收藏板块：导出收藏的指令
                commands = [c for c in self.data_service.commands if c.is_favorite]
                data = self.data_service.export_commands_list(commands, fmt)
                count = len(commands)
            else:
                board_id = self.selected_board_id
                data = self.data_service.export_commands(board_id=board_id, format=fmt)
                count = len([c for c in self.data_service.commands if c.board_id == board_id])
        else:
            # 所有板块
            data = self.data_service.export_commands(board_id=None, format=fmt)
            count = len(self.data_service.commands)

        # 添加文件扩展名
        ext = ".json" if fmt == "json" else ".csv"
        if not filename.endswith(ext):
            filename += ext

        # 使用跨平台文件保存对话框
        import threading
        import platform

        result = [None]  # 用于在线程间传递结果

        def run_dialog():
            system = platform.system()
            if system == "Darwin":  # macOS
                import subprocess
                script = f'''
set thePath to POSIX path of (choose file name default name "{filename}" with prompt "保存导出文件")
'''
                try:
                    proc = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
                    result[0] = proc.stdout.strip() if proc.returncode == 0 else None
                except:
                    result[0] = None
            else:  # Windows / Linux
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                root.update()
                try:
                    ext = ".json" if fmt == "json" else ".csv"
                    path = filedialog.asksaveasfilename(
                        initialfile=filename,
                        defaultextension=ext,
                        filetypes=[("JSON files", "*.json"), ("CSV files", "*.csv"), ("All files", "*.*")]
                    )
                    result[0] = path if path else None
                finally:
                    root.destroy()

        # 在新线程中运行对话框
        thread = threading.Thread(target=run_dialog)
        thread.start()
        thread.join()  # 等待用户选择
        path = result[0]

        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(data)
                self._show_snack_bar(f"导出成功，共 {count} 条指令")
            except Exception as ex:
                self._show_snack_bar(f"导出失败：{str(ex)}")
        self.page.update()

    def _show_snack_bar(self, message: str, duration: int = 4000):
        """显示 SnackBar

        Args:
            message: 提示消息
            duration: 显示时长（毫秒），默认 4000ms
        """
        # 清理 overlay 中已关闭的 SnackBar
        self.page.overlay[:] = [c for c in self.page.overlay if not isinstance(c, ft.SnackBar) or getattr(c, 'open', False)]

        snack_bar = ft.SnackBar(content=ft.Text(message), duration=duration)
        self.page.overlay.append(snack_bar)
        snack_bar.open = True
        self.page.update()

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

        def on_restore(backup_path: str):
            """从备份恢复数据"""
            import shutil
            # 备份当前数据
            current_backup = self.data_service.data_file.with_suffix(".json.bak")
            shutil.copy2(self.data_service.data_file, current_backup)
            # 复制备份文件
            shutil.copy2(backup_path, self.data_service.data_file)
            # 重新加载数据
            self.data_service.load()
            # 刷新界面
            self._refresh_sidebar()
            self._refresh_commands()
            self._show_snack_bar("数据已恢复（已备份当前数据）")

        def on_path_save(new_path: str):
            """保存新的数据存储路径"""
            old_path = self.config_service.get("repo_path")
            if new_path != old_path:
                self.config_service.set("repo_path", new_path)
                self._show_snack_bar("数据存储路径已更改，请重启应用生效")

        # 同步获取最新版本（直接请求不阻塞UI）
        latest_version = self._get_latest_version_sync()
        if latest_version:
            latest_version = latest_version.lstrip("v")

        dialog = SettingsDialog(
            repo_path=self.config_service.get("repo_path"),
            remote_url=current_remote_url,
            data_service=self.data_service,
            on_save=on_save,
            on_restore=on_restore,
            on_path_save=on_path_save,
            latest_version=latest_version
        )
        self.page.show_dialog(dialog)
        self.page.update()


def main(page: ft.Page):
    app = CmdBoxApp(page)

    # 处理窗口关闭事件，确保程序正确退出
    def on_window_event(e):
        if e.data == "close":
            # 清理 Git 资源
            try:
                app.git_service.cleanup()
            except Exception:
                pass

            page.window_destroy()
            import os
            import sys
            # Windows 需要额外处理 Flet 子进程
            if sys.platform == "win32":
                try:
                    import subprocess
                    # 获取当前进程 PID，终止所有子进程
                    current_pid = os.getpid()
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(current_pid)],
                                   capture_output=True, timeout=5)
                except Exception:
                    pass
            os._exit(0)

    page.on_window_event = on_window_event


def get_assets_dir():
    """获取 assets 目录路径，兼容 PyInstaller 打包环境"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，从 _MEIPASS 临时目录读取
        return os.path.join(sys._MEIPASS, "assets")
    return os.path.join(os.path.dirname(__file__), "assets")


if __name__ == "__main__":
    ft.app(target=main, assets_dir=get_assets_dir())
