"""Mock drivers: simulate ChatGPT and OpenCode without any real windows.

Used for:
  * the end-to-end loop test (tests/test_loop.py),
  * the `--simulate` console mode so the loop can be exercised anywhere,
  * dry-run rehearsals before touching the real UI.

The mocks model the important behaviours of the real drivers: async reply
generation with polling-based completion detection, and optional failure
injection (hang_forever) so the watchdog/retry path can be tested.
"""

from __future__ import annotations

import time
from typing import List, Optional

from ..config.profiles import ChatGPTConfig, OpenCodeConfig
from ..core.errors import CompletionError
from ..core.text_engine import TextEngine
from .base import ChatGPTDriver, OpenCodeDriver


class MockChatGPTDriver(ChatGPTDriver):
    """Simulates ChatGPT. `reply_latency_polls` controls how many polls a
    generation takes before it is 'done'."""

    def __init__(self, reply_latency_polls: int = 2,
                 cfg: Optional[ChatGPTConfig] = None,
                 text: Optional[TextEngine] = None,
                 initial_reply: str = "") -> None:
        self.cfg = cfg or ChatGPTConfig()
        self.text = text or TextEngine()
        self.reply_latency_polls = reply_latency_polls
        self._polls = 0
        # In real usage the loop is started after ChatGPT already produced a
        # reply; the mock accepts that initial reply up front.
        self._reply = initial_reply
        self.received: List[str] = []

    def wait_for_reply_done(self, deadline: float) -> None:
        while self._polls <= self.reply_latency_polls:
            if time.monotonic() > deadline:
                raise CompletionError("mock chatgpt: deadline exceeded")
            self._polls += 1
            time.sleep(0.05)

    def copy_latest_reply(self) -> str:
        return self._reply

    def paste_and_send(self, text: str) -> None:
        self.received.append(text)
        self._polls = 0
        self._reply = f"[ChatGPT] received and processed: {text[:80]}"


class MockOpenCodeDriver(OpenCodeDriver):
    """Simulates the OpenCode TUI."""

    def __init__(self, done_after_polls: int = 2,
                 cfg: Optional[OpenCodeConfig] = None,
                 text: Optional[TextEngine] = None,
                 initial_reply: str = "") -> None:
        self.cfg = cfg or OpenCodeConfig()
        self.text = text or TextEngine()
        self.done_after_polls = done_after_polls
        self._polls = 0
        self._reply = initial_reply
        self.received: List[str] = []
        self.hang_forever: bool = False

    def submit(self, text: str) -> None:
        self.received.append(text)
        self._polls = 0
        self._reply = f"[OpenCode] worked on: {text[:80]}"

    def wait_until_done(self, deadline: float) -> None:
        while self.hang_forever or self._polls <= self.done_after_polls:
            if time.monotonic() > deadline:
                raise CompletionError("mock opencode: deadline exceeded")
            self._polls += 1
            time.sleep(0.05)

    def copy_latest_reply(self) -> str:
        return self._reply
