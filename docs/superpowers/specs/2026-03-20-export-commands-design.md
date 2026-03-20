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

- tags 字段用逗号分隔
- description/content 中的特殊字符需要转义

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
