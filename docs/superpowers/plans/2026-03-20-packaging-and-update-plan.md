# 打包安装与自动更新功能实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 CmdBox 添加版本号管理、自动更新检测和打包功能

**Architecture:**
- 在 app.py 添加 `__version__` 常量
- 新增 `services/update_service.py` 处理 GitHub Releases API 调用
- 新增 `views/update_dialog.py` 显示更新提示对话框
- 启动时异步检测更新，不阻塞 UI

**Tech Stack:** Python + Flet + requests (GitHub API)

---

## Chunk 1: 添加版本号

**Files:**
- Modify: `app.py` (开头添加版本号)

- [ ] **Step 1: 在 app.py 开头添加版本号常量**

在 `app.py` 文件最开头（import 语句之前）添加：

```python
__version__ = "1.0.0"
```

- [ ] **Step 2: 验证语法正确**

Run: `cd /Users/hujiaxi/Documents/projects/CmdBox && python3 -c "import app; print(app.__version__)"`

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: 添加版本号常量"
```

---

## Chunk 2: 创建 UpdateService

**Files:**
- Create: `services/update_service.py`

- [ ] **Step 1: 创建 update_service.py**

创建 `services/update_service.py`：

```python
# services/update_service.py
import requests
from typing import Optional, Tuple

__version__ = "1.0.0"

GITHUB_REPO = "jxhu0/CmdBox"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


class UpdateService:
    """检查更新的服务"""

    @staticmethod
    def check_for_updates() -> Tuple[bool, Optional[str], Optional[str]]:
        """检查是否有新版本

        Returns:
            Tuple[有新版本, 最新版本号, 更新说明]
            - (False, None, None) 表示无新版本或检查失败
            - (True, "v1.1.0", "更新内容...") 表示有新版本
        """
        try:
            response = requests.get(API_URL, timeout=5)
            if response.status_code != 200:
                return False, None, None

            data = response.json()
            latest_version = data.get("tag_name", "")
            release_notes = data.get("body", "")

            # 去除 tag_name 的 'v' 前缀进行比较
            latest_ver = latest_version.lstrip("v")
            current_ver = __version__

            if latest_ver != current_ver:
                return True, latest_version, release_notes
            return False, None, None
        except Exception:
            return False, None, None
```

- [ ] **Step 2: 添加 requests 到 requirements.txt**

在 `requirements.txt` 中添加：

```
requests>=2.28.0
```

- [ ] **Step 3: 验证语法正确**

Run: `cd /Users/hujiaxi/Documents/projects/CmdBox && python3 -c "from services.update_service import UpdateService; print('OK')"`

- [ ] **Step 4: Commit**

```bash
git add services/update_service.py requirements.txt
git commit -m "feat: 创建更新检测服务"
```

---

## Chunk 3: 创建 UpdateDialog

**Files:**
- Create: `views/update_dialog.py`

- [ ] **Step 1: 创建 update_dialog.py**

创建 `views/update_dialog.py`：

```python
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
        url = f"https://github.com/jxhu0/CmdBox/releases"
        webbrowser.open(url)
        self.open = False
        self.update()
```

- [ ] **Step 2: 验证语法正确**

Run: `cd /Users/hujiaxi/Documents/projects/CmdBox && python3 -c "from views.update_dialog import UpdateDialog; print('OK')"`

- [ ] **Step 3: Commit**

```bash
git add views/update_dialog.py
git commit -m "feat: 创建更新提示对话框"
```

---

## Chunk 4: 集成更新检测到应用

**Files:**
- Modify: `app.py` (在初始化时调用更新检测)

- [ ] **Step 1: 在 app.py 中添加导入**

在 `app.py` 的 import 区域添加：

```python
from services.update_service import UpdateService
from views.update_dialog import UpdateDialog
```

- [ ] **Step 2: 在 _init_app 方法末尾添加更新检测**

找到 `_init_app` 方法，在末尾（`self._refresh_commands()` 之后）添加：

```python
# 异步检查更新（不阻塞 UI）
self._check_for_updates()
```

添加新方法：

```python
def _check_for_updates(self):
    """异步检查更新"""
    import threading

    def check():
        has_update, latest_ver, notes = UpdateService.check_for_updates()
        if has_update:
            # 在主线程中显示对话框
            def show_dialog():
                dialog = UpdateDialog(latest_ver, notes or "")
                self.page.show_dialog(dialog)

            self.page.run_task(lambda e: show_dialog())

    thread = threading.Thread(target=check)
    thread.start()
```

- [ ] **Step 3: 验证语法正确**

Run: `cd /Users/hujiaxi/Documents/projects/CmdBox && python3 -c "import app; print('OK')"`

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: 集成更新检测功能"
```

---

## Chunk 5: 更新 README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 添加打包说明到 README**

在 `README.md` 末尾添加：

```markdown
## 打包

使用 Flet 官方工具打包：

```bash
pip install flet

# macOS
flet pack --python-script main.py --platform macos

# Windows
flet pack --python-script main.py --platform windows
```

## 自动更新

程序启动时会自动检测新版本，发现新版本时会提示用户前往 GitHub 下载。
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: 添加打包和自动更新说明"
```

---

## 执行后验证

1. 运行应用：`cd /Users/hujiaxi/Documents/projects/CmdBox && python3 main.py`
2. 观察启动日志，确认无报错
3. 验证版本号：`python3 -c "import app; print(app.__version__)"`

## 发布新版本流程

1. 更新 `app.py` 中的 `__version__`
2. 创建 GitHub Release，tag 与版本号一致
3. 在 Release 页面填写更新说明
4. 打包发布
