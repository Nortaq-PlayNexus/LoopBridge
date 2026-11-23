"""Window manager: find and focus the Brave + PowerShell windows via UIA.

Uses the `uiautomation` package (pip install uiautomation). Imports are lazy so
the rest of the codebase runs (and is testable) on non-Windows machines.
"""

from __future__ import annotations

import re
import time
from typing import List, Optional

from ..config.profiles import WindowTarget
from ..core.errors import ConfigError, FocusError, TargetWindowNotFound
from .base import WindowHandle, WindowManager


def _import_uia():
    try:
        import uiautomation as auto  # type: ignore

        return auto
    except Exception as exc:  # pragma: no cover - environment dependent
        raise ConfigError(
            "The 'uiautomation' package is required for window control on "
            "Windows. Install it with: pip install uiautomation"
        ) from exc


class UiaWindowManager(WindowManager):
    def __init__(self, find_interval_ms: int = 500, auto_restore: bool = True,
                 set_topmost: bool = False) -> None:
        self._auto = _import_uia()
        self.find_interval_ms = find_interval_ms
        self.auto_restore = auto_restore
        self.set_topmost = set_topmost

    # ------------------------------------------------------------------ find
    def find(self, target: WindowTarget) -> WindowHandle:
        return self._find_matching(target, wait_s=10.0)

    def _iter_windows(self):
        try:
            # uiautomation exposes top-level windows via GetRootElement children
            root = self._auto.GetRootControl()
            for child in root.GetChildren():
                if child.ClassName == "Window" or child.ClassName == "Application":
                    yield child
        except Exception:
            # Fallback: enumerate via the UIA element from the desktop
            for win in self._auto.WindowControl(searchDepth=1).GetChildren() if hasattr(
                self._auto, "WindowControl"
            ) else []:
                yield win

    def _match(self, window, target: WindowTarget) -> bool:
        title = ""
        proc = ""
        try:
            title = window.Name or ""
        except Exception:
            pass
        try:
            proc = (window.ProcessId and str(window.ProcessId)) or ""
        except Exception:
            pass
        if target.title_regex and not re.search(target.title_regex, title, re.IGNORECASE):
            return False
        if target.processes and proc and not any(
            p.lower() in (proc.lower() or "") for p in target.processes
        ):
            # process name may not be resolvable; title match alone is enough
            if not (title and re.search(target.title_regex or ".", title, re.IGNORECASE)):
                return False
        return True

    def _find_matching(self, target: WindowTarget, wait_s: float = 10.0) -> WindowHandle:
        deadline = time.monotonic() + wait_s
        last_error: Optional[Exception] = None
        while time.monotonic() < deadline:
            for win in self._iter_windows():
                if self._match(win, target):
                    title, proc = "", ""
                    try:
                        title = win.Name or ""
                    except Exception:
                        pass
                    return WindowHandle(title=title, process=proc, control=win)
            time.sleep(self.find_interval_ms / 1000.0)
        raise TargetWindowNotFound(
            f"No window matching {target.title_regex!r} / {target.processes} "
            f"found within {wait_s:.0f}s."
        )

    # ------------------------------------------------------------------ focus
    def focus(self, window: WindowHandle) -> None:
        ctrl = window.control
        if ctrl is None:
            return
        try:
            if self.auto_restore and self._is_minimized(ctrl):
                ctrl.Restore()
            if self.set_topmost:
                ctrl.SetTopMost(True)
            ctrl.SetFocus()
            ctrl.SetActive()
            time.sleep(0.2)
        except Exception as exc:
            raise FocusError(f"Could not focus window {window.title!r}: {exc}") from exc

    @staticmethod
    def _is_minimized(ctrl) -> bool:
        try:
            return ctrl.IsMinimized()
        except Exception:
            return False

    # ------------------------------------------------------------------ helpers
    def send_keys(self, keys: str, wait_ms: int = 120) -> None:
        """Send keys to the currently focused window."""
        try:
            self._auto.SendKeys(keys, waitTime=wait_ms / 1000.0)
        except Exception as exc:
            raise FocusError(f"SendKeys({keys!r}) failed: {exc}") from exc

    def get_active_window(self) -> Optional[WindowHandle]:
        try:
            ctrl = self._auto.GetForegroundControl()
            return WindowHandle(title=getattr(ctrl, "Name", "") or "", control=ctrl)
        except Exception:
            return None
