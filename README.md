# Mod Organizer 2 - External File Manager

## Description

Opens Mod Organizer 2 folders directly in OneCommander or another configured file manager, using MO2's existing folder commands.

**Version:** 0.2.1

## Features

- Toolbar folder dropdown and mod **Open in Explorer** commands, including multiple selected mods, backups, and Overwrite.
- **Ctrl+double-click**, **Ctrl+Enter**, and an optional shortcut in the mod list.
- Mod information Images, Text/INI, Conflicts, and Filetree folder commands.
- Data, Saves, and Downloads reveal commands.
- Instance Manager Explore buttons, Settings → Theme → Explore, and Log → Open logs folder.
- One launch per distinct folder, with errors reported instead of falling back to Explorer.

## Requirements and installation

Requires **Mod Organizer 2.5.2** with its bundled Python/PyQt6 plugin support and a working external file manager. Other MO2 versions are unverified.

1. Close MO2.
2. Extract the release ZIP and copy its `ExternalFileManager` folder into MO2's `plugins` directory.
3. Restart MO2 and open **Tools → External File Manager**.
4. Choose your file manager and executable, then save.

Back up an older plugin version before replacing it. Do not merge a release into a directory junction used for another installation.

## Usage and settings

Use the existing MO2 folder commands. Their original Explorer labels are retained for compatibility with MO2's translations.

Configure the plugin in **Tools → External File Manager**. These settings are also available in MO2's Plugins settings.

| Setting | Behavior |
| --- | --- |
| Redirect MO2 folder commands | Enable or disable the plugin's redirection. Restart MO2 after changing. |
| File manager | Automatic registered OneCommander, explicit OneCommander executable, or another manager with custom arguments. |
| Executable | Full path to the file manager's `.exe`. |
| Custom arguments (JSON) | For other managers, enter a JSON array containing `{path}`, for example `["{path}"]`. Each element is one argument. |
| Mod-list shortcut | Optional shortcut such as `Alt+O`. Leave empty to disable. Changes saved here apply immediately. |

Automatic mode uses OneCommander when it can verify the Windows folder association and executable. Otherwise it uses the configured executable; a missing executable produces an error. The plugin does not change Windows associations or OneCommander settings.

OneCommander opens folders in **new tabs**, following its existing **Switch to new tab** preference. To reuse the current tab instead, choose the custom manager option, keep the OneCommander executable, and use `["-o", "{path}"]`.

## Compatibility and limitations

- Reveal commands open the containing folder; they do not automatically select the file.
- Disabled archive-reveal actions remain disabled. Separators are skipped, and mod context menus skip foreign mods as MO2 does.
- Backup support is implemented but has not been verified by clicking an actual backup mod in a live instance.
- Other file managers are configurable but have not been verified individually.
- Third-party plugins, native Windows shell context menus, file dialogs, and unrelated dialogs are outside scope.
- If MO2's interface changes in another version, some commands may remain native. Check the attachment status in the tool window.
- Diagnostic logs rotate locally inside the plugin folder and include requested folder paths. Nothing is uploaded.

## Removal

Close MO2 and remove only its `plugins/ExternalFileManager` folder. If that folder is a directory junction, remove only the junction and retain its target. Restart MO2 to restore native folder commands. Alternatively disable redirection and restart.

## References

- [MO2](https://github.com/ModOrganizer2/modorganizer)
- [OneCommander command-line reference](https://onecommander.com/help/3._Full_reference_guide/Starting_from_Command_line.html)

## Changelog

### 0.2.1 — 2026-11-21

- Added Instance Manager Explore buttons, Theme Explore, and Open logs folder.
- Simplified the External File Manager settings window.

### 0.2.0 — 2026-11-20

- Added mod information Images, Text/INI, Conflicts, and Filetree commands.
- Added Data, Saves, and Downloads reveal commands.
- Added editable settings to Tools → External File Manager.

### 0.1.0 — 2026-11-20

- Added direct OneCommander and configurable external file manager support.
- Added toolbar and mod context menus, Ctrl+double-click, Ctrl+Enter, and an optional shortcut.
- Added support for multiple selected mods, backups, and Overwrite.

## License

Licensed under the [MIT License](LICENSE). See the license file for the full terms.

---

made with ❤️ by SavageBulldogOG
