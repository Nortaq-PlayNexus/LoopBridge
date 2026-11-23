"""Application assembly: driver factory, console runner, GUI launcher."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, Tuple

from .config.profiles import Profile
from .core.errors import ConfigError
from .core.orchestrator import Orchestrator, RunStats
from .core.state import RunStats as _RS  # re-export convenience
from .core.text_engine import TextEngine
from .drivers.base import OpenCodeDriver, WindowManager
from .drivers.chatgpt_cdp import CdpChatGPTDriver
from .drivers.chatgpt_ui import UiaChatGPTDriver
from .drivers.mock import MockChatGPTDriver, MockOpenCodeDriver
from .drivers.opencode_api import ApiOpenCodeDriver
from .drivers.opencode_tui import UiaOpenCodeDriver
from .drivers.window_manager import UiaWindowManager


def build_text_engine(profile: Profile) -> TextEngine:
    t = profile.text
    eng = TextEngine(
        sanitize_ansi=t.sanitize_ansi,
        strip_markdown=t.strip_markdown,
        prefix=t.prefix,
        suffix=t.suffix,
        max_len=t.max_len,
    )
    return eng


def build_simulated_drivers(profile: Profile, log) -> Tuple[object, object, None]:
    """Mock drivers: the loop runs with no real windows (simulation)."""
    text = build_text_engine(profile)
    # Real usage: the loop starts after ChatGPT already produced a reply.
    # The simulation seeds that initial reply so the relay runs immediately.
    cgpt = MockChatGPTDriver(reply_latency_polls=2, cfg=profile.chatgpt, text=text,
                             initial_reply="[ChatGPT] Simulated reply to the first question.")
    oc = MockOpenCodeDriver(done_after_polls=2, cfg=profile.opencode, text=text)
    return cgpt, oc, None


def build_real_drivers(profile: Profile, log) -> Tuple[object, object, WindowManager]:
    """Real drivers on Windows 11.

    ChatGPT: CDP driver when `copy_method == "cdp"`, else the UIA keyboard
    driver against the Brave window.
    OpenCode: API driver when `completion_mode == "api"`, else the TUI driver
    against the PowerShell window.
    """
    if not _is_windows():
        raise ConfigError(
            "Real (window-driving) mode requires Windows 11. Use --simulate "
            "to rehearse the loop elsewhere."
        )
    text = build_text_engine(profile)
    wm = UiaWindowManager(
        find_interval_ms=profile.windows.find_interval_ms,
        auto_restore=profile.windows.auto_restore,
        set_topmost=profile.windows.set_topmost,
    )

    if profile.chatgpt.copy_method == "cdp":
        cgpt = CdpChatGPTDriver(port=9222, cfg=profile.chatgpt, text=text, log=log)
        brave_window = None
    else:
        brave_window = wm.find(profile.windows.brave)
        log(f"Using Brave window: {brave_window.title!r}")
        cgpt = UiaChatGPTDriver(brave_window, wm, profile.chatgpt, text, log=log)

    if profile.opencode.completion_mode == "api":
        oc = ApiOpenCodeDriver(profile.opencode, text, log=log)
        ps_window = None
    else:
        ps_window = wm.find(profile.windows.powershell)
        log(f"Using PowerShell window: {ps_window.title!r}")
        oc = UiaOpenCodeDriver(ps_window, wm, profile.opencode, text, log=log)

    handles = {}
    if brave_window:
        handles["brave"] = brave_window
    if ps_window:
        handles["powershell"] = ps_window
    return cgpt, oc, wm


def run_console(
    profile: Profile,
    simulate: bool = False,
    count: Optional[int] = None,
    log: Optional[Callable[[str, str], None]] = None,
) -> RunStats:
    """Run the loop in the foreground and print everything to stdout."""
    if log is None:
        def log(msg: str, level: str = "info") -> None:
            prefix = {"info": "[i]", "warn": "[!]", "error": "[x]", "debug": "[d]"}.get(level, "[i]")
            print(f"{prefix} {msg}")

    if count is not None:
        profile.loop.mode = "count"
        profile.loop.count = count

    if simulate:
        cgpt, oc, wm = build_simulated_drivers(profile, log)
        log("SIMULATION MODE — no real windows will be touched.", "warn")
    else:
        cgpt, oc, wm = build_real_drivers(profile, log)

    orch = Orchestrator(profile, cgpt, oc, build_text_engine(profile),
                        window_manager=wm, on_log=log)
    return orch.run()


def launch_gui(profile_path: str) -> None:
    """Launch the PySide6 desktop UI (Windows 11)."""
    from .ui.main_window import run_gui

    run_gui(profile_path)


def _is_windows() -> bool:
    import sys

    return sys.platform.startswith("win")
