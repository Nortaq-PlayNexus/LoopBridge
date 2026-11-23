# Development

## Setup

```powershell
git clone https://github.com/Nortaq-PlayNexus/LoopBridge
cd LoopBridge
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` includes the Windows automation packages and PySide6. The
loop tests themselves do not need Windows or a display.

## Run

```powershell
python run.py --simulate --count 2   # no windows
python run.py                        # real relay
python run.py --gui                  # desktop UI
```

## Tests

```powershell
python tests/test_loop.py
```

Five end-to-end tests: full relay loop, pause/stop, watchdog retry + abort, ANSI
sanitising, and dry-run.

```powershell
$env:QT_QPA_PLATFORM="offscreen"; python tests/smoke_gui.py
```

Headless Qt smoke test: builds the dashboard, opens settings, runs a simulated
loop, and checks the UI state.

Both are plain Python scripts with `assert`s. `pytest` can also collect the
`test_*` functions if you prefer.

## Code layout

```
loopbridge/
├── __main__.py          CLI parsing and dispatch
├── app.py               driver factory, console runner, GUI launcher
├── core/                orchestrator, state, watchdog, text engine, errors
├── drivers/             ChatGPT / OpenCode / window / mock drivers
├── config/profiles.py   dataclasses + JSON (de)serialisation
└── ui/                  dashboard, settings dialog, tray, theme
```

## Adding a driver

1. Implement `ChatGPTDriver` or `OpenCodeDriver` from
   [`loopbridge/drivers/base.py`](../loopbridge/drivers/base.py).
2. Raise the typed errors from `core/errors.py` (`CopyError`, `SendError`,
   `CompletionError`) rather than generic exceptions.
3. Wire the driver into `build_real_drivers()` in `app.py`.
4. Add a mock path if the driver should be testable without hardware.
5. Add a test using the mock or a fake window manager.

## Debugging

- `--simulate` exercises the full orchestrator without touching windows.
- `--dry-run` verifies window targeting and logs the intended text.
- `debug.enabled` and `debug.capture_tree` produce extra logging.
- `debug.screenshots` is reserved for per-phase captures.
- The GUI log is colour-coded: info, warn, error, debug.
- The watchdog log line names the exact phase and elapsed time.

### UIA troubleshooting

The UIA drivers are best-effort. If ChatGPT or the terminal changes:

1. Try `chatgpt.copy_method = "cdp"` (Brave with a debugging port).
2. Try `opencode.completion_mode = "api"`.
3. Adjust `windows.*.title_regex` and the process lists.
4. Increase `watchdog.default_timeout_s` for slow machines.

Do not hard-code fragile selectors without a fallback; prefer the CDP/API paths.

## Screenshots and social preview

```powershell
python scripts/capture_screenshots.py
python scripts/make_social_preview.py
```

`capture_screenshots.py` renders the real PySide6 UI (Windows platform plugin)
and writes `docs/screenshots/01..04`. `make_social_preview.py` writes the
1280×640 `docs/assets/social-preview.png` with Pillow.

## Style

- Type hints on public functions; `from __future__ import annotations`.
- Dataclasses for configuration; no loose dicts across module boundaries.
- Typed errors, never message string-matching for control flow.
- Keep the orchestrator driver-agnostic.
- No network calls and no secrets in the app.

## Pull requests

See [`CONTRIBUTING.md`](../CONTRIBUTING.md). Run both test commands before
opening a PR.
