# views/setup_wizard.py
import flet as ft
from services.file_dialog_service import choose_directory
from pathlib import Path
from typing import Callable


def create_setup_wizard(page: ft.Page, on_complete: Callable[[str], None]) -> ft.Container:
    """创建首次启动向导"""
    path_data = {"path": str(Path.home() / "cmdbox-data")}

    def on_path_change(e):
        path_data["path"] = e.control.value

    async def on_browse(e):
        try:
            folder = await choose_directory(page, path_data["path"])
        except Exception as error:
            path_input.error = f'无法选择目录：{error}'
            path_input.update()
            return
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
                        ft.Text("3. 进入应用后点击“拉取数据”获取远程数据", size=13, color=ft.Colors.GREY_700),
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
