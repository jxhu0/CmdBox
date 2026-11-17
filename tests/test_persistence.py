import json
import tempfile
import threading
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from services.data_service import DataService
from models.command import Command


class PersistenceTests(unittest.TestCase):
    def test_invalid_reload_does_not_partially_replace_models(self):
        with tempfile.TemporaryDirectory() as directory:
            service = DataService(directory)
            service.load()
            original_boards = service.boards
            data = json.loads(service.data_file.read_text())
            data['boards'][0]['name'] = '外部修改'
            data['tasks'] = [{}]
            service.data_file.write_text(json.dumps(data))
            with self.assertRaises(KeyError):
                service.load()
            self.assertIs(service.boards, original_boards)
            self.assertEqual(service.boards[0].name, 'Commands')

    def test_multiple_backups_in_same_second_preserve_both_snapshots(self):
        with tempfile.TemporaryDirectory() as directory:
            service = DataService(directory)
            service.save()
            with patch('services.data_service.datetime') as clock:
                clock.now.side_effect = [datetime(2026, 11, 17, microsecond=1),
                                         datetime(2026, 11, 17, microsecond=2)]
                first = service.backup()
                service.add_command(Command.create('board', 'new', 'echo new'))
                second = service.backup()
            self.assertNotEqual(first, second)
            self.assertEqual(len(json.loads(Path(first).read_text())['commands']), 0)
            self.assertEqual(len(json.loads(Path(second).read_text())['commands']), 1)

    def test_unchanged_records_reuse_snapshots_and_later_edits_persist(self):
        with tempfile.TemporaryDirectory() as directory:
            service = DataService(directory)
            service.commands = [Command.create('board', str(i), 'content') for i in range(100)]
            service.enable_background_saves()
            try:
                service.save()
                service.flush()
                with patch.object(service.commands[1], 'to_dict', side_effect=AssertionError('unchanged record rebuilt')):
                    service.commands[0].update(title='edited')
                    service.save()
                    service.flush()
                saved = json.loads(service.data_file.read_text(encoding='utf-8'))
                self.assertEqual(saved['commands'][0]['title'], 'edited')
                self.assertEqual(saved['commands'][1]['title'], '1')
            finally:
                service.close()

    def test_rapid_edits_coalesce_and_flush_writes_latest(self):
        with tempfile.TemporaryDirectory() as directory:
            service = DataService(directory)
            service.enable_background_saves()
            try:
                with patch.object(service, '_write_snapshot', wraps=service._write_snapshot) as write:
                    for index in range(10):
                        service.commands = [Command.create('board', str(index), 'content')]
                        service.save()
                    service.flush()
                    self.assertEqual(write.call_count, 1)
                saved = json.loads(service.data_file.read_text(encoding='utf-8'))
                self.assertEqual(saved['commands'][0]['title'], '9')
            finally:
                service.close()

    def test_background_save_does_not_wait_for_disk_and_flush_saves_latest(self):
        with tempfile.TemporaryDirectory() as directory:
            service = DataService(directory)
            command = Command.create('board', 'first', 'content', tags=['old'])
            service.commands = [command]
            started, release = threading.Event(), threading.Event()
            write = service._write_snapshot
            def slow_write(snapshot):
                started.set()
                self.assertTrue(release.wait(5))
                write(snapshot)
            service.enable_background_saves()
            try:
                with patch.object(service, '_write_snapshot', slow_write):
                    service.save()
                    self.assertTrue(started.wait(5))
                    command.update(title='latest', tags=['new'])
                    service.save()
                    release.set()
                    service.flush()
                saved = json.loads(service.data_file.read_text(encoding='utf-8'))
                self.assertEqual(saved['commands'][0]['title'], 'latest')
                self.assertEqual(saved['commands'][0]['tags'], ['new'])
            finally:
                release.set()
                service.close()

    def test_failed_write_keeps_valid_file_and_can_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            service = DataService(directory)
            service.save()
            original = service.data_file.read_bytes()
            errors = []
            service.enable_background_saves(errors.append)
            try:
                with patch('services.data_service.os.replace', side_effect=OSError('disk error')):
                    service.save()
                    with self.assertRaises(OSError):
                        service.flush()
                self.assertEqual(service.data_file.read_bytes(), original)
                self.assertEqual(len(errors), 1)
                service.save()
                service.flush()
                self.assertFalse(list(service.data_path.glob('.cmdbox-*.tmp')))
            finally:
                service.close()
