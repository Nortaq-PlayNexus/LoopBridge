"""Text engine: clipboard handling, sanitising and transforms.

All copy/paste in LoopBridge goes through here so that the messy real-world
text coming out of a terminal (ANSI escapes, control chars) or a web page
(markdown fences) is cleaned before it is pasted into the other side.
"""

from __future__ import annotations

import re
import time
from collections import deque
from typing import Deque, List, Optional

# Matches CSI, OSC and two-character escape sequences.
ANSI_RE = re.compile(r"\x1b(?:\[[0-9;?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\)|[@-Z\\-_])")
# Matches remaining control characters except newline and tab.
CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c-\x1f\x7f]")
FENCE_RE = re.compile(r"^```.*$", re.MULTILINE)


class _MemoryClipboard:
    """In-memory clipboard used when pyperclip is unavailable (e.g. headless)."""

    def __init__(self) -> None:
        self._text = ""

    def copy(self, text: str) -> None:
        self._text = text

    def paste(self) -> str:
        return self._text


def _make_clipboard():
    try:
        import pyperclip  # type: ignore

        return pyperclip
    except Exception:
        return _MemoryClipboard()


class TextEngine:
    """Clipboard access + text transforms."""

    def __init__(
        self,
        *,
        sanitize_ansi: bool = True,
        strip_markdown: bool = False,
        prefix: str = "",
        suffix: str = "",
        max_len: int = 0,
        max_history: int = 50,
        clipboard=None,
    ) -> None:
        self._clipboard = clipboard if clipboard is not None else _make_clipboard()
        self.sanitize_ansi = sanitize_ansi
        self.strip_markdown = strip_markdown
        self.prefix = prefix
        self.suffix = suffix
        self.max_len = max_len
        self._history: Deque[str] = deque(maxlen=max_history)

    # ------------------------------------------------------------------ clipboard
    def copy(self, text: str) -> str:
        """Copy text to the clipboard (and record history). Returns the stored text."""
        text = self.transform(text)
        self._clipboard.copy(text)
        self._history.append(text)
        return text

    def read(self) -> str:
        """Read whatever is currently on the clipboard."""
        try:
            return self._clipboard.paste() or ""
        except Exception:
            return ""

    @property
    def history(self) -> List[str]:
        return list(self._history)

    # ---------------------------------------------------------------- transforms
    def transform(self, text: str) -> str:
        """Apply the configured cleaning pipeline to a piece of text."""
        if text is None:
            return ""
        out = text.replace("\r\n", "\n").replace("\r", "\n")
        if self.sanitize_ansi:
            out = self.strip_ansi(out)
        if self.strip_markdown:
            out = self.strip_markdown_fences(out)
        out = "\n".join(line.rstrip() for line in out.splitlines())
        out = re.sub(r"\n{3,}", "\n\n", out).strip()
        if self.prefix:
            out = self.prefix + out
        if self.suffix:
            out = out + self.suffix
        if self.max_len and len(out) > self.max_len:
            out = out[: self.max_len]
        return out

    @staticmethod
    def strip_ansi(text: str) -> str:
        text = ANSI_RE.sub("", text)
        return CTRL_RE.sub("", text)

    @staticmethod
    def strip_markdown_fences(text: str) -> str:
        return FENCE_RE.sub("", text)

    def apply_transforms_from_config(self, cfg) -> None:
        """Re-apply transform options from a TextConfig-like object."""
        self.sanitize_ansi = cfg.sanitize_ansi
        self.strip_markdown = cfg.strip_markdown
        self.prefix = cfg.prefix
        self.suffix = cfg.suffix
        self.max_len = cfg.max_len
