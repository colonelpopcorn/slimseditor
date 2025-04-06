import os
import sys

from collections import defaultdict

import imgui
import glfw
import crossfiledialog
import OpenGL.GL as gl


from imgui.integrations.glfw import GlfwRenderer
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
    # Initialize GLFW
    initted = glfw.init()
    print(initted)
    if not initted:
        return
        
    # Configure GLFW
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    
    # Create window
    window = glfw.create_window(800, 600, "slimseditor", None, None)
    if not window:
        glfw.terminate()
        return
        
    glfw.make_context_current(window)
    
    
    imgui.create_context()
    impl = GlfwRenderer(window)

    while not glfw.window_should_close(window):
        glfw.poll_events()
        impl.process_inputs()
        
        imgui.new_frame()

        render_menu_bar()

        for frame in open_frames:
            print("Rendering frame!")
            frame.render()

        imgui.render()
        
        impl.render(imgui.get_draw_data())
        glfw.swap_buffers(window)

        process_menu_bar_events()
        for frame in open_frames:
            frame.process_events()

        # Remove closed frames
        open_frames[:] = [frame for frame in open_frames if frame.opened]
    impl.shutdown()
    glfw.terminate()


if __name__ == "__main__":
    main()
