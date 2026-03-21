# views/update_dialog.py
import flet as ft
import webbrowser


class UpdateDialog(ft.AlertDialog):
    """更新提示对话框"""

    def __init__(self, latest_version: str, release_notes: str, on_remind_later: callable = None):
        super().__init__()
        self.modal = True
        self.dismiss = False
        self.on_remind_later = on_remind_later

        # 格式化更新说明
        notes_text = release_notes.strip() if release_notes else ""
        if not notes_text:
            notes_text = "暂无更新说明"

        self.title = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.UPDATE, color=ft.Colors.BLUE_600, size=24),
                ft.Text(
                    f"发现新版本 v{latest_version.lstrip('v')}",
                    size=18,
                    weight=ft.FontWeight.W_600,
                    color=ft.Colors.BLUE_GREY_800
                )
            ], spacing=10),
            padding=ft.padding.only(top=5, bottom=5)
        )

        self.content = ft.Column([
            ft.Container(
                content=ft.Column([
                    ft.Text("有新版本可用！", size=14, weight=ft.FontWeight.W_500, color=ft.Colors.GREY_800),
                    ft.Container(height=8),
                    ft.Text(notes_text, size=13, color=ft.Colors.GREY_600),
                ], tight=True),
                padding=15,
                bgcolor=ft.Colors.BLUE_50,
                border_radius=12,
                border=ft.border.all(1, ft.Colors.BLUE_100)
            )
        ], tight=True, spacing=0)

        self.actions = [
            ft.TextButton(
                "暂不提醒",
                on_click=self._on_remind_later,
                style=ft.ButtonStyle(color=ft.Colors.GREY_600)
            ),
            ft.Container(width=10),
            ft.TextButton(
                "暂不更新",
                on_click=self._on_cancel,
                style=ft.ButtonStyle(color=ft.Colors.GREY_500)
            ),
            ft.Container(width=10),
            ft.ElevatedButton(
                "前往下载",
                on_click=self._on_download,
                style=ft.ButtonStyle(
                    bgcolor=ft.Colors.BLUE_600,
                    color=ft.Colors.WHITE,
                    shape=ft.RoundedRectangleBorder(radius=8)
                )
            ),
        ]
        self.actions_alignment = ft.MainAxisAlignment.END

    def _on_cancel(self, e):
        self.open = False
        self.update()

    def _on_remind_later(self, e):
        if self.on_remind_later:
            self.on_remind_later()
        self.open = False
        self.update()

    def _on_download(self, e):
        url = "https://github.com/jxhu0/CmdBox/releases"
        webbrowser.open(url)
        self.open = False
        self.update()
