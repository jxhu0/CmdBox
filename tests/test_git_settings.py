import tempfile
import unittest
from unittest.mock import Mock, patch

from git import Repo

from app import CmdBoxApp
from services.git_service import GitService


class GitRemoteSettingsTests(unittest.TestCase):
    def test_set_replace_and_clear_origin_preserves_other_remotes(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Repo.init(directory)
            service = GitService(directory)
            try:
                repo.create_remote('upstream', 'https://example.invalid/upstream.git')
                self.assertTrue(service.set_remote_url(' https://example.invalid/first.git ')[0])
                self.assertTrue(service.has_remote())
                self.assertEqual(service.get_remote_url(), 'https://example.invalid/first.git')
                self.assertTrue(service.set_remote_url('https://example.invalid/second.git')[0])
                self.assertEqual(service.get_remote_url(), 'https://example.invalid/second.git')
                self.assertEqual(service.set_remote_url('   '), (True, '远程地址已清除'))
                self.assertFalse(service.has_remote())
                self.assertIsNone(service.get_remote_url())
                self.assertEqual([r.name for r in repo.remotes], ['upstream'])
                self.assertTrue(service.set_remote_url('')[0])
            finally:
                repo.close()
                service.cleanup()

    def test_settings_clear_uses_actual_result_including_failure(self):
        app = CmdBoxApp.__new__(CmdBoxApp)
        app._syncing = app._closing = False
        app.data_service = Mock(records_generation=0)
        app.config_service = Mock()
        app.config_service.get_latest_version.return_value = None
        app.git_service, app.page, app._show_snack_bar = Mock(), Mock(), Mock()
        for result in [(True, '远程地址已清除'), (False, '无法修改 Git 配置')]:
            with self.subTest(result=result), patch('app.SettingsDialog') as dialog:
                app.git_service.set_remote_url.return_value = result
                CmdBoxApp._on_settings(app, None)
                dialog.call_args.kwargs['on_save']('')
                app.git_service.set_remote_url.assert_called_with('')
                expected = result[1] if result[0] else f'设置失败: {result[1]}'
                app._show_snack_bar.assert_called_with(expected)
