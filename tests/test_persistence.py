import json
import tempfile
import threading
import unittest
from unittest.mock import patch
from services.data_service import DataService
from models.command import Command


class PersistenceTests(unittest.TestCase):
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
