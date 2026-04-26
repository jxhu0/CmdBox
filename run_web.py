# run_web.py
"""以 Web 模式启动 CmdBox（适用于 WSL2 等无 GUI 环境下运行）"""

import os

os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"

import flet as ft
from app import CmdBoxApp


def main(page: ft.Page):
    CmdBoxApp(page)


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER, port=8765)
