# views/question_list.py
import flet as ft
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


class QuestionList(ft.Column):
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
        self.asked_expanded = False
        self.sort_mode_index = 0  # 默认按优先级

        self.expand = True
        self.scroll = ft.ScrollMode.AUTO
        self.controls = self._build_empty_state()

    def _get_sorted_questions(self) -> List[Question]:
        """根据当前排序模式排序问题"""
        mode = SORT_MODES[self.sort_mode_index][0]
        questions = list(self.questions)
        if mode == "priority":
            questions.sort(key=lambda q: PRIORITY_ORDER.get(q.priority, 1))
        elif mode == "time":
            questions.sort(key=lambda q: q.created_at or "", reverse=True)
        elif mode == "status":
            # 待询问在前，已询问在后；同状态按优先级排序
            questions.sort(key=lambda q: (q.asked, PRIORITY_ORDER.get(q.priority, 1)))
        return questions

    def _build_sort_bar(self) -> ft.Control:
        """构建排序切换栏"""
        _, icon, tooltip = SORT_MODES[self.sort_mode_index]
        return ft.Container(
            content=ft.Row([
                ft.Container(expand=True),
                ft.IconButton(
                    icon=icon,
                    icon_size=16,
                    icon_color=ft.Colors.GREY_500,
                    tooltip=tooltip,
                    on_click=self._cycle_sort_mode,
                    style=ft.ButtonStyle(padding=4),
                ),
            ], spacing=0, tight=True),
            padding=ft.padding.only(right=4, top=2),
        )

    def _cycle_sort_mode(self, e):
        self.sort_mode_index = (self.sort_mode_index + 1) % len(SORT_MODES)
        self.controls = self._build_question_cards()
        self.update()

    def _build_empty_state(self) -> List[ft.Control]:
        return [
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.HELP_OUTLINE, size=48, color=ft.Colors.GREY_400),
                    ft.Text("暂无问题", color=ft.Colors.GREY_500),
                    ft.Text("点击下方按钮添加第一个问题", size=12, color=ft.Colors.GREY_400),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
                alignment=ft.Alignment(0.5, 0.5),
                expand=True
            )
        ]

    def _build_question_card(self, question: Question) -> QuestionCard:
        return QuestionCard(
            question=question,
            on_toggle_asked=self.on_toggle_asked,
            on_edit=self.on_edit,
            on_delete=self.on_delete
        )

    def _build_question_cards(self) -> List[ft.Control]:
        if not self.questions:
            return self._build_empty_state()

        sorted_questions = self._get_sorted_questions()
        pending = [q for q in sorted_questions if not q.asked]
        asked = [q for q in sorted_questions if q.asked]

        cards = []

        # 排序切换栏
        cards.append(self._build_sort_bar())

        # 待询问问题
        if pending:
            for question in pending:
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
                for question in asked:
                    cards.append(self._build_question_card(question))

        # 底部占位，为 FAB 按钮预留空间
        cards.append(ft.Container(height=80))

        return cards

    def _toggle_asked_section(self, e):
        self.asked_expanded = not self.asked_expanded
        self.controls = self._build_question_cards()
        self.update()

    def update_questions(self, questions: List[Question]):
        self.questions = questions
        self.controls = self._build_question_cards()
        self.update()
