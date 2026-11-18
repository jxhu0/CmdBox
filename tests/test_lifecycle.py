import asyncio
import json
import tempfile
import threading
import unittest
from unittest.mock import Mock, AsyncMock, patch
import flet as ft
from app import CmdBoxApp
from models.task import Task
from services.data_service import DataService


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    def make_app(self):
        app = CmdBoxApp.__new__(CmdBoxApp)
        app.page = Mock()
        app.data_service = Mock()
        app.git_service = Mock()
        app._show_snack_bar = Mock()
        app._syncing = False
        app._closing = False
        app._recurring_check_task = Mock()
        app.page.window.prevent_close = True
        app.page.window.close = AsyncMock()
        app.page.window.destroy = AsyncMock()
        return app

    async def test_close_persists_and_cleans_up_before_platform_window_exit(self):
        for platform in ('win32', 'darwin', 'linux'):
            with self.subTest(platform=platform):
                app = self.make_app()
                calls = []
                app.data_service.close.side_effect = lambda: calls.append('saved')
                app.git_service.cleanup.side_effect = lambda: calls.append('cleaned')
                app._recurring_check_task.cancel.side_effect = lambda: calls.append('cancelled')
                app.page.update.side_effect = lambda: calls.append(('patch', app.page.window.prevent_close))
                app.page.window.close.side_effect = lambda: calls.append('close')
                app.page.window.destroy.side_effect = lambda: calls.append('destroy')
                with patch('app.sys', Mock(platform=platform)):
                    await app._on_window_event(Mock(type=ft.WindowEventType.CLOSE))
                expected = ['saved', 'cleaned', 'cancelled']
                if platform == 'win32':
                    expected += [('patch', False), 'close']
                    app.page.window.destroy.assert_not_awaited()
                else:
                    expected += ['destroy']
                    app.page.window.close.assert_not_awaited()
                    self.assertTrue(app.page.window.prevent_close)
                self.assertEqual(calls, expected)

    async def test_failed_save_keeps_window_open(self):
        app = self.make_app()
        app.data_service.close.side_effect = OSError('disk full')
        with patch('app.sys', Mock(platform='win32')):
            await app._on_window_event(Mock(type=ft.WindowEventType.CLOSE))
        app.page.window.close.assert_not_awaited()
        app.page.window.destroy.assert_not_called()
        self.assertTrue(app.page.window.prevent_close)
        app.page.update.assert_not_called()
        app.git_service.cleanup.assert_not_called()
        app._show_snack_bar.assert_called_once()
        self.assertFalse(app._closing)
        app._recurring_check_task.cancel.assert_not_called()

    async def test_sync_blocks_exit_without_disabling_close_protection(self):
        app = self.make_app()
        app._syncing = True
        with patch('app.sys', Mock(platform='win32')):
            await app._on_window_event(Mock(type=ft.WindowEventType.CLOSE))
        self.assertFalse(app._closing)
        self.assertTrue(app.page.window.prevent_close)
        app.data_service.close.assert_not_called()
        app.page.window.close.assert_not_awaited()
        app.page.window.destroy.assert_not_awaited()
        app._show_snack_bar.assert_called_once()

    async def test_windows_exit_waits_for_pending_write_and_ignores_duplicate_close(self):
        with tempfile.TemporaryDirectory() as directory:
            app = self.make_app()
            app.data_service = DataService(directory)
            app.data_service.enable_background_saves()
            started, release = threading.Event(), threading.Event()
            write = app.data_service._write_snapshot

            def delayed_write(snapshot):
                started.set()
                if not release.wait(5):
                    raise OSError('test write timed out')
                write(snapshot)

            pending = None
            try:
                with patch.object(app.data_service, '_write_snapshot', delayed_write), \
                        patch('app.sys', Mock(platform='win32')):
                    app.data_service.add_task(Task.create('关闭前刚编辑的任务'))
                    self.assertTrue(await asyncio.to_thread(started.wait, 5))
                    pending = asyncio.create_task(app._on_window_event(Mock(type=ft.WindowEventType.CLOSE)))
                    await asyncio.sleep(0)
                    await app._on_window_event(Mock(type=ft.WindowEventType.CLOSE))
                    self.assertTrue(app._closing)
                    self.assertTrue(app.page.window.prevent_close)
                    app.page.window.close.assert_not_awaited()
                    app.git_service.cleanup.assert_not_called()
                    release.set()
                    await pending
                saved = json.loads(app.data_service.data_file.read_text(encoding='utf-8'))
                self.assertEqual(saved['tasks'][0]['title'], '关闭前刚编辑的任务')
                app.page.window.close.assert_awaited_once()
                app.page.window.destroy.assert_not_awaited()
                app.git_service.cleanup.assert_called_once()
            finally:
                release.set()
                if pending:
                    await pending
                app.data_service.close()

    async def test_failed_restart_keeps_periodic_checks_enabled(self):
        app = self.make_app()
        with patch('subprocess.Popen', side_effect=OSError('cannot launch')):
            await app._on_restart(None)
        self.assertFalse(app._closing)
        app._recurring_check_task.cancel.assert_not_called()
        self.assertTrue(app.page.window.prevent_close)
        app.page.window.close.assert_not_awaited()
        app.page.window.destroy.assert_not_called()
        app._show_snack_bar.assert_called_once()

    async def test_restart_uses_same_windows_close_path_after_flush_and_launch(self):
        app = self.make_app()
        calls = []
        app.data_service.flush.side_effect = lambda: calls.append('saved')
        app.page.update.side_effect = lambda: calls.append(('patch', app.page.window.prevent_close))
        app.page.window.close.side_effect = lambda: calls.append('close')
        with patch('app.sys', Mock(platform='win32', executable='python', argv=['main.py'])), \
                patch('subprocess.Popen', side_effect=lambda *_: calls.append('launch')), \
                patch('app.os._exit', side_effect=lambda *_: calls.append('exit')):
            await app._on_restart(None)
        self.assertEqual(calls, ['saved', 'launch', ('patch', False), 'close', 'exit'])
        app.page.window.destroy.assert_not_awaited()
