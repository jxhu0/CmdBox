# CmdBox

![](https://img.shields.io/badge/version-v1.5.1-blue)
![](https://img.shields.io/badge/license-MIT-green)
![](https://img.shields.io/badge/last_update-2026--11--20-orange)

一款用于保存和管理命令行指令及大模型 Prompt 的桌面应用。

## 功能

- 📁 自定义板块分类，支持品牌图标（Linux、Git、Claude Code、OpenClaw、Rust 等）
- ✅ 任务板块（看板视图、优先级排序、已完成折叠）
- 📋 指令增删查改
- 🔍 实时搜索过滤
- ⭐ 收藏置顶
- 🏷️ 标签系统
- 🔄 Git 数据上传与拉取（操作前备份，冲突保护）
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

- 点击右上角“上传数据”，将本地改动提交并推送到远程仓库，不自动拉取
- 点击“拉取数据”，将远程改动合并到本地并刷新界面，不自动上传
- 远程有新提交导致上传被拒绝时，可选择取消或用本地数据覆盖远程数据
- 两种操作均在后台执行，操作前等待本地保存并创建备份，无需重启应用
- 应用自动提交 `data.json`。覆盖上传前会检查本地待推送的提交，涉及其他文件时会停止
- 首次连接独立初始化的仓库时，拉取会合并互不冲突的记录
- 拉取遇到无法合并的数据冲突时，可选择取消或用有效的远程数据覆盖本地数据
- 确认覆盖后，先在本地备份被替换的 `data.json`。覆盖备份可在设置中恢复，会保留到手动删除
- 优先使用 origin 的跟踪分支或远程默认分支，兼容 main、master；网络操作超时后会恢复可操作状态

### 搜索与数据恢复

- 搜索在后台执行，输入后自动搜索，也可回车立即搜索或点击清空按钮
- 连续输入仅保留最新的待执行搜索；跨板块复用缓存，并限制缓存容量
- 窄窗口自动收窄侧边栏，板块管理操作收进菜单；较长的问题解答可按需展开
- 设置中恢复备份前会确认并校验文件，成功后刷新界面；恢复前也会备份当前数据
- 检测到其他窗口或程序修改数据文件时，停止覆盖；退出时会把本窗口尚未保存的修改另存为 `data_local_*.json` 备份
- 自动备份保留最近 10 份；冲突时的本地副本单独保留，可在设置中手动恢复，确认后手动清理
- 数据损坏且没有有效备份时显示恢复提示，不会自动用空数据覆盖原文件

## 开发

### 环境配置

```bash
pip install -r requirements.txt
```

Linux 桌面环境的原生文件选择器还需要安装 `zenity`。

### 运行

```bash
python3 main.py
```

### 网页版（在不同设备上使用）

网页版运行在一台持续开机的电脑或服务器上。所有浏览器访问同一个服务器数据目录；桌面版的 `~/.cmdbox` 配置不会被修改。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
mkdir -p "$HOME/cmdbox-data"
export CMDBOX_WEB_DATA_DIR="$HOME/cmdbox-data"
export CMDBOX_WEB_PASSWORD='换成自己的长密码'
.venv/bin/python run_web.py
```

逐行执行命令，每行末尾直接回车。启动后保持终端运行，再在启动服务的电脑上打开 [本机网页版](http://127.0.0.1:8765/)。

如果已经有数据，可将 `CMDBOX_WEB_DATA_DIR` 设为现有 Git 数据仓库的**绝对路径**（其中应有 `data.json`），这样网页版直接使用现有板块、指令、任务和问题。默认地址为 `http://127.0.0.1:8765`，仅本机可访问。

其他机器访问时，在服务器上设置 `CMDBOX_WEB_HOST=0.0.0.0` 后启动，再通过局域网地址或私有网络地址访问 `http://服务器地址:8765`。跨公网使用时，请在前面配置 HTTPS 反向代理，不要直接公开 HTTP 端口。仅本机访问时可将 `CMDBOX_WEB_PASSWORD` 留空跳过登录；对外监听（`CMDBOX_WEB_HOST` 非 `127.0.0.1`）时强制要求密码，建议使用长且独立的密码。

网页端的复制操作写入当前浏览器的剪贴板，导出文件下载到当前设备。服务器统一保存数据；如另一台设备修改了数据，请刷新当前页面再继续编辑。多台设备同时编辑同一份数据时，现有的外部变更保护可能阻止较旧页面保存，以防覆盖新数据。Git 上传/拉取仍使用服务器上的 Git 仓库和凭据。

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
- Flet FilePicker (原生异步文件对话框)

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
