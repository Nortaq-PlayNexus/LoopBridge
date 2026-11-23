"""Loop state: the phase enum and run statistics."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict


class Phase(str, Enum):
    """The five steps of one relay iteration, in order."""

    WAIT_CHATGPT = "WAIT_CHATGPT_REPLY"
    COPY_CHATGPT = "COPY_CHATGPT_REPLY"
    PASTE_OPENCODE = "PASTE_OPENCODE_SUBMIT"
    WAIT_OPENCODE = "WAIT_OPENCODE_DONE"
    COPY_OPENCODE = "COPY_OPENCODE_REPLY"
    PASTE_CHATGPT = "PASTE_CHATGPT_SEND"

    @property
    def step_index(self) -> int:
        return _PHASE_ORDER.index(self)

    @classmethod
    def ordered(cls) -> list["Phase"]:
        return list(_PHASE_ORDER)


_PHASE_ORDER: list[Phase] = [
    Phase.WAIT_CHATGPT,
    Phase.COPY_CHATGPT,
    Phase.PASTE_OPENCODE,
    Phase.WAIT_OPENCODE,
    Phase.COPY_OPENCODE,
    Phase.PASTE_CHATGPT,
]


@dataclass
class PhaseStats:
    count: int = 0
    total_time_s: float = 0.0
    last_time_s: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "count": self.count,
            "total_time_s": round(self.total_time_s, 3),
            "last_time_s": round(self.last_time_s, 3),
        }


@dataclass
class RunStats:
    loops_completed: int = 0
    errors: int = 0
    retries: int = 0
    aborted: bool = False
    started_at: float = field(default_factory=time.time)
    phases: Dict[str, PhaseStats] = field(default_factory=dict)

    def phase_stats(self, phase: Phase) -> PhaseStats:
        return self.phases.setdefault(phase.value, PhaseStats())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loops_completed": self.loops_completed,
            "errors": self.errors,
            "retries": self.retries,
            "aborted": self.aborted,
            "elapsed_s": round(time.time() - self.started_at, 3),
            "phases": {name: ps.to_dict() for name, ps in self.phases.items()},
        }
