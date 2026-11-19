import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from models.command import Command
from models.task import Task
from services.config_service import ConfigService
from services.data_service import DataService


class DataIntegrityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.service = DataService(temporary.name)
        self.service.load()

    def document(self):
        return json.loads(self.service.data_file.read_text(encoding='utf-8'))

    def test_incomplete_or_mistyped_remote_documents_are_rejected(self):
        task = Task.create('任务').to_dict()
        documents = [{}, {'boards': []}, {'boards': [], 'commands': None}]
        for key, value in [('title', None), ('completed', 'false'), ('priority', 'urgent'),
                           ('id', []), ('recurring', 'sometimes')]:
            documents.append({**self.document(), 'tasks': [{**task, key: value}]})
        command = Command.create('missing-board', '命令', 'echo hello').to_dict()
        documents.append({**self.document(), 'commands': [command]})
        for document in documents:
            with self.subTest(document=document), self.assertRaises((ValueError, KeyError)):
                DataService.parse_data(document)

    def test_old_documents_without_tasks_or_questions_still_load(self):
        document = self.document()
        del document['tasks'], document['questions']
        parsed = DataService.parse_data(document)
        self.assertEqual(len(parsed['boards']), 2)
        self.assertEqual(parsed['tasks'], [])
        self.assertEqual(parsed['questions'], [])

    def test_second_instance_cannot_overwrite_newer_data(self):
        other = DataService(str(self.service.data_path))
        other.load()
        other.add_task(Task.create('另一个窗口刚保存的任务'))
        before = self.service.data_file.read_bytes()
        with self.assertRaisesRegex(OSError, '其他窗口'):
            self.service.add_task(Task.create('过期窗口的编辑'))
        self.assertEqual(self.service.data_file.read_bytes(), before)
        self.service.load()
        self.assertEqual(self.service.tasks[0].title, '另一个窗口刚保存的任务')

    def test_invalid_reload_also_keeps_old_write_version(self):
        self.service.data_file.write_text('{}', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.service.load()
        with self.assertRaises(OSError):
            self.service.save()
        self.assertEqual(self.service.data_file.read_text(encoding='utf-8'), '{}')

    def test_external_conflict_does_not_trap_window_open_or_lose_pending_edits(self):
        self.service.enable_background_saves()
        other = DataService(str(self.service.data_path))
        other.load()
        other.add_task(Task.create('磁盘中的新任务'))
        self.service.add_task(Task.create('本窗口的修改'))
        self.service.close()
        self.assertEqual(self.document()['tasks'][0]['title'], '磁盘中的新任务')
        drafts = list(self.service.backup_dir.glob('data_local_*.json'))
        self.assertEqual(len(drafts), 1)
        self.assertEqual(json.loads(drafts[0].read_text(encoding='utf-8'))['tasks'][0]['title'], '本窗口的修改')

    def test_removed_data_file_does_not_replace_existing_models(self):
        boards = self.service.boards
        self.service.data_file.unlink()
        with self.assertRaises(OSError):
            self.service.load()
        self.assertIs(self.service.boards, boards)

    def test_restoring_invalid_backup_never_changes_current_data(self):
        before = self.service.data_file.read_bytes()
        backup = self.service.data_path / 'invalid.json'
        backup.write_text('{}', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.service.restore_backup(backup)
        self.assertEqual(self.service.data_file.read_bytes(), before)
        self.assertEqual(self.service.get_backups(), [])

    def test_restore_backs_up_current_data_and_replaces_memory_after_write(self):
        backup = self.service.backup()
        self.service.add_task(Task.create('恢复前的新任务'))
        self.service.restore_backup(backup)
        self.assertEqual(self.service.tasks, [])
        documents = [json.loads(Path(b['path']).read_text(encoding='utf-8'))
                     for b in self.service.get_backups()]
        self.assertTrue(any(d['tasks'] for d in documents))
        self.assertEqual(self.document()['tasks'], [])

    def test_corrupted_json_skips_structurally_invalid_backup(self):
        backup = self.service.backup()
        self.service.backup_dir.joinpath('data_invalid.json').write_text('{}', encoding='utf-8')
        self.service.data_file.write_text('{broken', encoding='utf-8')
        self.service.load()
        self.assertEqual(len(self.service.boards), 2)
        self.assertEqual(self.document(), json.loads(Path(backup).read_text(encoding='utf-8')))

    def test_corruption_without_valid_backup_does_not_reset_to_empty(self):
        self.service.data_file.write_text('{broken', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '没有有效备份'):
            self.service.load()
        self.assertEqual(self.service.data_file.read_text(encoding='utf-8'), '{broken')

    def test_invalid_board_reorder_cannot_delete_boards(self):
        before = self.document()
        with self.assertRaises(ValueError):
            self.service.reorder_boards([self.service.boards[0].id])
        self.assertEqual(self.document(), before)

    def test_git_crlf_checkout_is_not_misidentified_as_external_data_change(self):
        raw = self.service.data_file.read_bytes()
        self.service.data_file.write_bytes(raw.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
        self.service.add_task(Task.create('Windows 换行后继续保存'))
        self.assertEqual(self.document()['tasks'][0]['title'], 'Windows 换行后继续保存')

    def test_automatic_backup_rotation_never_deletes_local_conflict_drafts(self):
        self.service.backup_dir.mkdir()
        draft = self.service.backup_dir / 'data_local_old.json'
        draft.write_text(json.dumps(self.document()), encoding='utf-8')
        with patch('services.data_service.datetime') as clock:
            clock.now.return_value.strftime.return_value = '2026-11-19_00-00-00_000000'
            for _ in range(12):
                self.service.backup()
        backups = self.service.get_backups()
        self.assertTrue(draft.exists())
        self.assertEqual(len([b for b in backups if not b['local_draft']]), 10)
        self.assertEqual(len([b for b in backups if b['local_draft']]), 1)

    def test_corruption_recovers_automatic_backup_and_leaves_local_draft_for_manual_choice(self):
        self.service.backup()
        document = self.document()
        document['tasks'] = [Task.create('未上传的本地修改').to_dict()]
        draft = self.service.backup_dir / 'data_local_latest.json'
        draft.write_text(json.dumps(document), encoding='utf-8')
        self.service.data_file.write_text('{broken', encoding='utf-8')
        self.service.load()
        self.assertEqual(self.service.tasks, [])
        self.assertTrue(draft.exists())
        self.service.restore_backup(draft)
        self.assertEqual(self.service.tasks[0].title, '未上传的本地修改')


class ConfigIntegrityTests(unittest.TestCase):
    def test_failed_atomic_write_preserves_existing_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            service = ConfigService(directory)
            service.init('/original')
            original = service.config_file.read_bytes()
            with patch('services.config_service.os.replace', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    service.set('repo_path', '/new')
            self.assertEqual(service.config_file.read_bytes(), original)
            self.assertEqual(service.get('repo_path'), '/original')
            self.assertFalse(list(Path(directory).glob('.config-*.tmp')))

    def test_corrupted_config_is_preserved_and_setup_can_recover(self):
        with tempfile.TemporaryDirectory() as directory:
            service = ConfigService(directory)
            service.config_file.write_text('{broken', encoding='utf-8')
            self.assertFalse(service.load())
            self.assertFalse(service.is_initialized())
            self.assertEqual(service.config_file.with_suffix('.json.corrupted').read_text(), '{broken')
