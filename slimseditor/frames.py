from collections import defaultdict
from datetime import datetime
from io import BytesIO

import imgui
import crossfiledialog

from diff_match_patch import diff_match_patch
from mymcplus import ps2mc

from slimseditor.backends import AbstractBackend, PS2WrappedBinBackend
from slimseditor.hexdump import hexdump

counter = 0


def get_next_count():
    global counter
    value, counter = counter, counter + 1
    return value


def format_patchline(t, text):
    text = text.strip('\n').replace('\n', '\n  ')
    return f"{'+' if t == 1 else '-'} {text}"


class FrameBase:
    def __init__(self):
        self._size = None
        self.opened = True
        self.click_states = defaultdict(lambda: False)

    def render(self):
        if not self._size:
            self._size = (400, 600)
            imgui.set_next_window_size(self._size[0], self._size[1])

    def process_events(self):
        pass


class SaveGameFrame(FrameBase):
    def __init__(self, backend_class, *backend_args, **backend_kwargs):
        super(SaveGameFrame, self).__init__()
        self.backend_class = backend_class
        self.backend_args = backend_args
        self.backend_kwargs = backend_kwargs
        self.load_backend()

        self.name = '{0}##{1}'.format(self.backend.get_friendly_name(), get_next_count())
        self.diff_string = ""

    def load_backend(self):
        self.backend = self.backend_class(*self.backend_args, **self.backend_kwargs)  # type: AbstractBackend
        try:
            self.items = self.backend.get_items()
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            self.items = dict()
            print(str(e))

    def render(self):
        super(SaveGameFrame, self).render()
        if imgui.begin(self.name, True, 
                    flags=imgui.WINDOW_NO_COLLAPSE | imgui.WINDOW_MENU_BAR):

            if imgui.begin_menu_bar():
                _, self.click_states['save'] = imgui.menu_item('Save', 'Cmd+S', self.click_states['save'])
                _, self.click_states['reload'] = imgui.menu_item('Reload', 'Cmd+R', self.click_states['reload'])
                _, self.click_states['export'] = imgui.menu_item('Export', 'Cmd+E', self.click_states['export'])
                _, self.click_states['reload_and_diff'] = imgui.menu_item('Reload & Diff', 'Cmd+D', self.click_states['reload_and_diff'])
                imgui.end_menu_bar()

            if self.diff_string:
                imgui.columns(2, "hex split")

            imgui.text('Game: ')
            imgui.same_line()
            imgui.text(self.backend.game.value)

            for section_name, section_items in self.items.items():
                if imgui.collapsing_header(section_name):
                    for item in section_items:
                        item.render_widget()

            if self.diff_string:
                imgui.next_column()
                for line in self.diff_string.splitlines():
                    imgui.text(line)

        imgui.end()
    def reload_and_diff(self):
        pre_reload_hex = hexdump(self.backend.data, print_ascii=False)
        self.load_backend()
        post_reload_hex = hexdump(self.backend.data, print_ascii=False)

        patcher = diff_match_patch()
        patcher.Diff_Timeout = 0
        text1, text2, line_array = patcher.diff_linesToChars(pre_reload_hex, post_reload_hex)
        diffs = patcher.diff_main(text1, text2)
        patcher.diff_cleanupSemantic(diffs)
        patcher.diff_charsToLines(diffs, line_array)
        patch = '\n'.join(format_patchline(t, text) for t, text in diffs if t != 0)

        self.diff_string = f'{datetime.now()}\n{patch}\n\n{self.diff_string}'

    def process_events(self):
        if self.click_states['save']:
            self.backend.write_all_items(self.items)
            self.backend.write_data()
            self.click_states['save'] = False

        if self.click_states['reload']:
            self.load_backend()
            self.click_states['reload'] = False

        if self.click_states['reload_and_diff']:
            self.reload_and_diff()
            self.click_states['reload_and_diff'] = False

        if self.click_states['export']:
            filename = crossfiledialog.save_file()
            if filename:
                with open(filename, 'wb') as f:
                    f.write(self.backend.data)

            self.click_states['export'] = False


class PS2MCFrame(FrameBase):
    NAME_EXCLUSIONS = [b'.', b'..']

    def __init__(self, path):
        self._size = None
        self.opened = True
        self.click_states = defaultdict(lambda: False)

        self.path = path
        self.name = '{0}##{1}'.format(path, get_next_count())
        self.child_frames = []
        self.tree = dict()
        self.load_card_data()

    def load_card_data(self):
        with open(self.path, 'rb') as f:
            self.data = BytesIO(f.read())

        self.card = ps2mc.ps2mc(self.data)
        self.tree = dict()
        root_dir = self.card.dir_open('/')
        for entry in root_dir:
            if not ps2mc.mode_is_dir(entry[0]):
                continue

            if entry[-1] not in self.NAME_EXCLUSIONS:
                dirname = entry[-1].decode('ascii')
                subnames = []
                dir_files = self.card.dir_open(dirname)
                for file_entry in dir_files:
                    if file_entry[-1] in self.NAME_EXCLUSIONS:
                        continue

                    decoded_name = file_entry[-1].decode('ascii')
                    if decoded_name.endswith('bin'):
                        subnames.append((
                            decoded_name,
                            'Open##{0}/{1}'.format(dirname, decoded_name)
                        ))

                self.tree[dirname] = subnames
                dir_files.close()

        root_dir.close()

    def write_card_data(self):
        self.card.flush()
        with open(self.path, 'wb') as f:
            self.data.seek(0)
            f.write(self.data.read())

    def render(self):
        if self._size is None:
            self._size = (400, 600)
            imgui.set_next_window_size(self._size[0], self._size[1])

        if imgui.begin(self.name, True, flags=imgui.WINDOW_NO_COLLAPSE | imgui.WINDOW_MENU_BAR):

            if imgui.begin_menu_bar():
                _, self.click_states['reload'] = imgui.menu_item('Reload', 'Cmd+R', self.click_states['reload'])
                imgui.end_menu_bar()

            for folder_name, folder_files in self.tree.items():
                if imgui.collapsing_header(folder_name):
                    for item, button_name in folder_files:
                        if imgui.button(button_name):
                            item_path = f'{folder_name}/{item}'
                            try:
                                new_savegame = SaveGameFrame(PS2WrappedBinBackend, item_path, self)
                                self.child_frames.append(new_savegame)
                            except KeyboardInterrupt as e:
                                raise e
                            except Exception as e:
                                print(e)

                        imgui.same_line()
                        imgui.text(item)

            imgui.end()

        for child_frame in self.child_frames:
            child_frame.render()

    def process_events(self):
        if self.click_states['reload']:
            self.load_card_data()
            self.click_states['reload'] = False

        for child_frame in self.child_frames:
            child_frame.process_events()

        open_frames_to_close = []
        for i, frame in enumerate(self.child_frames):
            if not frame.opened:
                open_frames_to_close.append(i)

        for i in sorted(open_frames_to_close, reverse=True):
            del self.child_frames[i]
