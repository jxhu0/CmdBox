# views/export_dialog.py
import flet as ft
from datetime import datetime


class ExportDialog(ft.AlertDialog):
    """导出指令对话框"""

    def __init__(
        self,
        on_export=None  # (scope, format, filename)
    ):
        super().__init__()
        self.on_export_callback = on_export

        self.modal = True
        self.title = ft.Text("导出指令")

        # 导出范围
        self.scope_group = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="current", label="当前板块的所有指令"),
                ft.Radio(value="all", label="所有板块的所有指令"),
            ])
        )
        self.scope_group.value = "all"

        # 格式
        self.format_group = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="json", label="JSON (.json)"),
                ft.Radio(value="csv", label="CSV (.csv)"),
            ])
        )
        self.format_group.value = "json"

        # 文件名输入框
        default_name = f"cmdbox_export_{datetime.now().strftime('%Y%m%d')}"
        self.filename_field = ft.TextField(
            label="文件名",
            value=default_name,
            suffix=ft.Text(".json"),
            on_change=self._on_filename_change
        )

        self.content = ft.Column([
            ft.Text("导出范围", size=14, weight=ft.FontWeight.W_500),
            self.scope_group,
            ft.Container(height=16),
            ft.Text("格式", size=14, weight=ft.FontWeight.W_500),
            self.format_group,
            ft.Container(height=16),
            self.filename_field,
        ], tight=True)

        self.actions = [
            ft.TextButton("取消", on_click=self._on_cancel),
            ft.TextButton("导出", on_click=self._on_export),
        ]
        self.actions_alignment = ft.MainAxisAlignment.END

    def _on_filename_change(self, e):
        """文件名变化时自动更新扩展名"""
        ext = ".json" if self.format_group.value == "json" else ".csv"
        self.filename_field.suffix = ft.Text(ext)

    def _on_cancel(self, e):
        self.open = False
        self.update()

    def _on_export(self, e):
        if self.on_export_callback:
            scope = self.scope_group.value
            fmt = self.format_group.value
            filename = self.filename_field.value
            self.on_export_callback(scope, fmt, filename)
        self.open = False
        self.update()
