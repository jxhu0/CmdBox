# main.py
"""CmdBox - 命令和 Prompt 管理工具"""

import flet as ft
from app import CmdBoxApp


def main(page: ft.Page):
    CmdBoxApp(page)


if __name__ == "__main__":
    ft.run(main)
