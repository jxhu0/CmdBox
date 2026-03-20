# 批量导出指令功能实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 CmdBox 添加批量导出指令功能，支持 JSON 和 CSV 两种格式

**Architecture:**
- 新增 `ExportDialog` 组件用于选择导出范围和格式
- 在 `DataService` 添加 `export_commands` 方法处理 JSON/CSV 序列化
- 顶部栏添加导出按钮，弹出对话框并保存文件

**Tech Stack:** Python + Flet + JSON/CSV

---

## Chunk 1: DataService 导出方法

**Files:**
- Modify: `services/data_service.py`

- [ ] **Step 1: 在 DataService 添加 export_commands 方法**

在 `data_service.py` 末尾添加以下方法：

```python
def export_commands(self, board_id: Optional[str] = None, format: str = "json") -> str:
    """导出指令为 JSON 或 CSV 格式

    Args:
        board_id: 若指定，则只导出该板块的指令；若为 None，则导出所有
        format: "json" 或 "csv"

    Returns:
        序列化后的字符串
    """
    # 获取要导出的指令
    if board_id:
        commands = [c for c in self.commands if c.board_id == board_id]
    else:
        commands = self.commands

    # 获取板块名称映射
    board_names = {b.id: b.name for b in self.boards}

    if format == "json":
        return self._export_as_json(commands, board_names)
    else:
        return self._export_as_csv(commands, board_names)

def _export_as_json(self, commands: List[Command], board_names: Dict[str, str]) -> str:
    """导出为 JSON 格式"""
    from datetime import datetime
    export_data = {
        "export_date": datetime.now().strftime("%Y-%m-%d"),
        "commands": []
    }
    for c in commands:
        export_data["commands"].append({
            "title": c.title,
            "description": c.description,
            "content": c.content,
            "board": board_names.get(c.board_id, ""),
            "tags": c.tags,
            "is_favorite": c.is_favorite,
            "created_at": c.created_at,
            "updated_at": c.updated_at
        })
    return json.dumps(export_data, ensure_ascii=False, indent=2)

def _export_as_csv(self, commands: List[Command], board_names: Dict[str, str]) -> str:
    """导出为 CSV 格式（UTF-8 BOM）"""
    import csv
    import io
    from datetime import datetime

    output = io.StringIO()
    # UTF-8 BOM for Excel compatibility
    writer = csv.writer(io.StringIO(), quoting=csv.QUOTE_ALL)

    # Write BOM
    output.write("\ufeff")

    # Header
    writer.writerow(["title", "description", "content", "board", "tags", "is_favorite", "created_at", "updated_at"])
    output.write("\ufeff".join(output.getvalue().split("\n")[0:1]))
    output = io.StringIO()

    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(["title", "description", "content", "board", "tags", "is_favorite", "created_at", "updated_at"])

    for c in commands:
        writer.writerow([
            c.title,
            c.description,
            c.content,
            board_names.get(c.board_id, ""),
            ",".join(c.tags) if c.tags else "",
            1 if c.is_favorite else 0,
            c.created_at,
            c.updated_at
        ])

    return output.getvalue()
```

- [ ] **Step 2: 运行测试验证语法正确**

Run: `cd /Users/hujiaxi/Documents/projects/CmdBox && python3 -c "from services.data_service import DataService; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add services/data_service.py
git commit -m "feat: 添加导出指令的 DataService 方法"
```

---

## Chunk 2: ExportDialog 对话框组件

**Files:**
- Create: `views/export_dialog.py`

- [ ] **Step 1: 创建 ExportDialog 组件**

创建 `views/export_dialog.py`：

```python
# views/export_dialog.py
import flet as ft
from typing import Optional, Callable
from datetime import datetime


class ExportDialog(ft.AlertDialog):
    """导出指令对话框"""

    def __init__(
        self,
        on_export: Callable[[str, str], None] = None  # (board_id, format)
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
```

- [ ] **Step 2: 运行测试验证语法正确**

Run: `cd /Users/hujiaxi/Documents/projects/CmdBox && python3 -c "from views.export_dialog import ExportDialog; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add views/export_dialog.py
git commit -m "feat: 创建导出对话框组件"
```

---

## Chunk 3: 顶部栏添加导出按钮

**Files:**
- Modify: `app.py` (line ~130-152)

- [ ] **Step 1: 在顶部栏同步按钮左侧添加导出按钮，并调整搜索栏位置**

找到 `self.header` 定义，修改按钮区域：

```python
self.header = ft.Container(
    content=ft.Row([
        self.logo,
        ft.Container(content=self.search_bar, expand=True, padding=ft.padding.symmetric(horizontal=30)),
        ft.Row([
            ft.IconButton(
                icon=ft.Icons.DOWNLOAD,
                icon_size=20,
                tooltip="导出指令",
                on_click=self._on_export_click
            ),
            ft.IconButton(
                icon=ft.Icons.SYNC,
                icon_size=20,
                tooltip="同步",
                on_click=self._on_sync
            ),
            ft.IconButton(
                icon=ft.Icons.SETTINGS_OUTLINED,
                icon_size=20,
                tooltip="设置",
                on_click=self._on_settings
            )
        ], spacing=0)
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, tight=False),
    padding=ft.padding.symmetric(horizontal=12, vertical=8),
    bgcolor=ft.Colors.WHITE,
    border=ft.border.only(bottom=ft.border.BorderSide(1, ft.Colors.GREY_200))
)
```

- [ ] **Step 2: 添加导出对话框实例变量和回调方法**

在 `app.py` 的 `__init__` 方法中找到 `self._is_moving = False`，在其后添加：

```python
# 导出对话框
self.export_dialog = ExportDialog(on_export=self._on_export_confirmed)
```

- [ ] **Step 3: 添加导出按钮点击处理和导出确认回调**

在 `app.py` 中找到 `_on_sync` 方法，在其附近添加：

```python
def _on_export_click(self, e):
    """点击导出按钮"""
    self.page.dialog = self.export_dialog
    self.export_dialog.open = True
    self.export_dialog.update()

def _on_export_confirmed(self, scope: str, fmt: str, filename: str):
    """确认导出"""
    import os

    # 确定板块 ID
    board_id = None
    if scope == "current":
        board_id = self.selected_board_id

    # 获取导出数据
    data = self.data_service.export_commands(board_id=board_id, format=fmt)

    # 添加文件扩展名
    ext = ".json" if fmt == "json" else ".csv"
    if not filename.endswith(ext):
        filename += ext

    # 弹出文件保存对话框
    save_path = self.page.get_storage_directory()

    def on_file_selected(e: ft.FilePickerResultEvent):
        if e.path:
            try:
                # 如果文件存在则直接覆盖
                with open(e.path, "w", encoding="utf-8") as f:
                    f.write(data)

                # 显示成功提示
                count = len(self.data_service.commands) if scope == "all" else \
                        len([c for c in self.data_service.commands if c.board_id == board_id])
                self.page.show_snack_bar(ft.SnackBar(
                    content=ft.Text(f"导出成功，共 {count} 条指令"),
                    bgcolor=ft.Colors.GREEN_100,
                ))
            except Exception as ex:
                self.page.show_snack_bar(ft.SnackBar(
                    content=ft.Text(f"导出失败：{str(ex)}"),
                    bgcolor=ft.Colors.RED_100,
                ))
        # 刷新页面
        self.page.update()

    file_picker = ft.FilePicker(on_result=on_file_selected)
    self.page.overlay.append(file_picker)
    self.page.update()
    file_picker.save_file(
        dialog_title="保存导出文件",
        file_name=filename,
        allowed_extensions=["json", "csv"] if fmt == "json" else ["csv"]
    )
```

- [ ] **Step 4: 运行测试验证语法正确**

Run: `cd /Users/hujiaxi/Documents/projects/CmdBox && python3 -c "import app" 2>&1`
Expected: 无错误输出

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "feat: 添加导出按钮和导出功能"
```

---

## 执行后验证

1. 运行应用：`cd /Users/hujiaxi/Documents/projects/CmdBox && python3 main.py`
2. 检查顶部栏是否显示导出按钮（下载图标）
3. 点击导出按钮，检查对话框是否正确显示
4. 测试导出 JSON 和 CSV 格式
5. 检查导出文件内容是否正确
