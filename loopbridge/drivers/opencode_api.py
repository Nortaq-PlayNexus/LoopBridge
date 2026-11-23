"""OpenCode driver: exact completion via the `opencode run` CLI (API mode).

Instead of reading a terminal, this driver launches:

    opencode run --format json "<prompt>"

as a child process (shown in a console window if `visible_console`), streams
its JSON event lines, and treats process exit — or an event whose type is in
`done_event_types` — as completion. The reply text is extracted from the
final assistant/text events. This is the exact, reliable alternative to the
TUI driver.

Note: the event JSON schema may vary between OpenCode versions; the parser
below is deliberately defensive (looks for common keys: type/parts/text/
content/role/done). Adjust `done_event_types` in the profile if needed.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import time
from typing import List, Optional

from ..config.profiles import OpenCodeConfig
from ..core.errors import CompletionError, CopyError, SendError
from ..core.text_engine import TextEngine
from .base import OpenCodeDriver


class ApiOpenCodeDriver(OpenCodeDriver):
    def __init__(self, cfg: OpenCodeConfig, text: TextEngine, log=None) -> None:
        self.cfg = cfg
        self.text = text
        self._log = log or (lambda msg, level="info": None)
        self._proc: Optional[subprocess.Popen] = None
        self._reply_lines: List[str] = []

    # --------------------------------------------------------------- submit
    def submit(self, text: str) -> None:
        cmd = self.cfg.command
        full = f"{cmd} {shlex.quote(text)}"
        try:
            creationflags = 0
            if self.cfg.visible_console and _is_windows():
                creationflags = 0x10  # CREATE_NEW_CONSOLE
            self._proc = subprocess.Popen(
                full,
                shell=True,
                cwd=self.cfg.working_dir or None,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=creationflags,
            )
        except Exception as exc:
            raise SendError(f"Failed to launch OpenCode API command: {exc}") from exc
        self._reply_lines = []
        self._log(f"opencode run launched: {full[:120]}…", "debug")

    # --------------------------------------------------------------- wait
    def wait_until_done(self, deadline: float) -> None:
        if self._proc is None:
            raise CompletionError("OpenCode process was never started.")
        assert self._proc.stdout is not None
        try:
            for raw in self._proc.stdout:
                if time.monotonic() > deadline:
                    self._kill()
                    raise CompletionError("OpenCode API run exceeded the deadline.")
                line = raw.strip()
                if not line:
                    continue
                event = self._parse_event(line)
                if event is None:
                    continue
                self._handle_event(event)
                if event.get("type", "").lower() in {t.lower() for t in self.cfg.done_event_types}:
                    break
            rc = self._proc.wait(timeout=max(1.0, deadline - time.monotonic()))
            if rc != 0:
                self._log(f"opencode exited with code {rc}", "warn")
        except CompletionError:
            raise
        except Exception as exc:
            self._kill()
            raise CompletionError(f"Error while waiting for OpenCode API run: {exc}") from exc

    # --------------------------------------------------------------- capture
    def copy_latest_reply(self) -> str:
        content = "\n".join(self._reply_lines).strip()
        if not content:
            raise CopyError("OpenCode API produced no reply text.")
        return content

    def close(self) -> None:
        self._kill()

    # --------------------------------------------------------------- internals
    def _kill(self) -> None:
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.kill()
            except Exception:
                pass

    @staticmethod
    def _parse_event(line: str) -> Optional[dict]:
        try:
            data = json.loads(line)
            return data if isinstance(data, dict) else None
        except (json.JSONDecodeError, TypeError):
            return None

    def _handle_event(self, event: dict) -> None:
        """Extract reply text from a JSON event (defensive to schema changes)."""
        etype = str(event.get("type", "")).lower()
        # skip lifecycle/tool noise
        if etype in ("done", "end", "exit", "error", "start", "message", "part", "update"):
            text = ""
            if isinstance(event.get("parts"), list):
                text = " ".join(
                    p.get("text", "") for p in event["parts"] if isinstance(p, dict) and p.get("text")
                )
            if not text:
                text = event.get("text") or event.get("content") or ""
            if text:
                self._reply_lines.append(text)
        elif event.get("role") == "assistant":
            text = event.get("text") or event.get("content") or ""
            if text:
                self._reply_lines.append(text)


def _is_windows() -> bool:
    import sys

    return sys.platform.startswith("win")
