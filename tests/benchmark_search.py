"""Run: python -m tests.benchmark_search. Measures search CPU time, not UI frames."""
from statistics import median
from time import perf_counter

from models.command import Command
from services.data_service import DataService


def main():
    for count in (1000, 10000):
        service = DataService('.')
        service.commands = [Command.create('benchmark', f'command {i}',
                                          '项目说明 command body ' * 300, tags=['work'])
                            for i in range(count)]
        started = perf_counter()
        service.search_commands('absent-query')
        first = 1000 * (perf_counter() - started)
        samples = []
        for index in range(7):
            started = perf_counter()
            assert service.search_commands(f'absent-query-{index}') == []
            samples.append(1000 * (perf_counter() - started))
        print(f'{count} commands: first={first:.2f}ms, warm median={median(samples):.2f}ms')


if __name__ == '__main__':
    main()
