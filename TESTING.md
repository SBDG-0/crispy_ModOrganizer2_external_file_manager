# Investigation and test results

## Target inspected — 2026-11-20

- MO2 installation: `I:\.other.games\Mod.Organizer-2.5.2`, version 2.5.2 revision `9c130cbf` reported by its log.
- Bundled plugin runtime: Python 3.12, PyQt6, Qt 6.7 generation.
- Active instance: S.T.A.L.K.E.R. Anomaly 1.5.3, existing xrRazom Profile.
- OneCommander: `H:\Program Files\OneCommander\OneCommander.exe`.
- Current-user `Directory\shell` default: `OpenInOneCommander`; executable confirmed on disk. No registry settings changed.
- Existing MO2 plugins, mods, profile configuration and load order were not replaced. Live test selection and scroll position were restored.

## Source evidence

Official tagged [MO2 2.5.2 source](https://github.com/ModOrganizer2/modorganizer/tree/v2.5.2/src) and [uibase API](https://github.com/ModOrganizer2/modorganizer-uibase/tree/v2.5.2/src) were inspected:

- `mainwindow.cpp`: `openFolderMenu()` creates eleven QAction callbacks. Folder paths include the application's `dataPath` (instance/logs), organizer paths, game directory/documents, and profile-local INI behavior.
- `modlistcontextmenu.cpp`: native regular, backup and Overwrite menus all connect Open in Explorer directly to `openExplorer(m_selected)` and have the mod list as parent.
- `modlistview.cpp`: Ctrl+double-click calls native `shell::Explore`; Ctrl+Enter is another native Explorer route. Consuming the input event prevents those handlers.
- `modlistviewactions.cpp`: multiselection loops through selected mods, skips foreign mods, and explores their absolute paths.
- `modlist.h` and `modlist.cpp`: IndexRole is 257; allMods returns internal names in the same ModInfo index order. This avoids ambiguity from sorting, grouping, translated display names, backups and Overwrite.
- `loglist.cpp`: logs are under application `dataPath`, not the configured mods base directory.

Menu actions are removed from recognized menus and replacement actions inserted before interaction. Original C++ connections are neither disconnected nor called. Toolbar menus are patched idempotently when shown, including recreated menus after a language change. Other menus remain untouched.

## Automated Qt tests

Nine tests passed with Python 3.13, PyQt6 6.7.0 / Qt 6.7.3 in a workspace-only environment:

- All eleven toolbar replacements, repeated patching, original callbacks uncalled.
- Context replacement, original callback uncalled; unrelated menus unchanged.
- Ctrl+double-click consumed before the view's native doubleClicked signal.
- Ctrl+Enter and actual optional shortcut key delivery: one request each.
- Regular/backup/Overwrite row identity resolution; separator and foreign handling.
- Duplicate folder paths yield one launch request.
- Missing paths fail without launching.
- Spaces, Unicode and punctuation remain separate, shell-free arguments; invalid argument configuration is rejected.

Run: `python -m unittest discover -s tests -v`.

## Installed-runtime checks

Opt-in checks were run inside installed MO2's embedded Python/PyQt6, against its actual window, menus, profile and model. A launch recorder replaced the process launcher only for the duration of these checks. No external processes were started by this runner.

| Case | Result |
| --- | --- |
| All 11 toolbar actions | Passed, 1 recorded request each; every folder resolved and existed |
| Real native regular-mod context menu | Passed, 1 request |
| Real native multiselection context menu | Passed, 2 distinct folders / 2 requests |
| Real native Overwrite context menu | Passed, correct Overwrite directory / 1 request |
| Ctrl+double-click event on native viewport | Passed, 1 request |
| Ctrl+Enter event on native view | Passed, 1 request |
| Optional configured shortcut action | Passed, 1 request; key delivery additionally tested offscreen |
| Existing backup mod | Not available in this instance; no backup fixture was added |

Backup support uses the same source-verified native menu action and API absolute-path resolution as regular mods, with backup identity covered by automated tests. It remains unverified by a click on an actual backup in this user's instance.

The raw installed-runtime report is generated locally as `ExternalFileManager/live-selftest.json` (ignored by Git because it contains local paths).

## Real external-launch checks

The existing toolbar Mods command, a regular mod's existing Open in Explorer command, and Ctrl+Enter were each triggered in installed MO2 with the real process launcher. Each recorded exactly one OneCommander invocation. The new Mods tab's path was visually verified as `I:\.other.games\Mod.Organizer_Instance_Anomaly\mods`; the mod request used its actual directory. No new Explorer window appeared in these successful checks.

The first pre-fix toolbar test opened Explorer because initialization had skipped attachment. This was corrected before the successful tests: startup plugin settings can initially be unavailable, and the native folder button is not a QToolButton. Teardown was also corrected to avoid accessing deleted Qt widgets. These initial failures are retained here rather than described as successful tests.

An independent Windows process-start trace could not be obtained from WMI on this machine. Therefore the evidence is the direct shell-free launcher, native-callback regression checks, recorded request counts, and observed windows; no claim is made of an exhaustive OS-level process trace.

## OneCommander focus preference

OneCommander's documented `-o <path> -newtab` and `-p <path> -newtab` both created background tabs in this installation. `-o <path>` without `-newtab` navigated the selected tab. The local `SwitchToNewTab` preference was found disabled. The user explicitly chose to retain that setting and prefers new tabs; the plugin retains `-o <path> -newtab`. No OneCommander settings were edited.

See [official command-line reference](https://onecommander.com/help/3._Full_reference_guide/Starting_from_Command_line.html).

## Scope and remaining limits

No global shell handler, Explorer process hook, MO2 executable patch, or system association change is installed. The plugin covers the requested toolbar/mod-list routes plus Ctrl+Enter. As of 0.2.0 the main Data, Saves and Downloads reveal commands and listed mod information routes are covered. File dialogs, third-party plugins, native shell menus and unrelated dialogs remain native. Other external managers are configurable but were not installed or exercised in this task. Non-English MO2 and a language switch are source-supported but not live-tested.


## 0.2.0 expanded coverage — 2026-11-20

The user's follow-up identified Explorer entry points outside the initial toolbar/mod-list scope. The following source adapters were added:

- `modinfodialogimages.cpp`: selected image path from `imagesPath`; replace `imagesExplore` before interaction.
- `modinfodialogfiletree.cpp`: `QFileSystemModel` provides the current mod root and selected real path; replace `openInExplorer` and the context action.
- `modinfodialogconflicts.cpp` / `modinfodialogconflictsmodels.cpp`: all four lists expose a root-relative file path (column 0 for general lists, column 1 for advanced). MO2 concatenates these leading-slash paths with the mod root. Parentless native menus are associated with their immediate context event.
- `texteditor.cpp`: replace the Text/INI editor's default reveal QAction using its read-only path field. Retain enabled-state updates from the original action.
- `filetreemodel.cpp`: the Data tree's HTML tooltip exposes an escaped real path. Parse its translated Real path field; retain disabled archive actions.
- `savestab.cpp`: resolve the native relative save-file column using the current profile's local save path or the game's save directory/INI override.
- `downloadlistview.cpp`: replace Reveal in Explorer and open the organizer's configured downloads directory; metadata display names are not used as filenames.

All these file-reveal commands open the containing folder, without automatic file selection. Native Explorer callbacks are not invoked. Buttons are replaced as widgets (or default actions) rather than given an additional clicked callback; hidden originals remain owned by MO2 for its tab updates.

### Validation

- 22 offscreen Qt tests passed, including the original nine regressions, all four conflict models with leading-slash paths, escaped Unicode Data paths, filetree root/selected file, Downloads, global/profile-local/INI-overridden Saves, native-button suppression and enabled-state synchronization, Text/INI actions, settings Save/Cancel, and validation failure without writes.
- Nine checks passed inside installed MO2 with a recording launcher, then passed with real OneCommander launches: Filetree root button, Filetree context menu, overwritten/nonconflicting/advanced conflict context menus, Images button after actual thumbnail selection, Downloads, Saves, and Data reveal. Every action produced exactly one request, and the final real-launch report had zero warnings. The test mod was the existing `Stealth_Overhaul_Reworked`; no test files or mods were added to the instance.
- No Explorer window appeared in the real-launch checks. As before, there is no independent OS-wide process trace; verification combines direct launching, native-handler suppression tests, request counts and window observations.
- The new Tools settings dialog was visually inspected in installed MO2 and Save was exercised without changing the user's chosen values. The final normal restart checks persisted settings and attachment.
- The general overwrite/winning conflict list had no rows in the selected live test mod; its adapter passed the offscreen test. Text/INI buttons passed a Qt default-action replacement test; they were not clicked in a live mod containing text/INI preview files during this pass.
- Initial expanded-view checks caught native-button wrapper lifetime and leading-slash path issues. The installed runner was also corrected to use explicit checks because MO2 runs optimized Python, which strips ordinary assert statements. The expanded tests were rerun after these corrections; only the corrected successful run is counted above.

The local `ExternalFileManager/extended-selftest.json` report is ignored by Git because it includes user paths. Mode 2 records launches; mode 3 executes them. The test runner navigates secondary views; it preserves main mod-list selection, expansion and scroll position.

The original 17 installed-runtime toolbar/mod-list checks were rerun on 0.2.0 with explicit checks active in optimized Python; all passed. The no-backup fixture limitation remains.

## Clean release bundler

Three standard-library packaging tests passed: exact clean archive contents with development source unchanged, deterministic rebuilds plus overwrite protection, and rejection of an unpackaged runtime dependency. The generated 0.2.0 archive was verified by reading back every entry and checking ZIP integrity. The package contains six runtime modules, README.md and CHANGELOG.md; no self-test modules, startup hooks, logs, reports or caches. No established license/notice file currently exists; future ones are preserved automatically. The installed development plugin was not changed or restarted for packaging.
