"""The orchestrator: the relay loop state machine.

Runs the 5 phases per iteration:
    WAIT_CHATGPT → COPY_CHATGPT → PASTE_OPENCODE → WAIT_OPENCODE
    → COPY_OPENCODE → PASTE_CHATGPT → (loop)

Every phase runs under a watchdog deadline, with configurable retries. The
:class:`LoopController` provides thread-safe start / pause / resume / stop /
step-once so the Qt UI (or console runner) can drive a run that executes in
its own thread.
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Dict, Optional

from ..config.profiles import Profile
from ..core.errors import CopyError, LoopAborted, LoopError
from ..core.state import Phase, RunStats
from ..core.watchdog import LoopWatchdog, PhaseGuard

LogFn = Callable[[str, str], None]
PhaseFn = Callable[[str, str, str], None]
StatsFn = Callable[[RunStats], None]


class LoopController:
    """Thread-safe control surface for a running (or upcoming) loop."""

    def __init__(self) -> None:
        self._stop = threading.Event()      # set => stop requested
        self._paused = threading.Event()   # set => paused
        self._step = threading.Event()     # set => run one phase, then pause

    # ------------------------------------------------------------- commands
    def reset(self) -> None:
        self._stop.clear()
        self._paused.clear()
        self._step.clear()

    def request_stop(self) -> None:
        self._stop.set()

    def pause(self) -> None:
        self._paused.set()

    def resume(self) -> None:
        self._paused.clear()

    def step(self) -> None:
        """Run exactly one phase, then pause again."""
        self._paused.set()
        self._step.set()

    # ------------------------------------------------------------- queries
    @property
    def stop_requested(self) -> bool:
        return self._stop.is_set()

    @property
    def is_paused(self) -> bool:
        return self._paused.is_set()

    # ------------------------------------------------------------- wait
    def await_phase(self) -> str:
        """Block until the loop may proceed with the next phase.

        Returns "resume" (normal run) or "step" (one phase, then auto-pause).
        Raises LoopAborted if a stop was requested.
        """
        while True:
            if self._stop.is_set():
                raise LoopAborted("Loop stopped by user.")
            if not self._paused.is_set():
                return "resume"
            if self._step.is_set():
                self._step.clear()
                return "step"
            self._step.wait(timeout=0.5)


class Orchestrator:
    def __init__(
        self,
        profile: Profile,
        cgpt_driver,
        oc_driver,
        text_engine,
        window_manager=None,
        window_handles: Optional[Dict[str, object]] = None,
        on_log: Optional[LogFn] = None,
        on_phase: Optional[PhaseFn] = None,
        on_stats: Optional[StatsFn] = None,
        on_reply: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self.profile = profile
        self.cgpt = cgpt_driver
        self.oc = oc_driver
        self.text = text_engine
        self.wm = window_manager
        self._windows: Dict[str, object] = window_handles or {}
        self._last_gpt_reply = ""
        self._last_oc_reply = ""
        self._log = on_log or (lambda msg, level="info": None)
        self._on_phase = on_phase or (lambda phase, status, detail="": None)
        self._on_stats = on_stats or (lambda stats: None)
        self._on_reply = on_reply or (lambda kind, text: None)
        self.watchdog = LoopWatchdog(
            profile.watchdog.default_timeout_s, profile.watchdog.phase_timeouts_s
        )
        self.controller = LoopController()

    # ------------------------------------------------------------- main loop
    def run(self) -> RunStats:
        stats = RunStats()
        self.controller.reset()
        self._log(
            f"Loop started — mode={self.profile.loop.mode}, "
            f"target={self.profile.loop.count or 'infinite'}"
        )
        try:
            while not self.controller.stop_requested:
                if self.profile.watchdog.max_run_time_s and \
                        time.monotonic() - stats.started_at > self.profile.watchdog.max_run_time_s:
                    self._log("Max run time reached — stopping loop.", "warn")
                    break

                for phase in Phase.ordered():
                    proceed = self.controller.await_phase()  # raises LoopAborted
                    self._execute_phase(phase, stats)
                    if proceed == "step":
                        self.controller.pause()
                        self._log("Step complete — paused again.")
                    self._phase_delay(phase)

                stats.loops_completed += 1
                self._log(f"Loop iteration {stats.loops_completed} complete.")
                self._on_stats(stats)

                if self.profile.loop.count and stats.loops_completed >= self.profile.loop.count:
                    self._log(f"Reached loop count {self.profile.loop.count} — done.")
                    break
                self._sleep_ms(self.profile.timing.between_loops_ms)
        except LoopAborted as exc:
            stats.aborted = True
            self._log(f"Loop aborted: {exc}", "warn")
        except LoopError as exc:  # unexpected engine error
            stats.aborted = True
            stats.errors += 1
            self._log(f"Loop aborted with error: {exc}", "error")
        finally:
            self._log(
                f"Loop finished — iterations={stats.loops_completed}, "
                f"errors={stats.errors}, retries={stats.retries}"
            )
            self._on_stats(stats)
        return stats

    # ------------------------------------------------------------- phase exec
    def _execute_phase(self, phase: Phase, stats: RunStats) -> None:
        retries = self.profile.watchdog.retries
        attempt = 0
        while True:
            guard = self.watchdog.guard(phase.value)
            start = time.monotonic()
            self._on_phase(phase.value, "running")
            self._log(f"→ {phase.value}")
            try:
                self._dispatch(phase, guard)
            except LoopError as exc:
                stats.errors += 1
                if attempt < retries:
                    attempt += 1
                    stats.retries += 1
                    backoff = self.profile.watchdog.backoff_ms * attempt / 1000.0
                    self._log(f"{phase.value} failed: {exc} — retry {attempt}/{retries}", "warn")
                    time.sleep(backoff)
                    continue
                if self.profile.watchdog.continue_on_error:
                    self._log(f"{phase.value} failed, continuing: {exc}", "error")
                    break
                raise LoopAborted(f"{phase.value} failed after retries: {exc}") from exc
            else:
                self._log(f"✓ {phase.value} done ({time.monotonic() - start:.2f}s)")
                self._on_phase(phase.value, "done")
                break
            finally:
                ps = stats.phase_stats(phase)
                elapsed = time.monotonic() - start
                ps.count += 1
                ps.total_time_s += elapsed
                ps.last_time_s = elapsed

    # ------------------------------------------------------------- dispatch
    def _dispatch(self, phase: Phase, guard: PhaseGuard) -> None:
        dry = self.profile.debug.dry_run
        if phase is Phase.WAIT_CHATGPT:
            self.cgpt.wait_for_reply_done(guard.deadline)
        elif phase is Phase.COPY_CHATGPT:
            reply = self.cgpt.copy_latest_reply()
            if not (reply or "").strip():
                raise CopyError("ChatGPT returned no reply text to copy.")
            self._last_gpt_reply = self.text.transform(reply)
            self._log(f"copied {len(self._last_gpt_reply)} chars from ChatGPT")
            self._on_reply("gpt", self._last_gpt_reply)
        elif phase is Phase.PASTE_OPENCODE:
            if self.wm is not None:
                self.wm.focus(self._ensure_window("powershell"))
            if dry:
                self._log(f"[dry-run] would submit to OpenCode: "
                          f"{self._last_gpt_reply[:80]}…", "debug")
                return
            self.oc.submit(self._last_gpt_reply)
        elif phase is Phase.WAIT_OPENCODE:
            self.oc.wait_until_done(guard.deadline)
        elif phase is Phase.COPY_OPENCODE:
            reply = self.oc.copy_latest_reply()
            if not (reply or "").strip():
                raise CopyError("OpenCode returned no reply text to copy.")
            self._last_oc_reply = self.text.transform(reply)
            self._log(f"copied {len(self._last_oc_reply)} chars from OpenCode")
            self._on_reply("oc", self._last_oc_reply)
        elif phase is Phase.PASTE_CHATGPT:
            if self.wm is not None:
                self.wm.focus(self._ensure_window("brave"))
            if dry:
                self._log(f"[dry-run] would send to ChatGPT: "
                          f"{self._last_oc_reply[:80]}…", "debug")
                return
            self.cgpt.paste_and_send(self._last_oc_reply)

    # ------------------------------------------------------------- helpers
    def _ensure_window(self, kind: str):
        """Resolve (or re-resolve) a target window handle."""
        if self.wm is None:
            return None
        win = self._windows.get(kind)
        if win is not None and getattr(win, "control", None) is not None:
            return win
        target = getattr(self.profile.windows, kind)
        win = self.wm.find(target)
        self._windows[kind] = win
        self._log(f"resolved {kind} window: {win.title!r}")
        return win

    def _phase_delay(self, phase: Phase) -> None:
        ms = int(self.profile.timing.phase_delays_ms.get(phase.value, 0)) * \
            self.profile.timing.global_multiplier
        if ms > 0:
            self._sleep_ms(int(ms))

    @staticmethod
    def _sleep_ms(ms: int) -> None:
        if ms > 0:
            time.sleep(ms / 1000.0)
