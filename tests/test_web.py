import inspect
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from run_web import create_main, web_settings


class WebTests(unittest.IsolatedAsyncioTestCase):
    def test_web_requires_password_and_existing_data_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            # 本机监听（默认 127.0.0.1）允许免密，返回空密码
            with patch.dict('os.environ', {'CMDBOX_WEB_DATA_DIR': directory}, clear=True):
                self.assertEqual(web_settings(), ('', str(Path(directory).resolve())))
            # 对外监听必须设置密码
            with patch.dict('os.environ', {
                'CMDBOX_WEB_DATA_DIR': directory,
                'CMDBOX_WEB_HOST': '0.0.0.0',
            }, clear=True):
                with self.assertRaises(SystemExit):
                    web_settings()
            # 有密码时正常返回
            with patch.dict('os.environ', {
                'CMDBOX_WEB_DATA_DIR': directory,
                'CMDBOX_WEB_PASSWORD': 'secret',
            }, clear=True):
                self.assertEqual(web_settings(), ('secret', str(Path(directory).resolve())))

    async def test_password_gate_opens_data_only_after_success(self):
        page = Mock()
        create_main('secret', '/tmp/data')(page)
        controls = page.add.call_args.args[0].content.controls
        password_field, error_text, login_button = controls[3], controls[4], controls[5]
        # Flet awaits async callbacks, but discards coroutines returned by sync callbacks.
        self.assertTrue(inspect.iscoroutinefunction(login_button.on_click))
        self.assertTrue(inspect.iscoroutinefunction(password_field.on_submit))
        with patch('run_web.CmdBoxApp') as app_class, patch('run_web.asyncio.sleep', new_callable=AsyncMock):
            password_field.value = 'wrong'
            await login_button.on_click(None)
            app_class.assert_not_called()
            page.clean.assert_not_called()
            self.assertEqual(error_text.value, '密码错误')

            password_field.value = 'secret'
            await password_field.on_submit(None)
            app_class.assert_called_once_with(page, web_data_dir='/tmp/data')
            page.clean.assert_called_once()

    async def test_empty_password_skips_login(self):
        page = Mock()
        with patch('run_web.CmdBoxApp') as app_class:
            create_main('', '/tmp/data')(page)
            app_class.assert_called_once_with(page, web_data_dir='/tmp/data')
            page.add.assert_not_called()  # 不渲染登录界面
            self.assertIsNotNone(page.on_disconnect)
