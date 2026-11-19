"""按记录版本缓存搜索文本，限制内存并保留跨板块的热缓存。"""
import sys
import threading
from collections import OrderedDict, deque


class SearchIndex:
    def __init__(self, fields, max_bytes=128 * 1024 * 1024):
        self.fields = fields
        self.max_bytes = max_bytes
        self._documents = OrderedDict()
        self._cache_bytes = 0
        self._epoch = 0
        self._lock = threading.Lock()

    def clear(self):
        with self._lock:
            self._documents.clear()
            self._cache_bytes = 0
            self._epoch += 1

    def filter(self, items, keyword):
        if not keyword:
            return list(items)
        keyword = keyword.casefold()
        with self._lock:
            previous = dict(self._documents)
            epoch = self._epoch
        result, documents = [], deque()
        staged_bytes = 0
        item_count = 0
        all_cached = True
        for item in items:
            item_count += 1
            version = (id(item), item.updated_at)
            cached = previous.get(item.id)
            if cached is None or cached[0] != version:
                all_cached = False
                values = []
                for field in self.fields:
                    value = getattr(item, field)
                    values.extend(value if isinstance(value, list) else [value])
                text = tuple(value.casefold() for value in values)
                # 文本、键与条目的近似大小；限制缓存估算值，而非进程 RSS。
                size = sum(map(sys.getsizeof, text)) + sys.getsizeof(text) + sys.getsizeof(item.id) + 256
                cached = (version, text, size)
            # 查询范围可以超过容量；临时候选缓存也要受限，不能先保存整份规范化正文。
            if cached[2] <= self.max_bytes:
                documents.append((item.id, cached))
                staged_bytes += cached[2]
                while staged_bytes > self.max_bytes:
                    _, removed = documents.popleft()
                    staged_bytes -= removed[2]
            if any(keyword in value for value in cached[1]):
                result.append(item)
        if all_cached and item_count == len(previous):
            return result
        with self._lock:
            # load/restore 已清空的索引不能被旧计算重新填入。
            if epoch != self._epoch:
                return result
            for key, entry in documents:
                old = self._documents.pop(key, None)
                if old:
                    self._cache_bytes -= old[2]
                self._documents[key] = entry
                self._cache_bytes += entry[2]
                while self._cache_bytes > self.max_bytes:
                    _, removed = self._documents.popitem(last=False)
                    self._cache_bytes -= removed[2]
        return result
