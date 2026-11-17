import unittest
from unittest.mock import Mock, PropertyMock, patch

from app import CmdBoxApp
from models.board import Board
from models.command import Command
from models.task import Task
from models.question import Question
from services.data_service import DataService
from services.update_service import UpdateService
from views.command_list import CommandList
from views.dialogs import BoardDialog, CommandDialog, TaskDialog, QuestionDialog
from views.question_list import QuestionList
from views.search_bar import SearchBar
from views.task_list import TaskList


class UsabilityTests(unittest.TestCase):
    def test_favorites_respect_keyword_board_and_tag_filters(self):
        app = CmdBoxApp.__new__(CmdBoxApp)
        app.FAVORITES_BOARD_ID, app.TASKS_BOARD_ID, app.QUESTIONS_BOARD_ID = 'fav', 'tasks', 'questions'
        app.selected_board_id, app.show_favorites_only = 'fav', True
        app.data_service = DataService('.')
        board = Board.create('命令')
        app.data_service.boards = [board]
        wanted = Command.create(board.id, 'deploy', 'run', tags=['work'], is_favorite=True)
        app.data_service.commands = [
            wanted, Command.create(board.id, 'deploy', 'run', tags=['work']),
            Command.create(board.id, 'other', 'run', tags=['work'], is_favorite=True),
            Command.create('other-board', 'deploy', 'run', tags=['work'], is_favorite=True),
            Command.create(board.id, 'deploy', 'run', tags=['home'], is_favorite=True),
        ]
        app.search_keyword, app.search_board_ids, app.search_tag = 'deploy', [board.id], 'work'
        app.command_list, app.command_stack = Mock(), Mock()
        app._command_views = {'fav': app.command_list}
        app._refresh_commands()
        app.command_list.update_commands.assert_called_once_with([wanted], update=True)

    def test_task_and_question_search_hide_irrelevant_filters(self):
        callback = Mock()
        search = SearchBar([], [], callback)
        with patch.object(SearchBar, 'update'):
            for context, hint in [('tasks', '任务'), ('questions', '问题')]:
                search.set_context(context)
                self.assertFalse(search.filters.visible)
                self.assertIn(hint, search.search_input.hint_text)
                search.board_dropdown.value, search.tag_dropdown.value = 'old-board', 'old-tag'
                search.search_input.value = 'hello'
                search._do_search()
                callback.assert_called_with('hello', None, None)
            search.set_context('commands')
            self.assertTrue(search.filters.visible)
            search._do_search()
            callback.assert_called_with('hello', ['old-board'], 'old-tag')

    def test_blank_titles_keep_dialog_open_and_valid_save_clears_error(self):
        cases = [
            (BoardDialog('新建', on_save=Mock()), 'name_field', ('板块', '📁', '')),
            (TaskDialog('新建', on_save=Mock()), 'title_field', ('任务', '', 'medium', '')),
            (QuestionDialog('新建', on_save=Mock()), 'title_field', ('问题', '', '', 'medium')),
        ]
        for dialog, field_name, expected in cases:
            with self.subTest(dialog=type(dialog).__name__), patch.object(type(dialog), 'update'), \
                    patch.object(type(dialog), 'page', new_callable=PropertyMock) as page_property:
                page = Mock()
                page_property.return_value = page
                field = getattr(dialog, field_name)
                field.value = '  '
                dialog._on_save(None)
                self.assertTrue(field.error)
                dialog.on_save_callback.assert_not_called()
                page.pop_dialog.assert_not_called()
                field.value = f'  {expected[0]}  '
                dialog._on_save(None)
                self.assertIsNone(field.error)
                dialog.on_save_callback.assert_called_once_with(*expected)
                page.pop_dialog.assert_called_once()

    def test_command_requires_title_content_and_board_without_trimming_script(self):
        board = Board.create('命令')
        dialog = CommandDialog('新建', [board], on_save=Mock())
        with patch.object(CommandDialog, 'update'), \
                patch.object(CommandDialog, 'page', new_callable=PropertyMock) as page_property:
            page_property.return_value = Mock()
            dialog.board_dropdown.value = None
            dialog._on_save(None)
            self.assertTrue(dialog.title_field.error)
            self.assertTrue(dialog.content_field.error)
            self.assertTrue(dialog.board_dropdown.error_text)
            dialog.on_save_callback.assert_not_called()
            dialog.title_field.value = '  命令  '
            dialog.content_field.value = '  echo test\n'
            dialog.board_dropdown.value = board.id
            dialog._on_save(None)
            values = dialog.on_save_callback.call_args.kwargs
            self.assertEqual(values['title'], '命令')
            self.assertEqual(values['content'], '  echo test\n')

    def test_reloaded_records_replace_cards_even_when_values_are_unchanged(self):
        for view, item, method, attribute in [
            (TaskList(*([Mock()] * 5)), Task.create('任务'), 'update_tasks', 'task'),
            (QuestionList(*([Mock()] * 4)), Question.create('问题'), 'update_questions', 'question'),
        ]:
            with patch.object(type(view), 'update'):
                refresh = getattr(view, method)
                refresh([item])
                card = view._card_cache[item.id][1]
                reloaded = type(item).from_dict(item.to_dict())
                refresh([reloaded])
                replacement = view._card_cache[item.id][1]
                self.assertIsNot(card, replacement)
                self.assertIs(getattr(replacement, attribute), reloaded)
        board = Board.create('板块')
        command = Command.create(board.id, '命令', 'echo test')
        view = CommandList({board.id: board}, *([Mock()] * 5))
        with patch.object(CommandList, 'update'):
            view.update_commands([command])
            card = view.controls[0]
            reloaded = Command.from_dict(command.to_dict())
            view.update_commands([reloaded])
            self.assertIsNot(view.controls[0], card)
            self.assertIs(view.controls[0].command, reloaded)
            card = view.controls[0]
            board.update(name='重命名')
            view.update_commands([reloaded])
            self.assertIsNot(view.controls[0], card)


class UpdateTests(unittest.TestCase):
    def test_only_newer_stable_versions_trigger_update(self):
        for latest, current, expected in [
            ('v1.4.1', '1.4.2', False), ('v1.4.2', '1.4.2', False),
            ('v1.10.0', '1.9.9', True), ('v2.0.0', '1.10.1', True),
            ('v1.4.3', '1.4.2', True), ('invalid', '1.4.2', False),
            ('v1.5.0-beta.1', '1.4.2', False), ('v1.4.2+build1', '1.4.2', False),
        ]:
            with self.subTest(latest=latest, current=current), patch('services.update_service.requests.get') as get:
                get.return_value.status_code = 200
                get.return_value.json.return_value = {'tag_name': latest, 'body': '说明'}
                self.assertEqual(UpdateService.check_for_updates(current), (expected, latest, '说明'))

    def test_network_failure_does_not_claim_an_update(self):
        with patch('services.update_service.requests.get', side_effect=OSError('offline')):
            self.assertEqual(UpdateService.check_for_updates('1.4.2'), (False, None, None))
