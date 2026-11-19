# views/question_list.py
import flet as ft
from views.isolated import IsolatedControl
from views.list_helpers import empty_state, sort_bar, scroll_to_top
from typing import List, Callable
from models.question import Question
from views.question_card import QuestionCard

# 排序模式：(mode_key, icon, tooltip)
SORT_MODES = [
    ("priority", ft.Icons.FLAG, "按优先级排序"),
    ("time", ft.Icons.SCHEDULE, "按时间排序"),
    ("status", ft.Icons.CHECKLIST, "按状态排序"),
]

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


class QuestionList(IsolatedControl, ft.ListView):
    def is_isolated(self):
        return True

    """问题列表组件"""

    def __init__(
        self,
        on_toggle_asked: Callable[[Question], None],
        on_edit: Callable[[Question], None],
        on_delete: Callable[[Question], None],
        on_add_question: Callable[[], None],
        on_clear_asked: Callable[[], None] = None
    ):
        super().__init__()
        self.on_toggle_asked = on_toggle_asked
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_add_question = on_add_question
        self.on_clear_asked = on_clear_asked
        self.questions: List[Question] = []
        self._query_ids = ()
        self.empty_filtered = False
        self._card_cache = {}
        self._visible_limit = 20
        self._page_start = 0
        self.asked_expanded = False
        self.sort_mode_index = 0  # 默认按优先级

        self.expand = True
        self.spacing = 8
        self.controls = self._build_empty_state()

    def _get_sorted_questions(self) -> List[Question]:
        """根据当前排序模式排序问题"""
        mode = SORT_MODES[self.sort_mode_index][0]
        questions = list(self.questions)
        questions.sort(key=lambda q: q.created_at or '', reverse=True)
        if mode == "priority":
            questions.sort(key=lambda q: PRIORITY_ORDER.get(q.priority, 1))
        elif mode == "time":
            questions.sort(key=lambda q: q.created_at or "", reverse=True)
        elif mode == "status":
            # 待询问在前，已询问在后；同状态按优先级排序
            questions.sort(key=lambda q: (q.asked, PRIORITY_ORDER.get(q.priority, 1)))
        return questions

    def _build_sort_bar(self) -> ft.Control:
        return sort_bar(SORT_MODES, self.sort_mode_index, self._select_sort_mode)

    def _select_sort_mode(self, index):
        if index == self.sort_mode_index:
            return
        self.sort_mode_index = index
        self._page_start = 0
        self.controls = self._build_question_cards()
        self.update()
        scroll_to_top(self)

    def _build_empty_state(self) -> List[ft.Control]:
        return empty_state('问题', ft.Icons.HELP_OUTLINE, self.empty_filtered)

    def _build_question_card(self, question: Question) -> QuestionCard:
        snapshot = (id(question), question.to_dict())
        cached = self._card_cache.get(question.id)
        if cached and cached[0] == snapshot:
            return cached[1]
        card = QuestionCard(
            question=question,
            on_toggle_asked=self.on_toggle_asked,
            on_edit=self.on_edit,
            on_delete=self.on_delete
        )
        self._card_cache[question.id] = (snapshot, card)
        return card

    def _build_question_cards(self) -> List[ft.Control]:
        if not self.questions:
            return self._build_empty_state()

        sorted_questions = self._get_sorted_questions()
        pending = [q for q in sorted_questions if not q.asked]
        asked = [q for q in sorted_questions if q.asked]
        largest_section = max(len(pending), len(asked) if self.asked_expanded else 0)
        self._page_start = min(self._page_start, max(0, (largest_section - 1) // self._visible_limit * self._visible_limit))

        cards = []

        # 排序切换栏
        cards.append(self._build_sort_bar())

        # 待询问问题
        if pending:
            for question in pending[self._page_start:self._page_start + self._visible_limit]:
                cards.append(self._build_question_card(question))
        else:
            cards.append(ft.Container(
                content=ft.Text("暂无待询问问题", size=13, color=ft.Colors.GREY_400),
                padding=ft.padding.symmetric(vertical=12),
            ))

        # 已询问问题（折叠区域）
        if asked:
            cards.append(ft.Divider(height=1))

            expand_icon = ft.Icons.EXPAND_MORE if self.asked_expanded else ft.Icons.CHEVRON_RIGHT
            header_row = [
                ft.Container(
                    content=ft.Row([
                        ft.Icon(expand_icon, size=16, color=ft.Colors.GREY_500),
                        ft.Text(f"已询问 ({len(asked)})", size=12, color=ft.Colors.GREY_500),
                    ], spacing=4, tight=True),
                    on_click=self._toggle_asked_section,
                ),
                ft.Container(expand=True),
            ]
            if self.on_clear_asked:
                header_row.append(
                    ft.IconButton(
                        icon=ft.Icons.DELETE_SWEEP,
                        icon_size=14,
                        icon_color=ft.Colors.GREY_400,
                        tooltip="清除已询问问题",
                        on_click=lambda e: self.on_clear_asked(),
                    )
                )
            asked_header = ft.Container(
                content=ft.Row(header_row, spacing=4, tight=True),
                padding=ft.padding.symmetric(vertical=6, horizontal=4),
            )
            cards.append(asked_header)

            if self.asked_expanded:
                for question in asked[self._page_start:self._page_start + self._visible_limit]:
                    cards.append(self._build_question_card(question))

        # 底部占位，为 FAB 按钮预留空间
        if self._page_start:
            cards.append(ft.TextButton('上一页', on_click=self._previous_page))
        if len(pending) > self._page_start + self._visible_limit or (self.asked_expanded and len(asked) > self._page_start + self._visible_limit):
            cards.append(ft.TextButton('下一页问题', on_click=self._load_more))
        cards.append(ft.Container(height=80))

        visible_ids = {item.id for item in pending[self._page_start:self._page_start + self._visible_limit]}
        if self.asked_expanded:
            visible_ids.update(item.id for item in asked[self._page_start:self._page_start + self._visible_limit])
        self._card_cache = {key: value for key, value in self._card_cache.items() if key in visible_ids}
        return cards

    def _toggle_asked_section(self, e):
        self.asked_expanded = not self.asked_expanded
        self._page_start = 0
        self.controls = self._build_question_cards()
        self.update()

    def update_questions(self, questions: List[Question]):
        active_ids = {question.id for question in questions}
        self._card_cache = {key: value for key, value in self._card_cache.items() if key in active_ids}
        ids = tuple(question.id for question in questions)
        if ids != self._query_ids:
            self._page_start = 0
            self._query_ids = ids
        self.questions = questions
        self.controls = self._build_question_cards()
        self.update()

    def _load_more(self, e):
        self._page_start += self._visible_limit
        self.controls = self._build_question_cards()
        self.update()
        scroll_to_top(self)

    def _previous_page(self, e):
        self._page_start = max(0, self._page_start - self._visible_limit)
        self.controls = self._build_question_cards()
        self.update()
        scroll_to_top(self)
