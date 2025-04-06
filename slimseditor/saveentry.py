import imgui


class AbstractSaveEntry:
    struct_type = 'i'
    python_type = int

    def __init__(self, name='', pos=0):
        self.name = name
        self.pos = pos
        self.bimpy_name = '{0}##{1}'.format(name, pos)
        self._value = self.python_type()

    @property
    def value(self):
        return self._value

    @property
    def export_value(self):
        return (self._value,)

    @value.setter
    def value(self, val):
        self._value = val[0]

    def render_widget(self):
        pass


class RangedInteger(AbstractSaveEntry):
    struct_type = 'i'
    python_type = int
    min = 0
    max = 100

    def __init__(self, name='', pos=0, max=max, min=min):
        super(RangedInteger, self).__init__(name=name, pos=pos)
        self.min = min
        self.max = max

    def render_widget(self):
        changed, value = imgui.slider_int(self.bimpy_name, self._value, self.min, self.max)
        if changed:
            self._value = value


class Boolean(AbstractSaveEntry):
    struct_type = '?'
    python_type = bool

    def render_widget(self):
        changed, value = imgui.checkbox(self.bimpy_name, self._value)
        if changed:
            self._value = value


class Integer(AbstractSaveEntry):
    struct_type = 'i'
    python_type = int

    def render_widget(self):
        changed, value = imgui.input_int(self.bimpy_name, self._value)
        if changed:
            self._value = int(value)


class UnsignedInteger(Integer):
    struct_type = 'I'


class Char(Integer):
    struct_type = 'b'


class UnsignedChar(Integer):
    struct_type = 'B'


class Short(Integer):
    struct_type = 'h'


class UnsignedShort(Integer):
    struct_type = 'H'


class DateTime(AbstractSaveEntry):
    struct_type = 'BBBBBBBB'
    python_type = tuple

    def __init__(self, name='', pos=0):
        super(DateTime, self).__init__(name=name, pos=pos)
        self._input_text = ""

    @property
    def value(self):
        _, s, i, h, _, d, m, y = self._value
        return f'{y:02X}-{m:02X}-{d:02X} {h:02X}:{i:02X}:{s:02X}'

    @property
    def export_value(self):
        return self._value

    @value.setter
    def value(self, val):
        self._value = val
        self._input_text = self.value

    def render_widget(self):
        changed, text = imgui.input_text(self.bimpy_name, self._input_text, 20)
        if changed:
            self._input_text = text
            try:
                his, ymd = text.split(' ')
                h, i, s = his.split(':')
                y, m, d = ymd.split('-')
                self._value = (0, int(s), int(i), int(h), 0, int(d), int(m), int(y))
            except:
                pass  # Handle parsing errors silently


class BitField(AbstractSaveEntry):
    struct_type = 'B'
    python_type = int
    bitmap = dict()
    bitmap_values = dict()

    def __init__(self, name='', pos=0, bitmap=None):
        super(BitField, self).__init__(name, pos)
        if bitmap is not None:
            self.bitmap = bitmap
        else:
            self.bitmap = dict()

        self.bitmap_values = dict()

    def _test_bit(self, offset):
        mask = 1 << offset
        return (self._value & mask)

    def _set_bit(self, offset):
        mask = 1 << offset
        self._value = (self._value | mask)

    def _clear_bit(self, offset):
        mask = ~(1 << offset)
        self._value = (self._value & mask)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        self._value = val[0]
        for key, pos in self.bitmap.items():
            self.bitmap_values[key] = bool(self._test_bit(pos))

    def render_widget(self):
        for key, pos in self.bitmap.items():
            changed, value = imgui.checkbox(key, self.bitmap_values.get(key, False))
            if changed:
                self.bitmap_values[key] = value
                if value:
                    self._set_bit(pos)
                else:
                    self._clear_bit(pos)


class Combo(AbstractSaveEntry):
    struct_type = 'i'
    python_type = int
    allowed_values = dict()

    def __init__(self, name='', pos=0, allowed_values=None):
        super(Combo, self).__init__(name, pos)
        if (allowed_values is None) or \
           (not isinstance(allowed_values, dict)) or \
           (not all(isinstance(v, int) for v in allowed_values.values())):
           raise RuntimeError("Field type Combo needs a mapping of allowed values")

        self.allowed_values = allowed_values
        self.allowed_values_list = list(allowed_values.keys())
        self._combo_current_item = 0

    def value_setter(self, val):
        self._value = val[0]
        # Find the index of the value in allowed_values
        for i, (label, value) in enumerate(self.allowed_values.items()):
            if value == self._value:
                self._combo_current_item = i
                break

    value = property(AbstractSaveEntry.value.fget, value_setter)

    def render_widget(self):
        if imgui.begin_combo(self.bimpy_name, self.allowed_values_list[self._combo_current_item]):
            for i, item in enumerate(self.allowed_values_list):
                is_selected = (self._combo_current_item == i)
                if imgui.selectable(item, is_selected)[0]:
                    self._combo_current_item = i
                    self._value = self.allowed_values[self.allowed_values_list[i]]
                if is_selected:
                    imgui.set_item_default_focus()
            imgui.end_combo()