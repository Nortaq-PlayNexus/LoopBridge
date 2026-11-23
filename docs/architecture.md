# Architecture

LoopBridge is a small, typed relay engine with a Qt front end. The engine does
not know whether it is driving real windows, a browser's DevTools endpoint, the
OpenCode CLI, or an in-memory mock. That separation is the core design choice.

## Data flow

```
┌────────────────────┐        clipboard / keys        ┌────────────────────┐
│  ChatGPT in Brave  │ ─────────────────────────────► │  OpenCode terminal │
│  (UIA or CDP)      │ ◄───────────────────────────── │  (TUI or CLI)      │
└────────────────────┘        clipboard / keys        └────────────────────┘
          ▲                                                     ▲
          │                    Orchestrator                     │
          └────────────── phase state machine ──────────────────┘
                              │        ▲
                       watchdog        │ stats / replies
                              │        │
                     ┌────────▼────────┴────────┐
                     │  Console runner / PySide6 │
                     │  dashboard (worker thread)│
                     └───────────────────────────┘
```

## One iteration

`core/state.py` defines the phase order:

1. `WAIT_CHATGPT_REPLY`
2. `COPY_CHATGPT_REPLY`
3. `PASTE_OPENCODE_SUBMIT`
4. `WAIT_OPENCODE_DONE`
5. `COPY_OPENCODE_REPLY`
6. `PASTE_CHATGPT_SEND`

The loop repeats until the configured count is reached, the run-time cap is hit,
or a stop is requested.

## Components

### `core/orchestrator.py`

- `Orchestrator.run()` owns the iteration loop.
- `Orchestrator._execute_phase()` applies retries, backoff, and the watchdog
  guard to every phase.
- `Orchestrator._dispatch()` maps a phase to a driver call.
- `LoopController` is the thread-safe control surface: `pause`, `resume`,
  `step`, `request_stop`, `reset`. The GUI and console runner both use it.

### `core/watchdog.py`

`LoopWatchdog.guard(phase)` returns a `PhaseGuard` with a monotonic deadline.
Waiting drivers receive that deadline, so a hung UI poll cannot block the loop
forever. Per-phase overrides come from `watchdog.phase_timeouts_s`.

### `core/text_engine.py`

All clipboard traffic passes through `TextEngine`:

- normalises line endings,
- strips ANSI/control characters,
- optionally strips markdown fences,
- trims trailing whitespace and collapses blank runs,
- applies prefix/suffix and an optional length cap.

It falls back to an in-memory clipboard when `pyperclip` is unavailable, which
keeps tests and simulation headless.

### `drivers/base.py`

Two abstract interfaces:

- `ChatGPTDriver`: `wait_for_reply_done`, `copy_latest_reply`, `paste_and_send`
- `OpenCodeDriver`: `submit`, `wait_until_done`, `copy_latest_reply`

`WindowManager` abstracts finding and focusing a window.

Concrete drivers:

| File | Role |
|---|---|
| `drivers/chatgpt_ui.py` | UIA tree + keyboard against Brave |
| `drivers/chatgpt_cdp.py` | DevTools Protocol JavaScript in the page |
| `drivers/opencode_tui.py` | Terminal text markers + clipboard capture |
| `drivers/opencode_api.py` | `opencode run --format json` child process |
| `drivers/mock.py` | Deterministic simulated drivers |
| `drivers/window_manager.py` | UIA window discovery, focus, key sending |

### `config/profiles.py`

Every option is a dataclass; `Profile` loads/saves JSON. Unknown keys are
ignored on load, and the settings dialog merges valid raw JSON over the form
values.

### `core/errors.py`

All expected failures derive from `LoopError`:

`ConfigError`, `TargetWindowNotFound`, `FocusError`, `CopyError`, `SendError`,
`CompletionError`, `PhaseTimeout`, `LoopAborted`.

The retry policy classifies errors by type, not by string matching.

## Threading

The console runner executes the loop on the calling thread.

The GUI creates a `QThread` and a `_Worker` object. `Orchestrator` callbacks
emit Qt signals; the main thread updates the dashboard. The `LoopController`
uses `threading.Event`s, so Start/Pause/Resume/Stop/Step are safe from the UI.

When the worker finishes, `MainWindow._finished()` stops the thread's event
loop. Closing the window while a loop is running prompts first and requests a
stop.

## Failure model

```
phase fails
   ├─ retries remaining → backoff, retry the same phase
   ├─ continue_on_error → log error, move on
   └─ otherwise         → LoopAborted, stats.aborted = true
```

A stop request raises `LoopAborted` at the next phase boundary. The loop always
logs a final summary and emits the last `RunStats`.

## Extension points

- Add a new driver by implementing the abstract interface and wiring it in
  `app.build_real_drivers()`.
- Add a phase-specific timeout in `watchdog.phase_timeouts_s`.
- Add a text transform in `TextEngine.transform()` and expose it in
  `TextConfig`.
- Add a profile field in `config/profiles.py` and, if it should be editable,
  in `ui/settings_page.py`.
