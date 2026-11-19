import unittest
from types import SimpleNamespace
from unittest.mock import patch

from models.task import Task
from views.task_card import TaskCard


class TaskTitleLayoutTests(unittest.TestCase):
    def make_card(self):
        return TaskCard(Task.create('长标题', '紧跟标题的描述'), *([lambda *_: None] * 4))

    def test_title_can_use_more_than_half_of_the_available_space(self):
        for measure_first in (True, False):
            with self.subTest(measure_first=measure_first):
                card = self.make_card()
                events = [(card._on_title_measured, 280), (card._on_text_area_resized, 400)]
                if not measure_first:
                    events.reverse()
                with patch.object(card, 'update') as update:
                    events[0][0](SimpleNamespace(width=events[0][1]))
                    update.assert_not_called()
                    events[1][0](SimpleNamespace(width=events[1][1]))
                    update.assert_called_once()
                self.assertEqual(card._title_text.width, 280)
                self.assertTrue(card._description_text.visible)
                self.assertIsNone(card._title_text.expand)

    def test_resize_preserves_title_first_and_restores_description_when_space_returns(self):
        card = self.make_card()
        with patch.object(card, 'update'):
            card._on_title_measured(SimpleNamespace(width=280))
            for available, expected_width, description_visible in [
                (200, 200, False), (400, 280, True), (280, 280, False), (0, 0, False),
                (600, 280, True),
            ]:
                with self.subTest(available=available):
                    card._on_text_area_resized(SimpleNamespace(width=available))
                    self.assertEqual(card._title_text.width, expected_width)
                    self.assertEqual(card._description_text.visible, description_visible)

    def test_same_native_measurements_do_not_trigger_repeated_updates(self):
        card = self.make_card()
        with patch.object(card, 'update') as update:
            card._on_title_measured(SimpleNamespace(width=280))
            card._on_text_area_resized(SimpleNamespace(width=400))
            update.reset_mock()
            card._on_title_measured(SimpleNamespace(width=280))
            card._on_text_area_resized(SimpleNamespace(width=400))
            update.assert_not_called()
