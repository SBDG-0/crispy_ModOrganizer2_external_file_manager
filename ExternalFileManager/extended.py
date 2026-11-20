"""MO2 2.5.2 dialog and secondary-view adapters. No native callbacks invoked."""
import html
import re
import time
from pathlib import Path
from PyQt6 import sip
from PyQt6.QtCore import Qt, QEvent, QDir, QSettings
from PyQt6.QtGui import QAction, QFileSystemModel
from PyQt6.QtWidgets import (QAbstractItemView, QDialog,
                            QLineEdit, QToolButton, QWidget, QAbstractButton, QPushButton)


CONFLICT_VIEWS = {'overwriteTree', 'overwrittenTree', 'noConflictTree', 'conflictsAdvancedList'}


def containing_folder(path):
    path = Path(path)
    if not path.exists():
        raise ValueError(f'The target no longer exists:\n{path}')
    return str(path if path.is_dir() else path.parent)


def mod_root(widget):
    dialog = widget.window()
    tree = dialog.findChild(QAbstractItemView, 'filetree')
    if tree is not None and isinstance(tree.model(), QFileSystemModel):
        root = tree.model().filePath(tree.rootIndex())
        if root and Path(root).is_dir(): return root
    raise ValueError('The mod information dialog has no valid filesystem root.')


def under(root, relative):
    # Displayed relative paths are source-verified model data, not mod display names.
    root = Path(root)
    relative = str(relative).replace('\\', '/')
    # ConflictItem.relativeName begins with '/' in MO2 (native code concatenates
    # it to the mod root). It is a root-relative model path, not a drive root.
    if relative.startswith('//') or ':' in relative:
        raise ValueError('Invalid relative file path.')
    path = root / relative.lstrip('/')
    if not path.is_absolute() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('The file path is outside the expected directory.')
    return str(path)


class Extended:
    def __init__(self, controller):
        self.c = controller
        self.pending = None
        self.pending_time = 0
        self.button_links = {}

    def observe_context(self, obj):
        current = obj
        while isinstance(current, QWidget):
            if isinstance(current, QAbstractItemView):
                self.pending = current
                self.pending_time = time.monotonic()
                break
            current = current.parentWidget()

    def source(self, menu):
        parent = menu.parentWidget()
        pending, self.pending = self.pending, None
        if isinstance(parent, QAbstractItemView): return parent
        # Parentless menus in FileTree, ConflictsTab and SavesTab execute synchronously
        # inside a context-menu event. Never infer them from an unrelated stale selection.
        return pending if pending is not None and not sip.isdeleted(pending) and time.monotonic() - self.pending_time < 3 else None

    def resolver(self, view):
        name = view.objectName()
        selected = view.selectionModel().selectedRows()
        if name == 'downloadView':
            return [self.c.organizer.downloadsPath()]
        if name == 'filetree' and isinstance(view.model(), QFileSystemModel):
            if len(selected) == 1: return [containing_folder(view.model().filePath(selected[0]))]
            return [mod_root(view)]
        if name in CONFLICT_VIEWS:
            # All conflict models expose relativeName in column 0, except advanced (1).
            column = 1 if name == 'conflictsAdvancedList' else 0
            return [containing_folder(under(mod_root(view), i.siblingAtColumn(column).data())) for i in selected]
        if name == 'dataTree':
            paths = []
            caption = self.c.translated('FileTreeModel', 'Real path')
            for index in selected:
                tooltip = str(index.siblingAtColumn(0).data(Qt.ItemDataRole.ToolTipRole) or '')
                match = re.search(r'<b>' + re.escape(caption) + r':</b>\s*(.*?)</p>', tooltip, re.S)
                if not match: raise ValueError('MO2 did not expose a real path for this Data item.')
                paths.append(containing_folder(html.unescape(match[1])))
            return paths
        if name == 'savegameList':
            if not selected: return []
            org = self.c.organizer
            profile, game = org.profile(), org.managedGame()
            if profile.localSavesEnabled():
                directory = QDir(str(Path(profile.absolutePath()) / 'saves'))
            else:
                directory = game.savesDirectory()
                inis = game.iniFiles()
                if inis:
                    settings = QSettings(profile.absoluteIniFilePath(inis[0]), QSettings.Format.IniFormat)
                    override = settings.value('General/SLocalSavePath', settings.value('SLocalSavePath', ''))
                    if override: directory = QDir(game.documentsDirectory().absoluteFilePath(str(override)))
            # Match native relative-path column, not translated save display names or sort order.
            relative = str(selected[0].siblingAtColumn(1).data())
            return [containing_folder(under(directory.absolutePath(), relative))]
        raise ValueError('Unsupported MO2 view.')

    def patch_menu(self, menu):
        view = self.source(menu)
        if view is None: return
        name = view.objectName()
        if name == 'logList':
            target = self.c.translated('LogList', '&Open logs folder')
            for action in list(menu.actions()):
                if action.text() == target and not action.property('externalFileManager'):
                    self.c.replace(menu, action, lambda: self.c.folder('logs'), 'log-context')
            return
        specifications = {
            'downloadView': ('DownloadListView', 'Reveal in Explorer'),
            'dataTree': ('FileTree', 'Reveal in E&xplorer'),
            'savegameList': ('SavesTab', 'Open in Explorer...'),
            'filetree': ('FileTreeTab', 'Open in &Explorer'),
        }
        if name in CONFLICT_VIEWS: spec = ('ConflictsTab', 'Open in &Explorer')
        else: spec = specifications.get(name)
        if spec is None: return
        target = self.c.translated(*spec)
        for action in list(menu.actions()):
            if action.text() != target or action.property('externalFileManager'): continue
            try:
                paths = self.resolver(view) if action.isEnabled() else []
                resolver = lambda p=paths: p
            except Exception as error:
                def resolver(e=error): raise e
            self.c.replace(menu, action, resolver, 'view:' + name)

    def patch_dialog(self, dialog):
        if dialog.objectName() == 'InstanceManagerDialog':
            for name, field in (('exploreLocation', 'location'), ('exploreBaseDirectory', 'baseDirectory'), ('exploreGame', 'gameDir')):
                button = dialog.findChild(QAbstractButton, name)
                path = dialog.findChild(QLineEdit, field)
                if button is not None and path is not None and not button.property('externalFileManager'):
                    self.replace_button(button, lambda p=path: p.text(), 'instance:' + field)
            return
        if dialog.objectName() == 'SettingsDialog':
            button = dialog.findChild(QAbstractButton, 'exploreStyles')
            if button is not None and not button.property('externalFileManager'):
                self.replace_button(button, lambda: self.c.folder('stylesheets'), 'settings:theme')
            return
        if dialog.objectName() != 'ModInfoDialog': return
        for button in dialog.findChildren(QToolButton):
            if button.property('externalFileManager') or button.objectName().endswith('_efm_native'): continue
            name = button.objectName()
            if name == 'imagesExplore':
                path = dialog.findChild(QLineEdit, 'imagesPath')
                resolver = lambda p=path: containing_folder(p.text())
            elif name == 'openInExplorer':
                resolver = lambda d=dialog: mod_root(d)
            elif button.defaultAction() and button.defaultAction().text() == self.c.translated('QObject', '&Open in Explorer'):
                path = button.parentWidget().findChild(QLineEdit)
                if path is None: continue
                resolver = lambda p=path: containing_folder(p.text())
                old = button.defaultAction()
                replacement = QAction(old.text(), button)
                replacement.setEnabled(old.isEnabled())
                replacement.setProperty('externalFileManager', True)
                replacement.triggered.connect(lambda checked=False, r=resolver: self.c.open(r, 'mod-info:text'))
                old.changed.connect(lambda o=old, n=replacement: n.setEnabled(o.isEnabled()))
                button.setDefaultAction(replacement)
                button.setProperty('externalFileManager', True)
                continue
            else: continue
            self.replace_button(button, resolver, 'mod-info:' + name)

    def replace_button(self, button, resolver, reason):
        # Keep the hidden native widget alive for MO2's state updates, but give
        # the user a separate button with no original clicked callback.
        parent = button.parentWidget()
        layout = parent.layout()
        if layout is None: return
        name = button.objectName()
        replacement = QToolButton(parent) if isinstance(button, QToolButton) else QPushButton(parent)
        replacement.setText(button.text())
        replacement.setIcon(button.icon())
        replacement.setToolTip(button.toolTip())
        replacement.setSizePolicy(button.sizePolicy())
        replacement.setFocusPolicy(button.focusPolicy())
        if isinstance(button, QToolButton):
            replacement.setToolButtonStyle(button.toolButtonStyle())
            replacement.setAutoRaise(button.autoRaise())
        else:
            replacement.setAutoDefault(button.autoDefault())
            replacement.setDefault(button.isDefault())
        replacement.setEnabled(button.isEnabled())
        replacement.setProperty('externalFileManager', True)
        if layout.replaceWidget(button, replacement) is None:
            replacement.deleteLater()
            return
        button.setObjectName(name + '_efm_native')
        replacement.setObjectName(name)
        button.hide()
        replacement.show()
        replacement.clicked.connect(lambda checked=False: self.c.open(resolver, reason))
        key = id(button)
        self.button_links[key] = (button, replacement)
        button.destroyed.connect(lambda _, k=key: self.button_links.pop(k, None))

    def event(self, obj, event):
        kind = event.type()
        if kind == QEvent.Type.ContextMenu: self.observe_context(obj)
        elif kind == QEvent.Type.Show and isinstance(obj, QDialog): self.patch_dialog(obj)
        elif kind == QEvent.Type.EnabledChange:
            pair = self.button_links.get(id(obj))
            if pair:
                old, new = pair
                if not sip.isdeleted(old) and not sip.isdeleted(new): new.setEnabled(old.isEnabled())

    def restore(self):
        # Used only when disabling at runtime; restart is safer for already open dialogs.
        self.pending = None
