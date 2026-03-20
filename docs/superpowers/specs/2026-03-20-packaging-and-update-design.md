# 打包安装与自动更新功能设计

## 概述

为 CmdBox 添加打包安装功能，支持 macOS 和 Windows 平台，并为程序添加自动更新检测机制。

## 打包安装

### 方案选择

使用 Flet 官方打包工具 `flet pack` 进行快速打包验证。

### 打包命令

```bash
# macOS
flet pack --python-script main.py --platform macos

# Windows
flet pack --python-script main.py --platform windows
```

### 打包产物

- macOS: `.app` 应用程序包（需进一步封装为 .dmg 可选）
- Windows: `.exe` 可执行文件

## 版本管理

### 版本号定义

在 `app.py` 开头添加版本号常量：

```python
__version__ = "1.0.0"
```

### GitHub Release 对应

- 每次发布新版本时更新 `__version__`
- 创建 GitHub Release，版本号与 tag 一致
- Release 说明（Release Notes）作为更新内容展示

## 自动更新检测

### 检测时机

程序启动时自动检测是否有新版本。

### 检测方式

1. 程序启动后，调用 GitHub Releases API 获取最新版本
2. API 端点：`https://api.github.com/repos/jxhu0/CmdBox/releases/latest`
3. 比较 `tag_name` 与本地 `__version__`
4. 若有新版本，显示更新提示

### 版本比较规则

使用简单的字符串比较（假设版本格式为 v1.0.0）：
- `tag_name` = "v1.1.0"，`__version__` = "1.0.0" → 有新版本
- `tag_name` = "v1.0.0"，`__version__` = "1.0.0" → 无新版本

### 界面交互

检测到新版本时，显示 AlertDialog：

```
┌─────────────────────────────────┐
│  发现新版本 v1.1.0              │
├─────────────────────────────────┤
│                                 │
│  更新内容：                      │
│  - 新增批量导出功能              │
│  - 优化搜索体验                  │
│  - 修复若干 Bug                  │
│                                 │
├─────────────────────────────────┤
│           [暂不更新] [前往下载]  │
└─────────────────────────────────┘
```

- **暂不更新**：关闭对话框，继续使用当前版本
- **前往下载**：打开浏览器，跳转到 GitHub Releases 页面

### 数据流

```
启动
  │
  ▼
检测版本（异步，不阻塞 UI）
  │
  ▼
有新版本？ ─── 否 ───→ 正常启动
  │
  是
  ▼
显示更新提示 Dialog
  │
  ├── 点击"暂不更新" → 关闭对话框，正常启动
  │
  └── 点击"前往下载" → 打开浏览器 → GitHub Releases 页面
```

## 实现文件

### 修改文件

- `app.py` - 添加版本号、更新检测逻辑
- `views/dialogs.py` - 添加 UpdateDialog 类（可选，或直接在 app.py 中实现）

### 新增文件

无

## 错误处理

- 网络请求失败：静默忽略，不影响正常启动
- GitHub API 限流：静默忽略
- 版本解析失败：静默忽略

## 后续优化方向（暂不实现）

- 自动下载并安装更新包
- 进度条显示下载进度
- 增量更新（只下载变化的部分）
