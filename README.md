# CmdBox

一款用于保存和管理命令行指令及大模型 Prompt 的桌面应用。

## 功能

- 📁 自定义板块分类
- 📋 指令增删查改
- 🔍 实时搜索过滤
- ⭐ 收藏置顶
- 🏷️ 标签系统
- 🔄 Git 仓库同步
- 📋 一键复制到剪贴板
- 📤 批量导出（JSON/CSV）

## 安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
python3 main.py
```

## 技术栈

- Python 3.10+
- Flet 0.82.2 (UI 框架)
- GitPython (Git 操作)
- pyperclip (剪贴板)
- requests (自动更新)

## 打包

使用 Flet 官方工具打包：

```bash
pip install -r requirements.txt
pip install flet

# macOS
flet pack --python-script main.py --platform macos

# Windows
flet pack --python-script main.py --platform windows
```

## 自动更新

程序启动时会自动检测新版本，发现新版本时会提示用户前往 GitHub 下载。
