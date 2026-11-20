import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
import mobase
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMessageBox
from .controller import Controller
from .launcher import registered_onecommander


class ExternalFileManager(mobase.IPluginTool):
    def __init__(self):
        super().__init__()
        self.organizer = None
        self.parent = None
        self.controller = None

    def name(self): return 'ExternalFileManager'
    def localizedName(self): return 'External File Manager'
    def displayName(self): return 'External File Manager'
    def author(self): return 'SavageBulldogOG'
    def description(self): return 'Open MO2 folders directly in OneCommander or another external file manager.'
    def tooltip(self): return 'Show external file manager status'
    def version(self): return mobase.VersionInfo(0, 2, 0)
    def isActive(self): return True
    def icon(self): return QIcon()
    def settings(self):
        return [
            mobase.PluginSetting('enabled', 'Redirect folder actions (restart MO2 after changing).', True),
            mobase.PluginSetting('manager', 'auto: verified OneCommander registry entry; onecommander: explicit executable; custom: custom arguments.', 'auto'),
            mobase.PluginSetting('executable', 'External file manager executable; auto falls back here, never to Explorer.', registered_onecommander()),
            mobase.PluginSetting('arguments', 'Custom manager only: JSON arguments with {path}. Example: ["{path}"]', '["{path}"]'),
            mobase.PluginSetting('shortcut', 'Optional additional shortcut while mod list has focus; restart required. Empty disables.', ''),
        ]

    def init(self, organizer):
        self.organizer = organizer
        organizer.onUserInterfaceInitialized(self.ui_ready)
        return True

    def setting(self, key):
        value = self.organizer.pluginSetting(self.name(), key)
        if value is None:
            return {'enabled': True, 'manager': 'auto', 'executable': registered_onecommander(),
                    'arguments': '["{path}"]', 'shortcut': ''}[key]
        return value

    def ui_ready(self, window):
        self.parent = window
        QTimer.singleShot(0, lambda: self.attach(window))

    def attach(self, window):
        logger = logging.getLogger('ExternalFileManager')
        if not logger.handlers:
            handler = RotatingFileHandler(str(Path(__file__).parent / 'external_file_manager.log'), maxBytes=512000, backupCount=1, encoding='utf-8')
            handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        logger.info('UI ready enabled=%r window=%r', self.setting('enabled'), window.objectName())
        if self.setting('enabled') is not False:
            try:
                self.controller = Controller(self.organizer, window, self.setting)
                if os.environ.get('CRISPY_EFM_SELFTEST') == '1':
                    from .selftest import run
                    QTimer.singleShot(1500, lambda: run(self.controller))
                elif os.environ.get('CRISPY_EFM_SELFTEST') in ('2', '3'):
                    from .extended_selftest import run
                    QTimer.singleShot(1500, lambda: run(self.controller))
            except Exception: logger.exception('External File Manager initialization failed')

    def setParentWidget(self, widget): self.parent = widget

    def display(self):
        from .settings_dialog import SettingsDialog
        SettingsDialog(self).exec()


def createPlugin(): return ExternalFileManager()
