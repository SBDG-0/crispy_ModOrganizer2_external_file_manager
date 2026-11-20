# Crispy MO2 External File Manager

## Description

Opens Mod Organizer 2 folders directly in OneCommander or another configured file manager. For MO2 2.5.2 users who want to use the existing folder commands without opening Windows Explorer first.

## Features

- Redirects all eleven existing folder dropdown commands.
- Redirects mod **Open in Explorer** commands, including multiple selected mods, backups, and Overwrite.
- Redirects Images and Filetree buttons, Text/INI editor reveal buttons, and mod information conflict/filetree context menus.
- Redirects Data and Downloads **Reveal in Explorer** and Saves **Open in Explorer**.
- Redirects **Ctrl+double-click** and **Ctrl+Enter** in the mod list.
- Supports an optional extra shortcut while the mod list has focus.
- Sends one launch request per distinct folder; no Explorer fallback.
- Uses the OneCommander path from your registered default folder handler, or an explicit executable you choose. Other managers accept configurable arguments.

## Requirements and installation

Requires MO2 2.5.2 with its bundled Python/PyQt6 plugin support and a working external file manager. Other MO2 versions are unverified.

With MO2 closed, place the `ExternalFileManager` folder inside MO2's `plugins` directory, or create a Windows directory junction to the repository's `ExternalFileManager` folder. Refuse an existing destination rather than replacing it. Restart MO2.

The local development install uses a junction at `I:\.other.games\Mod.Organizer-2.5.2\plugins\ExternalFileManager` pointing to this repository's plugin folder. Existing plugins are retained.

## Usage and configuration

Use MO2's existing folder dropdown or mod **Open in Explorer** command. The original label is retained for compatibility with MO2 translations. The Tools menu's **External File Manager** window shows attachment status and editable settings.

Open **Tools → External File Manager** to configure and save settings. They also remain available under **Settings → Plugins → ExternalFileManager**:

| Setting | Behavior |
| --- | --- |
| `enabled` | Enable interception. Restart after changing. |
| `manager` | `auto`, `onecommander`, or `custom`. |
| `executable` | Full `.exe` path. Used explicitly in `onecommander`/`custom` modes and as the fallback in `auto`. |
| `arguments` | Custom mode only: JSON string array containing `{path}`. Example: `["{path}"]`. |
| `shortcut` | Optional extra shortcut, for example `Alt+O`. Empty disables it. Changes saved in the Tools window apply immediately. |

`auto` accepts an existing OneCommander executable only from the current user's explicitly registered Directory default verb. It invokes that executable directly with OneCommander's documented arguments; it does not call Windows' shell or change the registry. If the association cannot be verified, it uses the configured executable. If that is missing, it reports an error.

For this installation, OneCommander was found at `H:\Program Files\OneCommander\OneCommander.exe`. Select `onecommander` to pin that explicit path independently of Windows associations.

OneCommander mode uses `-o {path} -newtab`. New tabs follow OneCommander's **Switch to new tab** preference. That preference is disabled in this user's installation and was deliberately retained, so folders open in background tabs. The plugin does not change OneCommander settings or add a second launch to force focus. To reuse the current tab, select `custom`, keep the OneCommander executable, and set arguments to `["-o", "{path}"]`.

For another manager, choose `custom`, its executable, and the arguments that manager documents. Each JSON element is one argument: do not add shell quoting, commands, or environment assignments. Folder names containing spaces or Unicode are passed as a single argument.

## Compatibility and limits

- This is targeted interception of known MO2 menus and gestures, not a universal replacement for every Windows folder operation. File dialogs, third-party plugins, native Windows shell context menus, and unrelated dialogs are outside scope. Images, Text/INI editors, Conflicts, Filetree, and the main Data/Saves/Downloads views are covered.
- Separators are skipped. Foreign mods are skipped in context menus, following MO2's behavior. Ctrl+double-click may open their actual directory, as MO2 does.
- Reveal commands open the containing directory. They do not automatically select the file in the external manager. Disabled archive-reveal actions stay disabled.
- Missing folders and invalid settings produce an error without launching Explorer.
- Matching uses the native translated labels and known menu ownership. Unrecognized or changed menus are left alone. Check attachment status after changing MO2 versions or other UI plugins.
- The plugin uses private UI details verified against 2.5.2. See [test results and development checks](TESTING.md).
- Diagnostic logs, including requested folder paths, rotate locally inside the plugin folder. Nothing is uploaded.

## Removal

Close MO2. Remove only the `plugins\ExternalFileManager` junction using a junction-aware, non-recursive operation; retain the repository and other plugin folders. After restart, native MO2 commands return. Alternatively disable this plugin and restart MO2.

## Development

Run `python -m unittest discover -s tests -v` in an environment with PyQt6 installed. Tests use Qt's offscreen platform. For opt-in checks inside installed MO2, start that process with `CRISPY_EFM_SELFTEST=1`; the runner writes `ExternalFileManager/live-selftest.json` and records external launches instead of executing them. It restores the main mod-list selection, expansion and scroll position. Mode `2` checks the additional views with a launch recorder; mode `3` performs real external launches. Both require `CRISPY_EFM_TEST_MOD` naming an existing mod with images and conflicts. These probes navigate secondary tabs and lists. Never leave these variables enabled for normal use.

See [changelog](CHANGELOG.md) and [test results](TESTING.md).

## References

- [MO2 2.5.2 source](https://github.com/ModOrganizer2/modorganizer/tree/v2.5.2/src)
- [MO2 plugin API source](https://github.com/ModOrganizer2/modorganizer-uibase/tree/v2.5.2/src)
- [OneCommander command-line reference](https://onecommander.com/help/3._Full_reference_guide/Starting_from_Command_line.html)

---

made with ❤️ by SavageBulldogOG
