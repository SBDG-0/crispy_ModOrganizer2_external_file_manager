# Changelog

## 0.2.1 — 2026-11-21

- Redirect Instance Manager's location, base folder, and game location Explore buttons to the configured external manager.
- Redirect Settings → Theme → Explore and Log → Open logs folder.
- Retain native button enabled-state updates and resolve Instance Manager paths at click time after selection changes.
- Simplify the tool settings window by removing the extra explanations; keep the short introduction and attachment status. Details remain in the documentation.

## 0.2.0 — 2026-11-20

- Added a reproducible clean-release bundler with an explicit runtime allowlist, removal of packaged self-test hooks, archive verification and SHA-256 checksums.

- Added Images and Filetree buttons, Text/INI editor reveal buttons, all mod information conflict lists, and Filetree context-menu interception.
- Added main Data and Downloads reveal commands and Saves Open in Explorer.
- Open file targets in their containing directory, retaining disabled archive actions.
- Added editable settings, executable browsing, validation, Save and Cancel to Tools → External File Manager, alongside status information.
- Apply shortcut changes from the Tools window immediately; preserve OneCommander new-tab and focus preferences.
- Follow native button enable-state changes and handle MO2's root-relative conflict paths.
- Added broader regression checks and native-view test modes; keep checks active under MO2's optimized Python runtime.

## 0.1.0 — 2026-11-20

- Added direct OneCommander and configurable external-manager launching.
- Replaced recognized toolbar and mod context-menu actions without calling native Explorer handlers.
- Added interception for Ctrl+double-click, Ctrl+Enter, and an optional extra shortcut.
- Added internal-ID path resolution for regular mods, backups, Overwrite, and multiselection.
- Added distinct-path deduplication, configuration validation, and local rotating diagnostics.
- Added Qt regression tests and opt-in installed-runtime checks.
- Corrected startup setting availability, the native folder button type, and teardown handling during installed-MO2 testing.
