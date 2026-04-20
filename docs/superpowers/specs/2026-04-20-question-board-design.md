# 问题板块设计文档

## 概述

新增"问题"板块，用于记录待询问和已询问的问题。参照任务板块的架构模式，独立实现模型、卡片、列表和对话框。放置在侧边栏中任务板块和收藏板块之间。

## 侧边栏最终渲染顺序

1. 任务板块（绿色，CHECKLIST 图标）
2. **问题板块（紫色，HELP_OUTLINE 图标）** ← 新增
3. 收藏板块
4. 可拖拽的普通板块

## 数据模型

### Question (`models/question.py`)

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| id | str | uuid4 | 唯一标识 |
| title | str | 必填 | 问题标题 |
| description | str | "" | 问题描述（补充说明） |
| answer | str | "" | 解答内容（可随时填写） |
| priority | str | "medium" | 优先级：high/medium/low |
| asked | bool | False | 是否已询问 |
| created_at | str | "" | 创建时间（ISO格式） |
| updated_at | str | "" | 更新时间（ISO格式） |

**方法签名**：

```python
@classmethod
def create(cls, title: str, description: str = "", answer: str = "", priority: str = "medium") -> "Question"

def update(self, title=None, description=None, answer=None, priority=None, asked=None)

def to_dict(self) -> dict

@classmethod
def from_dict(cls, data: dict) -> "Question"
```

**数据兼容性**：`from_dict()` 使用 `data.get("answer", "")` 和 `data.get("asked", False)`，旧数据不会报错。

## UI 组件

### QuestionCard (`views/question_card.py`)

参照 TaskCard 布局：

```
[✓] 问题标题 · 问题描述
    💬 解答内容摘要...
                        [高] [编辑] [删除]
```

- **左侧**：勾选按钮（切换已询问/待询问）+ 标题 + 描述 + 解答摘要（带💬图标前缀）
- **解答摘要**：仅当 `answer` 非空时显示，`max_lines=1` + `overflow=ELLIPSIS` 截断
- **右侧**：优先级标签 + 编辑 + 删除
- **背景色**：已询问 → `GREY_50`，待询问 → `WHITE`
- **左边框**：3px 颜色跟随优先级
- **回调**：`on_toggle_asked`, `on_edit`, `on_delete`

### QuestionList (`views/question_list.py`)

参照 TaskList：

- 三种排序模式：按优先级 / 按时间 / 按状态
  - 按优先级：high → medium → low，同优先级按创建时间倒序
  - 按时间：创建时间倒序
  - 按状态：待询问在前，已询问在后；同状态按优先级排序
- `PRIORITY_ORDER` 复用任务的定义
- 待询问问题列表
- 可折叠"已询问"区域（含清除按钮）
- 底部 80px 占位为 FAB 预留空间
- 空状态提示："暂无问题" / "点击下方按钮添加第一个问题"

### QuestionDialog (`views/dialogs.py` 内新增)

参照 TaskDialog，新增 `answer_field`：

- 标题输入框（必填）
- 问题描述输入框（可选）
- 解答输入框（可选，多行 TextField，min_lines=2, max_lines=4）
- 优先级下拉选择（高/中/低）
- `on_save` 回调签名：`(title, description, answer, priority)`

## 服务层

### DataService (`services/data_service.py`)

新增属性和方法：

- `self.questions: List[Question] = []`
- `add_question(question)`: 添加并保存
- `get_question(question_id) -> Question | None`: 按 ID 获取
- `get_sorted_questions() -> List[Question]`: 按优先级排序（高→中→低），同优先级按创建时间倒序
- `update_question(question)`: 更新并保存
- `delete_question(question_id)`: 删除并保存
- `delete_asked_questions()`: 批量删除已询问问题
- 数据加载：`self.questions = [Question.from_dict(q) for q in data.get("questions", [])]`
- 数据保存：`"questions": [q.to_dict() for q in self.questions]`

## 主应用集成 (`app.py`)

### 常量

- 新增 `QUESTIONS_BOARD_ID = "__questions__"` 常量

### QuestionList 实例

新增 `QuestionList` 实例，传入回调：`on_toggle_asked`, `on_edit`, `on_delete`, `on_add_question`, `on_clear_asked`

### 回调方法

- `_on_toggle_question_asked(question)`: 切换已询问状态
- `_on_edit_question(question)`: 编辑问题（弹出 QuestionDialog）
- `_on_delete_question(question)`: 删除问题
- `_on_add_question()`: 添加问题（弹出 QuestionDialog）
- `_on_clear_asked_questions()`: 清除所有已询问问题
- `_refresh_questions()`: 刷新问题列表（支持搜索过滤）
- `_show_question_list(show)`: 控制问题列表容器的可见性

### 需要修改的现有方法

1. **`_on_board_select()`**：新增 `__questions__` 分支，调用 `_show_question_list()` 并隐藏其他内容区
2. **`_on_fab_click()`**：新增问题板块分支，当前为任务板块时添加任务，为问题板块时添加问题，否则添加命令
3. **`_on_search()`**：新增问题板块搜索分支，搜索问题时过滤 title + description + answer
4. **`_show_task_list()`**：需同时隐藏问题列表容器（三态切换：命令列表 / 任务列表 / 问题列表）
5. **`_show_question_list(show)`**：需同时隐藏任务列表容器
6. **`_refresh_sidebar()`**：计算 `pending_question_count`（未询问问题数）并传入 `sidebar.update_boards()`
7. **`_refresh_board_desc()`**：排除列表加入 `QUESTIONS_BOARD_ID`
8. **`main_content`**：新增 `question_list_container`（与 `task_list_container` 并列）

## 侧边栏 (`views/sidebar.py`)

- `update_boards()` 新增 `questions_id` 和 `pending_question_count` 参数
- 问题板块项位于任务板块和收藏板块之间
- 使用 `HELP_OUTLINE` 图标，紫色主题色
- 显示待询问问题数量徽章（紫色圆点数字）

## 文件清单

| 文件 | 操作 |
|------|------|
| models/question.py | 新建 |
| views/question_card.py | 新建 |
| views/question_list.py | 新建 |
| views/dialogs.py | 修改（新增 QuestionDialog） |
| services/data_service.py | 修改（新增 questions 属性和 CRUD） |
| views/sidebar.py | 修改（新增问题板块入口） |
| app.py | 修改（集成问题板块） |

## 设计原则

- 完全复刻任务板块的架构模式，保持代码风格一致
- 独立模型和视图，与任务板块解耦，便于独立演进
- 数据向后兼容，旧数据无 questions 字段时默认为空列表
