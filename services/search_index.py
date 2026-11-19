"""按记录更新版本缓存搜索文本，避免每次输入都转换长正文。"""
import threading


class SearchIndex:
    def __init__(self, fields):
        self.fields = fields
        self._documents = {}
        self._lock = threading.Lock()

    def clear(self):
        with self._lock:
            self._documents.clear()

    def filter(self, items, keyword):
        if not keyword:
            return list(items)
        keyword = keyword.casefold()
        with self._lock:
            previous = dict(self._documents)
        result, documents = [], {}
        for item in items:
            version = (id(item), item.updated_at)
            cached = previous.get(item.id)
            if cached is None or cached[0] != version:
                values = []
                for field in self.fields:
                    value = getattr(item, field)
                    values.extend(value if isinstance(value, list) else [value])
                cached = (version, tuple(value.casefold() for value in values))
            documents[item.id] = cached
            if any(keyword in value for value in cached[1]):
                result.append(item)
        # 不保留已删除或已经离开当前搜索范围的记录。
        with self._lock:
            self._documents = documents
        return result
