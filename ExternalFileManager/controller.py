import logging
import os
from pathlib import Path
from PyQt6 import sip

from PyQt6.QtCore import QObject, QEvent, Qt, QCoreApplication
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QApplication, QMenu, QWidget, QTreeView, QMessageBox

from .launcher import command, launch, registered_onecommander
from .extended import Extended

LOG = logging.getLogger('ExternalFileManager')
FOLDERS = (
    ('Open Game folder', 'game'), ('Open MyGames folder', 'documents'),
    ('Open INIs folder', 'inis'), ('Open Instance folder', 'instance'),
    ('Open Mods folder', 'mods'), ('Open Profile folder', 'profile'),
    ('Open Downloads folder', 'downloads'), ('Open MO2 Install folder', 'install'),
    ('Open MO2 Plugins folder', 'plugins'), ('Open MO2 Stylesheets folder', 'stylesheets'),
    ('Open MO2 Logs folder', 'logs'),
)


class Controller(QObject):
    def __init__(self, organizer, window, setting):
        super().__init__(window)
        self.organizer, self.window, self.setting = organizer, window, setting
        self.tree = window.findChild(QTreeView, 'modList')
        self.button = window.findChild(QWidget, 'openFolderMenu')
        self.context_index = None
        self.shortcuts = []
        self.extended = Extended(self)
        QApplication.instance().installEventFilter(self)
        self.configure_shortcut()
        LOG.info('External File Manager attached: modList=%s folderButton=%s', bool(self.tree), bool(self.button))

    def translated(self, context, text):
        return QCoreApplication.translate(context, text)

    def folder(self, key):
        app = QApplication.instance()
        install = Path(QCoreApplication.applicationDirPath())
        instance = app.property('dataPath')
        org = self.organizer
        if key == 'game': return org.managedGame().gameDirectory().absolutePath()
        if key == 'documents': return org.managedGame().documentsDirectory().absolutePath()
        if key == 'inis':
            return org.profile().absolutePath() if org.profile().localSettingsEnabled() else self.folder('documents')
        if key == 'instance':
            if not instance: raise ValueError('MO2 did not expose its instance dataPath.')
            return str(instance)
        if key == 'mods': return org.modsPath()
        if key == 'profile': return org.profile().absolutePath()
        if key == 'downloads': return org.downloadsPath()
        if key == 'install': return str(install)
        if key in ('plugins', 'stylesheets'): return str(install / key)
        if key == 'logs': return str(Path(self.folder('instance')) / 'logs')
        raise ValueError(f'Unknown folder: {key}')

    def paths(self, indexes, allow_foreign=False):
        mods = self.organizer.modList()
        names = mods.allMods()
        result = []
        for index in indexes:
            if not index.isValid(): continue
            identity = index.data(int(Qt.ItemDataRole.UserRole) + 1)
            if not isinstance(identity, int) or not 0 <= identity < len(names):
                raise ValueError('Cannot resolve this mod row safely.')
            info = mods.getMod(names[identity])
            if info is None: raise ValueError('The selected mod is no longer available.')
            if info.isSeparator() or (info.isForeign() and not allow_foreign): continue
            result.append(info.absolutePath())
        return result

    def selected(self):
        rows = self.tree.selectionModel().selectedRows()
        if not rows and self.context_index is not None and self.context_index.isValid():
            rows = [self.context_index]
        return self.paths(rows)

    def open(self, resolver, reason):
        try:
            paths = resolver()
            if isinstance(paths, str): paths = [paths]
            unique = []
            seen = set()
            for path in paths:
                normalized = os.path.normpath(str(path))
                if not Path(normalized).is_dir(): raise ValueError(f'Folder does not exist:\n{normalized}')
                key = os.path.normcase(normalized)
                if key not in seen:
                    seen.add(key)
                    unique.append(normalized)
            if not unique: return
            mode = self.setting('manager')
            exe = str(self.setting('executable') or '')
            if mode == 'auto': exe = registered_onecommander() or exe
            if mode not in ('auto', 'onecommander', 'custom'):
                raise ValueError('Manager must be auto, onecommander, or custom.')
            args = str(self.setting('arguments')) if mode == 'custom' else '["-o", "{path}", "-newtab"]'
            commands = [command(exe, args, path) for path in unique]
            for argv in commands:
                launch(argv)
                LOG.info('External File Manager launched (%s): %r', reason, argv)
        except Exception as error:
            LOG.exception('External File Manager could not open folder (%s)', reason)
            QMessageBox.warning(self.window, 'External File Manager', str(error))

    def replace(self, menu, old, resolver, reason):
        replacement = QAction(old.icon(), old.text(), menu)
        replacement.setEnabled(old.isEnabled())
        replacement.setVisible(old.isVisible())
        replacement.setToolTip('Open directly in your configured external file manager')
        replacement.setProperty('externalFileManager', True)
        replacement.triggered.connect(lambda checked=False: self.open(resolver, reason))
        menu.insertAction(old, replacement)
        menu.removeAction(old)
        # Leave the native object and its C++ connections intact, but unreachable from this menu.

    def patch_menu(self, menu):
        self.extended.patch_menu(menu)
        if self.button is not None and self.button.menu() is menu:
            mapping = {self.translated('MainWindow', text): key for text, key in FOLDERS}
            for action in list(menu.actions()):
                if not action.property('externalFileManager') and action.text() in mapping:
                    key = mapping[action.text()]
                    self.replace(menu, action, lambda k=key: self.folder(k), f'toolbar:{key}')
        elif self.tree is not None and menu.parentWidget() is self.tree:
            label = self.translated('ModListContextMenu', 'Open in Explorer')
            for action in list(menu.actions()):
                if action.text() == label and not action.property('externalFileManager'):
                    # Capture paths now, while the same selection that built the C++ menu is active.
                    try:
                        paths = self.selected()
                        resolver = lambda p=paths: p
                    except Exception as error:
                        def resolver(e=error): raise e
                    self.replace(menu, action, resolver, 'mod-context')

    def configure_shortcut(self):
        for old in self.shortcuts:
            self.tree.removeAction(old)
            old.deleteLater()
        self.shortcuts = []
        sequence = QKeySequence(str(self.setting('shortcut') or ''))
        if sequence.isEmpty() or self.tree is None: return
        action = QAction(self.tree)
        action.setShortcut(sequence)
        action.setShortcutContext(Qt.ShortcutContext.WidgetShortcut)
        action.setAutoRepeat(False)
        action.triggered.connect(lambda: self.open(self.selected, 'custom-shortcut'))
        self.tree.addAction(action)
        self.shortcuts.append(action)

    def eventFilter(self, obj, event):
        if self.tree is not None and sip.isdeleted(self.tree):
            return False
        if self.button is not None and sip.isdeleted(self.button):
            self.button = None
        try:
            kind = event.type()
            self.extended.event(obj, event)
            if kind == QEvent.Type.Show and isinstance(obj, QMenu):
                self.patch_menu(obj)
            if self.tree is not None and obj in (self.tree, self.tree.viewport()):
                if kind == QEvent.Type.ContextMenu:
                    self.context_index = self.tree.indexAt(event.pos())
                if kind == QEvent.Type.MouseButtonDblClick and obj is self.tree.viewport():
                    if event.button() == Qt.MouseButton.LeftButton and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                        index = self.tree.indexAt(event.position().toPoint())
                        if index.isValid():
                            self.open(lambda: self.paths([index], allow_foreign=True), 'ctrl-double-click')
                            event.accept()
                            return True
                if kind == QEvent.Type.KeyPress and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                    if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                        if not event.isAutoRepeat(): self.open(self.selected, 'ctrl-enter')
                        event.accept()
                        return True
        except Exception:
            LOG.exception('External File Manager interception failed')
            # Consume folder gestures on failure; do not let the native Explorer handler run.
            if self.tree is not None and obj in (self.tree, self.tree.viewport()) and event.type() in (QEvent.Type.MouseButtonDblClick, QEvent.Type.KeyPress):
                return True
        return False
