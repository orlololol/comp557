from PyQt5 import QtWidgets

class ControlPanel(QtWidgets.QScrollArea):
    """Scrollable right-hand panel that binds spinboxes/checkboxes/combos to arbitrary target objects."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self._body = QtWidgets.QWidget()
        self._form = QtWidgets.QFormLayout(self._body)
        self.setWidget(self._body)

    def add_double(self, label, target, attr, min_val, max_val, step=0.01, on_change=None):
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setDecimals(4)
        spin.setSingleStep(step)
        spin.setValue(getattr(target, attr))
        def apply(val):
            setattr(target, attr, val)
            if on_change: on_change()
        spin.valueChanged.connect(apply)
        self._form.addRow(label, spin)
        return spin

    def add_int(self, label, target, attr, min_val, max_val, on_change=None):
        spin = QtWidgets.QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(getattr(target, attr))
        def apply(val):
            setattr(target, attr, val)
            if on_change: on_change()
        spin.valueChanged.connect(apply)
        self._form.addRow(label, spin)
        return spin

    def add_bool(self, label, target, attr, on_change=None):
        chk = QtWidgets.QCheckBox(label)
        chk.setChecked(getattr(target, attr))
        def apply(val):
            setattr(target, attr, val)
            if on_change: on_change()
        chk.toggled.connect(apply)
        self._form.addRow(chk)
        return chk

    def add_choice(self, label, target, attr, items, on_change=None):
        combo = QtWidgets.QComboBox()
        combo.addItems(items)
        combo.setCurrentIndex(getattr(target, attr))
        def apply(idx):
            setattr(target, attr, idx)
            if on_change: on_change()
        combo.currentIndexChanged.connect(apply)
        self._form.addRow(label, combo)
        return combo

    def add_group(self, title):
        group = QtWidgets.QGroupBox(title)
        layout = QtWidgets.QFormLayout(group)
        self._form.addRow(group)
        return layout  # caller can addRow(...) directly for nested controls

    def add_button(self, label, callback):
        btn = QtWidgets.QPushButton(label)
        btn.clicked.connect(callback)
        self._form.addRow(btn)


    def add_radio_group(self, title, target, attr, options, on_change=None):
        """ options: List of (label_text, value) tuples """
        group_box = QtWidgets.QGroupBox(title)
        layout = QtWidgets.QVBoxLayout(group_box)
        button_group = QtWidgets.QButtonGroup(group_box)
        current_val = getattr(target, attr)
        for i, (label, val) in enumerate(options):
            btn = QtWidgets.QRadioButton(label)
            btn.setProperty("group_value", val)
            if val == current_val:
                btn.setChecked(True)
            button_group.addButton(btn, i)
            layout.addWidget(btn)

        def apply(btn):
            setattr(target, attr, btn.property("group_value"))
            if on_change: on_change()

        button_group.buttonClicked.connect(apply)
        group_box._bg = button_group  # Prevent garbage collection
        self._form.addRow(group_box)
        return group_box