import unittest
from unittest.mock import Mock, AsyncMock, patch
import flet as ft
from app import CmdBoxApp


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
        app.page.window.destroy = AsyncMock()
        return app

    async def test_window_close_flushes_before_destroy(self):
        app = self.make_app()
        await CmdBoxApp._on_window_event(app, Mock(type=ft.WindowEventType.CLOSE))
        app.data_service.close.assert_called_once()
        app.page.window.destroy.assert_awaited_once()
        app._recurring_check_task.cancel.assert_called_once()

    async def test_failed_save_keeps_window_open(self):
        app = self.make_app()
        app.data_service.close.side_effect = OSError('disk full')
        app.page.window.destroy = AsyncMock()
        await CmdBoxApp._on_window_event(app, Mock(type=ft.WindowEventType.CLOSE))
        app.page.window.destroy.assert_not_called()
        app._show_snack_bar.assert_called_once()
        self.assertFalse(app._closing)
        app._recurring_check_task.cancel.assert_not_called()

    async def test_failed_restart_keeps_periodic_checks_enabled(self):
        app = self.make_app()
        with patch('subprocess.Popen', side_effect=OSError('cannot launch')):
            await app._on_restart(None)
        self.assertFalse(app._closing)
        app._recurring_check_task.cancel.assert_not_called()
        app.page.window.destroy.assert_not_called()
        app._show_snack_bar.assert_called_once()
