"""Run from the project root: python -m tests.benchmark_rendering.

Measures Python control construction only, not frontend frame/transport time.
"""
from time import perf_counter
from statistics import median
from unittest.mock import Mock, patch
from models.board import Board
from models.command import Command
from views.command_list import CommandList


def main():
    for count in (100, 1000):
        board = Board.create('Benchmark')
        commands = [Command.create(board.id, str(i), 'echo hello') for i in range(count)]
        view = CommandList({board.id: board}, *([Mock()] * 5))
        cold, warm = [], []
        with patch.object(CommandList, 'update'):
            for _ in range(5):
                view._card_cache.clear()
                start = perf_counter()
                view.update_commands(commands)
                cold.append(perf_counter() - start)
                start = perf_counter()
                view.update_commands(commands)
                warm.append(perf_counter() - start)
        print(f'{count} commands: fresh={median(cold)*1000:.1f}ms, cached={median(warm)*1000:.1f}ms')


if __name__ == '__main__':
    main()
