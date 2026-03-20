# views/setup_wizard.py
import flet as ft
from pathlib import Path
from typing import Callable
import tkinter as tk
from tkinter import filedialog


def create_setup_wizard(page: ft.Page, on_complete: Callable[[str], None]) -> ft.Container:
    """创建首次启动向导"""
    path_data = {"path": str(Path.home() / "cmdbox-data")}

    def on_path_change(e):
        path_data["path"] = e.control.value

    def on_browse(e):
        # 使用 tkinter 原生文件夹选择对话框
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        root.attributes('-topmost', True)  # 置顶
        folder = filedialog.askdirectory(initialdir=path_data["path"])
        root.destroy()
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
