"""Opt-in live Qt regression checks; set CRISPY_EFM_SELFTEST=1 before starting MO2.

No mods are modified. External launches are recorded instead of executed.
The test restores the selection and scroll position and writes a local report.
"""
import json
from pathlib import Path
import traceback

from PyQt6.QtCore import Qt, QItemSelectionModel, QEvent, QPointF
from PyQt6.QtGui import QContextMenuEvent, QMouseEvent, QKeyEvent
from PyQt6.QtCore import QTimer, QCoreApplication
from PyQt6.QtWidgets import QApplication, QMenu
from . import controller as module


def run(c):
    tree = c.tree
    results = []
    calls = []
    errors = []
    original_launch = module.launch
    original_open = c.open
    saved_selection = tree.selectionModel().selection()
    saved_current = tree.currentIndex()
    saved_scroll = tree.verticalScrollBar().value()
    original_shortcut = c.setting
    original_shortcuts = list(c.shortcuts)
    module.launch = lambda argv: calls.append(argv)

    # Do not let an error dialog stall unattended developer checks.
    original_warning = module.QMessageBox.warning
    module.QMessageBox.warning = lambda parent, title, text: errors.append(text)

    def check(name, fn):
        before, error_count = len(calls), len(errors)
        try:
            detail = fn()
            results.append({'case': name, 'ok': len(errors) == error_count,
                            'launches': len(calls) - before, 'detail': detail,
                            'errors': errors[error_count:]})
        except Exception:
            results.append({'case': name, 'ok': False, 'error': traceback.format_exc()})

    def indexes(parent=None):
        from PyQt6.QtCore import QModelIndex
        parent = parent or QModelIndex()
        for row in range(tree.model().rowCount(parent)):
            index = tree.model().index(row, 0, parent)
            yield index
            yield from indexes(index)

    names = c.organizer.modList().allMods()
    info_rows = []
    for index in indexes():
        identity = index.data(257)
        if isinstance(identity, int) and 0 <= identity < len(names):
            info = c.organizer.modList().getMod(names[identity])
            if info: info_rows.append((index, info))
    regular = [i for i, info in info_rows if not (info.isSeparator() or info.isForeign() or info.isOverwrite() or info.isBackup())]
    overwrite = [i for i, info in info_rows if info.isOverwrite()]
    backups = [i for i, info in info_rows if info.isBackup()]

    def select(rows):
        tree.selectionModel().clearSelection()
        for index in rows:
            tree.selectionModel().select(index, QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
        tree.selectionModel().setCurrentIndex(rows[0], QItemSelectionModel.SelectionFlag.NoUpdate)

    def context(rows):
        before = len(calls)
        select(rows)
        index = rows[0]
        tree.scrollTo(index)
        position = tree.visualRect(index).center()
        captured = []
        def activate():
            menu = QApplication.activePopupWidget()
            if not isinstance(menu, QMenu):
                captured.append('No active native context menu')
                return
            matching = [a for a in menu.actions() if a.text() == c.translated('ModListContextMenu', 'Open in Explorer')]
            if len(matching) == 1 and matching[0].property('externalFileManager'):
                matching[0].trigger()
                captured.append('Native context menu action replaced')
            else:
                captured.append('FAIL: native action was not replaced; deliberately not triggered')
            menu.close()
        QTimer.singleShot(80, activate)
        event = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, position, tree.viewport().mapToGlobal(position))
        QApplication.sendEvent(tree.viewport(), event)
        assert captured and captured[0] == 'Native context menu action replaced', captured
        expected = len({str(Path(p)).lower() for p in c.paths(rows)})
        assert len(calls) - before == expected, (len(calls) - before, expected)
        return expected

    try:
        menu = c.button.menu()
        menu.show()
        QCoreApplication.processEvents()
        menu.hide()
        for action in menu.actions():
            if action.isSeparator(): continue
            def trigger(a=action):
                assert a.property('externalFileManager'), a.text()
                a.trigger()
                return a.text()
            check('toolbar:' + action.text(), trigger)

        if regular:
            check('native-context-regular', lambda: context(regular[:1]))
            if len(regular) >= 2: check('native-context-multiselection', lambda: context(regular[:2]))
            select(regular[:1])
            tree.scrollTo(regular[0])
            def double_click():
                before = len(calls)
                position = QPointF(tree.visualRect(regular[0]).center())
                event = QMouseEvent(QEvent.Type.MouseButtonDblClick, position, position,
                                    Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                                    Qt.KeyboardModifier.ControlModifier)
                QApplication.sendEvent(tree.viewport(), event)
                assert len(calls) - before == 1
            check('ctrl-double-click', double_click)
            def ctrl_enter():
                before = len(calls)
                event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
                QApplication.sendEvent(tree, event)
                assert len(calls) - before == 1
            check('ctrl-enter', ctrl_enter)
            def shortcut():
                c.setting = lambda key: 'Alt+Shift+O' if key == 'shortcut' else original_shortcut(key)
                c.configure_shortcut()
                # QAction activation is deterministic even when another desktop app has focus.
                assert c.shortcuts[-1].shortcut().toString() == 'Alt+Shift+O'
                before = len(calls)
                c.shortcuts[-1].trigger()
                assert len(calls) - before == 1
            check('configurable-shortcut-action', shortcut)
        if overwrite: check('native-context-overwrite', lambda: context(overwrite[:1]))
        if backups: check('native-context-backup', lambda: context(backups[:1]))
        else: results.append({'case': 'native-context-backup', 'ok': None, 'detail': 'No existing backup mod; no fixture added to user instance.'})
    finally:
        module.launch = original_launch
        module.QMessageBox.warning = original_warning
        c.setting = original_shortcut
        for action in c.shortcuts[len(original_shortcuts):]:
            tree.removeAction(action)
            action.deleteLater()
        c.shortcuts = original_shortcuts
        tree.selectionModel().select(saved_selection, QItemSelectionModel.SelectionFlag.ClearAndSelect)
        tree.selectionModel().setCurrentIndex(saved_current, QItemSelectionModel.SelectionFlag.NoUpdate)
        tree.verticalScrollBar().setValue(saved_scroll)
        report = {'runtime': 'Installed MO2 / embedded Python / PyQt6', 'results': results,
                  'captured_commands': calls, 'external_processes_started_by_test': 0}
        (Path(__file__).parent / 'live-selftest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
