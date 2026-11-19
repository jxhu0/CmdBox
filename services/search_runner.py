"""串行执行搜索，只保留正在计算的请求和最新的待处理请求。"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Lock


class SearchRunner:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='cmdbox-search')
        self._lock = Lock()
        self._pending = None
        self._closed = False

    async def run(self, callback, *args):
        with self._lock:
            if self._closed:
                raise asyncio.CancelledError
            if self._pending is not None:
                self._pending.cancel()
            future = self._executor.submit(callback, *args)
            self._pending = future
        return await asyncio.wrap_future(future)

    def close(self):
        with self._lock:
            self._closed = True
            self._executor.shutdown(wait=False, cancel_futures=True)
