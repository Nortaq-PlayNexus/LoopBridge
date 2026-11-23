# Python API

LoopBridge is primarily a CLI/GUI tool, but the engine is importable and
driver-agnostic. This is useful for embedding the relay loop in another app or
writing your own front end.

## Minimal example

```python
from loopbridge.config.profiles import Profile
from loopbridge.core.orchestrator import Orchestrator
from loopbridge.core.text_engine import TextEngine
from loopbridge.drivers.mock import MockChatGPTDriver, MockOpenCodeDriver

profile = Profile()
profile.loop.mode = "count"
profile.loop.count = 2

text = TextEngine()
cgpt = MockChatGPTDriver(reply_latency_polls=1, cfg=profile.chatgpt, text=text,
                         initial_reply="[ChatGPT] hello")
oc = MockOpenCodeDriver(done_after_polls=1, cfg=profile.opencode, text=text)

orch = Orchestrator(profile, cgpt, oc, text, on_log=print)
stats = orch.run()
print(stats.to_dict())
```

## `Profile`

```python
from loopbridge.config.profiles import Profile

profile = Profile.load("loopbridge-profile.json")
profile.chatgpt.copy_method = "cdp"
profile.opencode.completion_mode = "api"
profile.save("my-profile.json")
```

All sections are dataclasses: `loop`, `timing`, `windows`, `chatgpt`,
`opencode`, `text`, `watchdog`, `debug`.

## `Orchestrator`

```python
Orchestrator(
    profile,
    cgpt_driver,
    oc_driver,
    text_engine,
    window_manager=None,
    window_handles=None,
    on_log=None,       # (message, level) -> None
    on_phase=None,     # (phase, status, detail) -> None
    on_stats=None,     # (RunStats) -> None
    on_reply=None,     # (kind, text) -> None
)
```

`run()` returns `RunStats`:

```python
{
  "loops_completed": 2,
  "errors": 0,
  "retries": 0,
  "aborted": False,
  "elapsed_s": 1.234,
  "phases": {"COPY_CHATGPT_REPLY": {"count": 2, "total_time_s": 0.1, "last_time_s": 0.05}, ...}
}
```

## `LoopController`

Accessible as `orchestrator.controller`:

```python
orch.controller.pause()
orch.controller.resume()
orch.controller.step()          # one phase, then pause
orch.controller.request_stop()
orch.controller.is_paused
orch.controller.stop_requested
```

## `TextEngine`

```python
from loopbridge.core.text_engine import TextEngine

text = TextEngine(sanitize_ansi=True, strip_markdown=False, max_len=0)
clean = text.transform("\x1b[32mhello\x1b[0m\r\nworld")
text.copy(clean)
text.read()
text.history
```

## Drivers

Implement `ChatGPTDriver` or `OpenCodeDriver` from
`loopbridge.drivers.base`:

```python
from loopbridge.drivers.base import ChatGPTDriver

class MyDriver(ChatGPTDriver):
    def wait_for_reply_done(self, deadline: float) -> None: ...
    def copy_latest_reply(self) -> str: ...
    def paste_and_send(self, text: str) -> None: ...
```

Raise `CopyError`, `SendError`, or `CompletionError` from `loopbridge.core.errors`
so the watchdog and retry policy can classify failures.

## Building real drivers

`loopbridge.app.build_real_drivers(profile, log)` returns
`(chatgpt_driver, opencode_driver, window_manager)` using the profile to choose
UIA/CDP and TUI/API. `build_simulated_drivers(profile, log)` returns the mocks.
