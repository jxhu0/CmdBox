import asyncio
import threading
import unittest

from models.command import Command
from services.search_index import SearchIndex
from services.search_runner import SearchRunner
from concurrent.futures import ThreadPoolExecutor


class SearchSchedulingTests(unittest.IsolatedAsyncioTestCase):
    async def test_burst_runs_only_current_and_latest_query(self):
        runner = SearchRunner()
        started, release = threading.Event(), threading.Event()
        calls = []

        def search(value):
            calls.append(value)
            if value == 0:
                started.set()
                if not release.wait(5):
                    raise TimeoutError('test worker not released')
            return value

        tasks = [asyncio.create_task(runner.run(search, 0))]
        try:
            self.assertTrue(await asyncio.to_thread(started.wait, 5))
            for value in range(1, 10):
                tasks.append(asyncio.create_task(runner.run(search, value)))
                await asyncio.sleep(0)
            self.assertEqual(calls, [0])
        finally:
            release.set()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            runner.close()
        self.assertEqual(calls, [0, 9])
        self.assertEqual(results[0], 0)
        self.assertEqual(results[-1], 9)
        self.assertTrue(all(isinstance(result, asyncio.CancelledError) for result in results[1:-1]))

    async def test_cancelling_running_caller_cannot_start_another_worker(self):
        runner = SearchRunner()
        started, release = threading.Event(), threading.Event()
        second_started = threading.Event()

        def first():
            started.set()
            if not release.wait(5):
                raise TimeoutError('test worker not released')

        task = asyncio.create_task(runner.run(first))
        next_task = None
        try:
            self.assertTrue(await asyncio.to_thread(started.wait, 5))
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            next_task = asyncio.create_task(runner.run(second_started.set))
            await asyncio.sleep(0)
            self.assertFalse(second_started.is_set())
        finally:
            release.set()
            if next_task:
                await next_task
            runner.close()
        self.assertTrue(second_started.is_set())

    async def test_closed_runner_cannot_accept_more_work(self):
        runner = SearchRunner()
        runner.close()
        with self.assertRaises(asyncio.CancelledError):
            await runner.run(lambda: self.fail('closed runner executed work'))


class CountingText(str):
    calls = 0

    def casefold(self):
        type(self).calls += 1
        return super().casefold()


class SearchCacheTests(unittest.TestCase):
    def test_switching_search_scopes_keeps_both_warm(self):
        index = SearchIndex(('content',))
        first = Command.create('first', 'first', CountingText('STRASSE'))
        second = Command.create('second', 'second', CountingText('Straße'))
        CountingText.calls = 0
        for _ in range(4):
            self.assertEqual(index.filter([first], 'strasse'), [first])
            self.assertEqual(index.filter([second], 'STRASSE'), [second])
        self.assertEqual(CountingText.calls, 2)
        first.update(content=CountingText('changed'))
        self.assertEqual(index.filter([first], 'changed'), [first])
        self.assertEqual(CountingText.calls, 3)

    def test_cache_budget_does_not_change_search_results(self):
        index = SearchIndex(('content',), max_bytes=3000)
        commands = [Command.create('board', str(i), 'x' * 1000 + str(i)) for i in range(20)]
        for _ in range(2):
            self.assertEqual(index.filter(commands, 'x'), commands)
            self.assertLessEqual(index._cache_bytes, index.max_bytes)
            self.assertEqual(index._cache_bytes, sum(value[2] for value in index._documents.values()))
        index.clear()
        self.assertEqual(index._cache_bytes, 0)
        self.assertFalse(index._documents)

    def test_one_oversized_record_is_searchable_without_being_cached(self):
        index = SearchIndex(('content',), max_bytes=500)
        command = Command.create('board', 'large', 'body' * 1000)
        self.assertEqual(index.filter([command], 'body'), [command])
        self.assertEqual(index._cache_bytes, 0)
        self.assertFalse(index._documents)

    def test_load_clearing_index_during_search_cannot_restore_old_cache(self):
        entered, release = threading.Event(), threading.Event()

        class BlockingText(str):
            def casefold(self):
                entered.set()
                if not release.wait(5):
                    raise TimeoutError('test normalization not released')
                return super().casefold()

        index = SearchIndex(('content',))
        command = Command.create('board', 'old', BlockingText('body'))
        with ThreadPoolExecutor(max_workers=1) as worker:
            pending = worker.submit(index.filter, [command], 'body')
            try:
                self.assertTrue(entered.wait(5))
                index.clear()
            finally:
                release.set()
            self.assertEqual(pending.result(5), [command])
        self.assertFalse(index._documents)
