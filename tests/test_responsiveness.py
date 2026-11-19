import asyncio
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from app import CmdBoxApp
from models.command import Command
from models.board import Board
from models.task import Task
from models.question import Question
from services.data_service import DataService
from services.search_runner import SearchRunner
from views.question_card import QuestionCard
from views.question_list import QuestionList
from views.search_bar import SearchBar
from views.task_list import TaskList
from views.sidebar import Sidebar


class SearchAndPagingTests(unittest.TestCase):
    def test_cached_search_sees_edits_reloads_and_removals(self):
        service = DataService('.')
        first = Command.create('board', 'Straße', 'old')
        second = Command.create('board', 'Second', 'old')
        service.commands = [first, second]
        self.assertEqual(service.search_commands('STRASSE'), [first])
        first.update(content='new content')
        self.assertEqual(service.search_commands('new'), [first])
        replacement = Command.from_dict(first.to_dict())
        replacement.content = 'reloaded'
        service.commands = [replacement]
        self.assertEqual(service.search_commands('old'), [])
        self.assertEqual(service.search_commands('reloaded'), [replacement])

    def test_new_item_on_same_list_and_sorting_reset_pagination(self):
        for cls, model, collection, refresh in [
            (TaskList, Task, 'tasks', 'update_tasks'),
            (QuestionList, Question, 'questions', 'update_questions'),
        ]:
            view = cls(*([Mock()] * (5 if cls is TaskList else 4)))
            items = [model.create(str(i)) for i in range(50)]
            with patch.object(view, 'update'):
                getattr(view, refresh)(items)
                view._load_more(None)
                self.assertEqual(view._page_start, 20)
                items.append(model.create('新增'))
                getattr(view, refresh)(items)
                self.assertEqual(view._page_start, 0)
                view._load_more(None)
                view._select_sort_mode(1)
                self.assertEqual(view._page_start, 0)

    def test_clear_and_submit_cancel_pending_search_and_apply_immediately(self):
        callback = Mock()
        search = SearchBar([], [], callback)
        search._pending_search = Mock()
        pending = search._pending_search
        search.search_input.value = 'keyword'
        asyncio.run(search._on_submit(None))
        pending.cancel.assert_called_once()
        callback.assert_called_with('keyword', None, None)
        with patch.object(search.search_input, 'update'):
            asyncio.run(search.clear_search())
        callback.assert_called_with('', None, None)

    def test_time_sort_also_orders_running_tasks_and_priority_ties_are_newest_first(self):
        older, newer = Task.create('older'), Task.create('newer')
        older.created_at, newer.created_at = '2026-01-01', '2026-01-02'
        older.in_progress = newer.in_progress = True
        view = TaskList(*([Mock()] * 5))
        view.tasks = [older, newer]
        for mode in (0, 1, 2):
            view.sort_mode_index = mode
            self.assertEqual(view._get_sorted_tasks(), [newer, older])

    def test_filtered_empty_state_changes_back_when_filter_is_cleared(self):
        from views.command_list import CommandList
        cases = [(CommandList({}, *([Mock()] * 5)), 'update_commands', '指令'),
                 (TaskList(*([Mock()] * 5)), 'update_tasks', '任务'),
                 (QuestionList(*([Mock()] * 4)), 'update_questions', '问题')]
        for view, method, noun in cases:
            with self.subTest(noun=noun), patch.object(view, 'update'):
                view.empty_filtered = True
                getattr(view, method)([])
                self.assertEqual(view.controls[0].content.controls[1].value, f'没有匹配的{noun}')
                view.empty_filtered = False
                getattr(view, method)([])
                self.assertEqual(view.controls[0].content.controls[1].value, f'暂无{noun}')

    def test_long_answers_can_expand_without_rebuilding_other_cards(self):
        question = Question.create('问题', answer='很长的解答' * 100)
        card = QuestionCard(question, *([Mock()] * 3))
        with patch.object(card, 'update'):
            self.assertEqual(card._answer_text.max_lines, 6)
            card._toggle_answer(None)
            self.assertIsNone(card._answer_text.max_lines)
            card._toggle_answer(None)
            self.assertEqual(card._answer_text.max_lines, 6)

    def test_compact_sidebar_keeps_navigation_and_board_management(self):
        board = Board.create('一个很长的板块名称')
        select, add, edit, delete, reorder = [Mock() for _ in range(5)]
        sidebar = Sidebar([board], select, add, edit, delete, reorder,
                          favorites_board_id='fav', tasks_board_id='tasks', questions_board_id='questions')
        with patch('flet.controls.base_control.BaseControl.update'):
            sidebar.set_compact(True)
            self.assertEqual(sidebar.width, 96)
            row = sidebar.content.controls[-2].content.controls[0].content.content.content
            self.assertFalse(row.controls[1].visible)
            row.controls[3].items[0].on_click(None)
            edit.assert_called_once_with(board.id)
            row.controls[3].items[1].on_click(None)
            delete.assert_called_once_with(board.id)
            sidebar.select_board('questions')
            self.assertEqual(sidebar.selected_board_id, 'questions')
            sidebar.set_compact(False)
            self.assertEqual(sidebar.width, 180)


class AsyncExportTests(unittest.IsolatedAsyncioTestCase):
    async def test_file_picker_does_not_block_loop_and_export_uses_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            app = CmdBoxApp.__new__(CmdBoxApp)
            app.page = Mock()
            app._show_snack_bar = Mock()
            app.FAVORITES_BOARD_ID, app.TASKS_BOARD_ID, app.QUESTIONS_BOARD_ID = 'fav', 'tasks', 'questions'
            app.selected_board_id = 'fav'
            app.data_service = DataService(directory)
            app.data_service.load()
            command = Command.create(app.data_service.boards[0].id, '导出时的标题', 'echo hello', is_favorite=True)
            app.data_service.commands = [command]
            entered, release = asyncio.Event(), asyncio.Event()
            target = Path(directory) / 'export.json'

            async def choose(*_):
                entered.set()
                await release.wait()
                return str(target)

            with patch('app.choose_export_path', side_effect=choose):
                pending = asyncio.create_task(app._on_export_confirmed('current', 'json', 'export'))
                await asyncio.wait_for(entered.wait(), timeout=2)
                command.update(title='导出期间继续编辑')
                release.set()
                await pending
            self.assertEqual(json.loads(target.read_text(encoding='utf-8'))['commands'][0]['title'], '导出时的标题')
            self.assertFalse(app._exporting)

    async def test_cancelled_or_failed_picker_allows_retry(self):
        app = CmdBoxApp.__new__(CmdBoxApp)
        app.page = Mock()
        app._show_snack_bar = Mock()
        app.data_service = Mock(commands=[], boards=[])
        with patch('app.choose_export_path', new=AsyncMock(return_value=None)):
            await app._on_export_confirmed('all', 'csv', 'export')
            self.assertFalse(app._exporting)
        with patch('app.choose_export_path', side_effect=OSError('no picker')):
            await app._on_export_confirmed('all', 'csv', 'export')
            self.assertFalse(app._exporting)
            app._show_snack_bar.assert_called_once()


class AsyncSearchTests(unittest.IsolatedAsyncioTestCase):
    def make_app(self):
        app = CmdBoxApp.__new__(CmdBoxApp)
        app._syncing = app._closing = False
        app.FAVORITES_BOARD_ID, app.TASKS_BOARD_ID, app.QUESTIONS_BOARD_ID = 'fav', 'tasks', 'questions'
        app.selected_board_id = 'fav'
        app.search_keyword = ''
        app.search_bar = Mock(_search_generation=1)
        app.data_service = Mock(revision=0)
        app._search_runner = SearchRunner()
        self.addCleanup(app._search_runner.close)
        app._refresh_commands = Mock()
        app._refresh_tasks = Mock()
        app._refresh_questions = Mock()
        return app

    async def test_old_background_result_cannot_override_navigation(self):
        app = self.make_app()
        started, release = threading.Event(), threading.Event()
        ui_thread = threading.get_ident()

        def search(*_):
            self.assertNotEqual(threading.get_ident(), ui_thread)
            started.set()
            self.assertTrue(release.wait(5))
            return ['old result']

        app.data_service.search_commands.side_effect = search
        pending = asyncio.create_task(app._on_search('old', None))
        try:
            self.assertTrue(await asyncio.to_thread(started.wait, 5))
            app.selected_board_id = 'tasks'
            app.search_bar._search_generation += 1
        finally:
            release.set()
            await pending
        app._refresh_commands.assert_not_called()
        self.assertEqual(app.search_keyword, '')

    async def test_search_retries_when_data_changes_before_result_is_applied(self):
        app = self.make_app()
        def search(*_):
            if app.data_service.revision == 0:
                app.data_service.revision = 1
                return ['outdated']
            return ['latest']
        app.data_service.search_commands.side_effect = search
        await app._on_search('query', None)
        self.assertEqual(app.data_service.search_commands.call_count, 2)
        app._refresh_commands.assert_called_once_with(['latest'])
