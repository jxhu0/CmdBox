"""Fonts served with CmdBox for browser sessions."""

import flet as ft


WEB_TEXT_FONT = "Noto Sans CJK SC"
WEB_EMOJI_FONT = "Noto Color Emoji"


def configure_web_fonts(page: ft.Page):
    page.fonts = {
        WEB_TEXT_FONT: "fonts/NotoSansCJKsc-Regular.otf",
        WEB_EMOJI_FONT: "fonts/Noto-COLRv1.ttf",
    }
    page.theme = ft.Theme(font_family=WEB_TEXT_FONT)
