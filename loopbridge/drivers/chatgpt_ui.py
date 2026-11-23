"""ChatGPT driver: keyboard/UIA automation inside the Brave browser window.

This is the default (no-browser-flags) driver. It works by:
  * focusing the Brave window,
  * polling the UIA tree for the last assistant message + its copy button /
    the "Stop generating" control to know when a reply is done,
  * copying the reply via the copy button (or select-all fallback),
  * focusing the composer and pasting + sending.

The selectors are best-effort against the live ChatGPT UI; when UI drift
breaks this driver, switch to the CDP driver (chatgpt_cdp.py) which reads
and writes the page directly.
"""

from __future__ import annotations

import re
import time
from typing import Optional, Tuple

from ..config.profiles import ChatGPTConfig
from ..core.errors import CopyError, SendError, TargetWindowNotFound
from ..core.text_engine import TextEngine
from .base import ChatGPTDriver, WindowHandle, WindowManager

# Heuristics for the UIA tree. ChatGPT is a React app rendered in a Chromium
# window, so we look for generic pane/text patterns rather than stable IDs.
COPY_BUTTON_RE = re.compile(r"^(copy|复制)\s*$", re.IGNORECASE)
STOP_BUTTON_RE = re.compile(r"^(stop|停止|stop generating)\s*$", re.IGNORECASE)
COMPOSER_HINTS = ("prompt", "textarea", "message", "composer")


class UiaChatGPTDriver(ChatGPTDriver):
    def __init__(self, window: WindowHandle, wm: WindowManager,
                 cfg: ChatGPTConfig, text: TextEngine, log=None) -> None:
        self.window = window
        self.wm = wm
        self.cfg = cfg
        self.text = text
        self._log = log or (lambda msg, level="info": None)
        self._send_keys_template = {
            "enter": "{ENTER}",
            "ctrl_enter": "{CTRL}{ENTER}",
            "custom": cfg.custom_send_keys or "{ENTER}",
        }.get(cfg.send_key, "{ENTER}")

    # --------------------------------------------------------------- waiting
    def wait_for_reply_done(self, deadline: float) -> None:
        interval = self.cfg.poll_interval_ms / 1000.0
        while time.monotonic() < deadline:
            self.wm.focus(self.window)
            state = self._inspect_last_assistant()
            if state is None:
                # No reply block found yet: ChatGPT may still be generating the
                # first message, or the tree is being rebuilt. Keep waiting.
                time.sleep(interval)
                continue
            has_copy, stop_active = state
            if has_copy and not stop_active:
                return
            time.sleep(interval)
        raise CopyError("Timed out waiting for ChatGPT to finish generating a reply.")

    def _inspect_last_assistant(self) -> Optional[Tuple[bool, bool]]:
        """Return (copy_button_present, stop_button_active) for the last message."""
        ctrl = self.window.control
        if ctrl is None:
            return None
        try:
            copy_found = False
            stop_active = False
            last_pane = None
            panes = self._find_panes(ctrl)
            if not panes:
                return None
            last_pane = panes[-1]
            for el in self._walk(last_pane, max_depth=8):
                name = ""
                try:
                    name = (el.Name or "").strip()
                except Exception:
                    continue
                if COPY_BUTTON_RE.match(name):
                    copy_found = True
                if STOP_BUTTON_RE.match(name):
                    try:
                        if el.GetTogglePattern() is not None or el.GetSelectionPattern() is not None:
                            stop_active = True
                    except Exception:
                        stop_active = True
            return copy_found, stop_active
        except Exception:
            return None

    # --------------------------------------------------------------- copy
    def copy_latest_reply(self) -> str:
        self.wm.focus(self.window)
        if self.cfg.copy_method == "select_all":
            return self._copy_by_select_all()
        # default: click the copy button on the last assistant message
        ctrl = self.window.control
        if ctrl is None:
            raise CopyError("Brave window has no UIA control.")
        panes = self._find_panes(ctrl)
        if not panes:
            raise CopyError("Could not find a message pane in the ChatGPT window.")
        for el in self._walk(panes[-1], max_depth=8):
            name = ""
            try:
                name = (el.Name or "").strip()
            except Exception:
                continue
            if COPY_BUTTON_RE.match(name):
                self._click(el)
                time.sleep(0.4)
                content = self.text.read()
                if content.strip():
                    return content
                break
        # fallback: select-all within the message pane
        return self._copy_by_select_all()

    def _copy_by_select_all(self) -> str:
        ctrl = self.window.control
        if ctrl is None:
            raise CopyError("Brave window has no UIA control.")
        panes = self._find_panes(ctrl)
        if not panes:
            raise CopyError("Could not find a message pane in the ChatGPT window.")
        pane = panes[-1]
        try:
            pane.ClickLeft()
        except Exception:
            pass
        self.wm.send_keys("{CTRL}a", wait_ms=100)
        self.wm.send_keys("{CTRL}c", wait_ms=200)
        content = self.text.read()
        if not content.strip():
            raise CopyError("ChatGPT reply copy produced empty clipboard.")
        return content

    # --------------------------------------------------------------- send
    def paste_and_send(self, text: str) -> None:
        self.wm.focus(self.window)
        if self.cfg.paste_method == "typing":
            self._type_text(text)
        else:
            self.text.copy(text)
            self._focus_composer()
            self.wm.send_keys("{CTRL}a", wait_ms=100)
            self.wm.send_keys("{CTRL}v", wait_ms=200)
        # verify the composer actually accepted the text
        if self._composer_text() and not self._composer_text().strip():
            raise SendError("Composer was empty after paste — aborting send.")
        self.wm.send_keys(self._send_keys_template)
        time.sleep(0.5)
        if self._composer_text() and self.cfg.send_key != "enter":
            # Ctrl+Enter on some layouts leaves text; not fatal, just log.
            self._log("Note: composer may still hold text after send key", "debug")

    def _focus_composer(self) -> None:
        ctrl = self.window.control
        if ctrl is None:
            raise SendError("Brave window has no UIA control.")
        for el in self._walk(ctrl, max_depth=6):
            cls = ""
            try:
                cls = (el.ClassName or "")
            except Exception:
                continue
            name = ""
            try:
                name = (el.Name or "")
            except Exception:
                pass
            if cls == "Edit" or any(h in name.lower() for h in COMPOSER_HINTS):
                try:
                    el.ClickLeft()
                    return
                except Exception:
                    continue
        raise SendError("Could not find the ChatGPT composer textarea.")

    def _composer_text(self) -> Optional[str]:
        try:
            ctrl = self.window.control
            for el in self._walk(ctrl, max_depth=6):
                if (el.ClassName or "") == "Edit":
                    try:
                        return el.GetValue()
                    except Exception:
                        pass
        except Exception:
            return None
        return None

    def _type_text(self, text: str) -> None:
        self._focus_composer()
        # SendKeys has trouble with very long text; chunk it.
        chunk_size = 200
        for i in range(0, len(text), chunk_size):
            self.wm.send_keys(text[i: i + chunk_size], wait_ms=50)

    # --------------------------------------------------------------- helpers
    def _find_panes(self, root):
        """Return candidate message panes (Elements that look like message containers)."""
        out = []
        for el in self._walk(root, max_depth=6):
            try:
                cls = (el.ClassName or "")
                if cls in ("Pane", "Document") and el.Name:
                    out.append(el)
            except Exception:
                continue
        return out

    def _walk(self, root, max_depth: int = 6):
        """Breadth-first walk of the UIA tree (bounded, defensive)."""
        auto = self.wm._auto
        out = []
        queue = [(root, 0)]
        seen = 0
        while queue and seen < 4000:
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

    @staticmethod
    def _click(el) -> None:
        try:
            el.ClickLeft()
        except Exception:
            try:
                el.Invoke()
            except Exception:
                pass
