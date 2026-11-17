import asyncio
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from git import Repo

from app import CmdBoxApp
from models.command import Command
from models.task import Task
from services.data_service import DataService
from services.git_service import GitService


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.remote = Repo.init(root / 'remote.git', bare=True, initial_branch='main')
        self.local = Repo.init(root / 'local', initial_branch='main')
        self.addCleanup(self.remote.close)
        self.addCleanup(self.local.close)
        self.configure(self.local)
        self.data = DataService(str(root / 'local'))
        self.data.load()
        self.local.index.add(['data.json'])
        self.local.index.commit('初始化数据')
        self.local.create_remote('origin', str(root / 'remote.git'))
        self.local.git.push('--set-upstream', 'origin', 'main')
        self.other = Repo.clone_from(str(root / 'remote.git'), root / 'other', branch='main')
        self.configure(self.other)
        self.addCleanup(self.other.close)
        self.git = GitService(str(root / 'local'))
        self.addCleanup(self.git.cleanup)

    @staticmethod
    def configure(repo):
        with repo.config_writer() as config:
            config.set_value('user', 'name', '测试用户')
            config.set_value('user', 'email', 'test@example.invalid')

    def publish_command(self):
        other_data = DataService(self.other.working_tree_dir)
        other_data.load()
        command = Command.create(other_data.boards[0].id, '远程新增', 'echo remote')
        other_data.add_command(command)
        self.other.git.add('data.json')
        self.other.index.commit('远程更新')
        self.other.git.push('origin', 'main')
        return command

    def test_sync_reloads_remote_before_next_edit(self):
        command = self.publish_command()
        self.data.enable_background_saves()
        self.addCleanup(self.data.close)
        success, message = self.git.sync(self.data)
        self.assertTrue(success, message)
        self.assertEqual(self.data.commands[0].id, command.id)
        self.data.add_task(Task.create('同步后继续编辑'))
        self.data.flush()
        saved = json.loads(self.data.data_file.read_text())
        self.assertEqual(saved['commands'][0]['id'], command.id)
        self.assertEqual(len(saved['tasks']), 1)
        self.assertEqual(self.remote.commit('main').hexsha, self.local.head.commit.hexsha)

    def test_failed_push_still_keeps_pulled_data_in_memory(self):
        command = self.publish_command()
        with patch.object(self.git, 'push', return_value=(False, '推送失败')):
            self.assertEqual(self.git.sync(self.data), (False, '推送失败'))
        self.data.add_task(Task.create('继续编辑'))
        self.assertEqual(json.loads(self.data.data_file.read_text())['commands'][0]['id'], command.id)

    def test_conflict_aborts_without_overwriting_either_side(self):
        self.publish_command()
        remote_head = self.remote.commit('main').hexsha
        command = Command.create(self.data.boards[0].id, '本地新增', 'echo local')
        self.data.add_command(command)
        original = self.data.data_file.read_bytes()
        success, message = self.git.sync(self.data)
        self.assertFalse(success)
        self.assertIn('冲突', message)
        self.assertEqual(self.data.data_file.read_bytes(), original)
        self.assertEqual(self.remote.commit('main').hexsha, remote_head)
        self.assertFalse((Path(self.local.git_dir) / 'MERGE_HEAD').exists())
        self.assertEqual(self.data.commands[0].id, command.id)
        self.assertTrue(self.data.get_backups())

    def test_invalid_remote_data_is_rejected_before_merge_commit(self):
        original = self.data.data_file.read_bytes()
        duplicate = Task.create('重复记录').to_dict()
        for invalid in ['{"commands": [invalid]}', json.dumps({'tasks': [duplicate, duplicate]})]:
            with self.subTest(data=invalid):
                (Path(self.other.working_tree_dir) / 'data.json').write_text(invalid)
                self.other.git.add('data.json')
                self.other.index.commit('损坏的数据')
                self.other.git.push('origin', 'main')
                success, message = self.git.sync(self.data)
                self.assertFalse(success)
                self.assertIn('校验', message)
                self.assertEqual(self.data.data_file.read_bytes(), original)
                self.assertFalse((Path(self.local.git_dir) / 'MERGE_HEAD').exists())

    def test_backup_failure_prevents_git_changes(self):
        original = self.local.head.commit.hexsha
        with patch.object(self.data, 'backup', side_effect=OSError('磁盘已满')):
            success, message = self.git.sync(self.data)
        self.assertFalse(success)
        self.assertIn('备份失败', message)
        self.assertEqual(self.local.head.commit.hexsha, original)

    def test_first_sync_of_fresh_install_uses_remote_data(self):
        command = self.publish_command()
        fresh = Path(self.directory.name) / 'fresh'
        repo = Repo.init(fresh, initial_branch='main')
        self.addCleanup(repo.close)
        self.configure(repo)
        repo.create_remote('origin', self.remote.git_dir)
        service = DataService(str(fresh))
        service.load()
        git = GitService(str(fresh))
        self.addCleanup(git.cleanup)
        success, message = git.sync(service)
        self.assertTrue(success, message)
        self.assertEqual(len(service.boards), 2)
        self.assertEqual(service.commands[0].id, command.id)

    def test_first_sync_preserves_records_from_both_independent_repositories(self):
        command = self.publish_command()
        fresh = Path(self.directory.name) / 'independent'
        repo = Repo.init(fresh, initial_branch='main')
        self.addCleanup(repo.close)
        self.configure(repo)
        repo.create_remote('origin', self.remote.git_dir)
        service = DataService(str(fresh))
        service.load()
        task = Task.create('本地已有任务')
        service.add_task(task)
        git = GitService(str(fresh))
        self.addCleanup(git.cleanup)
        success, message = git.sync(service)
        self.assertTrue(success, message)
        self.assertEqual(service.commands[0].id, command.id)
        self.assertEqual(service.tasks[0].id, task.id)

    def test_first_sync_does_not_replace_different_records_with_the_same_id(self):
        command = self.publish_command()
        fresh = Path(self.directory.name) / 'same-id'
        repo = Repo.init(fresh, initial_branch='main')
        self.addCleanup(repo.close)
        self.configure(repo)
        repo.create_remote('origin', self.remote.git_dir)
        service = DataService(str(fresh))
        service.load()
        local = Command.from_dict(command.to_dict())
        local.update(content='本地不同内容')
        service.add_command(local)
        git = GitService(str(fresh))
        self.addCleanup(git.cleanup)
        success, message = git.sync(service)
        self.assertFalse(success)
        self.assertIn('冲突', message)
        self.assertEqual(service.commands[0].content, '本地不同内容')

    def test_sync_pushes_current_branch_without_switching_to_stale_main(self):
        self.local.git.checkout('-b', 'work')
        self.data.add_task(Task.create('当前分支任务'))
        success, message = self.git.sync(self.data)
        self.assertTrue(success, message)
        self.assertEqual(self.local.active_branch.name, 'work')
        self.assertEqual(self.remote.commit('main').hexsha, self.local.head.commit.hexsha)

    def test_existing_merge_is_not_automatically_committed(self):
        self.publish_command()
        self.data.add_command(Command.create(self.data.boards[0].id, '本地新增', 'echo local'))
        self.git.commit()
        self.local.remotes.origin.fetch()
        with self.assertRaises(Exception):
            self.local.git.merge('origin/main')
        head = self.local.head.commit.hexsha
        success, message = self.git.sync(self.data)
        self.assertFalse(success)
        self.assertIn('未完成的合并', message)
        self.assertEqual(self.local.head.commit.hexsha, head)
        self.assertTrue((Path(self.local.git_dir) / 'MERGE_HEAD').exists())


class SyncUiTests(unittest.IsolatedAsyncioTestCase):
    async def test_network_runs_off_ui_thread_and_refreshes_even_when_push_fails(self):
        app = CmdBoxApp.__new__(CmdBoxApp)
        app._syncing, app._closing = False, False
        app.page = Mock(overlay=[])
        app.git_service = Mock()
        app.data_service = Mock()
        app.config_service = Mock()
        controls = ['sidebar', 'command_stack', 'task_list', 'question_list', 'add_btn', 'search_bar']
        for name in controls:
            setattr(app, name, Mock())
        for name in ['_reset_recurring_tasks', '_refresh_sidebar', '_on_board_select', '_show_snack_bar']:
            setattr(app, name, Mock())
        app.FAVORITES_BOARD_ID, app.TASKS_BOARD_ID, app.QUESTIONS_BOARD_ID = 'fav', 'tasks', 'questions'
        app.selected_board_id = 'removed-board'
        app.data_service.get_board.return_value = None
        ui_thread = threading.get_ident()
        started, release = threading.Event(), threading.Event()

        def sync(_):
            self.assertNotEqual(threading.get_ident(), ui_thread)
            started.set()
            self.assertTrue(release.wait(5))
            return False, '推送失败'

        app.git_service.sync.side_effect = sync
        pending = asyncio.create_task(app._on_sync(None))
        try:
            for _ in range(100):
                if started.is_set():
                    break
                await asyncio.sleep(0.01)
            self.assertTrue(started.is_set())
            self.assertTrue(app._syncing)
            self.assertTrue(all(getattr(app, name).disabled for name in controls))
            await app._on_sync(None)
            self.assertEqual(app.git_service.sync.call_count, 1)
        finally:
            release.set()
            await pending
        self.assertFalse(app._syncing)
        self.assertTrue(all(not getattr(app, name).disabled for name in controls))
        app._on_board_select.assert_called_once_with('fav')
        app._show_snack_bar.assert_called_with('推送失败', 8000)
        app.config_service.update_last_sync.assert_not_called()
