import asyncio
import tempfile
import threading
import unittest
from unittest.mock import Mock, PropertyMock, patch

from app import CmdBoxApp
from models.command import Command
from models.task import Task
from models.question import Question
from services.data_service import DataService
from services.config_service import ConfigService
from views.dialogs import BoardDialog, TaskDialog, QuestionDialog, CommandDialog, ConfirmDialog, SettingsDialog
from views.search_bar import SearchBar


class EditGuardTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.app = CmdBoxApp.__new__(CmdBoxApp)
        self.app.data_service = DataService(directory.name)
        self.app.data_service.load()
        self.app.page, self.app._show_snack_bar = Mock(), Mock()
        self.app._syncing = self.app._closing = False

    def test_delayed_edit_cannot_write_during_transfer_or_after_reload(self):
        task = Task.create('原始任务')
        self.app.data_service.add_task(task)
        self.app._on_edit_task(task)
        callback = self.app.page.show_dialog.call_args.args[0].on_save_callback
        self.app._syncing = True
        self.assertFalse(callback('同步期间的编辑', '', 'medium'))
        self.assertEqual(task.title, '原始任务')
        self.app._syncing = False
        self.app.data_service.load()
        self.assertFalse(callback('旧弹窗的编辑', '', 'medium'))
        self.assertEqual(self.app.data_service.tasks[0].title, '原始任务')

    def test_ordinary_edits_do_not_invalidate_another_open_editor(self):
        callback = Mock()
        guarded = self.app._guard_data_edit(callback)
        self.app.data_service.add_task(Task.create('另一个正常编辑'))
        guarded('有效编辑')
        callback.assert_called_once_with('有效编辑')

    def test_delivered_toggle_events_do_not_mutate_data_while_busy(self):
        command = Command.create(self.app.data_service.boards[0].id, '指令', 'echo hello')
        task, question = Task.create('任务'), Question.create('问题')
        for closing in (False, True):
            self.app._closing, self.app._syncing = closing, not closing
            self.app._on_toggle_favorite(command)
            self.app._on_toggle_task_complete(task)
            self.app._on_toggle_task_in_progress(task)
            self.app._on_toggle_question_asked(question)
            self.assertFalse(command.is_favorite or task.completed or task.in_progress or question.asked)

    def test_rejected_saves_keep_editor_values_and_confirmation_open(self):
        board = self.app.data_service.boards[0]
        dialogs = [BoardDialog('编辑', board, on_save=Mock(return_value=False)),
                   TaskDialog('编辑', Task.create('任务'), on_save=Mock(return_value=False)),
                   QuestionDialog('编辑', Question.create('问题'), on_save=Mock(return_value=False)),
                   CommandDialog('编辑', [board], command=Command.create(board.id, '指令', 'body'),
                                 on_save=Mock(return_value=False)),
                   ConfirmDialog('确认', '删除？', on_confirm=Mock(return_value=False))]
        for dialog in dialogs:
            with self.subTest(dialog=type(dialog).__name__), \
                    patch.object(type(dialog), 'page', new_callable=PropertyMock) as page:
                page.return_value = Mock()
                if isinstance(dialog, ConfirmDialog):
                    dialog._on_confirm(None)
                else:
                    dialog._on_save(None)
                page.return_value.pop_dialog.assert_not_called()

    def test_removing_last_tag_clears_both_visible_and_applied_filter(self):
        app = self.app
        app.search_tag = 'removed'
        app.search_bar = SearchBar([], ['removed'], Mock())
        app.search_bar.tag_dropdown.value = 'removed'
        with patch.object(app.search_bar.tag_dropdown, 'update'):
            app._refresh_search_tags()
        self.assertIsNone(app.search_tag)
        self.assertEqual(app.search_bar.tag_dropdown.value, 'all')


class RestoreInteractionTests(unittest.IsolatedAsyncioTestCase):
    async def test_restore_blocks_repeat_and_other_actions_and_recovers_after_failure(self):
        entered, release = asyncio.Event(), asyncio.Event()

        async def restore(_):
            entered.set()
            await release.wait()
            return False

        dialog = SettingsDialog('/data', '', on_restore=restore)
        dialog.open = True
        page = Mock()
        with patch.object(SettingsDialog, 'page', new_callable=PropertyMock, return_value=page), \
                patch.object(dialog, 'update'):
            dialog._on_restore('/backup.json')
            confirm = page.show_dialog.call_args.args[0]
            pending = asyncio.create_task(confirm.actions[-1].on_click(None))
            await asyncio.wait_for(entered.wait(), 2)
            self.assertTrue(dialog.disabled)
            self.assertTrue(dialog._restoring)
            dialog._on_cancel(None)
            await confirm.actions[-1].on_click(None)
            page.pop_dialog.assert_called_once()
            release.set()
            await pending
            self.assertTrue(dialog.open)
            self.assertFalse(dialog.disabled)
            self.assertFalse(dialog._restoring)


class UpdateLifecycleTests(unittest.TestCase):
    def make_app(self):
        app = CmdBoxApp.__new__(CmdBoxApp)
        app._closing = False
        app.config_service, app.page = Mock(), Mock()
        app.config_service.is_in_update_remind_period.return_value = False
        return app

    def test_duplicate_checks_coalesce_and_closing_suppresses_late_prompt(self):
        app = self.make_app()
        entered, release = threading.Event(), threading.Event()

        def fetch(_):
            entered.set()
            if not release.wait(5):
                raise TimeoutError('test check not released')
            return True, 'v2.0.0', 'notes'

        with patch('app.UpdateService.check_for_updates', side_effect=fetch) as request:
            app._check_for_updates()
            try:
                self.assertTrue(entered.wait(5))
                app._check_for_updates()
                app._closing = True
            finally:
                release.set()
                app._update_check_thread.join(5)
            self.assertFalse(app._update_check_thread.is_alive())
            request.assert_called_once()
        app.page.run_task.assert_not_called()
        self.assertFalse(app._checking_updates)

    def test_update_cache_write_error_does_not_hide_available_update(self):
        app = self.make_app()
        app.config_service.set_latest_version.side_effect = OSError('read-only configuration')
        with patch('app.UpdateService.check_for_updates', return_value=(True, 'v2.0.0', 'notes')):
            app._check_for_updates()
            app._update_check_thread.join(5)
        app.page.run_task.assert_called_once_with(app._show_update_dialog, 'v2.0.0', 'notes')

    def test_wrong_optional_config_types_do_not_break_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            import json
            config = ConfigService(directory)
            config.config_file.write_text(json.dumps({
                'repo_path': '/valid', 'latest_version': [], 'update_remind_until': 7,
            }), encoding='utf-8')
            self.assertTrue(config.load())
            self.assertEqual(config.get('repo_path'), '/valid')
            self.assertEqual(config.get_latest_version(), '')
            self.assertFalse(config.is_in_update_remind_period())
