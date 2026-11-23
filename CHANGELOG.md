# Changelog

All notable changes to LoopBridge are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.0.0] — 2026-11-23

### Added

- Six-phase relay loop between ChatGPT in Brave and OpenCode in a PowerShell
  window: wait, copy, paste, wait, copy, send.
- ChatGPT drivers: UIA keyboard driver (default) and Chrome DevTools Protocol
  driver (`copy_method = "cdp"`).
- OpenCode drivers: terminal TUI driver (default) and `opencode run --format
  json` API driver (`completion_mode = "api"`).
- Mock drivers for simulation and tests.
- PySide6 dashboard: phase stepper, live stats, reply previews, colour-coded
  log, Start/Pause/Resume/Stop/Step once, Dry-run and Simulate toggles.
- Tabbed settings dialog covering every profile option, plus raw JSON editing.
- JSON profiles with load/save presets.
- Per-phase watchdog deadlines, retries, exponential backoff, optional
  continue-on-error, and an optional maximum run time.
- ANSI/control-character sanitising, optional markdown-fence stripping,
  prefix/suffix and length cap.
- Console runner with `--simulate`, `--dry-run`, `--count`, `--profile`, and
  `--gui`.
- Typed error hierarchy so the retry policy classifies failures by type.
- Tests: full relay loop, pause/stop, watchdog retry + abort, ANSI sanitising,
  dry-run, and a headless GUI smoke test.
- CI for Python 3.10–3.12 on Windows and a tag-driven PyInstaller release
  workflow.
- Documentation, screenshots, social preview, and the house README.

### Fixed

- Dashboard stats grid calls passed the wrong number of arguments, so the main
  window could not be constructed.
- Elapsed time compared a monotonic clock against an epoch timestamp and
  displayed a negative value.
- The GUI worker thread's event loop kept running after a loop finished.
- Test output crashed on the Windows `cp1252` console when printing check
  marks; the tests now reconfigure stdout to UTF-8.
