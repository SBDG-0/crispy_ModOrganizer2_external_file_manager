import json
from pathlib import Path
import tempfile
import time
import types
import unittest
from unittest.mock import patch
import test_interception as base
app = base.app
from PyQt6.QtCore import Qt, QDir
from PyQt6.QtGui import QFileSystemModel, QStandardItemModel, QStandardItem, QAction
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QToolButton, QLineEdit, QTreeView, QMenu, QWidget, QPushButton, QLabel
from ExternalFileManager.extended import containing_folder, under
from ExternalFileManager.settings_dialog import SettingsDialog


class ExtendedTests(unittest.TestCase):
    def setUp(self):
        base.Interception.setUp(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'textures').mkdir()
        self.file = self.root / 'textures' / 'é & image.png'
        self.file.write_bytes(b'test')
        self.dialog = QDialog(self.window)
        self.dialog.setObjectName('ModInfoDialog')
        self.layout = QVBoxLayout(self.dialog)
        self.files = QTreeView(self.dialog)
        self.files.setObjectName('filetree')
        self.fs = QFileSystemModel(self.files)
        self.fs.setRootPath(str(self.root))
        self.files.setModel(self.fs)
        self.files.setRootIndex(self.fs.index(str(self.root)))
        self.layout.addWidget(self.files)

    def tearDown(self):
        self.dialog.close()
        self.dialog.deleteLater()
        app.processEvents()
        base.Interception.tearDown(self)
        self.tmp.cleanup()

    def view(self, name, cells, tooltip=None):
        view = QTreeView(self.dialog)
        view.setObjectName(name)
        model = QStandardItemModel(view)
        items = [QStandardItem(cell) for cell in cells]
        if tooltip: items[0].setToolTip(tooltip)
        model.appendRow(items)
        view.setModel(model)
        view.setCurrentIndex(model.index(0, 0))
        return view

    def trigger_menu(self, view, label, expected, parentless=False):
        menu = QMenu(None if parentless else view)
        native = []
        original = menu.addAction(label)
        original.triggered.connect(lambda: native.append(True))
        self.c.extended.observe_context(view)
        with patch.object(self.c, 'open') as opened:
            menu.show()
            app.processEvents()
            self.assertNotIn(original, menu.actions())
            menu.actions()[0].trigger()
            opened.assert_called_once()
            self.assertEqual([Path(p) for p in opened.call_args.args[0]()], [Path(p) for p in expected])
        self.assertEqual(native, [])
        menu.close()

    def test_filetree_context_file_and_root(self):
        self.files.setCurrentIndex(self.fs.index(str(self.file)))
        self.trigger_menu(self.files, 'Open in &Explorer', [str(self.file.parent)])
        self.files.clearSelection()
        self.trigger_menu(self.files, 'Open in &Explorer', [str(self.root)])

    def test_all_conflict_models_and_parentless_menus(self):
        for name in ('overwriteTree', 'overwrittenTree', 'noConflictTree', 'conflictsAdvancedList'):
            cells = ['/textures/é & image.png']
            if name == 'conflictsAdvancedList': cells.insert(0, 'other mod')
            view = self.view(name, cells)
            self.trigger_menu(view, 'Open in &Explorer', [str(self.file.parent)], True)

    def test_data_reveal_parses_escaped_real_path(self):
        import html
        tip = '<p><b>Real path:</b> ' + html.escape(str(self.file)) + '</p>'
        view = self.view('dataTree', ['image.png'], tip)
        self.trigger_menu(view, 'Reveal in E&xplorer', [str(self.file.parent)], True)

    def test_downloads_reveal_uses_configured_folder(self):
        self.org.downloadsPath = lambda: str(self.root)
        self.trigger_menu(self.view('downloadView', ['friendly metadata title']), 'Reveal in Explorer', [str(self.root)])

    def test_saves_global(self):
        self.org.profile = lambda: types.SimpleNamespace(localSavesEnabled=lambda: False)
        self.org.managedGame = lambda: types.SimpleNamespace(savesDirectory=lambda: QDir(str(self.root)), iniFiles=lambda: [])
        view = self.view('savegameList', ['friendly name', 'textures/é & image.png'])
        self.trigger_menu(view, 'Open in Explorer...', [str(self.file.parent)], True)

    def test_saves_profile_local(self):
        folder = self.root / 'saves'
        folder.mkdir()
        (folder / 'test.sav').write_bytes(b'test')
        self.org.profile = lambda: types.SimpleNamespace(localSavesEnabled=lambda: True, absolutePath=lambda: str(self.root))
        self.org.managedGame = lambda: types.SimpleNamespace()
        self.trigger_menu(self.view('savegameList', ['friendly', 'test.sav']), 'Open in Explorer...', [str(folder)], True)

    def test_saves_ini_override(self):
        ini = self.root / 'game.ini'
        ini.write_text('[General]\nSLocalSavePath=textures\n')
        self.org.profile = lambda: types.SimpleNamespace(localSavesEnabled=lambda: False, absoluteIniFilePath=lambda _: str(ini))
        self.org.managedGame = lambda: types.SimpleNamespace(savesDirectory=lambda: QDir(str(self.root)),
            iniFiles=lambda: ['game.ini'], documentsDirectory=lambda: QDir(str(self.root)))
        self.trigger_menu(self.view('savegameList', ['friendly', self.file.name]), 'Open in Explorer...', [str(self.file.parent)], True)

    def test_buttons_are_replaced_and_enabled_state_stays_synced(self):
        native = []
        image_path = QLineEdit(str(self.file), self.dialog)
        image_path.setObjectName('imagesPath')
        self.layout.addWidget(image_path)
        originals = []
        for name in ('imagesExplore', 'openInExplorer'):
            button = QToolButton(self.dialog)
            button.setObjectName(name)
            button.clicked.connect(lambda: native.append(True))
            self.layout.addWidget(button)
            originals.append(button)
        self.dialog.show()
        app.processEvents()
        with patch.object(self.c, 'open') as opened:
            for name in ('imagesExplore', 'openInExplorer'):
                button = self.dialog.findChild(QToolButton, name)
                self.assertTrue(button.property('externalFileManager'))
                button.click()
            self.assertEqual(opened.call_count, 2)
        self.assertEqual(native, [])
        originals[0].setEnabled(False)
        self.assertFalse(self.dialog.findChild(QToolButton, 'imagesExplore').isEnabled())
        originals[0].setEnabled(True)
        self.assertTrue(self.dialog.findChild(QToolButton, 'imagesExplore').isEnabled())

    def test_path_escape_rejected(self):
        with self.assertRaises(ValueError): under(str(self.root), '../other')
        with self.assertRaises(ValueError): containing_folder(self.root / 'missing')

    def test_instance_buttons_follow_selected_instance_fields(self):
        dialog = QDialog(self.window)
        dialog.setObjectName('InstanceManagerDialog')
        layout = QVBoxLayout(dialog)
        native = []
        for name, field in (('exploreLocation', 'location'), ('exploreBaseDirectory', 'baseDirectory'), ('exploreGame', 'gameDir')):
            edit = QLineEdit(str(self.root), dialog)
            edit.setObjectName(field)
            layout.addWidget(edit)
            button = QPushButton('Explore', dialog)
            button.setObjectName(name)
            button.clicked.connect(lambda: native.append(True))
            layout.addWidget(button)
        dialog.show()
        app.processEvents()
        with patch.object(self.c, 'open') as opened:
            for name, field in (('exploreLocation', 'location'), ('exploreBaseDirectory', 'baseDirectory'), ('exploreGame', 'gameDir')):
                # MO2 updates these fields when the selected instance changes.
                dialog.findChild(QLineEdit, field).setText(str(self.file.parent))
                replacement = dialog.findChild(QPushButton, name)
                self.assertTrue(replacement.property('externalFileManager'))
                replacement.click()
                self.assertEqual(opened.call_args.args[0](), str(self.file.parent))
            self.assertEqual(opened.call_count, 3)
        self.assertEqual(native, [])
        dialog.close()
        dialog.deleteLater()

    def test_theme_explore_replaces_native_button(self):
        dialog = QDialog(self.window)
        dialog.setObjectName('SettingsDialog')
        layout = QVBoxLayout(dialog)
        button = QPushButton('Explore...', dialog)
        button.setObjectName('exploreStyles')
        native = []
        button.clicked.connect(lambda: native.append(True))
        layout.addWidget(button)
        dialog.show()
        app.processEvents()
        with patch.object(self.c, 'open') as opened, patch.object(self.c, 'folder', return_value=str(self.root)):
            replacement = dialog.findChild(QPushButton, 'exploreStyles')
            self.assertTrue(replacement.property('externalFileManager'))
            replacement.click()
            self.assertEqual(opened.call_args.args[0](), str(self.root))
            opened.assert_called_once()
        self.assertEqual(native, [])
        dialog.close()
        dialog.deleteLater()

    def test_log_menu_replaces_native_action(self):
        with patch.object(self.c, 'folder', return_value=str(self.root)):
            self.trigger_menu(self.view('logList', ['entry']), '&Open logs folder', str(self.root))

    def test_settings_window_keeps_only_short_status(self):
        values = {'enabled': True, 'manager': 'auto', 'executable': '', 'arguments': '["{path}"]', 'shortcut': ''}
        plugin = types.SimpleNamespace(parent=self.window, controller=self.c, setting=values.get)
        dialog = SettingsDialog(plugin)
        labels = '\n'.join(label.text() for label in dialog.findChildren(QLabel))
        self.assertIn('Mod list:', labels)
        for removed in ('Also covers', 'Errors are reported', 'OneCommander opens', 'Reveal commands', 'Custom arguments are', 'Settings also remain'):
            self.assertNotIn(removed, labels)

    def test_text_ini_editor_action_is_replaced(self):
        toolbar = QWidget(self.dialog)
        layout = QVBoxLayout(toolbar)
        path = QLineEdit(str(self.file), toolbar)
        button = QToolButton(toolbar)
        old = QAction('&Open in Explorer', toolbar)
        native = []
        old.triggered.connect(lambda: native.append(True))
        button.setDefaultAction(old)
        layout.addWidget(button)
        layout.addWidget(path)
        self.layout.addWidget(toolbar)
        self.dialog.show()
        app.processEvents()
        with patch.object(self.c, 'open') as opened:
            button.click()
            opened.assert_called_once()
            self.assertEqual(Path(opened.call_args.args[0]()), self.file.parent)
        self.assertEqual(native, [])
        old.setEnabled(False)
        self.assertFalse(button.isEnabled())

    def test_failed_settings_validation_does_not_save(self):
        saved = {'enabled': True, 'manager': 'custom', 'executable': '',
                 'arguments': '["{path}"]', 'shortcut': ''}
        writes = []
        self.org.setPluginSetting = lambda *args: writes.append(args)
        plugin = types.SimpleNamespace(parent=self.window, controller=self.c, organizer=self.org,
                                       name=lambda: 'ExternalFileManager', setting=saved.get)
        dialog = SettingsDialog(plugin)
        with patch('ExternalFileManager.settings_dialog.QMessageBox.warning') as warning:
            dialog.save()
            warning.assert_called_once()
        self.assertEqual(writes, [])

    def test_unrecognized_view_keeps_native_action(self):
        view = self.view('thirdPartyView', ['x'])
        menu = QMenu(view)
        original = menu.addAction('Open in &Explorer')
        self.c.extended.patch_menu(menu)
        self.assertIs(menu.actions()[0], original)

    def test_settings_save_and_cancel(self):
        saved = {'enabled': True, 'manager': 'custom', 'executable': __import__('sys').executable,
                 'arguments': '["{path}"]', 'shortcut': ''}
        self.org.setPluginSetting = lambda plugin, key, value: saved.__setitem__(key, value)
        plugin = types.SimpleNamespace(parent=self.window, controller=self.c, organizer=self.org,
                                       name=lambda: 'ExternalFileManager', setting=saved.get)
        self.c.setting = saved.get
        dialog = SettingsDialog(plugin)
        dialog.shortcut.setText('Alt+O')
        dialog.save()
        self.assertEqual(saved['shortcut'], 'Alt+O')
        self.assertEqual(len(self.c.shortcuts), 1)
        cancel = SettingsDialog(plugin)
        cancel.shortcut.setText('Alt+P')
        cancel.reject()
        self.assertEqual(saved['shortcut'], 'Alt+O')


if __name__ == '__main__': unittest.main()

