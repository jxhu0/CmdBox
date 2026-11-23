# app.py
__version__ = "1.5.1"

import os
import sys
import flet as ft
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta, timezone

from services.config_service import ConfigService
from services.data_service import DataService, ExternalDataChangeError
from services.git_service import GitService
from services.clipboard_service import ClipboardService
from services.update_service import UpdateService
from services.file_dialog_service import choose_export_path
from services.search_runner import SearchRunner
from models.board import Board
from models.command import Command
from models.task import Task
from models.question import Question
from views.sidebar import Sidebar
from views.search_bar import SearchBar
from views.command_list import CommandList, CommandStack
from views.task_list import TaskList
from views.question_list import QuestionList
from views.board_desc_card import BoardDescCard
from views.dialogs import BoardDialog, CommandDialog, ConfirmDialog, EditAndCopyDialog, SettingsDialog, TaskDialog, QuestionDialog
from views.export_dialog import ExportDialog
from views.setup_wizard import create_setup_wizard
from views.update_dialog import UpdateDialog


class CmdBoxApp:
    """CmdBox 主应用"""

    def __init__(self, page: ft.Page, *, web_data_dir: Optional[str] = None):
        self.page = page
        self.web_data_dir = web_data_dir
        self._closing = False
        self._recurring_check_task = None
        self._last_recurring_check_date = None
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
        # 问题板块ID（虚拟板块，不存储在数据中）
        self.QUESTIONS_BOARD_ID = "__questions__"

        # 状态
        self.selected_board_id: Optional[str] = self.FAVORITES_BOARD_ID
        self.show_favorites_only: bool = True  # 初始显示收藏板块
        self.search_keyword: str = ""
        self.search_board_ids: Optional[List[str]] = None
        self.search_tag: Optional[str] = None

        # 移动指令时的防重复点击标志
        self._is_moving: bool = False

        # 检查是否已初始化
        config_path = (Path(web_data_dir) / ".web-config") if web_data_dir else (Path.home() / ".cmdbox")
        self.config_service = ConfigService(str(config_path))

        if web_data_dir:
            self.config_service.load()
            if self.config_service.get("repo_path") != web_data_dir:
                self.config_service.init(web_data_dir)
            self._init_app()
        elif self.config_service.load() and self.config_service.is_initialized():
            self._init_app()
        else:
            self._show_setup_wizard()

    def _setup_page(self):
        """设置页面属性"""
        self.page.title = "CmdBox"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.on_resize = self._on_page_resize

        if self.web_data_dir:
            return
        self.page.window.width = 900
        self.page.window.height = 600
        self.page.window.prevent_close = True
        self.page.window.on_event = self._on_window_event

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

    async def _on_window_event(self, event):
        if event.type in (ft.WindowEventType.FOCUS, ft.WindowEventType.RESTORE):
            self._check_recurring_tasks(force=True)
            return
        if event.type != ft.WindowEventType.CLOSE:
            return
        if self._closing:
            return
        if getattr(self, '_syncing', False):
            self._show_snack_bar('请等待当前数据操作完成后退出')
            return
        import asyncio
        self._closing = True
        self._set_edit_controls_disabled(True)
        try:
            if self.data_service:
                await asyncio.to_thread(self.data_service.close)
        except OSError as error:
            self._closing = False
            self._set_edit_controls_disabled(False)
            self._show_snack_bar(str(error), 10000)
            return
        if self.git_service:
            await asyncio.to_thread(self.git_service.cleanup)
        if self._recurring_check_task:
            self._recurring_check_task.cancel()
        if getattr(self, '_search_runner', None):
            self._search_runner.close()
        await self._close_window()

    def _on_page_resize(self, event):
        if not hasattr(self, 'sidebar_container'):
            return
        compact = event.width < 760
        self.sidebar.set_compact(compact)
        width = 104 if compact else 200
        if self.sidebar_container.width != width:
            self.sidebar_container.width = width
            self.sidebar_container.update()

    async def _close_window(self):
        """保存、清理完成后退出，避开旧版 Flet 在 Windows 的 destroy 延迟。"""
        if sys.platform == 'win32':
            # 与 Flet 上游修复一致：https://github.com/flet-dev/flet/pull/6428
            # 先将解除关闭拦截的补丁发送到客户端，再请求正常关闭。
            self.page.window.prevent_close = False
            self.page.update()
            await self.page.window.close()
        else:
            await self.page.window.destroy()

    def _show_setup_wizard(self):
        """显示设置向导"""
        self.page.clean()
        wizard = create_setup_wizard(self.page, on_complete=self._on_setup_complete)
        self.page.add(wizard)

    def _on_setup_complete(self, repo_path: str):
        """设置向导完成"""
        self.git_service = GitService(repo_path)
        if not self.git_service.is_repo() and not self.git_service.init_repo():
            self._show_snack_bar('无法初始化数据目录，请检查路径与写入权限', 8000)
            return
        try:
            self.config_service.init(repo_path)
        except OSError as error:
            self._show_snack_bar(f'配置保存失败：{error}', 8000)
            return
        self._init_app()

    def _init_app(self):
        """初始化应用"""
        repo_path = self.config_service.get("repo_path")

        # 初始化服务
        self.git_service = GitService(repo_path)
        try:
            self.data_service = DataService(repo_path)
            self.data_service.load()
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.page.clean()
            self.page.add(ft.Container(content=ft.Column([
                ft.Icon(ft.Icons.ERROR_OUTLINE, size=40, color=ft.Colors.ORANGE),
                ft.Text('无法加载数据', size=20, weight=ft.FontWeight.BOLD),
                ft.Text(str(error), selectable=True),
                ft.Text(f'数据目录：{repo_path}', selectable=True),
                ft.TextButton('重试', on_click=lambda e: self._init_app()),
                ft.TextButton('选择其他数据目录', on_click=lambda e: self._show_setup_wizard(),
                              visible=not bool(self.web_data_dir)),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
                alignment=ft.Alignment(0, 0), expand=True))
            return
        self.data_service.enable_background_saves(self._on_save_error)

        # 重置过期的周期性任务
        self._reset_recurring_tasks()

        # 构建界面
        self._build_ui()

        # 保持运行时跨天也能重置任务；窗口重新激活时另做即时检查。
        if self._recurring_check_task:
            self._recurring_check_task.cancel()
        self._recurring_check_task = self.page.run_task(self._watch_recurring_tasks)

        # 异步检查更新（不阻塞 UI）
        self._check_for_updates()

    def _reset_recurring_tasks(self, today=None):
        """重置过期的周期性任务"""
        _BJ_TZ = timezone(timedelta(hours=8))
        now = today or datetime.now(_BJ_TZ).date()
        changed = False
        for task in self.data_service.tasks:
            if not task.completed or not task.recurring or not task.completed_at:
                continue
            try:
                completed_date = datetime.strptime(task.completed_at, "%Y-%m-%d %H:%M").date()
            except ValueError:
                continue
            should_reset = False
            if task.recurring == "daily":
                should_reset = completed_date < now
            elif task.recurring == "weekly":
                completed_week = completed_date - timedelta(days=completed_date.weekday())
                current_week = now - timedelta(days=now.weekday())
                should_reset = completed_week < current_week
            elif task.recurring == "monthly":
                should_reset = (completed_date.year, completed_date.month) < (now.year, now.month)
            if should_reset:
                task.update(completed=False)
                changed = True
        if changed:
            self.data_service.save()
        self._last_recurring_check_date = now
        return changed

    def _check_recurring_tasks(self, force=False):
        """跨天或激活窗口时检查；同步和关闭期间不修改数据。"""
        if (not getattr(self, 'data_service', None)
                or not hasattr(self, 'sidebar')
                or getattr(self, '_closing', False)
                or getattr(self, '_syncing', False)):
            return
        today = datetime.now(timezone(timedelta(hours=8))).date()
        if not force and today == self._last_recurring_check_date:
            return
        if self._reset_recurring_tasks(today):
            if self.selected_board_id == self.TASKS_BOARD_ID:
                self._refresh_tasks()
            self._refresh_sidebar()

    async def _watch_recurring_tasks(self):
        import asyncio
        while True:
            await asyncio.sleep(60)
            self._check_recurring_tasks()

    def _on_save_error(self, error):
        async def notify():
            if isinstance(error, ExternalDataChangeError):
                self._show_snack_bar('检测到外部数据更新。请关闭后重新打开应用；本窗口的修改会在退出时另存为本地备份', 15000)
            else:
                self._show_snack_bar(f'保存失败，请重试或检查数据目录：{error}', 10000)
        self.page.run_task(notify)

    def _check_for_updates(self):
        """异步检查更新"""
        import threading
        if getattr(self, '_checking_updates', False) or self._closing:
            return
        self._checking_updates = True

        def check():
            try:
                has_update, latest_ver, notes = UpdateService.check_for_updates(__version__)
                if self._closing:
                    return
                if latest_ver and latest_ver != self.config_service.get_latest_version():
                    try:
                        self.config_service.set_latest_version(latest_ver)
                    except OSError:
                        # 缓存保存失败不应阻止本次更新提示，也不影响主数据。
                        pass
                if has_update and not self.config_service.is_in_update_remind_period():
                    self.page.run_task(self._show_update_dialog, latest_ver, notes or "")
            finally:
                self._checking_updates = False

        self._update_check_thread = threading.Thread(target=check, daemon=True)
        self._update_check_thread.start()

    async def _show_update_dialog(self, version, notes):
        """显示更新对话框"""
        if self._closing or getattr(self, '_syncing', False):
            return
        def on_remind_later():
            try:
                self.config_service.set_update_remind_until()
            except OSError as error:
                self._show_snack_bar(f'提醒设置保存失败：{error}', 6000)
                return False

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

        self.upload_btn = ft.IconButton(
            icon=ft.Icons.CLOUD_UPLOAD_OUTLINED,
            icon_size=20,
            tooltip="上传数据",
            on_click=self._on_upload_data
        )
        self.pull_btn = ft.IconButton(
            icon=ft.Icons.CLOUD_DOWNLOAD_OUTLINED,
            icon_size=20,
            tooltip="拉取数据",
            on_click=self._on_pull_data
        )
        self.header = ft.Container(
            content=ft.Row([
                self.logo,
                self.search_bar,
                ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.DOWNLOAD,
                        icon_size=20,
                        tooltip="导出指令",
                        on_click=self._on_export_click
                    ),
                    self.upload_btn,
                    self.pull_btn,
                    ft.IconButton(
                        icon=ft.Icons.SETTINGS_OUTLINED,
                        icon_size=20,
                        tooltip="设置",
                        on_click=self._on_settings
                    )
                ], spacing=0, tight=True),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
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
        self._command_views = {self.selected_board_id: self.command_list}
        self.command_stack = CommandStack([self.command_list], expand=True)

        # 任务列表
        self.task_list = TaskList(
            on_toggle_complete=self._on_toggle_task_complete,
            on_toggle_in_progress=self._on_toggle_task_in_progress,
            on_edit=self._on_edit_task,
            on_delete=self._on_delete_task,
            on_add_task=self._on_add_task,
            on_clear_completed=self._on_clear_completed_tasks
        )

        # 问题列表
        self.question_list = QuestionList(
            on_toggle_asked=self._on_toggle_question_asked,
            on_edit=self._on_edit_question,
            on_delete=self._on_delete_question,
            on_add_question=self._on_add_question,
            on_clear_asked=self._on_clear_asked_questions
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
            content=self.command_stack, expand=True,
            padding=ft.padding.only(left=5, right=5, top=4, bottom=5),
            visible=True
        )
        self.task_list_container = ft.Container(
            content=self.task_list, expand=True,
            padding=ft.padding.only(left=5, right=5, top=4, bottom=5),
            visible=False
        )
        self.question_list_container = ft.Container(
            content=self.question_list, expand=True,
            padding=ft.padding.only(left=5, right=5, top=4, bottom=5),
            visible=False
        )
        main_content = ft.Column([
            self.board_desc_container,
            self.command_list_container,
            self.task_list_container,
            self.question_list_container,
        ], expand=True, spacing=0)

        # 布局（侧边栏宽度减小）
        self.sidebar_container = ft.Container(content=self.sidebar, width=200)
        layout = ft.Row([
            self.sidebar_container,
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
        if isinstance(self.page.width, (int, float)):
            self._on_page_resize(self.page)

    def _refresh_commands(self, commands=None):
        """刷新指令列表"""
        if self.selected_board_id in (self.TASKS_BOARD_ID, self.QUESTIONS_BOARD_ID):
            return
        old_view = self.command_list
        view = self._command_views.pop(self.selected_board_id, None)
        is_new = view is None
        if is_new:
            view = CommandList(
                {board.id: board for board in self.data_service.boards},
                self._on_copy_command, self._on_edit_command, self._on_delete_command,
                self._on_toggle_favorite, self._on_add_command,
                self._on_move_up, self._on_move_down)
        self._command_views[self.selected_board_id] = view
        self.command_list = view
        view.boards = {board.id: board for board in self.data_service.boards}
        if commands is None:
            commands = self.data_service.search_commands(
                self.search_keyword, self.search_board_ids, self.search_tag)
        if self.show_favorites_only:
            commands = [command for command in commands if command.is_favorite]
            self.command_list.set_show_move_buttons(False)
        else:
            self.command_list.set_show_move_buttons(True)
        view.empty_filtered = bool(self.search_keyword or self.search_tag)
        view.update_commands(commands, update=not is_new)
        if old_view is not view:
            old_view.visible = False
            view.visible = True
            if is_new:
                self.command_stack.controls.append(view)
            if len(self._command_views) > 6:
                oldest = next(iter(self._command_views))
                removed = self._command_views.pop(oldest)
                self.command_stack.controls.remove(removed)
            self.command_stack.update()

    def _refresh_sidebar(self):
        """刷新侧边栏"""
        pending_count = len([t for t in self.data_service.tasks if not t.completed])
        pending_question_count = len([q for q in self.data_service.questions if not q.asked])
        self.sidebar.update_boards(
            self.data_service.boards,
            self.selected_board_id,
            self.FAVORITES_BOARD_ID,
            tasks_id=self.TASKS_BOARD_ID,
            questions_id=self.QUESTIONS_BOARD_ID,
            pending_task_count=pending_count,
            pending_question_count=pending_question_count
        )
        if self.search_bar.update_boards(self.data_service.boards):
            self.search_board_ids = None
            self.search_bar.cancel_pending_search()
        self._refresh_search_tags()
        # 同时更新指令列表的板块字典
        boards_dict = {b.id: b for b in self.data_service.boards}
        self.command_list.update_boards(boards_dict)

    def _refresh_status_counts(self):
        """Refresh badges without rebuilding search filters or board metadata."""
        self.sidebar.update_boards(
            self.data_service.boards, self.selected_board_id,
            self.FAVORITES_BOARD_ID, tasks_id=self.TASKS_BOARD_ID,
            questions_id=self.QUESTIONS_BOARD_ID,
            pending_task_count=sum(not task.completed for task in self.data_service.tasks),
            pending_question_count=sum(not question.asked for question in self.data_service.questions),
        )

    def _on_board_select(self, board_id: str):
        """选择板块"""
        self.selected_board_id = board_id
        # 切换板块时清除搜索关键词
        self.search_keyword = ""
        self.search_tag = None
        self.search_bar.reset_filters(board_id if board_id not in (
            self.FAVORITES_BOARD_ID, self.TASKS_BOARD_ID, self.QUESTIONS_BOARD_ID
        ) else None)
        self.search_bar.set_context(
            'tasks' if board_id == self.TASKS_BOARD_ID else
            'questions' if board_id == self.QUESTIONS_BOARD_ID else 'commands'
        )
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
        elif board_id == self.QUESTIONS_BOARD_ID:
            # 问题板块
            self.show_favorites_only = False
            self.search_board_ids = None
            self._show_question_list()
        else:
            self.show_favorites_only = False
            self.search_board_ids = [board_id]
            self._show_task_list(False)
        self._refresh_commands()
        self.sidebar.select_board(board_id)
        self._refresh_board_desc()

    async def _on_search(self, keyword: str, board_ids: Optional[List[str]], tag: Optional[str] = None):
        """后台搜索；输入、页面或数据版本变化时，不显示过期结果。"""
        if not getattr(self, '_search_runner', None):
            self._search_runner = SearchRunner()
        selected = self.selected_board_id
        search_bar = self.search_bar
        generation = self.search_bar._search_generation
        while True:
            if getattr(self, '_syncing', False) or getattr(self, '_closing', False):
                return
            revision = self.data_service.revision
            if selected == self.TASKS_BOARD_ID:
                results = await self._search_runner.run(self.data_service.search_tasks, keyword)
            elif selected == self.QUESTIONS_BOARD_ID:
                results = await self._search_runner.run(self.data_service.search_questions, keyword)
            else:
                results = await self._search_runner.run(self.data_service.search_commands, keyword, board_ids, tag)
            if (search_bar is not self.search_bar or generation != self.search_bar._search_generation
                    or selected != self.selected_board_id
                    or getattr(self, '_syncing', False) or getattr(self, '_closing', False)):
                return
            if revision == self.data_service.revision:
                break
        self.search_keyword, self.search_board_ids, self.search_tag = keyword, board_ids, tag
        if selected == self.TASKS_BOARD_ID:
            self._refresh_tasks(results)
        elif selected == self.QUESTIONS_BOARD_ID:
            self._refresh_questions(results)
        else:
            self._refresh_commands(results)

    def _get_all_tags(self) -> List[str]:
        """获取所有已使用的标签"""
        tags = set()
        for cmd in self.data_service.commands:
            tags.update(cmd.tags)
        return sorted(tags)

    def _refresh_search_tags(self):
        if self.search_bar.update_tags(self._get_all_tags()):
            self.search_tag = None
            self.search_bar.cancel_pending_search()

    def _can_edit_data(self):
        if getattr(self, '_closing', False):
            return False
        if getattr(self, '_syncing', False):
            self._show_snack_bar('请等待当前数据操作完成后再修改')
            return False
        return True

    def _guard_data_edit(self, callback):
        """延迟的弹窗回调同时检查忙碌状态与数据是否已整体替换。"""
        service = self.data_service
        generation = service.records_generation

        def guarded(*args, **kwargs):
            if not self._can_edit_data():
                return False
            if service is not self.data_service or generation != service.records_generation:
                self._show_snack_bar('数据已更新，请关闭此窗口后重新操作', 6000)
                return False
            return callback(*args, **kwargs)
        return guarded

    def _on_add_board(self):
        """添加板块"""
        def on_save(name: str, icon: str, description: str = ""):
            if name:
                board = Board.create(name, icon, description)
                self.data_service.add_board(board)
                self._refresh_sidebar()

        dialog = BoardDialog("新建板块", on_save=self._guard_data_edit(on_save))
        self.page.show_dialog(dialog)

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

        dialog = BoardDialog("编辑板块", board=board, on_save=self._guard_data_edit(on_save))
        self.page.show_dialog(dialog)

    def _on_edit_board_desc(self, board: Board):
        """编辑板块描述（从描述卡片）"""
        if getattr(self, '_syncing', False):
            return
        def on_save(name: str, icon: str, description: str = ""):
            if getattr(self, '_syncing', False):
                return
            if name:
                board.update(name=name, icon=icon, description=description)
                self.data_service.update_board(board)
                self._refresh_sidebar()
                self._refresh_board_desc()

        dialog = BoardDialog("编辑板块", board=board, on_save=self._guard_data_edit(on_save))
        self.page.show_dialog(dialog)

    def _refresh_board_desc(self):
        """刷新板块描述卡片"""
        # 收藏板块、任务板块和问题板块不显示描述卡片
        if self.selected_board_id in (self.FAVORITES_BOARD_ID, self.TASKS_BOARD_ID, self.QUESTIONS_BOARD_ID):
            self.board_desc_card.update_board(None)
            self.board_desc_container.visible = False
        elif self.selected_board_id:
            board = self.data_service.get_board(self.selected_board_id)
            self.board_desc_card.update_board(board)
            self.board_desc_container.visible = bool(board and board.description)
        else:
            self.board_desc_card.update_board(None)
            self.board_desc_container.visible = False
        self.page.update(self.board_desc_container, self.command_list_container,
                         self.task_list_container, self.question_list_container)

    def _on_delete_board(self, board_id: str):
        """删除板块"""
        board = next((b for b in self.data_service.boards if b.id == board_id), None)
        if not board:
            return

        def on_confirm():
            deleted_count = self.data_service.delete_board(board_id)
            # 如果删除的是当前选中的板块，清除选择
            if self.selected_board_id == board_id:
                self.selected_board_id = self.FAVORITES_BOARD_ID
                self.show_favorites_only = True
                self.search_board_ids = None
                self.search_keyword = ''
                self.search_tag = None
                self.search_bar.reset_filters()
            self._refresh_sidebar()
            self._refresh_commands()
            self._refresh_board_desc()
            self._show_snack_bar(f"已删除板块「{board.name}」及 {deleted_count} 条指令")

        dialog = ConfirmDialog(
            "确认删除",
            f"确定要删除板块「{board.name}」吗？该板块下的所有指令也会被删除。",
            on_confirm=self._guard_data_edit(on_confirm)
        )
        self.page.show_dialog(dialog)

    def _on_reorder_boards(self, board_ids: list):
        """处理板块拖拽重排序"""
        if not self._can_edit_data():
            return
        self.data_service.reorder_boards(board_ids)
        self._refresh_sidebar()

    def _on_add_command(self):
        """添加指令"""
        if not self.data_service.boards:
            self._show_snack_bar('请先创建板块')
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
            self._refresh_search_tags()
            self._refresh_commands()

        dialog = CommandDialog(
            "新建指令",
            boards=self.data_service.boards,
            selected_board_id=self.selected_board_id,
            existing_tags=self._get_all_tags(),
            on_save=self._guard_data_edit(on_save)
        )
        self.page.show_dialog(dialog)

    def _on_copy_command(self, command: Command):
        """复制指令"""
        if getattr(self, 'web_data_dir', None):
            self.page.run_task(self._copy_to_browser, command.content)
            return
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

    async def _copy_to_browser(self, content: str):
        try:
            await ft.Clipboard().set(content)
            self._show_snack_bar('已复制到剪贴板')
        except Exception as error:
            self._show_snack_bar(f'复制失败：{error}。可选中文本手动复制', 8000)

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
            self._refresh_search_tags()
            self._refresh_commands()

        dialog = CommandDialog(
            "编辑指令",
            boards=self.data_service.boards,
            command=command,
            existing_tags=self._get_all_tags(),
            on_save=self._guard_data_edit(on_save)
        )
        self.page.show_dialog(dialog)

    def _on_delete_command(self, command: Command):
        """删除指令"""
        def on_confirm():
            self.data_service.delete_command(command.id)
            self._refresh_search_tags()
            self._refresh_commands()

        dialog = ConfirmDialog(
            "确认删除",
            f"确定要删除指令「{command.title}」吗？",
            on_confirm=self._guard_data_edit(on_confirm)
        )
        self.page.show_dialog(dialog)

    def _on_toggle_favorite(self, command: Command):
        """切换收藏"""
        if not self._can_edit_data():
            return
        command.update(is_favorite=not command.is_favorite)
        self.data_service.update_command(command)
        self._refresh_commands()

    def _on_move_up(self, command: Command):
        """上移指令"""
        if not self._can_edit_data() or self._is_moving:
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
        if not self._can_edit_data() or self._is_moving:
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
        self.question_list_container.visible = False
        if show_tasks:
            self._refresh_tasks()

    def _show_question_list(self):
        """切换右侧内容区：问题列表"""
        self.command_list_container.visible = False
        self.task_list_container.visible = False
        self.question_list_container.visible = True
        self._refresh_questions()

    def _refresh_tasks(self, tasks=None):
        """刷新任务列表"""
        if tasks is None:
            tasks = self.data_service.search_tasks(self.search_keyword)
        self.task_list.empty_filtered = bool(self.search_keyword)
        self.task_list.update_tasks(tasks)

    def _on_fab_click(self, e):
        """FAB 按钮点击分发"""
        if self.selected_board_id == self.TASKS_BOARD_ID:
            self._on_add_task()
        elif self.selected_board_id == self.QUESTIONS_BOARD_ID:
            self._on_add_question()
        else:
            self._on_add_command()

    def _on_add_task(self):
        """添加任务"""
        def on_save(title: str, description: str, priority: str, recurring: str = ""):
            if title:
                task = Task.create(title=title, description=description, priority=priority)
                task.update(recurring=recurring)
                self.data_service.add_task(task)
                self._refresh_tasks()
                self._refresh_status_counts()

        dialog = TaskDialog("新建任务", on_save=self._guard_data_edit(on_save))
        self.page.show_dialog(dialog)

    def _on_edit_task(self, task: Task):
        """编辑任务"""
        def on_save(title: str, description: str, priority: str, recurring: str = ""):
            if title:
                task.update(title=title, description=description, priority=priority, recurring=recurring)
                self.data_service.update_task(task)
                self._refresh_tasks()

        dialog = TaskDialog("编辑任务", task=task, on_save=self._guard_data_edit(on_save))
        self.page.show_dialog(dialog)

    def _on_delete_task(self, task: Task):
        """删除任务"""
        def on_confirm():
            self.data_service.delete_task(task.id)
            self._refresh_tasks()
            self._refresh_status_counts()

        dialog = ConfirmDialog(
            "确认删除",
            f"确定要删除任务「{task.title}」吗？",
            on_confirm=self._guard_data_edit(on_confirm)
        )
        self.page.show_dialog(dialog)

    def _on_toggle_task_complete(self, task: Task):
        """切换任务完成状态"""
        if not self._can_edit_data():
            return
        task.update(completed=not task.completed)
        if task.completed:
            task.update(in_progress=False)
        self.data_service.update_task(task)
        self._refresh_tasks()
        self._refresh_status_counts()

    def _on_toggle_task_in_progress(self, task: Task):
        """切换任务执行中状态"""
        if not self._can_edit_data() or task.completed:
            return
        task.update(in_progress=not task.in_progress)
        self.data_service.update_task(task)
        self._refresh_tasks()

    def _on_clear_completed_tasks(self):
        """清除所有已完成任务"""
        def on_confirm():
            self.data_service.delete_completed_tasks()
            self._refresh_tasks()
            self._refresh_status_counts()

        completed_count = len([t for t in self.data_service.tasks if t.completed])
        dialog = ConfirmDialog(
            "确认清除",
            f"确定要清除 {completed_count} 个已完成的任务吗？",
            on_confirm=self._guard_data_edit(on_confirm)
        )
        self.page.show_dialog(dialog)

    # ==================== 问题相关 ====================

    def _refresh_questions(self, questions=None):
        """刷新问题列表"""
        if questions is None:
            questions = self.data_service.search_questions(self.search_keyword)
        self.question_list.empty_filtered = bool(self.search_keyword)
        self.question_list.update_questions(questions)

    def _on_add_question(self):
        """添加问题"""
        def on_save(title: str, description: str, answer: str, priority: str):
            if title:
                question = Question.create(title=title, description=description, answer=answer, priority=priority)
                self.data_service.add_question(question)
                self._refresh_questions()
                self._refresh_status_counts()

        dialog = QuestionDialog("新建问题", on_save=self._guard_data_edit(on_save))
        self.page.show_dialog(dialog)

    def _on_edit_question(self, question: Question):
        """编辑问题"""
        def on_save(title: str, description: str, answer: str, priority: str):
            if title:
                question.update(title=title, description=description, answer=answer, priority=priority)
                self.data_service.update_question(question)
                self._refresh_questions()

        dialog = QuestionDialog("编辑问题", question=question, on_save=self._guard_data_edit(on_save))
        self.page.show_dialog(dialog)

    def _on_delete_question(self, question: Question):
        """删除问题"""
        def on_confirm():
            self.data_service.delete_question(question.id)
            self._refresh_questions()
            self._refresh_status_counts()

        dialog = ConfirmDialog(
            "确认删除",
            f"确定要删除问题「{question.title}」吗？",
            on_confirm=self._guard_data_edit(on_confirm)
        )
        self.page.show_dialog(dialog)

    def _on_toggle_question_asked(self, question: Question):
        """切换问题询问状态"""
        if not self._can_edit_data():
            return
        question.update(asked=not question.asked)
        self.data_service.update_question(question)
        self._refresh_questions()
        self._refresh_status_counts()

    def _on_clear_asked_questions(self):
        """清除所有已询问问题"""
        def on_confirm():
            self.data_service.delete_asked_questions()
            self._refresh_questions()
            self._refresh_status_counts()

        asked_count = len([q for q in self.data_service.questions if q.asked])
        dialog = ConfirmDialog(
            "确认清除",
            f"确定要清除 {asked_count} 个已询问的问题吗？",
            on_confirm=self._guard_data_edit(on_confirm)
        )
        self.page.show_dialog(dialog)

    async def _on_upload_data(self, e):
        await self._run_data_transfer(upload=True)

    async def _on_pull_data(self, e):
        await self._run_data_transfer(upload=False)

    def _set_edit_controls_disabled(self, disabled):
        names = ('sidebar', 'command_stack', 'task_list', 'question_list', 'add_btn',
                 'search_bar', 'board_desc_container', 'upload_btn', 'pull_btn')
        controls = [getattr(self, name) for name in names if hasattr(self, name)]
        for control in controls:
            control.disabled = disabled
        if controls:
            self.page.update(*controls)
        return controls

    async def _run_data_transfer(self, upload: bool):
        """上传与拉取独立执行，并共享忙碌状态和错误处理。"""
        import asyncio
        if getattr(self, '_syncing', False) or getattr(self, '_closing', False):
            return
        self._syncing = True
        self.search_bar.cancel_pending_search()
        self._set_edit_controls_disabled(True)
        syncing_snack = None
        action = "上传" if upload else "拉取"
        try:
            # 检查是否有远程仓库
            if not self.git_service.has_remote():
                self._show_snack_bar("未配置远程仓库，请在设置中配置 Git 远程地址", 6000)
                return

            syncing_snack = ft.SnackBar(
                content=ft.Row([
                    ft.ProgressRing(width=16, height=16, stroke_width=2, color=ft.Colors.WHITE),
                    ft.Text(f"正在{action}数据...", size=14)
                ], spacing=10),
                duration=180000
            )
            self.page.overlay.append(syncing_snack)
            syncing_snack.open = True
            self.page.update()

            if upload and self._reset_recurring_tasks():
                # 将本周期任务状态纳入本次上传，而不是推送后才修改。
                self._refresh_sidebar()
                if self.selected_board_id == self.TASKS_BOARD_ID:
                    self._refresh_tasks()
            operation = self.git_service.upload_data if upload else self.git_service.pull_data
            success, msg = await asyncio.to_thread(operation, self.data_service)
            if not upload and success:
                self._reset_recurring_tasks()
                self._refresh_sidebar()
                selected = self.selected_board_id
                if (selected not in (self.FAVORITES_BOARD_ID, self.TASKS_BOARD_ID, self.QUESTIONS_BOARD_ID)
                        and not self.data_service.get_board(selected)):
                    selected = self.FAVORITES_BOARD_ID
                self._on_board_select(selected)

            # 关闭同步中提示
            syncing_snack.open = False
            if syncing_snack in self.page.overlay:
                self.page.overlay.remove(syncing_snack)
            self.page.update()

            if success:
                self.config_service.update_last_sync()
                self._show_snack_bar(msg)
            else:
                self._show_snack_bar(msg, 8000)
        except Exception as ex:
            # 确保关闭同步中提示
            if syncing_snack:
                syncing_snack.open = False
                if syncing_snack in self.page.overlay:
                    self.page.overlay.remove(syncing_snack)
                self.page.update()
            self._show_snack_bar(f"{action}失败: {str(ex)}", 8000)
        finally:
            self._syncing = False
            self._set_edit_controls_disabled(False)

    def _on_export_click(self, e):
        """点击导出按钮"""
        self.export_dialog.current_scope.disabled = self.selected_board_id in (
            self.TASKS_BOARD_ID, self.QUESTIONS_BOARD_ID)
        if self.export_dialog.current_scope.disabled:
            self.export_dialog.scope_group.value = 'all'
        self.page.show_dialog(self.export_dialog)

    async def _on_export_confirmed(self, scope: str, fmt: str, filename: str):
        """选择路径和写文件均异步执行，导出点击时的数据快照。"""
        import asyncio
        from dataclasses import replace
        if getattr(self, '_exporting', False):
            return
        self._exporting = True
        try:
            commands = self.data_service.commands
            if scope == 'current':
                if self.selected_board_id == self.FAVORITES_BOARD_ID:
                    commands = [c for c in commands if c.is_favorite]
                elif self.selected_board_id in (self.TASKS_BOARD_ID, self.QUESTIONS_BOARD_ID):
                    self._show_snack_bar('任务和问题板块没有指令，请选择“所有板块”导出')
                    return
                else:
                    commands = [c for c in commands if c.board_id == self.selected_board_id]
            commands = [replace(c, tags=list(c.tags)) for c in commands]
            board_names = {b.id: b.name for b in self.data_service.boards}
            filename = Path(filename or 'cmdbox_export').name
            ext = f'.{fmt}'
            if not filename.lower().endswith(ext):
                filename += ext
            if getattr(self, 'web_data_dir', None):
                data = await asyncio.to_thread(
                    self.data_service.export_commands_list, commands, fmt, board_names)
                await ft.FilePicker().save_file(
                    file_name=filename, file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=[fmt], src_bytes=data.encode('utf-8'))
            else:
                path = await choose_export_path(self.page, filename, fmt)
                if not path:
                    return
                data = await asyncio.to_thread(
                    self.data_service.export_commands_list, commands, fmt, board_names)
                await asyncio.to_thread(Path(path).write_text, data, encoding='utf-8')
            self._show_snack_bar(f'导出成功，共 {len(commands)} 条指令')
        except Exception as error:
            self._show_snack_bar(f'导出失败：{error}', 8000)
        finally:
            self._exporting = False

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
        if getattr(self, '_syncing', False):
            self._show_snack_bar('请等待上传或拉取完成后修改设置')
            return
        # 获取当前远程仓库地址
        current_remote_url = self.git_service.get_remote_url() or ""

        def on_save(remote_url: str):
            success, msg = self.git_service.set_remote_url(remote_url)
            if success:
                self._show_snack_bar(msg)
            else:
                self._show_snack_bar(f"设置失败: {msg}")
            return success

        async def on_restore(backup_path: str):
            """从备份恢复数据"""
            import asyncio
            if not self._can_edit_data():
                return False
            self._syncing = True
            self.search_bar.cancel_pending_search()
            self._set_edit_controls_disabled(True)
            try:
                await asyncio.to_thread(self.data_service.restore_backup, backup_path)
            except (OSError, ValueError, KeyError, TypeError) as error:
                self._show_snack_bar(f'恢复失败：{error}', 8000)
                return False
            finally:
                self._syncing = False
                self._set_edit_controls_disabled(False)
            # 刷新界面
            self.selected_board_id = self.FAVORITES_BOARD_ID
            self.show_favorites_only = True
            self.search_keyword, self.search_board_ids, self.search_tag = '', None, None
            self._build_ui()
            self._show_snack_bar("数据已恢复（已备份当前数据）")
            return True

        def on_path_save(new_path: str):
            """保存新的数据存储路径"""
            if getattr(self, 'web_data_dir', None):
                return False
            old_path = self.config_service.get("repo_path")
            if new_path != old_path:
                try:
                    self.config_service.set("repo_path", new_path)
                except OSError as error:
                    self._show_snack_bar(f'路径保存失败：{error}', 8000)
                    return False
                self._show_snack_bar("数据存储路径已更改，关闭并重新打开应用后生效")
            return True

        # 后台启动检查已缓存版本，打开设置不等待网络
        latest_version = self.config_service.get_latest_version()
        if latest_version:
            latest_version = latest_version.lstrip("v")

        dialog = SettingsDialog(
            repo_path=self.config_service.get("repo_path"),
            remote_url=current_remote_url,
            data_service=self.data_service,
            on_save=self._guard_data_edit(on_save),
            on_restore=on_restore,
            on_path_save=self._guard_data_edit(on_path_save),
            latest_version=latest_version
        )
        if getattr(self, 'web_data_dir', None):
            dialog.path_field.read_only = True
            dialog.browse_btn.visible = False
            dialog.tutorial_btn.visible = False
        self.page.show_dialog(dialog)


def main(page: ft.Page):
    CmdBoxApp(page)


def get_assets_dir():
    """获取 assets 目录路径，兼容 PyInstaller 打包环境"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，从 _MEIPASS 临时目录读取
        return os.path.join(sys._MEIPASS, "assets")
    return os.path.join(os.path.dirname(__file__), "assets")


if __name__ == "__main__":
    ft.app(target=main, assets_dir=get_assets_dir())
