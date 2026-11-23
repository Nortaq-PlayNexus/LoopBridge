"""Watchdog: per-phase deadlines and timeout detection.

The orchestrator creates a :class:`PhaseGuard` for each phase. Waiting driver
calls receive the guard's deadline, so a hung UI poll can't block the loop
forever.
"""

from __future__ import annotations

import time
from typing import Optional

from .errors import PhaseTimeout


class PhaseGuard:
    """Deadline + elapsed tracking for one loop phase."""

    def __init__(self, phase: str, timeout_s: float) -> None:
        self.phase = phase
        self.timeout_s = timeout_s
        self.start = time.monotonic()
        self.deadline = self.start + timeout_s

    @property
    def elapsed_s(self) -> float:
        return time.monotonic() - self.start

    def remaining_s(self) -> float:
        return self.deadline - time.monotonic()

    def check(self, detail: str = "") -> None:
        """Raise PhaseTimeout if the deadline has passed."""
        if time.monotonic() >= self.deadline:
            raise PhaseTimeout(self.phase, detail or "deadline reached", self.timeout_s)

    def expired(self) -> bool:
        return time.monotonic() >= self.deadline


class LoopWatchdog:
    """Builds guards for phases, using per-phase overrides from config."""

    def __init__(self, default_timeout_s: float, overrides: Optional[dict] = None) -> None:
        self.default_timeout_s = default_timeout_s
        self.overrides = overrides or {}

    def guard(self, phase: str) -> PhaseGuard:
        timeout_s = float(self.overrides.get(phase, self.default_timeout_s))
        return PhaseGuard(phase, timeout_s)
