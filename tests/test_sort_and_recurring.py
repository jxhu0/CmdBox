import asyncio
import unittest
from datetime import date, datetime
from unittest.mock import AsyncMock, Mock, patch

import flet as ft

from app import CmdBoxApp
from models.question import Question
from models.task import Task
from views.question_list import QuestionList
from views.task_list import TaskList


class SortMenuTests(unittest.TestCase):
    def test_menu_selects_requested_sort_and_keeps_one_checkmark(self):
        cases = [
            (TaskList(*([Mock()] * 5)), 'tasks', Task, '_get_sorted_tasks'),
            (QuestionList(*([Mock()] * 4)), 'questions', Question, '_get_sorted_questions'),
        ]
        for view, collection, model, sorted_method in cases:
            with self.subTest(view=type(view).__name__), patch.object(type(view), 'update'):
                older = model.create('older', priority='high')
                newer = model.create('newer', priority='low')
                older.created_at, newer.created_at = '2026-01-01', '2026-01-02'
                setattr(view, collection, [older, newer])
                menu = view._build_sort_bar().content.controls[-1]
                self.assertIsInstance(menu, ft.PopupMenuButton)
                self.assertEqual([item.checked for item in menu.items], [True, False, False])
                # 直接选时间，不依赖循环点击。
                menu.items[1].on_click(None)
                self.assertEqual(getattr(view, sorted_method)(), [newer, older])
                menu = view._build_sort_bar().content.controls[-1]
                self.assertEqual([item.checked for item in menu.items], [False, True, False])
                menu.items[0].on_click(None)
                self.assertEqual(getattr(view, sorted_method)(), [older, newer])
                menu.items[2].on_click(None)
                self.assertEqual(view.sort_mode_index, 2)


class RecurringTaskTests(unittest.IsolatedAsyncioTestCase):
    def make_app(self):
        app = CmdBoxApp.__new__(CmdBoxApp)
        app.data_service = Mock(tasks=[])
        app.sidebar = Mock()
        app._refresh_tasks = Mock()
        app._refresh_sidebar = Mock()
        app._syncing = False
        app._closing = False
        app._last_recurring_check_date = date(2026, 11, 16)
        app.TASKS_BOARD_ID = 'tasks'
        app.selected_board_id = 'tasks'
        return app

    def task(self, recurring, completed_at):
        task = Task.create(recurring)
        task.completed = True
        task.recurring = recurring
        task.completed_at = completed_at
        return task

    def test_daily_weekly_monthly_boundaries_save_once(self):
        cases = [
            (date(2026, 11, 17), 'daily', '2026-11-16 23:59', True),
            (date(2026, 11, 17), 'daily', '2026-11-17 00:00', False),
            (date(2026, 11, 16), 'weekly', '2026-11-15 23:59', True),
            (date(2026, 11, 17), 'weekly', '2026-11-16 00:00', False),
            (date(2027, 1, 1), 'monthly', '2026-12-31 23:59', True),
            (date(2026, 11, 17), 'monthly', '2026-11-01 00:00', False),
            (date(2026, 11, 17), 'daily', 'invalid', False),
            (date(2026, 11, 17), '', '2026-11-01 00:00', False),
        ]
        for today, recurring, completed_at, expected in cases:
            with self.subTest(today=today, recurring=recurring, completed_at=completed_at):
                app = self.make_app()
                task = self.task(recurring, completed_at)
                app.data_service.tasks = [task]
                self.assertEqual(app._reset_recurring_tasks(today), expected)
                self.assertEqual(task.completed, not expected)
                self.assertEqual(app.data_service.save.call_count, int(expected))

    async def test_focus_and_restore_refresh_immediately(self):
        for event_type in (ft.WindowEventType.FOCUS, ft.WindowEventType.RESTORE):
            with self.subTest(event=event_type):
                app = self.make_app()
                task = self.task('daily', '2026-11-16 23:59')
                app.data_service.tasks = [task]
                with patch('app.datetime', wraps=datetime) as clock:
                    clock.now.return_value = datetime(2026, 11, 17)
                    await app._on_window_event(Mock(type=event_type))
                    await app._on_window_event(Mock(type=event_type))
                self.assertFalse(task.completed)
                app.data_service.save.assert_called_once()
                app._refresh_tasks.assert_called_once()
                app._refresh_sidebar.assert_called_once()

    async def test_background_watcher_detects_day_change(self):
        app = self.make_app()
        task = self.task('daily', '2026-11-16 23:59')
        app.data_service.tasks = [task]
        with patch('app.datetime', wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 11, 17)
            with patch('asyncio.sleep', new=AsyncMock(side_effect=[None, asyncio.CancelledError])):
                with self.assertRaises(asyncio.CancelledError):
                    await app._watch_recurring_tasks()
        self.assertFalse(task.completed)
        app._refresh_tasks.assert_called_once()

    def test_same_day_timer_skips_task_scan(self):
        app = self.make_app()
        app._last_recurring_check_date = date(2026, 11, 17)
        with patch('app.datetime', wraps=datetime) as clock, patch.object(app, '_reset_recurring_tasks') as reset:
            clock.now.return_value = datetime(2026, 11, 17)
            app._check_recurring_tasks()
            reset.assert_not_called()

    def test_sync_defers_reset_and_hidden_list_waits_until_selected(self):
        app = self.make_app()
        task = self.task('daily', '2026-11-16 23:59')
        app.data_service.tasks = [task]
        app.selected_board_id = 'questions'
        with patch('app.datetime', wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 11, 17)
            app._syncing = True
            app._check_recurring_tasks(force=True)
            self.assertTrue(task.completed)
            app._syncing = False
            app._check_recurring_tasks()
        self.assertFalse(task.completed)
        app._refresh_tasks.assert_not_called()
        app._refresh_sidebar.assert_called_once()

    def test_closing_does_not_modify_tasks(self):
        app = self.make_app()
        task = self.task('daily', '2026-11-16 23:59')
        app.data_service.tasks = [task]
        app._closing = True
        app._check_recurring_tasks(force=True)
        self.assertTrue(task.completed)
        app.data_service.save.assert_not_called()
