"""Profile configuration for LoopBridge.

Every custom option from the design doc is represented here as a dataclass.
Profiles serialize to/from JSON so users can save presets and tweak them
without touching code.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class LoopConfig:
    mode: str = "infinite"          # "infinite" | "count"
    count: int = 0                  # target loop count (0 = unlimited)
    start_phase: str = "chatgpt_to_opencode"  # which relay direction to start with


@dataclass
class TimingConfig:
    global_multiplier: float = 1.0
    phase_delays_ms: Dict[str, int] = field(default_factory=dict)
    between_loops_ms: int = 500


@dataclass
class WindowTarget:
    title_regex: str = ""
    processes: List[str] = field(default_factory=list)
    match: str = "first"            # "first" | "all"


@dataclass
class WindowConfig:
    brave: WindowTarget = field(default_factory=lambda: WindowTarget(
        title_regex=".*ChatGPT.*", processes=["brave.exe"]))
    powershell: WindowTarget = field(default_factory=lambda: WindowTarget(
        title_regex=".*(OpenCode|opencode|PowerShell).*",
        processes=["WindowsTerminal.exe", "powershell.exe", "pwsh.exe"]))
    auto_restore: bool = True
    set_topmost: bool = False
    find_interval_ms: int = 500


@dataclass
class ChatGPTConfig:
    copy_method: str = "autocopy_button"   # autocopy_button | select_all | cdp
    done_detection: str = "uia_poll"      # uia_poll | stop_button_gone | cdp
    send_key: str = "enter"               # enter | ctrl_enter | custom
    custom_send_keys: str = ""
    paste_method: str = "clipboard"       # clipboard | typing
    poll_interval_ms: int = 800
    timeout_s: float = 300.0


@dataclass
class OpenCodeConfig:
    completion_mode: str = "screen_marker"  # screen_marker | clipboard_noop | api
    marker_regex: str = r"^>\s*$"
    submit: str = "paste_select_enter"     # paste_enter | paste_select_enter
    capture: str = "select_all_copy"       # select_all_copy | anchor_last_block
    timeout_s: float = 600.0
    command: str = "opencode run --format json"   # api mode command
    working_dir: str = ""
    visible_console: bool = True
    done_event_types: List[str] = field(default_factory=lambda: ["done", "end", "exit", "error"])


@dataclass
class TextConfig:
    sanitize_ansi: bool = True
    strip_markdown: bool = False
    prefix: str = ""
    suffix: str = ""
    max_len: int = 0


@dataclass
class WatchdogConfig:
    default_timeout_s: float = 300.0
    phase_timeouts_s: Dict[str, float] = field(default_factory=dict)
    retries: int = 3
    backoff_ms: int = 1000
    continue_on_error: bool = False
    max_run_time_s: float = 0.0    # 0 = no cap


@dataclass
class DebugConfig:
    enabled: bool = False
    dry_run: bool = False          # act but do not actually send
    screenshots: bool = False
    capture_tree: bool = False


@dataclass
class Profile:
    name: str = "default"
    loop: LoopConfig = field(default_factory=LoopConfig)
    timing: TimingConfig = field(default_factory=TimingConfig)
    windows: WindowConfig = field(default_factory=WindowConfig)
    chatgpt: ChatGPTConfig = field(default_factory=ChatGPTConfig)
    opencode: OpenCodeConfig = field(default_factory=OpenCodeConfig)
    text: TextConfig = field(default_factory=TextConfig)
    watchdog: WatchdogConfig = field(default_factory=WatchdogConfig)
    debug: DebugConfig = field(default_factory=DebugConfig)

    # ------------------------------------------------------------ (de)serialize
    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "Profile":
        p = cls()
        p.name = data.get("name", p.name)
        for section in ("loop", "timing", "windows", "chatgpt", "opencode", "text", "watchdog", "debug"):
            raw = data.get(section) or {}
            target = getattr(p, section)
            if section == "windows":
                if "brave" in raw:
                    target.brave = WindowTarget(**{k: v for k, v in raw["brave"].items() if k in WindowTarget.__dataclass_fields__})
                if "powershell" in raw:
                    target.powershell = WindowTarget(**{k: v for k, v in raw["powershell"].items() if k in WindowTarget.__dataclass_fields__})
                for k, v in raw.items():
                    if k in WindowConfig.__dataclass_fields__ and k not in ("brave", "powershell"):
                        setattr(target, k, v)
            else:
                for k, v in raw.items():
                    if k in target.__dataclass_fields__:
                        setattr(target, k, v)
        return p

    @classmethod
    def load(cls, path: str | Path) -> "Profile":
        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


DEFAULT_PROFILE = Profile()
