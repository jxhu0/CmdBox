"""Regression checks for performance-sensitive interactions."""
import asyncio
import unittest
from unittest.mock import Mock, patch
from app import CmdBoxApp
from models.board import Board
from models.command import Command
from views.command_list import CommandList
from views.search_bar import SearchBar
from views.sidebar import Sidebar
from services.data_service import DataService
from models.task import Task
from models.question import Question
from views.task_list import TaskList
from views.question_list import QuestionList


class PerformanceTests(unittest.TestCase):
    def test_settings_does_not_wait_for_update_network_request(self):
        app = Mock()
        app._syncing = False
        app.config_service.get_latest_version.return_value = '1.4.0'
        with patch('app.SettingsDialog'), patch('app.UpdateService.check_for_updates') as request:
            CmdBoxApp._on_settings(app, None)
            request.assert_not_called()
            app.page.show_dialog.assert_called_once()

    def test_task_and_question_cards_reused_and_invalidated(self):
        cases = [(TaskList(*([Mock()] * 5)), Task.create('task'), 'update_tasks'),
                 (QuestionList(*([Mock()] * 4)), Question.create('question'), 'update_questions')]
        for view, item, method in cases:
            with patch.object(type(view), 'update'):
                refresh = getattr(view, method)
                refresh([item])
                card = view._card_cache[item.id][1]
                refresh([item])
                self.assertIs(view._card_cache[item.id][1], card)
                item.update(title='changed')
                refresh([item])
                self.assertIsNot(view._card_cache[item.id][1], card)
                refresh([])
                self.assertFalse(view._card_cache)

    def test_recurring_reset_saves_once(self):
        app = Mock()
        tasks = [Task.create(str(i)) for i in range(100)]
        for task in tasks:
            task.completed, task.recurring, task.completed_at = True, 'daily', '2020-01-01 00:00'
        app.data_service.tasks = tasks
        CmdBoxApp._reset_recurring_tasks(app)
        app.data_service.save.assert_called_once()
        app.data_service.update_task.assert_not_called()
        self.assertTrue(all(not task.completed for task in tasks))

    def test_card_reuse_and_in_place_invalidation(self):
        board = Board.create('Commands')
        commands = [Command.create(board.id, str(i), 'echo hello') for i in range(1000)]
        view = CommandList({board.id: board}, *([Mock()] * 5))
        with patch.object(CommandList, 'update'):
            view.update_commands(commands)
            self.assertLess(len(repr(view)), 80)
            first = view.controls[0]
            view.update_commands(commands)
            self.assertIs(first, view.controls[0])
            commands[0].update(content='changed')
            view.update_commands(commands)
            self.assertIsNot(first, view.controls[0])
            self.assertEqual(len(view.controls), 22)
            view._load_more(None)
            self.assertEqual(len(view.controls), 42)
            view.set_show_move_buttons(False)
            view.update_commands(commands)
            self.assertFalse(view.controls[0].show_move_buttons)

    def test_navigation_avoids_metadata_and_hidden_list_refresh(self):
        app = Mock()
        app.FAVORITES_BOARD_ID, app.TASKS_BOARD_ID, app.QUESTIONS_BOARD_ID = 'fav', 'tasks', 'questions'
        CmdBoxApp._on_board_select(app, 'board')
        app._refresh_sidebar.assert_not_called()
        app.sidebar.select_board.assert_called_once_with('board')
        app.search_bar.reset_filters.assert_called_once_with('board')
        app.selected_board_id = 'tasks'
        CmdBoxApp._refresh_commands(app)
        app.data_service.search_commands.assert_not_called()

    def test_sidebar_retains_controls(self):
        board = Board.create('Commands')
        sidebar = Sidebar([board], *([Mock()] * 5), selected_board_id='fav',
                          favorites_board_id='fav', tasks_board_id='tasks', questions_board_id='questions')
        content = sidebar.content
        with patch('flet.controls.base_control.BaseControl.update'):
            for key in [board.id, 'tasks', 'questions', 'fav']:
                sidebar.select_board(key)
                self.assertIs(sidebar.content, content)

    def test_stale_search_ignored_after_navigation(self):
        search = SearchBar([], [], Mock())
        with patch.object(SearchBar, 'update'):
            search.reset_filters('board')
        asyncio.run(search._debounced_search(0))
        search.on_search.assert_not_called()
        asyncio.run(search._debounced_search(search._search_generation))
        search.on_search.assert_called_once_with('', ['board'], None)

    def test_search_preserves_manual_order(self):
        service = DataService('.')
        first = Command.create('board', 'first', 'test')
        second = Command.create('board', 'second', 'test')
        first.updated_at, second.updated_at = '2020', '2026'
        service.commands = [first, second]
        self.assertEqual(service.search_commands('test'), [second, first])
        self.assertEqual(service.commands, [first, second])


if __name__ == '__main__':
    unittest.main()
