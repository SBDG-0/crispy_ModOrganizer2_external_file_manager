"""Build a clean MO2 plugin ZIP using only the Python standard library."""
import argparse
import ast
import hashlib
from pathlib import Path
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent
RUNTIME = ('__init__.py', 'controller.py', 'extended.py', 'launcher.py',
           'plugin.py', 'settings_dialog.py')


def version(source):
    tree = ast.parse(source)
    method = next(node for node in ast.walk(tree)
                  if isinstance(node, ast.FunctionDef) and node.name == 'version')
    call = next(node for node in ast.walk(method) if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute) and node.func.attr == 'VersionInfo')
    values = [ast.literal_eval(arg) for arg in call.args]
    if len(values) != 3 or any(type(n) is not int or n < 0 for n in values):
        raise ValueError('Expected three numeric plugin version components.')
    return '.'.join(map(str, values))


def release_plugin(source):
    """Remove opt-in development entry points in the archive copy only."""
    tree = ast.parse(source)
    remove = set()
    branches = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and len(node.names) == 1 and node.names[0].name == 'os':
            remove.update(range(node.lineno, node.end_lineno + 1))
        if isinstance(node, ast.If) and 'CRISPY_EFM_SELFTEST' in ast.get_source_segment(source, node.test):
            branches.append(node)
    # Removing the outer if also removes its elif branches.
    for node in branches:
        remove.update(range(node.lineno, node.end_lineno + 1))
    result = ''.join(line for number, line in enumerate(source.splitlines(keepends=True), 1)
                     if number not in remove)
    ast.parse(result)
    if 'selftest' in result or 'CRISPY_EFM_SELFTEST' in result:
        raise ValueError('Development test entry points remain in release plugin.')
    return result


def release_readme(number):
    return f'''# Crispy MO2 External File Manager

## Description

Opens supported Mod Organizer 2 folder commands directly in OneCommander or another configured file manager.

**Version:** {number}

## Installation

Close MO2. Copy the `ExternalFileManager` folder into MO2's `plugins` directory, then restart MO2. Requires MO2 2.5.2 and its bundled Python/PyQt6 support. Keep a backup of an older plugin version before replacing it; do not merge a release into a development junction.

## Usage and settings

Configure the manager, executable, arguments and optional shortcut under **Tools → External File Manager**. Status information is shown in the same window. Settings also remain available in MO2's Plugins settings. Restart after enabling or disabling interception.

Supported routes include the eleven toolbar folder commands, mod context menus and multiselection/Overwrite, Ctrl+double-click, Ctrl+Enter, mod information Images/Conflicts/Filetree commands, Text/INI editor reveal buttons, the main Data/Saves/Downloads reveal commands, Instance Manager Explore buttons, Theme Explore, and Log Open logs folder.

OneCommander opens a new tab and follows your existing tab-focus preference. Reveal commands open the containing folder without automatically selecting the file. Custom arguments use a JSON string array containing {{path}}, for example `["{{path}}"]`. Invalid settings and missing paths produce an error without an Explorer fallback.

## Limits

Targets MO2 2.5.2. Third-party plugins, native Windows shell menus, file dialogs and unrelated dialogs are outside scope. Backup handling is implemented but has not been clicked in a live backup-mod fixture. Other external managers are configurable but unverified. Disabled archive reveal actions remain disabled.

Development tests, reports, caches, local paths and existing logs are excluded from this package. The plugin creates a rotating diagnostic log during normal use; it includes requested folder paths and stays local.

See [changelog](CHANGELOG.md).

---

made with ❤️ by SavageBulldogOG
'''


def payload(root=ROOT):
    plugin_dir = root / 'ExternalFileManager'
    source = (plugin_dir / 'plugin.py').read_text(encoding='utf-8-sig')
    number = version(source)
    files = {}
    for name in RUNTIME:
        path = plugin_dir / name
        if path.is_symlink(): raise ValueError(f'Refusing linked source file: {path}')
        text = path.read_text(encoding='utf-8-sig')
        if name == 'plugin.py': text = release_plugin(text)
        tree = ast.parse(text, filename=name)
        # Catch newly introduced runtime modules missing from the explicit allowlist.
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level:
                if node.level != 1 or not node.module or node.module.split('.')[0] + '.py' not in RUNTIME:
                    raise ValueError(f'Unpackaged relative dependency in {name}: {ast.unparse(node)}')
        files['ExternalFileManager/' + name] = text.replace('\r\n', '\n').encode('utf-8')
    files['README.md'] = release_readme(number).encode('utf-8')
    files['CHANGELOG.md'] = (root / 'CHANGELOG.md').read_bytes()
    # Preserve any future established license; do not invent one.
    for name in ('LICENSE', 'LICENSE.md', 'LICENSE.txt', 'NOTICE', 'NOTICE.md'):
        path = root / name
        if path.is_file(): files[name] = path.read_bytes()
    return number, files


def bundle(root=ROOT, force=False):
    number, files = payload(root)
    releases = root / '.releases'
    if releases.is_symlink() or getattr(releases, 'is_junction', lambda: False)():
        raise ValueError('Refusing a linked .releases directory.')
    releases.mkdir(exist_ok=True)
    target = releases / f'Crispy_MO2_External_File_Manager-{number}.zip'
    if target.exists() and not force:
        raise FileExistsError(f'Release already exists: {target}\nUse --force to replace this archive.')
    with tempfile.NamedTemporaryFile(dir=releases, suffix='.tmp', delete=False) as temporary:
        staging = Path(temporary.name)
    try:
        with zipfile.ZipFile(staging, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, data in sorted(files.items()):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, data)
        with zipfile.ZipFile(staging) as archive:
            if archive.testzip() is not None or set(archive.namelist()) != set(files):
                raise ValueError('Archive verification failed.')
            for name, data in files.items():
                if archive.read(name) != data: raise ValueError(f'Archive content mismatch: {name}')
        staging.replace(target)
    finally:
        staging.unlink(missing_ok=True)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.zip.sha256').write_text(f'{digest}  {target.name}\n', encoding='ascii')
    return target, digest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--force', action='store_true', help='Replace an existing archive of the same version.')
    args = parser.parse_args()
    try:
        path, digest = bundle(force=args.force)
    except (OSError, ValueError, SyntaxError, StopIteration) as error:
        parser.exit(1, f'Release failed: {error}\n')
    print(f'Created: {path}\nSHA256: {digest}')
