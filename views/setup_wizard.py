# views/setup_wizard.py
import flet as ft
import subprocess
import platform
from pathlib import Path
from typing import Callable


def _browse_folder(initial_dir: str) -> str:
    """跨平台选择文件夹"""
    system = platform.system()

    if system == "Darwin":  # macOS
        escaped_path = initial_dir.replace('"', '\\"')
        script = f'''
set targetFolder to POSIX file "{escaped_path}"
set chosen to choose folder with prompt "选择数据存储文件夹" default location targetFolder
return POSIX path of chosen
'''
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, Exception):
            pass
        return ""

    else:  # Windows / Linux - 使用 tkinter
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        root.update()
        try:
            folder = filedialog.askdirectory(initialdir=initial_dir)
        finally:
            root.destroy()
        return folder if folder else ""


def create_setup_wizard(page: ft.Page, on_complete: Callable[[str], None]) -> ft.Container:
    """创建首次启动向导"""
    path_data = {"path": str(Path.home() / "cmdbox-data")}

    def on_path_change(e):
        path_data["path"] = e.control.value

    def on_browse(e):
        folder = _browse_folder(path_data["path"])
        if folder:
            path_input.value = folder
            path_input.update()
            path_data["path"] = folder

    def on_start(e):
        path = path_data["path"].strip()
        if path:
            on_complete(path)

    def on_show_tutorial(e):
        """显示教程对话框"""
        tutorial_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.MENU_BOOK, color=ft.Colors.BLUE_600),
                    ft.Text("使用教程", weight=ft.FontWeight.BOLD)
                ], spacing=10)
            ),
            content=ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Text("在新电脑使用已有数据初始化：", size=14, weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_GREY_800),
                        ft.Container(height=10),
                        ft.Text("1. 在本地 clone 远程仓库到指定文件夹", size=13, color=ft.Colors.GREY_700),
                        ft.Container(height=6),
                        ft.Text("2. 打开 CmdBox，在向导中选择该文件夹路径", size=13, color=ft.Colors.GREY_700),
                        ft.Container(height=6),
                        ft.Text("3. 进入应用后即可直接使用同步功能", size=13, color=ft.Colors.GREY_700),
                        ft.Container(height=12),
                        ft.Text("提示：通过 git clone 克隆的仓库会自动配置远程地址，无需手动填写。", size=12, color=ft.Colors.BLUE_600),
                    ], tight=True),
                    padding=15,
                    bgcolor=ft.Colors.BLUE_50,
                    border_radius=12
                )
            ], tight=True),
            actions=[
                ft.TextButton("我知道了", on_click=lambda e: close_tutorial(tutorial_dialog))
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )

        def close_tutorial(dialog):
            dialog.open = False
            page.update()

        page.show_dialog(tutorial_dialog)

    path_input = ft.TextField(
        hint_text="选择或输入目录路径",
        width=400,
        value=path_data["path"],
        on_change=on_path_change
    )

    content = ft.Column([
        ft.Icon(ft.Icons.FOLDER_OPEN, size=64, color=ft.Colors.BLUE),
        ft.Container(height=20),
        ft.Text("欢迎使用 CmdBox", size=24, weight=ft.FontWeight.BOLD),
        ft.Container(height=10),
        ft.Text("请选择数据存储目录", size=14, color=ft.Colors.GREY_600),
        ft.Container(height=30),
        ft.Row([
            path_input,
            ft.IconButton(
                icon=ft.Icons.FOLDER_OPEN,
                tooltip="浏览",
                on_click=on_browse
            )
        ], alignment=ft.MainAxisAlignment.CENTER),
        ft.Container(height=40),
        ft.ElevatedButton(
            "开始使用",
            on_click=on_start,
            width=200,
            height=45
        ),
        ft.Container(height=20),
        ft.TextButton(
            "使用已有远程仓库？查看教程",
            icon=ft.Icons.MENU_BOOK,
            on_click=on_show_tutorial
        )
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, expand=True)

    return ft.Container(
        content=content,
        expand=True,
        alignment=ft.Alignment(0.5, 0.5)
    )
