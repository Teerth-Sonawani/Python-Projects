# Sticky Todo

A tiny, always-on-top desktop todo widget for Windows. It looks like a sticky
note, stays out of your way in the corner of your screen, and never quietly
disappears on you — even if something covers it, minimizes it, or you close
it by accident.

Each day gets its own independent checklist, so you can page back through
history without losing anything, and it can optionally mirror everything to
a Google Sheet for a longer-term log and some at-a-glance charts.

![priority: dark, minimal, sticky-note style](https://img.shields.io/badge/style-dark%20%26%20minimal-1c1c1e)
![platform: windows](https://img.shields.io/badge/platform-Windows-0078D6)
![python](https://img.shields.io/badge/python-3.9%2B-3776AB)

---

## Features

- **Genuinely always-on-top.** A background watchdog re-asserts topmost
  every ~400ms and restores the window if anything minimizes it — not just
  a one-time `-topmost` flag that other apps can knock down.
- **Per-day checklists.** Navigate between days with the arrow buttons or
  jump straight to any date with the built-in calendar popup. Nothing from
  a previous day is ever lost or overwritten.
- **Drag to reorder**, **right-click for priority** (None / Low / Medium /
  High / Urgent — each with its own subtle tint), and a clean checkbox +
  strikethrough for completed tasks.
- **System tray icon** as a safety net — left-click to bring the widget
  back instantly, right-click for Show / Start with Windows / Quit.
- **Start with Windows** (optional, one click from the right-click menu).
- **"Attach to desktop" mode** (optional) — reparents the widget behind
  every other window, like a desktop icon, for a wallpaper-widget look.
- **Rounded corners** on Windows 11, and it stays out of the taskbar/Alt+Tab.
- **Optional Google Sheets sync** — a live "Log" tab of every task plus a
  "Summary" tab with completion stats and pie charts, so you get a
  permanent record beyond your local machine.
- **Crash-safe.** Any startup or runtime error is written to
  `~/.sticky_todo/crash.log` instead of vanishing into a `pythonw.exe`
  black hole.

## Requirements

- Windows (some things — the tray icon, autostart, topmost hardening, and
  "attach to desktop" — are Windows-only; the widget will still run on
  other platforms with those features quietly disabled)
- Python 3.9+
- No third-party packages required for the core app (uses only the
  standard library: `tkinter`, `ctypes`, etc.)
- Optional, only if you want Google Sheets sync:
  ```bash
  pip install gspread google-auth-oauthlib
  ```

## Getting started

1. Clone or download this repo.
2. Run it:
   ```bash
   python sticky_todo.py
   ```
   (On Windows, run with `pythonw.exe` instead of `python.exe` if you don't
   want a console window hanging around.)
3. The widget appears in the corner of your screen. Type in the box at the
   bottom and hit **Enter** to add a task.

That's it — no configuration is required for normal use. Everything is
stored locally in `~/.sticky_todo/`.

## Usage

| Action | How |
|---|---|
| Add a task | Type in the entry box, press **Enter** |
| Complete a task | Click its checkbox |
| Delete a task | Click the **✕** on the right of the row |
| Set priority | Right-click a task |
| Reorder tasks | Click and drag a row |
| Move the widget | Drag the title bar |
| Resize the widget | Drag the bottom-right corner grip |
| Switch day | Click the **‹ ›** arrows, or click the date to open the calendar |
| Jump to today | Right-click the title bar → **Jump to today** |
| Clear completed tasks | Right-click the title bar → **Clear completed** |
| Options (always on top, autostart, attach to desktop, sync) | Right-click the title bar |
| Hide / restore | Close button hides to tray (if tray is active); click the tray icon to bring it back |

## Data storage

Everything lives under `~/.sticky_todo/` (on Windows,
`%USERPROFILE%\.sticky_todo\`):

| File | Purpose |
|---|---|
| `todos.json` | All tasks, keyed by date (`{"2026-08-09": [...tasks]}`) |
| `window_state.json` | Window position, size, and settings |
| `crash.log` | Startup/runtime errors, if any |
| `credentials.json` | Your Google OAuth client secret (only if you set up sync) |
| `token.json` | Cached Google auth token (created automatically after first sync) |
| `sheet_config.json` | Remembers which Google Sheet belongs to this app |

Nothing is sent anywhere unless you deliberately set up Google Sheets sync.

## Optional: Google Sheets sync

The app works completely fine, fully offline, without ever setting this up.
`sheets_sync.py` is only imported in a `try/except`, and every call into it
checks `is_configured()` first — so nothing here can break the widget if
it's absent or misconfigured.

When enabled, every add/tick/edit/delete (after a short debounce) pushes
your current data to a Google Sheet titled **"Sticky Todo Tracker"**:

- **Log tab** — one row per task, every day, newest first, with a
  dark-styled frozen header. Completed tasks are dimmed and struck through;
  everything else stays plain.
- **Summary tab** — total / completed / pending counts, a breakdown by
  priority, and two live pie charts (Done vs. Pending, and tasks by
  priority) that update automatically on every sync.

### Setup

1. Install the extra dependencies:
   ```bash
   pip install gspread google-auth-oauthlib
   ```
2. In the [Google Cloud Console](https://console.cloud.google.com/), create
   a project, then enable the **Google Sheets API** and **Google Drive
   API**.
3. Create an **OAuth Client ID** of type **Desktop app** and download the
   JSON file.
4. Save it as:
   ```
   ~/.sticky_todo/credentials.json
   ```
   (Windows: `%USERPROFILE%\.sticky_todo\credentials.json`)
5. Restart Sticky Todo, then right-click the title bar → **Sync to Google
   Sheets now**. A browser window opens once so you can sign in and grant
   access — after that, a token is cached locally and it syncs silently in
   the background.
6. Right-click → **Open Google Sheet** any time to jump straight to it.

## Project structure

```
sticky_todo.py    Main application — window, UI, todo logic, persistence
sheets_sync.py    Optional Google Sheets sync (imported lazily, never required)
```

## Notes on platform support

The core todo functionality (add/complete/delete/reorder/prioritize,
per-day navigation, persistence) works anywhere Tkinter runs. The
following are Windows-only and no-op silently elsewhere:

- Rounded window corners
- Hiding from the taskbar/Alt+Tab
- The bulletproof always-on-top watchdog (via `SetWindowPos`)
- "Attach to desktop" mode
- Start-with-Windows autostart
- The system tray icon

## License

MIT — see [LICENSE](LICENSE) for the full text.
