import importlib.util
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
root = Path(__file__).resolve().parents[1]
package = types.ModuleType('ExternalFileManager')
package.__path__ = [str(root / 'ExternalFileManager')]
sys.modules['ExternalFileManager'] = package

from PyQt6.QtCore import Qt, QPoint, QEvent
from PyQt6.QtGui import QAction, QStandardItemModel, QStandardItem
from PyQt6.QtWidgets import QApplication, QMainWindow, QTreeView, QToolButton, QMenu
from PyQt6.QtTest import QTest
from ExternalFileManager.controller import Controller, FOLDERS
from ExternalFileManager.launcher import command

app = QApplication.instance() or QApplication([])


class Info:
    def __init__(self, path, kind='regular'): self.path, self.kind = path, kind
    def absolutePath(self): return self.path
    def isForeign(self): return self.kind == 'foreign'
    def isSeparator(self): return self.kind == 'separator'


class Mods:
    def __init__(self, infos): self.infos = infos
    def allMods(self): return list(self.infos)
    def getMod(self, name): return self.infos[name]


class Interception(unittest.TestCase):
    def setUp(self):
        self.window = QMainWindow()
        self.tree = QTreeView(self.window)
        self.tree.setObjectName('modList')
        self.window.setCentralWidget(self.tree)
        self.model = QStandardItemModel()
        for i, label in enumerate(('normal', 'backup', 'Overwrite', 'separator', 'foreign')):
            item = QStandardItem(label)
            item.setData(i, 257)
            self.model.appendRow(item)
        self.tree.setModel(self.model)
        self.tree.setSelectionMode(QTreeView.SelectionMode.ExtendedSelection)
        self.button = QToolButton(self.window)
        self.button.setObjectName('openFolderMenu')
        self.menu = QMenu(self.window)
        self.button.setMenu(self.menu)
        self.native = []
        for text, key in FOLDERS:
            action = self.menu.addAction(text)
            action.triggered.connect(lambda checked=False, k=key: self.native.append(k))
        infos = {name: Info(str(root), name if name in ('separator','foreign') else 'regular')
                 for name in ('normal', 'backup', 'Overwrite', 'separator', 'foreign')}
        self.org = types.SimpleNamespace(modList=lambda: Mods(infos))
        settings = {'shortcut': 'Alt+O', 'manager': 'custom', 'executable': sys.executable,
                    'arguments': '["{path}"]'}
        self.c = Controller(self.org, self.window, settings.get)
        self.window.show()
        app.processEvents()

    def tearDown(self):
        app.removeEventFilter(self.c)
        self.window.close()
        self.window.deleteLater()
        app.processEvents()

    def test_toolbar_replaces_each_original_and_is_idempotent(self):
        with patch.object(self.c, 'open') as opened:
            self.menu.show()
            app.processEvents()
            self.c.patch_menu(self.menu)
            self.assertEqual(len(self.menu.actions()), len(FOLDERS))
            for action in self.menu.actions(): action.trigger()
            self.assertEqual(opened.call_count, len(FOLDERS))
            self.assertEqual(self.native, [])

    def test_context_native_handler_never_runs(self):
        self.tree.setCurrentIndex(self.model.index(1, 0))
        menu = QMenu(self.tree)
        old = menu.addAction('Open in Explorer')
        old.triggered.connect(lambda: self.native.append('context'))
        with patch.object(self.c, 'open') as opened:
            menu.show()
            app.processEvents()
            self.assertNotIn(old, menu.actions())
            menu.actions()[0].trigger()
            opened.assert_called_once()
            self.assertEqual(opened.call_args.args[0](), [str(root)])
        self.assertEqual(self.native, [])
        menu.close()

    def test_unrelated_menu_unchanged(self):
        menu = QMenu(self.window)
        old = menu.addAction('Open in Explorer')
        self.c.patch_menu(menu)
        self.assertIs(menu.actions()[0], old)

    def test_ctrl_double_click_consumes_before_native_signal(self):
        index = self.model.index(0, 0)
        native_double = []
        self.tree.doubleClicked.connect(lambda _: native_double.append(True))
        with patch.object(self.c, 'open') as opened:
            QTest.mouseDClick(self.tree.viewport(), Qt.MouseButton.LeftButton,
                             Qt.KeyboardModifier.ControlModifier,
                             self.tree.visualRect(index).center())
            opened.assert_called_once()
        self.assertEqual(native_double, [])

    def test_ctrl_enter_and_custom_shortcut_once(self):
        self.tree.setCurrentIndex(self.model.index(0, 0))
        self.tree.setFocus()
        app.processEvents()
        with patch.object(self.c, 'open') as opened:
            QTest.keyClick(self.tree, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
            self.assertEqual(opened.call_count, 1)
            QTest.keyClick(self.tree, Qt.Key.Key_O, Qt.KeyboardModifier.AltModifier)
            self.assertEqual(opened.call_count, 2)

    def test_backups_overwrite_and_separator(self):
        indexes = [self.model.index(i, 0) for i in range(5)]
        self.assertEqual(len(self.c.paths(indexes)), 3)
        self.assertEqual(len(self.c.paths(indexes, allow_foreign=True)), 4)

    def test_unique_paths_launch_once_with_no_shell(self):
        with patch('ExternalFileManager.controller.launch') as launched:
            self.c.open(lambda: [str(root), str(root)], 'test')
            launched.assert_called_once()

    def test_missing_path_and_bad_config_do_not_launch(self):
        with patch('ExternalFileManager.controller.launch') as launched, patch('ExternalFileManager.controller.QMessageBox.warning'):
            self.c.open(lambda: [str(root / 'missing-test-folder')], 'test')
            launched.assert_not_called()

    def test_spaces_unicode_and_arguments_are_separate(self):
        argv = command(sys.executable, '["-o", "{path}", "-newtab"]', 'C:\\Mods\\ü & space')
        self.assertEqual(argv[1:], ['-o', 'C:\\Mods\\ü & space', '-newtab'])
        with self.assertRaises(ValueError): command(sys.executable, '["no-placeholder"]', 'C:\\Mods')


if __name__ == '__main__': unittest.main(verbosity=2)
