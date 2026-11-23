"""End-to-end tests for the LoopBridge orchestrator (run anywhere, no Windows).

Run with:  python tests/test_loop.py
"""

from __future__ import annotations

import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from loopbridge.config.profiles import Profile
from loopbridge.core.errors import CompletionError
from loopbridge.core.orchestrator import Orchestrator
from loopbridge.core.text_engine import TextEngine
from loopbridge.drivers.mock import MockChatGPTDriver, MockOpenCodeDriver


def make_orch(profile: Profile, cgpt, oc, log=None):
    text = TextEngine(sanitize_ansi=True)
    lines = []
    if log is None:
        def log(msg, level="info"):
            lines.append((level, msg))
    orch = Orchestrator(profile, cgpt, oc, text, on_log=log)
    return orch, lines


def test_full_relay_loop():
    """The core requirement: GPT reply → OpenCode → OC reply → GPT, looping."""
    profile = Profile()
    profile.loop.mode = "count"
    profile.loop.count = 3
    profile.watchdog.default_timeout_s = 5.0

    text = TextEngine()
    cgpt = MockChatGPTDriver(reply_latency_polls=1, cfg=profile.chatgpt, text=text,
                                initial_reply="[ChatGPT] the answer to your first question")
    oc = MockOpenCodeDriver(done_after_polls=1, cfg=profile.opencode, text=text)

    orch, lines = make_orch(profile, cgpt, oc)
    stats = orch.run()

    assert stats.loops_completed == 3, stats.to_dict()
    assert stats.errors == 0, lines
    # OpenCode must have received the ChatGPT replies (pasted + submitted)
    assert len(oc.received) == 3
    assert all(r.startswith("[ChatGPT]") for r in oc.received)
    # ChatGPT must have received the OpenCode replies (pasted + sent),
    # and each reply chains on what OpenCode received from ChatGPT
    assert len(cgpt.received) == 3
    assert all(r.startswith("[OpenCode] worked on: [ChatGPT]") for r in cgpt.received)
    print("PASS test_full_relay_loop — 3 iterations relayed correctly")


def test_pause_stop():
    """Stop is honoured mid-run."""
    profile = Profile()
    profile.loop.mode = "count"
    profile.loop.count = 100
    profile.timing.between_loops_ms = 0
    profile.watchdog.default_timeout_s = 5.0

    cgpt = MockChatGPTDriver(reply_latency_polls=0, initial_reply="[ChatGPT] initial answer")
    oc = MockOpenCodeDriver(done_after_polls=0)
    orch, _ = make_orch(profile, cgpt, oc)

    import threading
    t = threading.Thread(target=lambda: orch.run())
    t.start()
    import time
    time.sleep(0.3)
    orch.controller.request_stop()
    t.join(timeout=5)

    assert t.is_alive() is False
    assert orch.controller.stop_requested
    print("PASS test_pause_stop — loop stopped cleanly")


def test_watchdog_timeout_and_retry():
    """A hanging OpenCode phase triggers retries, then aborts (continue_on_error off)."""
    profile = Profile()
    profile.loop.mode = "count"
    profile.loop.count = 1
    profile.watchdog.default_timeout_s = 0.3
    profile.watchdog.retries = 2
    profile.watchdog.backoff_ms = 10
    profile.watchdog.continue_on_error = False

    cgpt = MockChatGPTDriver(reply_latency_polls=0, initial_reply="[ChatGPT] initial answer")
    oc = MockOpenCodeDriver(done_after_polls=0)
    oc.hang_forever = True

    orch, lines = make_orch(profile, cgpt, oc)
    stats = orch.run()

    assert stats.aborted is True
    assert stats.loops_completed == 0
    assert stats.errors >= 1
    assert stats.retries >= 2
    print("PASS test_watchdog_timeout_and_retry — aborted after retries as configured")


def test_text_sanitize():
    """ANSI garbage from the terminal is stripped before pasting."""
    text = TextEngine(sanitize_ansi=True, prefix="", suffix="")
    messy = "\x1b[32mhello\x1b[0m world\x07\nsecond line"
    clean = text.transform(messy)
    assert "\x1b" not in clean and "\x07" not in clean
    assert clean == "hello world\nsecond line"
    print("PASS test_text_sanitize — ANSI/control chars stripped")


def test_dry_run_does_not_send():
    """Dry-run mode logs the intended actions but does not call send."""
    profile = Profile()
    profile.loop.mode = "count"
    profile.loop.count = 1
    profile.debug.dry_run = True
    profile.watchdog.default_timeout_s = 5.0

    cgpt = MockChatGPTDriver(reply_latency_polls=0, initial_reply="[ChatGPT] initial answer")
    oc = MockOpenCodeDriver(done_after_polls=0, initial_reply="[OpenCode] existing reply")
    orch, lines = make_orch(profile, cgpt, oc)
    stats = orch.run()

    assert stats.loops_completed == 1
    assert oc.received == [], "dry-run must not submit to OpenCode"
    assert cgpt.received == [], "dry-run must not send to ChatGPT"
    assert any("dry-run" in msg for _, msg in lines)
    print("PASS test_dry_run_does_not_send")


if __name__ == "__main__":
    test_full_relay_loop()
    test_pause_stop()
    test_watchdog_timeout_and_retry()
    test_text_sanitize()
    test_dry_run_does_not_send()
    print("\nAll loop tests passed.")
