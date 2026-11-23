"""Driver interfaces.

Each side of the relay is behind a small protocol so the orchestrator is
independent of the concrete automation technology (UIA keyboard, CDP in-page
JS, opencode CLI, or the mock used for simulation/tests).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class WindowHandle:
    """A handle to an automation-controllable window."""

    def __init__(self, title: str, process: str = "", control=None) -> None:
        self.title = title
        self.process = process
        self.control = control  # UIA control object (or None for mocks)

    def __repr__(self) -> str:
        return f"<WindowHandle {self.title!r} ({self.process})>"


class WindowManager(ABC):
    @abstractmethod
    def find(self, target) -> WindowHandle:
        """Find a window matching a WindowTarget config."""

    @abstractmethod
    def focus(self, window: WindowHandle) -> None:
        """Restore (if needed) and focus a window."""


class ChatGPTDriver(ABC):
    """Drives ChatGPT inside Brave: read replies, paste + send."""

    @abstractmethod
    def wait_for_reply_done(self, deadline: float) -> None:
        """Block until the current ChatGPT generation is finished."""

    @abstractmethod
    def copy_latest_reply(self) -> str:
        """Return the text of the latest assistant reply."""

    @abstractmethod
    def paste_and_send(self, text: str) -> None:
        """Paste text into the ChatGPT composer and send it."""

    def close(self) -> None:
        pass


class OpenCodeDriver(ABC):
    """Drives OpenCode: submit a prompt, detect completion, capture reply."""

    @abstractmethod
    def submit(self, text: str) -> None:
        """Paste text into the OpenCode input and submit it."""

    @abstractmethod
    def wait_until_done(self, deadline: float) -> None:
        """Block until OpenCode has finished responding."""

    @abstractmethod
    def copy_latest_reply(self) -> str:
        """Return the text of the latest OpenCode reply."""

    def close(self) -> None:
        pass
