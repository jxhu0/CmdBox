# 批量导出指令功能设计

## 概述

为 CmdBox 添加批量导出指令功能，支持 JSON 和 CSV 两种格式导出。

## UI 调整

### 顶部栏布局

```
[Logo]   [搜索栏........................]   [导出] [同步] [设置]
```

- 搜索栏右移约 20px，腾出空间
- 导出按钮放置在同步按钮左侧
- 图标：`ft.Icons.DOWNLOAD`，悬停提示"导出指令"

## 导出对话框

### 结构

- 标题："导出指令"
- 导出范围单选框：
  - 当前板块的所有指令
  - 所有板块的所有指令
- 格式单选框：
  - JSON (.json)
  - CSV (.csv)
- 文件名输入框（默认：`cmdbox_export_YYYYMMDD`）
- 底部按钮：[取消] [导出]

### 行为

- 点击"导出"后弹出文件保存对话框
- 用户选择路径后保存文件
- 成功后显示 SnackBar 提示

## 导出数据格式

### JSON 格式

```json
{
  "export_date": "2026-03-20",
  "commands": [
    {
      "title": "查找文件",
      "description": "描述内容",
      "content": "find . -name '*.py'",
      "board": "板块名称",
      "tags": ["标签1", "标签2"],
      "is_favorite": true,
      "created_at": "2026-03-15T10:30:00",
      "updated_at": "2026-03-18T14:20:00"
    }
  ]
}
```

### CSV 格式

```
title,description,content,board,tags,is_favorite,created_at,updated_at
查找文件,描述内容,find . -name '*.py',Linux命令,"标签1,标签2",true,2026-03-15T10:30:00,2026-03-18T14:20:00
```

- 文件编码：UTF-8 BOM（确保 Excel 等工具正确识别中文）
- 字段分隔符：逗号 `,`
- 文本字段（description, content, title 包含逗号、引号、换行时）：用双引号包裹，内部双引号转义为两个双引号 `""`
- tags 字段：多个标签用逗号分隔，整体用双引号包裹
- is_favorite：导出为 `1`（收藏）或 `0`（未收藏）

## 行为与错误处理

### 文件保存

- 文件名输入框自动根据格式添加扩展名（选择 JSON 时自动添加 `.json`，选择 CSV 时自动添加 `.csv`）
- 默认文件名：`cmdbox_export_YYYYMMDD`
- 若文件已存在，直接覆盖（不提示）

### 边界情况

- **空导出**：若选中范围内无指令，仍导出空数组/空文件，显示 SnackBar "导出成功，共 0 条指令"
- **用户取消**：用户关闭文件对话框时，不做任何操作，不报错
- **保存失败**（磁盘满、权限问题等）：显示 SnackBar 错误提示 "导出失败：[原因]"

## 文件结构

### 新增文件

- `views/export_dialog.py` - 导出对话框组件

### 修改文件

- `app.py` - 添加导出按钮、调整搜索栏位置、添加导出逻辑
- `services/data_service.py` - 添加 `export_commands` 方法

## 实现步骤

1. 创建 `ExportDialog` 对话框组件
2. 在 `DataService` 添加 `export_commands` 方法
3. 在顶部栏添加导出按钮，调整搜索栏位置
4. 连接导出逻辑到主应用
