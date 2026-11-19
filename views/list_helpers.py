"""列表共用的空状态、排序菜单和翻页行为。"""
import flet as ft


def empty_state(noun, icon, filtered=False):
    title = f'没有匹配的{noun}' if filtered else f'暂无{noun}'
    hint = '请尝试其他关键词或清空筛选' if filtered else f'点击右下角按钮添加{noun}'
    return [ft.Container(
        content=ft.Column([
            ft.Icon(icon, size=48, color=ft.Colors.GREY_400),
            ft.Text(title, color=ft.Colors.GREY_500),
            ft.Text(hint, size=12, color=ft.Colors.GREY_400),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
        alignment=ft.Alignment(0, 0), expand=True)]


def sort_bar(modes, selected, on_select):
    _, icon, label = modes[selected]
    return ft.Container(
        content=ft.Row([
            ft.Container(expand=True),
            ft.PopupMenuButton(
                content=ft.Row([
                    ft.Icon(icon, size=16, color=ft.Colors.GREY_500),
                    ft.Text(label, size=12, color=ft.Colors.GREY_700),
                    ft.Icon(ft.Icons.ARROW_DROP_DOWN, size=16),
                ], spacing=4, tight=True),
                tooltip='选择排序方式',
                items=[ft.PopupMenuItem(
                    content=text, checked=index == selected,
                    on_click=lambda e, index=index: on_select(index),
                ) for index, (_, _, text) in enumerate(modes)],
            ),
        ], spacing=0, tight=True),
        padding=ft.padding.only(right=4, top=2))


def scroll_to_top(control):
    # 未挂载的列表用于离线预构建；挂载后翻页要回到新一页开头。
    try:
        page = control.page
    except RuntimeError:
        return

    async def scroll():
        try:
            await control.scroll_to(offset=0, duration=0)
        except RuntimeError:
            # 翻页后立即切换板块，列表可能已从缓存淘汰。
            pass
    page.run_task(scroll)
