"""Compare list refresh and alternating search: python -m tests.benchmark_lists --baseline 7afae2f."""
import argparse
import subprocess
from statistics import median
from time import perf_counter
from unittest.mock import Mock, patch

from models.board import Board
from models.command import Command
from services.search_index import SearchIndex
from views.command_list import CommandList


def measure(label, list_class, index_class):
    board = Board.create('benchmark')
    body = '项目说明 command body ' * 3000
    commands = [Command.create(board.id, str(i), body, tags=['work']) for i in range(1000)]
    view = list_class({board.id: board}, *([Mock()] * 5))
    samples = []
    with patch.object(view, 'update'):
        view.update_commands(commands)
        for index in range(9):
            commands[0].update(title=str(index))
            started = perf_counter()
            view.update_commands(commands)
            samples.append(1000 * (perf_counter() - started))
    print(f'{label}: long command page refresh median={median(samples):.2f}ms')

    scopes = [[Command.create(str(scope), str(i), '项目说明 command body ' * 300)
               for i in range(1000)] for scope in range(2)]
    search = index_class(('title', 'content'))
    for scope in scopes:
        search.filter(scope, 'absent-query')
    samples = []
    for _ in range(7):
        for scope in scopes:
            started = perf_counter()
            assert search.filter(scope, 'absent-query') == []
            samples.append(1000 * (perf_counter() - started))
    print(f'{label}: alternating 1000-command boards median={median(samples):.2f}ms')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', help='read-only Git revision to compare')
    args = parser.parse_args()
    if args.baseline:
        classes = []
        for filename, name in [('views/command_list.py', 'CommandList'), ('services/search_index.py', 'SearchIndex')]:
            source = subprocess.run(['git', 'show', f'{args.baseline}:{filename}'],
                                    check=True, capture_output=True, text=True).stdout
            namespace = {'__name__': f'benchmark_baseline_{name}'}
            exec(compile(source, filename, 'exec'), namespace)
            classes.append(namespace[name])
        measure(args.baseline, *classes)
    measure('current', CommandList, SearchIndex)


if __name__ == '__main__':
    main()
