"""Opt-in installed-runtime checks: mode 2 records, mode 3 launches file managers."""
import json
import os
from pathlib import Path
import traceback
from PyQt6.QtCore import Qt, QEvent, QPointF, QTimer, QModelIndex, QItemSelectionModel
from PyQt6.QtGui import QContextMenuEvent, QMouseEvent
from PyQt6.QtWidgets import QApplication, QMenu, QDialog, QAbstractItemView, QToolButton, QLineEdit, QTabWidget, QWidget
from . import controller as module


def run_admin(c):
    """Exercise native instance/theme/log routes with real external launches."""
    from PyQt6.QtCore import QPoint
    from PyQt6.QtWidgets import QAbstractButton
    results, calls, errors = [], [], []
    old_launch, old_warning = module.launch, module.QMessageBox.warning
    def record(argv):
        old_launch(argv)
        calls.append(argv)
    module.launch = record
    module.QMessageBox.warning = lambda parent, title, text: errors.append(text)

    def check(name, action):
        before, count_errors = len(calls), len(errors)
        try:
            action()
            if len(errors) != count_errors or len(calls) != before + 1:
                raise AssertionError((calls[before:], errors[count_errors:]))
            results.append({'case': name, 'ok': True, 'command': calls[-1]})
        except Exception:
            results.append({'case': name, 'ok': False, 'error': traceback.format_exc()})

    def button(dialog, name):
        widget = dialog.findChild(QAbstractButton, name)
        if widget is None or not widget.property('externalFileManager') or not widget.isEnabled():
            raise AssertionError('Native button not replaced or not enabled: ' + name)
        for tabs in dialog.findChildren(QTabWidget):
            parent = widget.parentWidget()
            while parent is not None:
                index = tabs.indexOf(parent)
                if index >= 0:
                    tabs.setCurrentIndex(index)
                    break
                parent = parent.parentWidget()
        widget.click()

    def modal(action_name, dialog_name, buttons):
        seen = []
        def inspect():
            dialog = next((w for w in QApplication.topLevelWidgets() if w.objectName() == dialog_name and w.isVisible()), None)
            if dialog is None: return
            seen.append(True)
            try:
                for name in buttons:
                    check(dialog_name + ':' + name, lambda n=name: button(dialog, n))
            finally: dialog.reject()
        QTimer.singleShot(150, inspect)
        action = c.window.findChild(module.QAction, action_name)
        if action is None: raise AssertionError('Native dialog action unavailable')
        action.trigger()
        if not seen: raise AssertionError('Native dialog not observed')

    try:
        modal('actionChange_Game', 'InstanceManagerDialog', ('exploreLocation', 'exploreBaseDirectory', 'exploreGame'))
        modal('actionSettings', 'SettingsDialog', ('exploreStyles',))
        def log_menu():
            view = c.window.findChild(QAbstractItemView, 'logList')
            view.customContextMenuRequested.emit(QPoint(3, 3))
            QApplication.processEvents()
            menu = QApplication.activePopupWidget()
            if not isinstance(menu, QMenu): raise AssertionError('No native log menu')
            try:
                matches = [a for a in menu.actions() if a.text() == c.translated('LogList', '&Open logs folder')]
                if len(matches) != 1 or not matches[0].property('externalFileManager'):
                    raise AssertionError('Native log action not replaced')
                matches[0].trigger()
            finally: menu.close()
        check('native-log-menu', log_menu)
    except Exception:
        results.append({'case': 'runner', 'ok': False, 'error': traceback.format_exc()})
    finally:
        module.launch, module.QMessageBox.warning = old_launch, old_warning
        (Path(__file__).parent / 'admin-selftest.json').write_text(json.dumps({'results': results, 'errors': errors}, indent=2), encoding='utf-8')

def run(c):
    rows, calls, warnings = ([], [], [])
    old_launch, old_warning = (module.launch, module.QMessageBox.warning)
    real_launches = os.environ.get('CRISPY_EFM_SELFTEST') == '3'
    def record_launch(argv):
        if real_launches:
            old_launch(argv)
        calls.append(argv)
    module.launch = record_launch
    module.QMessageBox.warning = lambda parent, title, text: warnings.append(text)
    tree = c.tree
    selection, current, scroll = (tree.selectionModel().selection(), tree.currentIndex(), tree.verticalScrollBar().value())
    expansions = []
    main_tabs = c.window.findChild(QTabWidget, 'tabWidget')
    saved_tab = main_tabs.currentIndex()

    def check(name, fn):
        before, errors = (len(calls), len(warnings))
        try:
            fn()
            if not len(warnings) == errors:
                raise AssertionError(warnings[errors:])
            if not len(calls) == before + 1:
                raise AssertionError(('Expected one launch', len(calls) - before))
            rows.append({'case': name, 'ok': True, 'command': calls[-1]})
        except Exception:
            rows.append({'case': name, 'ok': False, 'error': traceback.format_exc()})

    def activate_tab(widget):
        for tabs in widget.window().findChildren(QTabWidget):
            page = widget
            while page is not None:
                index = tabs.indexOf(page)
                if index >= 0:
                    tabs.setCurrentIndex(index)
                    break
                page = page.parentWidget()
        QApplication.processEvents()

    def native_menu(view, label):
        activate_tab(view)
        index = view.model().index(0, 0, view.rootIndex())
        if not index.isValid():
            raise AssertionError('View has no rows')
        view.setCurrentIndex(index)
        view.scrollTo(index)
        QApplication.processEvents()
        pos = view.visualRect(index).center()
        outcome = []

        def choose():
            menu = QApplication.activePopupWidget()
            if not isinstance(menu, QMenu):
                outcome.append('No native menu')
                return
            actions = [a for a in menu.actions() if a.text() == label]
            if len(actions) == 1 and actions[0].property('externalFileManager') and actions[0].isEnabled():
                actions[0].trigger()
                outcome.append(True)
            else:
                outcome.append([(a.text(), a.property('externalFileManager'), a.isEnabled()) for a in menu.actions()])
            menu.close()
        QTimer.singleShot(60, choose)
        QApplication.sendEvent(view.viewport(), QContextMenuEvent(QContextMenuEvent.Reason.Mouse, pos, view.viewport().mapToGlobal(pos)))
        if not outcome == [True]:
            raise AssertionError(outcome)

    def walk(parent=QModelIndex()):
        for row in range(tree.model().rowCount(parent)):
            index = tree.model().index(row, 0, parent)
            expansions.append((index, tree.isExpanded(index)))
            yield index
            yield from walk(index)

    def inspect_dialog():
        dialog = next((w for w in QApplication.topLevelWidgets() if w.objectName() == 'ModInfoDialog' and w.isVisible()), None)
        if dialog is None:
            rows.append({'case': 'mod-dialog', 'ok': False, 'error': 'No native dialog'})
            return
        try:
            files = dialog.findChild(QAbstractItemView, 'filetree')

            def root_button():
                button = dialog.findChild(QToolButton, 'openInExplorer')
                activate_tab(button)
                if not (button.property('externalFileManager') and button.isEnabled()):
                    raise AssertionError('Check failed')
                button.click()
            check('native-filetree-root-button', root_button)
            check('native-filetree-menu', lambda: native_menu(files, c.translated('FileTreeTab', 'Open in &Explorer')))
            for name in ('overwriteTree', 'overwrittenTree', 'noConflictTree', 'conflictsAdvancedList'):
                view = dialog.findChild(QAbstractItemView, name)
                if view and view.model().rowCount():
                    check('native-conflict:' + name, lambda v=view: native_menu(v, c.translated('ConflictsTab', 'Open in &Explorer')))
            button = dialog.findChild(QToolButton, 'imagesExplore')
            activate_tab(button)
            thumb = dialog.findChild(QWidget, 'imagesThumbnails')
            event = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(30, 30), QPointF(30, 30), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
            QApplication.sendEvent(thumb, event)
            QApplication.processEvents()

            def image_button():
                if not (button.property('externalFileManager') and button.isEnabled()):
                    raise AssertionError('Image button is not enabled')
                if not dialog.findChild(QLineEdit, 'imagesPath').text():
                    raise AssertionError('No image selected')
                button.click()
            check('native-images-button', image_button)
        except Exception:
            rows.append({'case': 'mod-dialog', 'ok': False, 'error': traceback.format_exc()})
        finally:
            dialog.reject()
    try:
        names = c.organizer.modList().allMods()
        wanted = os.environ.get('CRISPY_EFM_TEST_MOD', '')
        index = next((i for i in walk() if isinstance(i.data(257), int) and names[i.data(257)] == wanted), None)
        if index is None:
            raise ValueError('Set CRISPY_EFM_TEST_MOD to an existing mod with images and conflicts.')
        tree.setCurrentIndex(index)
        tree.scrollTo(index)
        QTimer.singleShot(400, inspect_dialog)
        tree.doubleClicked.emit(index)
        for name, context, label in [('downloadView', 'DownloadListView', 'Reveal in Explorer'), ('savegameList', 'SavesTab', 'Open in Explorer...'), ('dataTree', 'FileTree', 'Reveal in E&xplorer')]:
            view = c.window.findChild(QAbstractItemView, name)
            activate_tab(view)
            if name == 'dataTree':

                def find_file(parent=QModelIndex(), depth=0):
                    if depth > 8:
                        return None
                    model = view.model()
                    if model.canFetchMore(parent):
                        model.fetchMore(parent)
                    for r in range(model.rowCount(parent)):
                        item = model.index(r, 0, parent)
                        tip = str(item.data(Qt.ItemDataRole.ToolTipRole) or '')
                        if '<b>' + c.translated('FileTreeModel', 'Real path') + ':</b>' in tip:
                            return item
                        found = find_file(item, depth + 1) if model.hasChildren(item) else None
                        if found is not None:
                            return found
                    return None
                item = find_file()
                if item is not None:
                    old_root = view.rootIndex()
                    view.setRootIndex(item.parent())
                    check('native-data-reveal', lambda: native_menu(view, c.translated(context, label)))
                    view.setRootIndex(old_root)
                else:
                    rows.append({'case': 'native-data-reveal', 'ok': None, 'error': 'No loose file found'})
            elif view.model().rowCount():
                check('native:' + name, lambda v=view, x=context, y=label: native_menu(v, c.translated(x, y)))
            else:
                rows.append({'case': 'native:' + name, 'ok': None, 'error': 'No existing rows'})
    except Exception:
        rows.append({'case': 'runner', 'ok': False, 'error': traceback.format_exc()})
    finally:
        module.launch, module.QMessageBox.warning = (old_launch, old_warning)
        main_tabs.setCurrentIndex(saved_tab)
        tree.selectionModel().select(selection, QItemSelectionModel.SelectionFlag.ClearAndSelect)
        tree.selectionModel().setCurrentIndex(current, QItemSelectionModel.SelectionFlag.NoUpdate)
        for index, expanded in expansions:
            tree.setExpanded(index, expanded)
        tree.verticalScrollBar().setValue(scroll)
        (Path(__file__).parent / 'extended-selftest.json').write_text(json.dumps({'real_launches': real_launches, 'results': rows, 'warnings': warnings}, indent=2), encoding='utf-8')

