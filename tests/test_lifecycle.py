import unittest
from unittest.mock import Mock, AsyncMock
import flet as ft
from app import CmdBoxApp


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_window_close_flushes_before_destroy(self):
        app = Mock()
        app._syncing = False
        app.page.window.destroy = AsyncMock()
        await CmdBoxApp._on_window_event(app, Mock(type=ft.WindowEventType.CLOSE))
        app.data_service.close.assert_called_once()
        app.page.window.destroy.assert_awaited_once()

    async def test_failed_save_keeps_window_open(self):
        app = Mock()
        app._syncing = False
        app.data_service.close.side_effect = OSError('disk full')
        app.page.window.destroy = AsyncMock()
        await CmdBoxApp._on_window_event(app, Mock(type=ft.WindowEventType.CLOSE))
        app.page.window.destroy.assert_not_called()
        app._show_snack_bar.assert_called_once()
