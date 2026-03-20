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
        )
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, expand=True)

    return ft.Container(
        content=content,
        expand=True,
        alignment=ft.Alignment(0.5, 0.5)
    )
