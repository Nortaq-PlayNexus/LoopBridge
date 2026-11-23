# Contributing to LoopBridge

Thanks for taking a look. This is a small Windows desktop automation tool, so
changes should stay focused and testable.

## Setup

```powershell
git clone https://github.com/Nortaq-PlayNexus/LoopBridge
cd LoopBridge
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Before you open a PR

Run both test commands:

```powershell
python tests/test_loop.py
$env:QT_QPA_PLATFORM="offscreen"; python tests/smoke_gui.py
```

If you changed the UI, also run:

```powershell
python scripts/capture_screenshots.py
```

and include updated screenshots if the layout changed meaningfully.

## What to change

- Keep the orchestrator driver-agnostic. New automation belongs in `drivers/`.
- Raise the typed errors from `core/errors.py`, not generic exceptions.
- Add configuration as a dataclass field in `config/profiles.py`, then expose it
  in `ui/settings_page.py` if users should edit it.
- Prefer CDP/API fallbacks over brittle new UIA selectors.
- Do not add network calls, telemetry, or secrets.

## Code style

- Python 3.10+, type hints on public functions, `from __future__ import
  annotations`.
- Dataclasses for structured config and state.
- Keep comments useful; explain *why*, not *what*.
- No new runtime dependencies without a clear reason.

## Commit and PR

- One logical change per PR.
- Describe the problem, the fix, and how you tested it.
- Link an issue when one exists.
- Never include tokens, profile files with personal data, or screenshots of
  private conversations.

## Reporting bugs

Use the bug report template. Include:

- Windows version and Python version
- driver mode (`uia`, `cdp`, `tui`, `api`)
- the exact profile section you changed
- the log lines around the failure (redact anything private)

## Security

Do not report security issues in a public issue. See [SECURITY.md](SECURITY.md).
