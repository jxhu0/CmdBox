"""Render task/question cards at normal and narrow widths.

Run: python -m tests.visual_regression
Requires the Flet desktop runtime; writes screenshots to /tmp for inspection.
"""
import asyncio
from pathlib import Path
from tempfile import gettempdir
import flet as ft
from models.task import Task
from models.question import Question
from views.task_list import TaskList
from views.question_list import QuestionList


async def main(page: ft.Page):
    page.enable_screenshots = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window.height = 850
    noop = lambda *_: None
    tasks = TaskList(*([noop] * 5))
    tasks.tasks = [Task.create('短任务'),
                   Task.create('这是能完整放下的长标题测试', '短描述'),
                   Task.create('短标题', '很长的说明' * 40),
                   Task.create('长标题' * 40, '说明' * 40)]
    tasks.controls = tasks._build_task_cards()
    questions = QuestionList(*([noop] * 4))
    questions.questions = [Question.create('普通问题'),
                           Question.create('长解答', '问题描述', '解答内容需要换行。' * 35),
                           Question.create('下一张卡片')]
    questions.controls = questions._build_question_cards()
    page.add(ft.Text('任务'), ft.Container(tasks, height=300), ft.Text('问题'),
             ft.Container(questions, expand=True))
    for width in (700, 460):
        page.window.width = width
        page.update()
        await asyncio.sleep(0.5)
        png = await page.take_screenshot(pixel_ratio=1)
        target = Path(gettempdir()) / f'cmdbox-layout-{width}.png'
        target.write_bytes(png)
        print(target)
    await page.window.destroy()


if __name__ == '__main__':
    ft.run(main)
