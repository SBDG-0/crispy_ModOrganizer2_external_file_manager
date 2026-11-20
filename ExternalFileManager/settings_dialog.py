from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QLabel,
    QCheckBox, QComboBox, QLineEdit, QPushButton, QFileDialog, QDialogButtonBox, QMessageBox)
from PyQt6.QtGui import QKeySequence
from .launcher import command, registered_onecommander


class SettingsDialog(QDialog):
    def __init__(self, plugin):
        super().__init__(plugin.parent)
        self.plugin = plugin
        self.setWindowTitle('External File Manager')
        self.setMinimumWidth(640)
        layout = QVBoxLayout(self)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        form = QFormLayout()
        layout.addLayout(form)
        self.enabled = QCheckBox('Redirect MO2 folder commands (restart after changing)')
        self.enabled.setChecked(bool(plugin.setting('enabled')))
        form.addRow(self.enabled)
        self.manager = QComboBox()
        for label, value in [('Automatic — registered OneCommander', 'auto'),
                             ('OneCommander — explicit executable', 'onecommander'),
                             ('Other file manager — custom arguments', 'custom')]:
            self.manager.addItem(label, value)
        self.manager.setCurrentIndex(max(0, self.manager.findData(plugin.setting('manager'))))
        form.addRow('File manager', self.manager)
        row = QHBoxLayout()
        self.executable = QLineEdit(str(plugin.setting('executable')))
        self.executable.setObjectName('executable')
        browse = QPushButton('Browse…')
        browse.clicked.connect(self.browse)
        row.addWidget(self.executable)
        row.addWidget(browse)
        form.addRow('Executable', row)
        self.arguments = QLineEdit(str(plugin.setting('arguments')))
        self.arguments.setObjectName('arguments')
        form.addRow('Custom arguments (JSON)', self.arguments)
        self.shortcut = QLineEdit(str(plugin.setting('shortcut')))
        self.shortcut.setPlaceholderText('Optional, for example Alt+O')
        form.addRow('Mod-list shortcut', self.shortcut)
        self.manager.currentIndexChanged.connect(self.update_mode)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.update_mode()
        self.refresh_status()

    def update_mode(self): self.arguments.setEnabled(self.manager.currentData() == 'custom')

    def refresh_status(self):
        c = self.plugin.controller
        self.status.setText('Opens supported MO2 folder commands directly in your external file manager.\n'
            f'Mod list: {"attached" if c and c.tree else "not attached"} · '
            f'Folder menu: {"attached" if c and c.button else "not attached"}')

    def browse(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Choose a file manager', self.executable.text(), 'Applications (*.exe)')
        if filename: self.executable.setText(filename)

    def values(self):
        return {'enabled': self.enabled.isChecked(), 'manager': self.manager.currentData(),
                'executable': self.executable.text().strip().strip('"'),
                'arguments': self.arguments.text().strip(), 'shortcut': self.shortcut.text().strip()}

    def save(self):
        values = self.values()
        try:
            if values['enabled']:
                exe = registered_onecommander() if values['manager'] == 'auto' else ''
                exe = exe or values['executable']
                args = values['arguments'] if values['manager'] == 'custom' else '["-o", "{path}", "-newtab"]'
                command(exe, args, str(Path.home()))
            if values['shortcut']:
                sequence = QKeySequence(values['shortcut'])
                if sequence.isEmpty() or sequence.count() != 1 or sequence[0].key() in (0, Qt.Key.Key_unknown):
                    raise ValueError('Enter a valid single shortcut, for example Alt+O.')
            old = {key: self.plugin.setting(key) for key in values}
            try:
                for key, value in values.items():
                    self.plugin.organizer.setPluginSetting(self.plugin.name(), key, value)
            except Exception:
                for key, value in old.items():
                    self.plugin.organizer.setPluginSetting(self.plugin.name(), key, value)
                raise
            if self.plugin.controller: self.plugin.controller.configure_shortcut()
            if values['enabled'] != old['enabled']:
                QMessageBox.information(self, 'Restart MO2', 'The enable/disable change takes effect after restarting MO2.')
            self.accept()
        except Exception as error:
            QMessageBox.warning(self, 'External File Manager', str(error))
