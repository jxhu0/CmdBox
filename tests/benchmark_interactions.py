"""Measure real Flet patch generation, not only Python card construction."""
import asyncio
import tempfile
import msgpack
from time import perf_counter
from unittest.mock import Mock
from flet.messaging.session import Session
from flet.controls.base_control import BaseControl
from flet.messaging.protocol import configure_encode_object_for_msgpack
from app import CmdBoxApp
from services.data_service import DataService
from models.board import Board
from models.command import Command


async def main():
    with tempfile.TemporaryDirectory() as directory:
        conn = Mock()
        encode = configure_encode_object_for_msgpack(BaseControl)
        conn.send_message.side_effect = lambda message: msgpack.packb(message, default=encode)
        conn.loop = asyncio.get_running_loop()
        session = Session(conn)
        msgpack.packb(session.get_page_patch(), default=encode)
        app = CmdBoxApp.__new__(CmdBoxApp)
        app.page = session.page
        app.data_service = DataService(directory)
        app.FAVORITES_BOARD_ID, app.TASKS_BOARD_ID, app.QUESTIONS_BOARD_ID = '__favorites__', '__tasks__', '__questions__'
        app.selected_board_id = app.FAVORITES_BOARD_ID
        app.show_favorites_only = True
        app.search_keyword, app.search_board_ids, app.search_tag = '', None, None
        app._is_moving = False
        boards = [Board.create(str(i)) for i in range(10)]
        app.data_service.boards = boards
        app.data_service.commands = [Command.create(b.id, str(i), 'echo hello') for b in boards for i in range(100)]
        app._build_ui()
        app.data_service.enable_background_saves()
        for board in boards[:3] + boards[:3]:
            conn.send_message.reset_mock()
            start = perf_counter()
            app._on_board_select(board.id)
            await session.after_event(app.sidebar)
            print(f'switch: {(perf_counter()-start)*1000:.1f} ms, patches={conn.send_message.call_count}')
        async def measure(label, action, event_control=None):
            start = perf_counter()
            action()
            await session.after_event(event_control or app.sidebar)
            print(f'{label}: {(perf_counter()-start)*1000:.1f} ms')

        command = app.data_service.commands[200]
        await measure('open command editor', lambda: app._on_edit_command(command))
        dialog = app.page._dialogs.controls[-1]
        dialog.content_field.value = 'changed'
        await measure('save command', lambda: dialog._on_save(None), dialog)
        assert command.content == 'changed'
        await measure('open command deletion', lambda: app._on_delete_command(command))
        dialog = app.page._dialogs.controls[-1]
        await measure('delete command', lambda: dialog._on_confirm(None), dialog)
        assert app.data_service.get_command(command.id) is None
        await measure('open board editor', lambda: app._on_edit_board(boards[2].id))
        dialog = app.page._dialogs.controls[-1]
        dialog.name_field.value = 'Renamed'
        await measure('save board', lambda: dialog._on_save(None), dialog)
        assert boards[2].name == 'Renamed'
        await measure('open board deletion', lambda: app._on_delete_board(boards[2].id))
        dialog = app.page._dialogs.controls[-1]
        await measure('delete board', lambda: dialog._on_confirm(None), dialog)
        assert app.selected_board_id == app.FAVORITES_BOARD_ID
        assert not app.board_desc_container.visible
        app.data_service.close()
        import json
        saved = json.loads(app.data_service.data_file.read_text(encoding='utf-8'))
        assert len(saved['commands']) == 900
        print('Persistence checked: 900 commands remain after deletion and flush.')


if __name__ == '__main__':
    asyncio.run(main())
