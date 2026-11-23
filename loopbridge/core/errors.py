"""Typed errors used across LoopBridge.

Every failure the orchestrator can hit is a subclass of :class:`LoopError`,
so the watchdog/retry policy can classify and decide what to do without
string-matching messages.
"""


class LoopError(Exception):
    """Base error for the loop engine."""


class ConfigError(LoopError):
    """Bad or missing configuration."""


class TargetWindowNotFound(LoopError):
    """A required window (Brave / PowerShell) could not be located."""


class FocusError(LoopError):
    """A window could not be focused / activated before sending keys."""


class CopyError(LoopError):
    """Copying text out of a window failed or produced nothing."""


class SendError(LoopError):
    """Pasting / sending into a window failed."""


class CompletionError(LoopError):
    """OpenCode (or ChatGPT) never signalled completion within the deadline."""


class PhaseTimeout(LoopError):
    """A phase exceeded its deadline (raised by the watchdog guard)."""

    def __init__(self, phase: str, detail: str, timeout_s: float):
        super().__init__(f"[{phase}] timed out after {timeout_s:.1f}s: {detail}")
        self.phase = phase
        self.detail = detail
        self.timeout_s = timeout_s


class LoopAborted(LoopError):
    """The loop was stopped manually or aborted after exhausted retries."""
