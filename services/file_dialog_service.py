"""复用 Flet 原生异步文件选择器，避免混用 tkinter、AppleScript 和阻塞等待。"""
import flet as ft


def get_file_picker(page):
    cached = getattr(page, '_cmdbox_file_picker', None)
    if isinstance(cached, ft.FilePicker):
        return cached
    picker = ft.FilePicker()
    # Flet 0.82 的 Service 会自动向当前 page 注册；保存引用以复用。
    page._cmdbox_file_picker = picker
    return picker


async def choose_directory(page, initial_directory):
    return await get_file_picker(page).get_directory_path(
        dialog_title='选择数据存储文件夹', initial_directory=initial_directory)


async def choose_export_path(page, filename, fmt):
    return await get_file_picker(page).save_file(
        dialog_title='保存导出文件', file_name=filename,
        file_type=ft.FilePickerFileType.CUSTOM, allowed_extensions=[fmt])
