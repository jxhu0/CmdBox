"""统一校验磁盘、远程仓库及备份中的数据；兼容早期没有任务/问题的格式。"""
from models.board import Board
from models.command import Command
from models.task import Task
from models.question import Question


MODELS = {'boards': Board, 'commands': Command, 'tasks': Task, 'questions': Question}


def parse_data(data):
    if not isinstance(data, dict):
        raise ValueError('数据必须是 JSON 对象')
    if not {'boards', 'commands'} <= data.keys():
        raise ValueError('数据缺少 boards 或 commands，已拒绝不完整的数据')
    records = {}
    for name, model in MODELS.items():
        rows = data.get(name, [])
        if not isinstance(rows, list):
            raise ValueError(f'{name} 必须是列表')
        items, ids = [], set()
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f'{name} 中的记录必须是对象')
            # from_dict 负责旧字段的默认值；类型检查覆盖所有运行时使用的字段。
            item = model.from_dict(row)
            for key, value in item.to_dict().items():
                if key == 'tags':
                    valid = isinstance(value, list) and all(isinstance(tag, str) for tag in value)
                elif key in ('completed', 'in_progress', 'asked', 'is_favorite'):
                    valid = isinstance(value, bool)
                else:
                    valid = isinstance(value, str)
                if not valid:
                    raise ValueError(f'{name}.{key} 的类型无效')
            if not item.id.strip() or item.id in ids:
                raise ValueError(f'{name} 包含空白或重复 ID')
            if hasattr(item, 'priority') and item.priority not in ('high', 'medium', 'low'):
                raise ValueError(f'{name}.priority 无效')
            if isinstance(item, Task) and item.recurring not in ('', 'daily', 'weekly', 'monthly'):
                raise ValueError('tasks.recurring 无效')
            ids.add(item.id)
            items.append(item)
        records[name] = items
    board_ids = {board.id for board in records['boards']}
    if any(command.board_id not in board_ids for command in records['commands']):
        raise ValueError('存在指向已删除板块的指令')
    return records
