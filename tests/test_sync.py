import asyncio
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, Mock, patch

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
            config.set_value('core', 'autocrlf', False)

    def publish_command(self):
        other_data = DataService(self.other.working_tree_dir)
        other_data.load()
        command = Command.create(other_data.boards[0].id, '远程新增', 'echo remote')
        other_data.add_command(command)
        self.other.git.add('data.json')
        self.other.index.commit('远程更新')
        self.other.git.push('origin', 'main')
        return command

    def test_pull_reloads_remote_before_next_edit(self):
        command = self.publish_command()
        self.data.enable_background_saves()
        self.addCleanup(self.data.close)
        success, message = self.git.pull_data(self.data)
        self.assertTrue(success, message)
        self.assertEqual(self.data.commands[0].id, command.id)
        self.data.add_task(Task.create('同步后继续编辑'))
        self.data.flush()
        saved = json.loads(self.data.data_file.read_text(encoding='utf-8'))
        self.assertEqual(saved['commands'][0]['id'], command.id)
        self.assertEqual(len(saved['tasks']), 1)
        self.assertNotEqual(self.remote.commit('main').hexsha, self.local.head.commit.hexsha)
        self.assertTrue(self.git.upload_data(self.data)[0])
        self.assertEqual(self.remote.commit('main').hexsha, self.local.head.commit.hexsha)

    def test_upload_rejection_does_not_pull_or_overwrite_remote(self):
        self.publish_command()
        remote_head = self.remote.commit('main').hexsha
        task = Task.create('仅本地任务')
        self.data.add_task(task)
        before = self.data.data_file.read_bytes()
        success, message = self.git.upload_data(self.data)
        self.assertFalse(success)
        self.assertIn('先点击“拉取数据”', message)
        self.assertEqual(self.data.data_file.read_bytes(), before)
        self.assertEqual([t.id for t in self.data.tasks], [task.id])
        self.assertEqual(self.data.commands, [])
        self.assertEqual(self.remote.commit('main').hexsha, remote_head)
        self.assertNotIn('refs/remotes/origin/main', [r.path for r in self.local.references
                         if r.commit.hexsha == remote_head])

    def test_pull_never_pushes_even_with_local_changes(self):
        task = Task.create('本地未上传任务')
        self.data.add_task(task)
        self.assertTrue(self.git.upload_data(self.data)[0])
        self.other.git.pull('--ff-only')
        self.publish_command()
        remote_head = self.remote.commit('main').hexsha
        task.update(title='本地修改，尚未上传')
        self.data.update_task(task)
        with patch.object(self.git, 'push', side_effect=AssertionError('拉取不能推送')):
            success, message = self.git.pull_data(self.data)
        self.assertTrue(success, message)
        self.assertEqual(self.remote.commit('main').hexsha, remote_head)
        self.assertEqual(self.data.tasks[0].id, task.id)
        self.assertEqual(self.data.tasks[0].title, '本地修改，尚未上传')
        remote_data = json.loads(self.remote.commit('main').tree['data.json'].data_stream.read())
        self.assertEqual(remote_data['tasks'][0]['title'], '本地未上传任务')

    def test_upload_only_commits_data_and_no_edits_do_not_create_commits(self):
        directory = Path(self.local.working_tree_dir)
        (directory / '.env').write_text('TEST_ONLY=yes', encoding='utf-8')
        (directory / 'notes.txt').write_text('不应上传', encoding='utf-8')
        self.local.git.add('notes.txt')
        self.data.enable_background_saves()
        self.addCleanup(self.data.close)
        task = Task.create('排队保存的任务')
        self.data.add_task(task)
        with patch.object(self.git, 'pull', side_effect=AssertionError('上传不能拉取')):
            success, message = self.git.upload_data(self.data)
        self.assertTrue(success, message)
        remote_tree = self.remote.commit('main').tree
        self.assertEqual([item.path for item in remote_tree], ['data.json'])
        self.assertEqual(json.loads(remote_tree['data.json'].data_stream.read())['tasks'][0]['id'], task.id)
        self.assertIn('notes.txt', self.local.git.diff('--cached', '--name-only').splitlines())
        head = self.local.head.commit.hexsha
        self.assertTrue(self.git.upload_data(self.data)[0])
        self.assertEqual(self.local.head.commit.hexsha, head)

    def test_conflict_aborts_without_overwriting_either_side(self):
        self.publish_command()
        remote_head = self.remote.commit('main').hexsha
        command = Command.create(self.data.boards[0].id, '本地新增', 'echo local')
        self.data.add_command(command)
        original = self.data.data_file.read_bytes()
        success, message = self.git.pull_data(self.data)
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
                (Path(self.other.working_tree_dir) / 'data.json').write_text(invalid, encoding='utf-8')
                self.other.git.add('data.json')
                self.other.index.commit('损坏的数据')
                self.other.git.push('origin', 'main')
                success, message = self.git.pull_data(self.data)
                self.assertFalse(success)
                self.assertIn('校验', message)
                self.assertEqual(self.data.data_file.read_bytes(), original)
                self.assertFalse((Path(self.local.git_dir) / 'MERGE_HEAD').exists())

    def test_backup_failure_prevents_git_changes(self):
        original = self.local.head.commit.hexsha
        with patch.object(self.data, 'backup', side_effect=OSError('磁盘已满')):
            success, message = self.git.pull_data(self.data)
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
        success, message = git.pull_data(service)
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
        success, message = git.pull_data(service)
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
        success, message = git.pull_data(service)
        self.assertFalse(success)
        self.assertIn('冲突', message)
        self.assertEqual(service.commands[0].content, '本地不同内容')

    def test_upload_pushes_current_branch_without_switching_to_stale_main(self):
        self.local.git.checkout('-b', 'work')
        self.data.add_task(Task.create('当前分支任务'))
        success, message = self.git.upload_data(self.data)
        self.assertTrue(success, message)
        self.assertEqual(self.local.active_branch.name, 'work')
        self.assertEqual(self.remote.commit('main').hexsha, self.local.head.commit.hexsha)

    def test_pull_and_upload_follow_existing_master_branch(self):
        self.local.git.push('origin', 'HEAD:master')
        self.remote.git.symbolic_ref('HEAD', 'refs/heads/master')
        self.local.git.push('origin', '--delete', 'main')
        self.local.git.fetch('--prune')
        self.local.git.branch('-m', 'master')
        self.local.git.branch('--set-upstream-to=origin/master', 'master')
        other_data = DataService(self.other.working_tree_dir)
        other_data.load()
        task = Task.create('master 分支上的远程任务')
        other_data.add_task(task)
        self.other.git.add('data.json')
        self.other.index.commit('更新 master 数据')
        self.other.git.push('origin', 'HEAD:master')
        success, message = self.git.pull_data(self.data)
        self.assertTrue(success, message)
        self.assertEqual(self.data.tasks[0].id, task.id)
        self.data.add_task(Task.create('本地更新'))
        success, message = self.git.upload_data(self.data)
        self.assertTrue(success, message)
        self.assertEqual(self.remote.commit('master').hexsha, self.local.head.commit.hexsha)
        self.assertNotIn('main', [head.name for head in self.remote.heads])

    def test_remote_documents_with_invalid_field_types_are_rejected(self):
        self.publish_command()
        self.assertTrue(self.git.pull_data(self.data)[0])
        before = self.data.data_file.read_bytes()
        document = json.loads(before)
        document['commands'][0]['title'] = None
        path = Path(self.other.working_tree_dir) / 'data.json'
        path.write_text(json.dumps(document), encoding='utf-8')
        self.other.git.add('data.json')
        self.other.index.commit('无效字段')
        self.other.git.push('origin', 'main')
        success, message = self.git.pull_data(self.data)
        self.assertFalse(success)
        self.assertIn('校验', message)
        self.assertEqual(self.data.data_file.read_bytes(), before)

    def test_network_environment_keeps_custom_ssh_configuration(self):
        with self.local.config_writer() as config:
            config.set_value('core', 'sshCommand', 'ssh -i custom-key')
        with patch.dict(os.environ, {'GIT_SSH_COMMAND': '', 'GIT_SSH': ''}):
            self.assertNotIn('GIT_SSH_COMMAND', self.git._network_environment())
        with patch.dict(os.environ, {'GIT_SSH_COMMAND': 'custom-ssh-client'}):
            self.assertNotIn('GIT_SSH_COMMAND', self.git._network_environment())

    def test_existing_merge_is_not_automatically_committed(self):
        self.publish_command()
        self.data.add_command(Command.create(self.data.boards[0].id, '本地新增', 'echo local'))
        self.git.commit()
        self.local.remotes.origin.fetch()
        with self.assertRaises(Exception):
            self.local.git.merge('origin/main')
        head = self.local.head.commit.hexsha
        success, message = self.git.pull_data(self.data)
        self.assertFalse(success)
        self.assertIn('未完成的合并', message)
        self.assertEqual(self.local.head.commit.hexsha, head)
        self.assertTrue((Path(self.local.git_dir) / 'MERGE_HEAD').exists())


class SyncUiTests(unittest.IsolatedAsyncioTestCase):
    controls = ['sidebar', 'command_stack', 'task_list', 'question_list', 'add_btn',
                'search_bar', 'board_desc_container', 'upload_btn', 'pull_btn']

    def make_app(self):
        app = CmdBoxApp.__new__(CmdBoxApp)
        app._syncing, app._closing = False, False
        app.page = Mock(overlay=[])
        app.git_service = Mock()
        app.data_service = Mock()
        app.config_service = Mock()
        for name in self.controls:
            setattr(app, name, Mock(disabled=False))
        for name in ['_refresh_tasks', '_refresh_sidebar', '_on_board_select', '_show_snack_bar']:
            setattr(app, name, Mock())
        app._reset_recurring_tasks = Mock(return_value=False)
        app.FAVORITES_BOARD_ID, app.TASKS_BOARD_ID, app.QUESTIONS_BOARD_ID = 'fav', 'tasks', 'questions'
        app.selected_board_id = 'removed-board'
        app.data_service.get_board.return_value = None
        return app

    async def test_each_operation_runs_off_ui_thread_and_blocks_both_buttons(self):
        for upload in (True, False):
            with self.subTest(upload=upload):
                app = self.make_app()
                ui_thread = threading.get_ident()
                started, release = threading.Event(), threading.Event()
                operation = app.git_service.upload_data if upload else app.git_service.pull_data
                unused = app.git_service.pull_data if upload else app.git_service.upload_data

                def transfer(_):
                    self.assertNotEqual(threading.get_ident(), ui_thread)
                    started.set()
                    self.assertTrue(release.wait(5))
                    return True, '上传成功' if upload else '拉取成功'

                operation.side_effect = transfer
                handler = app._on_upload_data if upload else app._on_pull_data
                pending = asyncio.create_task(handler(None))
                try:
                    for _ in range(100):
                        if started.is_set():
                            break
                        await asyncio.sleep(0.01)
                    self.assertTrue(started.is_set())
                    self.assertTrue(app._syncing)
                    self.assertTrue(all(getattr(app, name).disabled for name in self.controls))
                    await app._on_upload_data(None)
                    await app._on_pull_data(None)
                    self.assertEqual(operation.call_count, 1)
                finally:
                    release.set()
                    await pending
                self.assertFalse(app._syncing)
                self.assertTrue(all(not getattr(app, name).disabled for name in self.controls))
                self.assertEqual(app.page.overlay, [])
                unused.assert_not_called()
                if upload:
                    app._on_board_select.assert_not_called()
                else:
                    app._on_board_select.assert_called_once_with('fav')
                app._show_snack_bar.assert_called_with('上传成功' if upload else '拉取成功')
                app.config_service.update_last_sync.assert_called_once()

    async def test_failures_and_missing_remote_unlock_controls(self):
        for upload in (True, False):
            for failure in ('result', 'exception', 'no-remote'):
                with self.subTest(upload=upload, failure=failure):
                    app = self.make_app()
                    operation = app.git_service.upload_data if upload else app.git_service.pull_data
                    operation.return_value = False, '操作失败'
                    if failure == 'exception':
                        operation.side_effect = OSError('网络中断')
                    app.git_service.has_remote.return_value = failure != 'no-remote'
                    await app._run_data_transfer(upload)
                    self.assertFalse(app._syncing)
                    self.assertTrue(all(not getattr(app, name).disabled for name in self.controls))
                    self.assertEqual(app.page.overlay, [])
                    app.config_service.update_last_sync.assert_not_called()
                    app._on_board_select.assert_not_called()
                    if failure == 'no-remote':
                        operation.assert_not_called()
                    else:
                        operation.assert_called_once_with(app.data_service)

    async def test_upload_resets_expired_recurring_tasks_before_transfer(self):
        app = self.make_app()
        app.selected_board_id = app.TASKS_BOARD_ID
        app._reset_recurring_tasks.return_value = True
        calls = []
        app._reset_recurring_tasks.side_effect = lambda: calls.append('reset') or True
        app.git_service.upload_data.side_effect = lambda _: (calls.append('upload') or True, '上传成功')
        await app._on_upload_data(None)
        self.assertEqual(calls, ['reset', 'upload'])
        app._refresh_tasks.assert_called_once()

    def test_description_cannot_be_edited_during_transfer(self):
        app = self.make_app()
        app._syncing = True
        app._on_edit_board_desc(Mock())
        app.page.show_dialog.assert_not_called()


class NetworkDeadlineTests(unittest.TestCase):
    def make_service(self):
        service = GitService('.')
        repo = MagicMock()
        service._get_repo = Mock(return_value=repo)
        service.has_remote = Mock(return_value=True)
        service._target_branch = Mock(return_value='main')
        return service, repo

    def test_push_has_deadline_and_never_opens_interactive_prompt(self):
        service, repo = self.make_service()
        repo.git.push.side_effect = OSError('Timeout: command did not finish')
        success, message = service.push()
        self.assertFalse(success)
        self.assertIn('超时', message)
        repo.git.push.assert_called_once_with('--set-upstream', 'origin', 'HEAD:main',
                                              kill_after_timeout=service.NETWORK_TIMEOUT)
        environment = repo.git.custom_environment.call_args.kwargs
        self.assertEqual(environment['GIT_TERMINAL_PROMPT'], '0')
        self.assertEqual(environment['GCM_INTERACTIVE'], 'Never')

    def test_fetch_has_deadline_and_prunes_stale_branches(self):
        service, repo = self.make_service()
        repo.remotes.origin.fetch.side_effect = OSError('Timeout')
        success, message = service.pull()
        self.assertFalse(success)
        self.assertIn('超时', message)
        repo.remotes.origin.fetch.assert_called_once_with(prune=True, kill_after_timeout=service.NETWORK_TIMEOUT)
