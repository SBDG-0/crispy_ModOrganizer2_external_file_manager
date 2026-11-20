"""Direct, shell-free launching. Never falls back to Explorer."""
import json
import os
from pathlib import Path
import re
import subprocess


def registered_onecommander():
    """Only accept the current user's explicit Directory default verb."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\Directory\shell") as key:
            verb = winreg.QueryValue(key, None)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\Directory\shell\{verb}\command") as key:
            command = winreg.QueryValue(key, None)
        match = re.match(r'^\s*"?(.+?\.exe)"?(?:\s|$)', command, re.I)
        if match:
            exe = os.path.expandvars(match[1])
            if Path(exe).name.lower() == 'onecommander.exe' and Path(exe).is_file():
                return exe
    except (OSError, ImportError):
        pass
    return ''


def command(executable, arguments_json, folder):
    exe = os.path.expandvars(executable.strip().strip('"'))
    if not Path(exe).is_file() or Path(exe).suffix.lower() != '.exe':
        raise ValueError('Choose an existing file manager .exe in plugin settings.')
    if Path(exe).name.lower() == 'explorer.exe':
        raise ValueError('Explorer is deliberately excluded. Choose an external file manager.')
    arguments = json.loads(arguments_json)
    if not isinstance(arguments, list) or not all(isinstance(arg, str) for arg in arguments):
        raise ValueError('Arguments must be a JSON array of strings.')
    if not any('{path}' in arg for arg in arguments):
        raise ValueError('Arguments must contain {path}.')
    return [exe] + [arg.replace('{path}', folder) for arg in arguments]


def launch(argv):
    # No cmd, shell verbs, MO2 virtual filesystem injection, or Explorer intermediary.
    subprocess.Popen(argv, cwd=str(Path(argv[0]).parent), shell=False,
                     close_fds=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
