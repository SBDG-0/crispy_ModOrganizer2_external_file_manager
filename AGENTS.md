# External File Manager development

- Target installed MO2 2.5.2, embedded Python 3.12, PyQt6 / Qt 6.7.
- Preserve native actions and connections. Replace actions in recognized menus; consume folder gestures before native handlers. Never add a second launch callback to a native action.
- Resolve mod paths from IndexRole (257) through IModList.allMods(), then getMod().absolutePath(). Do not infer paths from display names or proxy row numbers.
- Never use Explorer, shell=True, registry writes, global URL handlers, or filesystem redirection as a fallback.
- Retain unrelated plugins, mods, profiles, and settings. Install through the dedicated ExternalFileManager junction only.
- Run Qt regression tests after interception changes; validate startup and teardown in installed MO2. Record live test limitations honestly in TESTING.md.
- Keep user instructions in README.md, development results in TESTING.md, and dated changes in CHANGELOG.md. Follow parent README conventions. Do not invent a GitHub remote or license grant.
