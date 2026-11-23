# Configuration

The default profile is [`loopbridge-profile.json`](../loopbridge-profile.json).
Load a different one with `--profile PATH`, or use **Load profile… / Save
profile…** in the GUI.

Every field is defined in [`loopbridge/config/profiles.py`](../loopbridge/config/profiles.py).
Unknown keys are ignored on load.

## `loop`

| Key | Type | Default | Meaning |
|---|---|---|---|
| `mode` | string | `infinite` | `infinite` or `count` |
| `count` | int | `0` | Iterations to run; `0` means unlimited |
| `start_phase` | string | `chatgpt_to_opencode` | Intended starting direction |

## `timing`

| Key | Type | Default | Meaning |
|---|---|---|---|
| `global_multiplier` | float | `1.0` | Scales every configured delay |
| `phase_delays_ms` | object | `{}` | Per-phase extra delay, keyed by phase value |
| `between_loops_ms` | int | `500` | Pause between completed iterations |

## `windows`

| Key | Type | Default | Meaning |
|---|---|---|---|
| `brave.title_regex` | string | `.*ChatGPT.*` | Title regex for the ChatGPT window |
| `brave.processes` | list | `["brave.exe"]` | Process hints |
| `brave.match` | string | `first` | `first` or `all` |
| `powershell.title_regex` | string | `.*(OpenCode\|opencode\|PowerShell).*` | Title regex for the terminal |
| `powershell.processes` | list | `["WindowsTerminal.exe", "powershell.exe", "pwsh.exe"]` | Process hints |
| `powershell.match` | string | `first` | `first` or `all` |
| `auto_restore` | bool | `true` | Restore a minimized window before acting |
| `set_topmost` | bool | `false` | Keep the target window on top while driving |
| `find_interval_ms` | int | `500` | Window re-scan interval |

## `chatgpt`

| Key | Type | Default | Meaning |
|---|---|---|---|
| `copy_method` | string | `autocopy_button` | `autocopy_button`, `select_all`, or `cdp` |
| `done_detection` | string | `uia_poll` | `uia_poll`, `stop_button_gone`, or `cdp` |
| `send_key` | string | `enter` | `enter`, `ctrl_enter`, or `custom` |
| `custom_send_keys` | string | `""` | Keys used when `send_key = custom` |
| `paste_method` | string | `clipboard` | `clipboard` or `typing` |
| `poll_interval_ms` | int | `800` | Reply-completion poll interval |
| `timeout_s` | float | `300.0` | Reply wait timeout |

### CDP setup

```powershell
brave.exe --remote-debugging-port=9222
```

Then set `chatgpt.copy_method = "cdp"`. The driver connects to
`http://127.0.0.1:9222/json`, finds the ChatGPT tab, and evaluates JavaScript
in the page.

## `opencode`

| Key | Type | Default | Meaning |
|---|---|---|---|
| `completion_mode` | string | `screen_marker` | `screen_marker`, `clipboard_noop`, or `api` |
| `marker_regex` | string | `^>\s*$` | Terminal line that means "done" |
| `submit` | string | `paste_select_enter` | `paste_enter` or `paste_select_enter` |
| `capture` | string | `select_all_copy` | `select_all_copy` or `anchor_last_block` |
| `timeout_s` | float | `600.0` | OpenCode wait timeout |
| `command` | string | `opencode run --format json` | API-mode command |
| `working_dir` | string | `""` | API-mode working directory |
| `visible_console` | bool | `true` | Show the API-mode console window |
| `done_event_types` | list | `["done","end","exit","error"]` | JSON event types treated as completion |

## `text`

| Key | Type | Default | Meaning |
|---|---|---|---|
| `sanitize_ansi` | bool | `true` | Strip ANSI/control characters |
| `strip_markdown` | bool | `false` | Remove markdown code fences |
| `prefix` | string | `""` | Prepended to every copied reply |
| `suffix` | string | `""` | Appended to every copied reply |
| `max_len` | int | `0` | Character cap; `0` means no cap |

## `watchdog`

| Key | Type | Default | Meaning |
|---|---|---|---|
| `default_timeout_s` | float | `300.0` | Default phase deadline |
| `phase_timeouts_s` | object | `{}` | Per-phase overrides |
| `retries` | int | `3` | Retries per failed phase |
| `backoff_ms` | int | `1000` | Base backoff; grows per attempt |
| `continue_on_error` | bool | `false` | Keep looping after exhausted retries |
| `max_run_time_s` | float | `0.0` | Stop after N seconds; `0` means no cap |

## `debug`

| Key | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `false` | General debug logging |
| `dry_run` | bool | `false` | Act but do not actually send |
| `screenshots` | bool | `false` | Capture a screenshot per phase |
| `capture_tree` | bool | `false` | Log the UIA tree on failures |

## Recipes

### Safe rehearsal

```powershell
python run.py --simulate --count 3
```

Uses the mock drivers: no windows, no clipboard, no sends.

### Verify window targeting

```powershell
python run.py --dry-run --count 1
```

Finds and focuses the windows, logs the intended text, and does not submit.

### Exact OpenCode completion

```json
"opencode": { "completion_mode": "api" }
```

### Most robust ChatGPT read/write

```json
"chatgpt": { "copy_method": "cdp" }
```

Launch Brave with `--remote-debugging-port=9222` first.
