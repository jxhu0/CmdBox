# views/update_dialog.py
import flet as ft
import webbrowser


class UpdateDialog(ft.AlertDialog):
    """更新提示对话框"""

    def __init__(self, latest_version: str, release_notes: str):
        super().__init__()
        self.modal = True
        self.title = ft.Text(f"发现新版本 {latest_version}")
        self.dismiss = False  # 防止点击外部关闭

        # 格式化更新说明
        notes_text = release_notes[:500] + "..." if len(release_notes) > 500 else release_notes
        if not notes_text.strip():
            notes_text = "暂无更新说明"

        self.content = ft.Column([
            ft.Text("更新内容：", size=14, weight=ft.FontWeight.W_500),
            ft.Container(
                content=ft.Text(notes_text, size=12),
                padding=10,
                bgcolor=ft.Colors.GREY_100,
                border_radius=8,
                max_height=200
            )
        ], tight=True)

        self.actions = [
            ft.TextButton("暂不更新", on_click=self._on_cancel),
            ft.TextButton("前往下载", on_click=self._on_download),
        ]
        self.actions_alignment = ft.MainAxisAlignment.END

    def _on_cancel(self, e):
        self.open = False
        self.update()

    def _on_download(self, e):
        url = "https://github.com/jxhu0/CmdBox/releases"
        webbrowser.open(url)
        self.open = False
        self.update()
