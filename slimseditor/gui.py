import os
import sys

from collections import defaultdict

import imgui
import crossfiledialog

from slimseditor.backends import PS2BinBackend, PS3DecryptedBackend, PSVitaDecryptedBackend
from slimseditor.frames import FrameBase, SaveGameFrame, PS2MCFrame

click_states = defaultdict(lambda: False)
open_frames = []  # type: List[FrameBase]


def render_menu_bar():
    if imgui.begin_main_menu_bar():
        if imgui.begin_menu('File'):
            _, click_states['file_quit'] = imgui.menu_item('Quit', 'Cmd+Q', click_states['file_quit'])
            if click_states['file_quit']:
                sys.exit(0)

            imgui.end_menu()

        if imgui.begin_menu('Open'):
            _, click_states['open_ps2_bin'] = imgui.menu_item("PS2 .bin file", '', click_states['open_ps2_bin'])
            _, click_states['open_ps2_mc'] = imgui.menu_item("PS2 memory card (.ps2)", '', click_states['open_ps2_mc'])
            _, click_states['open_ps3_dec'] = imgui.menu_item("PS3 decrypted", '', click_states['open_ps3_dec'])
            _, click_states['open_vita_dec'] = imgui.menu_item("Vita decrypted", '', click_states['open_vita_dec'])

            imgui.end_menu()

        imgui.end_main_menu_bar()


def open_savegame(backend, *args, **kwargs):
    new_savegame = SaveGameFrame(backend, *args, **kwargs)
    open_frames.append(new_savegame)
    return new_savegame


def process_menu_bar_events():
    if click_states['open_ps2_bin']:
        path = crossfiledialog.open_file()
        if path:
            open_savegame(PS2BinBackend, path)

        click_states['open_ps2_bin'] = False

    if click_states['open_ps2_mc']:
        path = crossfiledialog.open_file()
        if path:
            open_frames.append(PS2MCFrame(path))

        click_states['open_ps2_mc'] = False

    if click_states['open_ps3_dec']:
        path = crossfiledialog.choose_folder()
        if path:
            open_savegame(PS3DecryptedBackend, path)

        click_states['open_ps3_dec'] = False

    if click_states['open_vita_dec']:
        path = crossfiledialog.open_file()
        if path:
            open_savegame(PSVitaDecryptedBackend, path)

        click_states['open_vita_dec'] = False


def process_envvars():
    ps2_bin = os.environ.get('OPEN_PS2BIN', '')
    if ps2_bin:
        for path in ps2_bin.split(':'):
            open_savegame(PS2BinBackend, path)

    ps2_mc = os.environ.get('OPEN_PS2MC', '')
    if ps2_mc:
        for path in ps2_mc.split(':'):
            try:
                open_frames.append(PS2MCFrame(path))
            except KeyboardInterrupt as e:
                raise e

    ps3_savegames = os.environ.get('OPEN_PS3_DEC', '')
    if ps3_savegames:
        for path in ps3_savegames.split(':'):
            open_savegame(PS3DecryptedBackend, path)

    vita_savegames = os.environ.get('OPEN_VITA_DEC', '')
    if vita_savegames:
        for path in vita_savegames.split(':'):
            open_savegame(PSVitaDecryptedBackend, path)


def main():
    process_envvars()

    imgui.create_context()
    io = imgui.get_io()
    io.display_size = (600, 800)
    fonts = io.fonts
    fonts.get_tex_data_as_rgba32()

    while True:
        imgui.new_frame()

        render_menu_bar()

        for frame in open_frames:
            frame.render()

        imgui.render()

        process_menu_bar_events()
        for frame in open_frames:
            frame.process_events()

        # Remove closed frames
        open_frames[:] = [frame for frame in open_frames if frame.opened]


if __name__ == "__main__":
    main()
