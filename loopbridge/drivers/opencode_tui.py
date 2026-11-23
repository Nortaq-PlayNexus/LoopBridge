"""OpenCode driver: drives the OpenCode TUI inside the PowerShell window.

Completion detection (config `completion_mode`):
  * screen_marker   — poll the terminal's UIA text for a marker regex
                      (default: a bare prompt line, "> ").
  * clipboard_noop  — after submit, repeatedly try select+copy; when the
                      selected content stops changing, assume the reply ended.

Reply capture (config `capture`):
  * select_all_copy      — select everything visible and copy (clipboard is
                           then the full transcript tail).
  * anchor_last_block    — select from the anchor (end of the prompt echo)
                           to the end of the window and copy.

Terminal TUIs expose a limited UIA tree, so these are best-effort strategies
that work well with Windows Terminal. The API driver (opencode_api.py) is the
exact alternative when you need guaranteed completion signals.
"""

from __future__ import annotations

import re
import time
from typing import Optional

from ..config.profiles import OpenCodeConfig
from ..core.errors import CompletionError, CopyError, SendError
from ..core.text_engine import TextEngine
from .base import OpenCodeDriver, WindowHandle, WindowManager


class UiaOpenCodeDriver(OpenCodeDriver):
    def __init__(self, window: WindowHandle, wm: WindowManager,
                 cfg: OpenCodeConfig, text: TextEngine, log=None) -> None:
        self.window = window
        self.wm = wm
        self.cfg = cfg
        self.text = text
        self._log = log or (lambda msg, level="info": None)
        self._submitted_text = ""

    # --------------------------------------------------------------- submit
    def submit(self, text: str) -> None:
        self._submitted_text = text
        self.wm.focus(self.window)
        self.text.copy(text)
        self.wm.send_keys("{CTRL}v", wait_ms=250)
        if self.cfg.submit == "paste_select_enter":
            # "select" the pasted prompt, then submit (matches the user's flow)
            self.wm.send_keys("{CTRL}a", wait_ms=100)
        self.wm.send_keys("{ENTER}", wait_ms=200)
        time.sleep(0.5)

    # --------------------------------------------------------------- wait
    def wait_until_done(self, deadline: float) -> None:
        if self.cfg.completion_mode == "clipboard_noop":
            self._wait_clipboard_noop(deadline)
        else:
            self._wait_screen_marker(deadline)

    def _wait_screen_marker(self, deadline: float) -> None:
        interval = 0.8
        marker = re.compile(self.cfg.marker_regex)
        while time.monotonic() < deadline:
            self.wm.focus(self.window)
            content = self._terminal_text()
            if content and marker.search(content):
                return
            time.sleep(interval)
        raise CompletionError(
            f"OpenCode did not reach completion marker {self.cfg.marker_regex!r} "
            f"before the deadline."
        )

    def _wait_clipboard_noop(self, deadline: float) -> None:
        """Sample select+copy until the content stabilises (heuristic)."""
        stable_rounds = 0
        last = None
        interval = 1.0
        while time.monotonic() < deadline:
            self.wm.focus(self.window)
            self.wm.send_keys("{CTRL}a", wait_ms=100)
            self.wm.send_keys("{CTRL}c", wait_ms=200)
            content = self.text.read()
            if content == last and len(content) > 20:
                stable_rounds += 1
                if stable_rounds >= 2:
                    return
            else:
                stable_rounds = 0
                last = content
            time.sleep(interval)
        raise CompletionError("Clipboard-noop completion detection timed out.")

    # --------------------------------------------------------------- capture
    def copy_latest_reply(self) -> str:
        self.wm.focus(self.window)
        if self.cfg.capture == "anchor_last_block":
            content = self._capture_anchor()
        else:
            content = self._capture_select_all()
        if not content.strip():
            raise CopyError("OpenCode reply capture produced empty text.")
        return content

    def _capture_select_all(self) -> str:
        self.wm.send_keys("{CTRL}a", wait_ms=100)
        self.wm.send_keys("{CTRL}c", wait_ms=250)
        return self.text.read()

    def _capture_anchor(self) -> str:
        """Select from the prompt echo to the end of the window, then copy."""
        self.wm.send_keys("{CTRL}a", wait_ms=100)
        self.wm.send_keys("{END}", wait_ms=100)
        self.wm.send_keys("{CTRL}c", wait_ms=250)
        return self.text.read()

    # --------------------------------------------------------------- helpers
    def _terminal_text(self) -> str:
        """Best-effort read of the terminal window text via the UIA tree."""
        ctrl = self.window.control
        if ctrl is None:
            return ""
        chunks = []
        try:
            for el in self._walk(ctrl, max_depth=5):
                cls = ""
                try:
                    cls = (el.ClassName or "")
                except Exception:
                    continue
                if cls in ("Edit", "Document", "Text"):
                    for getter in ("GetValue", "GetText", "window_text"):
                        fn = getattr(el, getter, None)
                        if fn is None:
                            continue
                        try:
                            chunks.append(fn() or "")
                            break
                        except Exception:
                            continue
        except Exception:
            return ""
        return "\n".join(chunks)

    def _walk(self, root, max_depth: int = 5):
        out = []
        queue = [(root, 0)]
        seen = 0
        while queue and seen < 2000:
            el, depth = queue.pop(0)
            if depth > max_depth:
                continue
            seen += 1
            out.append(el)
            try:
                for child in el.GetChildren():
                    queue.append((child, depth + 1))
            except Exception:
                pass
        return out
