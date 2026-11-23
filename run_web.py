# run_web.py
"""在一台机器上运行 CmdBox，供其他设备通过浏览器访问。"""

import asyncio
import hmac
import os
from pathlib import Path

import flet as ft

from app import CmdBoxApp, get_assets_dir
from utils.web_fonts import configure_web_fonts


def web_settings():
    password = os.environ.get("CMDBOX_WEB_PASSWORD", "")
    data_dir = os.environ.get("CMDBOX_WEB_DATA_DIR", "")
    if not password:
        raise SystemExit("请设置 CMDBOX_WEB_PASSWORD 后再启动网页版")
    if not data_dir:
        raise SystemExit("请设置 CMDBOX_WEB_DATA_DIR（服务器上的数据目录）")
    path = Path(data_dir).expanduser().resolve()
    if not path.is_dir():
        raise SystemExit(f"数据目录不存在：{path}")
    return password, str(path)


def create_main(password: str, data_dir: str):
    def main(page: ft.Page):
        page.title = "CmdBox · 登录"
        configure_web_fonts(page)
        attempts = 0

        async def login(e):
            nonlocal attempts
            if attempts:
                await asyncio.sleep(min(2 ** min(attempts, 5), 30))
            supplied = password_field.value or ""
            if not hmac.compare_digest(supplied.encode(), password.encode()):
                attempts += 1
                password_field.value = ""
                error_text.value = "密码错误"
                page.update()
                return
            page.clean()
            app = CmdBoxApp(page, web_data_dir=data_dir)

            async def disconnect(e):
                if app.data_service:
                    await asyncio.to_thread(app.data_service.close)
                if app.git_service:
                    await asyncio.to_thread(app.git_service.cleanup)

            page.on_disconnect = disconnect

        password_field = ft.TextField(
            label="访问密码", password=True, can_reveal_password=True,
            autofocus=True, on_submit=login, width=320,
        )
        error_text = ft.Text("", color=ft.Colors.RED_600)
        login_button = ft.Button("进入 CmdBox", on_click=login)

        page.add(ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.TERMINAL, size=48, color=ft.Colors.BLUE_700),
                ft.Text("CmdBox", size=28, weight=ft.FontWeight.BOLD),
                ft.Text("输入访问密码，使用服务器上的指令和任务数据"),
                password_field, error_text, login_button,
            ], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            alignment=ft.Alignment(0, 0), expand=True,
        ))

    return main


if __name__ == "__main__":
    web_password, web_data_dir = web_settings()
    ft.run(
        create_main(web_password, web_data_dir),
        view=ft.AppView.WEB_BROWSER,
        assets_dir=get_assets_dir(),
        host=os.environ.get("CMDBOX_WEB_HOST", "127.0.0.1"),
        port=int(os.environ.get("CMDBOX_WEB_PORT", "8765")),
    )
