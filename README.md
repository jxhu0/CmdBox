# CmdBox

![](https://img.shields.io/badge/version-v1.3.12-blue)
![](https://img.shields.io/badge/license-MIT-green)
![](https://img.shields.io/badge/last_update-2026--04--21-orange)

一款用于保存和管理命令行指令及大模型 Prompt 的桌面应用。

## 功能

- 📁 自定义板块分类，支持品牌图标（Linux、Git、Claude Code、OpenClaw、Rust 等）
- ✅ 任务板块（看板视图、优先级排序、已完成折叠）
- 📋 指令增删查改
- 🔍 实时搜索过滤
- ⭐ 收藏置顶
- 🏷️ 标签系统
- 🔄 Git 仓库同步（自动合并冲突，跨平台数据安全）
- 📋 一键复制到剪贴板
- 📤 批量导出（JSON/CSV）
- 🔔 自动检测更新

## 下载安装

前往 [Releases](https://github.com/jxhu0/CmdBox/releases) 页面下载对应平台的安装包：

- **macOS**: 下载 `CmdBox.zip`，解压后运行 `CmdBox.app`
- **Windows**: 下载 `CmdBox.exe`，双击运行

## 使用教程

### 首次使用

1. 在 GitHub 创建一个**私有仓库**用于存储数据
2. 将仓库 `git clone` 到本地
3. 首次打开 CmdBox，选择刚才 clone 的本地文件夹
4. 在设置中填入 Git 远程仓库地址（通过 `git clone` 克隆的仓库会自动配置远程地址）

### 同步功能

- 点击右上角同步按钮，将本地数据推送到远程仓库
- 在另一台电脑上点击同步，拉取远程更新
- 同步成功后需要重启应用才能看到最新数据
- 跨平台同步时自动处理冲突，保留双方数据

## 开发

### 环境配置

```bash
pip install -r requirements.txt
```

### 运行

```bash
python3 main.py
```

### 打包

使用 PyInstaller 打包：

```bash
pip install pyinstaller flet flet-desktop

# macOS
pyinstaller --name CmdBox --windowed --onedir --icon assets/icon.icns --add-data "assets;assets" --hidden-import=pyperclip --hidden-import=pyperclip.__init__ main.py

# Windows
pyinstaller --name CmdBox --windowed --onefile --icon assets/icon.ico --add-data "assets;assets" --hidden-import=pyperclip --hidden-import=pyperclip.__init__ main.py
```

## 技术栈

- Python 3.10+
- Flet 0.82.2 (UI 框架)
- GitPython (Git 操作)
- pyperclip (剪贴板)
- requests (HTTP 请求)
- tkinter (文件对话框)

## 项目结构

```
CmdBox/
├── app.py              # 主应用入口
├── main.py             # Flet 启动文件
├── requirements.txt    # 依赖列表
├── assets/             # 应用图标
│   └── icons/          # 品牌图标（SVG/PNG）
├── models/             # 数据模型
│   ├── board.py        # 板块模型
│   ├── command.py      # 命令模型
│   └── task.py         # 任务模型
├── views/              # UI 组件
│   ├── sidebar.py      # 侧边栏
│   ├── command_list.py # 命令列表
│   ├── task_list.py    # 任务列表
│   └── dialogs.py      # 对话框
├── services/           # 服务层
│   ├── data_service.py # 数据服务
│   └── git_service.py  # Git 同步
└── docs/               # 文档
```

## License

MIT License

Copyright (c) 2026 hujiaxi

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
