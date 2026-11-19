import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from models.board import Board
from models.command import Command
from models.task import Task
from models.question import Question
from services.search_index import SearchIndex


class TimestampTests(unittest.TestCase):
    def test_consecutive_edits_in_same_clock_tick_have_distinct_versions(self):
        now = datetime(2026, 11, 19, 10, 0, 0)
        records = [Board.create('board'), Command.create('board', 'command', 'old'),
                   Task.create('task'), Question.create('question')]
        with patch('utils.timestamps.datetime', wraps=datetime) as clock:
            clock.now.return_value = now
            for record in records:
                record.updated_at = now.isoformat()
                versions = [record.updated_at]
                for _ in range(3):
                    record.update()
                    versions.append(record.updated_at)
                self.assertEqual(len(set(versions)), 4)
                self.assertEqual(versions, sorted(versions))

    def test_search_sees_rapid_edits_even_when_clock_moves_backwards(self):
        now = datetime(2026, 11, 19, 10, 0, 0)
        record = Command.create('board', 'command', 'old')
        record.updated_at = now.isoformat()
        search = SearchIndex(('content',))
        self.assertEqual(search.filter([record], 'old'), [record])
        with patch('utils.timestamps.datetime', wraps=datetime) as clock:
            clock.now.return_value = now - timedelta(seconds=1)
            record.update(content='new')
            self.assertEqual(search.filter([record], 'new'), [record])
            record.update(content='latest')
            self.assertEqual(search.filter([record], 'latest'), [record])
