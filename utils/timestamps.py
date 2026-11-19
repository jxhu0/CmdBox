"""避免低精度时钟或时钟回拨使连续编辑拥有同一个缓存版本。"""
from datetime import datetime, timedelta


def next_updated_at(previous):
    now = datetime.now()
    try:
        before = datetime.fromisoformat(previous)
        if now <= before:
            now = before + timedelta(microseconds=1)
    except (ValueError, TypeError):
        pass
    return now.isoformat()
