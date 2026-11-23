"""Main window: live dashboard for the relay loop.

Polished layout:
  * header with title + live status pill
  * 6 phase cards (idle / running / done / error)
  * stats panel (loops, errors, retries, elapsed, driver mode)
  * reply preview panel (last copied ChatGPT & OpenCode replies)
  * styled controls: Start / Pause / Resume / Stop / Step / Dry-run / Simulate
  * colour-coded monospace log

The orchestrator runs on a worker thread; all UI updates arrive via Qt signals.
"""

from __future__ import annotations

import html
import sys
import time
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QPlainTextEdit, QPushButton,
    QVBoxLayout, QWidget,
)

from ..config.profiles import Profile
from ..core.orchestrator import Orchestrator
from ..core.state import Phase, RunStats
from .theme import PHASE_COLORS, apply_theme

PHASE_SHORT = {
    Phase.WAIT_CHATGPT: "Wait ChatGPT",
    Phase.COPY_CHATGPT: "Copy ChatGPT",
    Phase.PASTE_OPENCODE: "Paste → OpenCode",
    Phase.WAIT_OPENCODE: "Wait OpenCode",
    Phase.COPY_OPENCODE: "Copy OpenCode",
    Phase.PASTE_CHATGPT: "Send → ChatGPT",
}


class _PhaseCard(QFrame):
    """One stepper card: number, label, state indicator."""

    def __init__(self, index: int, label: str):
        super().__init__()
        self.setFrameShape(QFrame.NoFrame)
        self.setFixedHeight(58)
        self._num = QLabel(f"{index}")
        self._num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._num.setStyleSheet("font-weight: 700; color: #7dd3fc; font-size: 15px;")
        self._label = QLabel(label)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setWordWrap(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.addWidget(self._num)
        layout.addWidget(self._label, stretch=1)
        self.set_state("idle")

    def set_state(self, state: str) -> None:
        bg, fg, border = PHASE_COLORS.get(state, PHASE_COLORS["idle"])
        self.setStyleSheet(
            f"QFrame {{ background: {bg}; border: 1px solid {border}; "
            f"border-radius: 8px; }}"
        )
        self._label.setStyleSheet(f"color: {fg};")


class _Worker(QObject):
    log_sig = Signal(str, str)
    phase_sig = Signal(str, str)
    stats_sig = Signal(object)
    reply_sig = Signal(str, str)
    done_sig = Signal(object)

    def __init__(self, profile: Profile, simulate: bool):
        super().__init__()
        self.profile = profile
        self.simulate = simulate
        self.orch: Orchestrator = None

    def run(self):
        from ..app import build_real_drivers, build_simulated_drivers, build_text_engine

        def log(msg, level="info"):
            self.log_sig.emit(msg, level)

        if self.simulate:
            cgpt, oc, wm = build_simulated_drivers(self.profile, log)
            log("SIMULATION MODE — no real windows will be touched.", "warn")
        else:
            cgpt, oc, wm = build_real_drivers(self.profile, log)

        self.orch = Orchestrator(
            self.profile, cgpt, oc, build_text_engine(self.profile),
            window_manager=wm,
            on_log=log,
            on_phase=lambda p, s, d="": self.phase_sig.emit(p, s),
            on_stats=lambda st: self.stats_sig.emit(st),
            on_reply=lambda kind, text: self.reply_sig.emit(kind, text),
        )
        stats = self.orch.run()
        self.done_sig.emit(stats)


class MainWindow(QMainWindow):
    def __init__(self, profile_path: str):
        super().__init__()
        self.profile_path = profile_path
        self.profile = Profile.load(profile_path) if Path(profile_path).exists() else Profile()
        self.thread: QThread = None
        self.worker: _Worker = None
        self._run_stats: RunStats = RunStats()
        self._running = False

        self.setWindowTitle("LoopBridge — ChatGPT ↔ OpenCode relay")
        self.resize(1040, 760)

        self._build_header()
        self._build_stepper()
        self._build_controls()
        self._build_stats_and_replies()
        self._build_log()

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 14, 16, 12)
        layout.setSpacing(10)
        layout.addWidget(self.header)
        layout.addLayout(self.stepper_row)
        layout.addWidget(self.controls_panel)
        layout.addLayout(self.stats_row, stretch=0)
        layout.addWidget(self.log_panel, stretch=1)
        self.setCentralWidget(central)

        self._connect_buttons()
        self._start_elapsed_timer()
        self._log("Ready. Configure options in Settings, then press Start.")

    # ------------------------------------------------------------- building
    def _build_header(self):
        self.header = QFrame()
        self.header.setFrameShape(QFrame.NoFrame)
        h = QHBoxLayout(self.header)
        title = QLabel("🔁 LoopBridge")
        title.setObjectName("heading")
        sub = QLabel("relay between ChatGPT (Brave) and OpenCode (PowerShell)")
        sub.setObjectName("subheading")
        h.addWidget(title)
        h.addWidget(sub, stretch=1)
        self.status_pill = QLabel("idle")
        self.status_pill.setStyleSheet(
            "padding: 4px 14px; border-radius: 999px; background: #232838; "
            "color: #9aa3b8; font-weight: 600;"
        )
        h.addWidget(self.status_pill)

    def _build_stepper(self):
        self.stepper_row = QHBoxLayout()
        self.phase_cards: dict[str, _PhaseCard] = {}
        for i, ph in enumerate(Phase.ordered(), start=1):
            card = _PhaseCard(i, PHASE_SHORT[ph])
            card.setToolTip(ph.value)
            self.phase_cards[ph.value] = card
            self.stepper_row.addWidget(card, stretch=1)

    def _build_controls(self):
        self.controls_panel = QFrame()
        self.controls_panel.setFrameShape(QFrame.NoFrame)
        row = QHBoxLayout(self.controls_panel)
        row.setContentsMargins(0, 0, 0, 0)

        self.btn_start = QPushButton("▶  Start")
        self.btn_start.setObjectName("primary")
        self.btn_pause = QPushButton("⏸  Pause")
        self.btn_resume = QPushButton("⏵  Resume")
        self.btn_stop = QPushButton("⏹  Stop")
        self.btn_stop.setObjectName("danger")
        self.btn_step = QPushButton("⏭  Step once")

        self.btn_dry = QPushButton("Dry-run")
        self.btn_dry.setObjectName("toggle")
        self.btn_dry.setCheckable(True)
        self.btn_sim = QPushButton("Simulate")
        self.btn_sim.setObjectName("toggle")
        self.btn_sim.setCheckable(True)
        self.btn_sim.setToolTip(
            "Run with mock drivers — the full loop logic is exercised without "
            "touching your real Brave / PowerShell windows.")

        self.btn_settings = QPushButton("⚙  Settings…")
        self.btn_load = QPushButton("Load profile…")
        self.btn_save = QPushButton("Save profile…")

        for w in (self.btn_start, self.btn_pause, self.btn_resume,
                  self.btn_stop, self.btn_step):
            row.addWidget(w)
        row.addSpacing(12)
        row.addWidget(self.btn_dry)
        row.addWidget(self.btn_sim)
        row.addStretch(1)
        row.addWidget(self.btn_settings)
        row.addWidget(self.btn_load)
        row.addWidget(self.btn_save)

    def _build_stats_and_replies(self):
        self.stats_row = QHBoxLayout()

        # stats panel
        stats_panel = QFrame()
        stats_panel.setFrameShape(QFrame.NoFrame)
        stats_panel.setStyleSheet("QFrame { border: 1px solid #2b2f3d; border-radius: 8px; }")
        grid = QGridLayout(stats_panel)
        grid.setContentsMargins(14, 10, 14, 10)

        self.lbl_loops = self._stat(grid, 0, 0, "Loops", "0")
        self.lbl_errors = self._stat(grid, 0, 1, "Errors", "0")
        self.lbl_retries = self._stat(grid, 0, 2, "Retries", "0")
        self.lbl_elapsed = self._stat(grid, 1, 0, "Elapsed", "0s")
        self.lbl_phase = self._stat(grid, 1, 1, "Phase", "—")
        self.lbl_mode = self._stat(grid, 1, 2, "Mode", "real")
        self.stats_row.addWidget(stats_panel, stretch=1)

        # reply preview panel
        reply_panel = QFrame()
        reply_panel.setFrameShape(QFrame.NoFrame)
        reply_panel.setStyleSheet("QFrame { border: 1px solid #2b2f3d; border-radius: 8px; }")
        rl = QVBoxLayout(reply_panel)
        rl.setContentsMargins(14, 10, 14, 10)
        rl.setSpacing(4)
        gpt_lbl = QLabel("Last ChatGPT reply")
        gpt_lbl.setStyleSheet("color: #9aa3b8; font-weight: 600;")
        self.lbl_gpt_reply = QLabel("—")
        self.lbl_gpt_reply.setWordWrap(True)
        self.lbl_gpt_reply.setStyleSheet("color: #7dd3fc;")
        oc_lbl = QLabel("Last OpenCode reply")
        oc_lbl.setStyleSheet("color: #9aa3b8; font-weight: 600;")
        self.lbl_oc_reply = QLabel("—")
        self.lbl_oc_reply.setWordWrap(True)
        self.lbl_oc_reply.setStyleSheet("color: #86efac;")
        for w in (gpt_lbl, self.lbl_gpt_reply, oc_lbl, self.lbl_oc_reply):
            rl.addWidget(w)
        rl.addStretch(1)
        self._truncate(self.lbl_gpt_reply, 160)
        self._truncate(self.lbl_oc_reply, 160)
        self.stats_row.addWidget(reply_panel, stretch=1)

    def _stat(self, grid: QGridLayout, row: int, col: int, title: str, value: str) -> QLabel:
        t = QLabel(title)
        t.setStyleSheet("color: #9aa3b8;")
        v = QLabel(value)
        v.setObjectName("statValue")
        grid.addWidget(t, row * 2, col)
        grid.addWidget(v, row * 2 + 1, col)
        return v

    def _truncate(self, label: QLabel, limit: int) -> None:
        text = label.text()
        if len(text) > limit:
            label.setText(text[:limit] + "…")

    def _build_log(self):
        self.log_panel = QFrame()
        self.log_panel.setFrameShape(QFrame.NoFrame)
        self.log_panel.setStyleSheet("QFrame { border: 1px solid #2b2f3d; border-radius: 8px; }")
        v = QVBoxLayout(self.log_panel)
        v.setContentsMargins(10, 8, 10, 10)
        header = QLabel("Log")
        header.setStyleSheet("color: #9aa3b8; font-weight: 600;")
        v.addWidget(header)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(3000)
        self.log_view.setFont(QFont("Cascadia Code", 11))
        v.addWidget(self.log_view, stretch=1)

    # ------------------------------------------------------------- controls
    def _connect_buttons(self):
        self.btn_start.clicked.connect(self._start)
        self.btn_pause.clicked.connect(lambda: self._ctrl("pause"))
        self.btn_resume.clicked.connect(lambda: self._ctrl("resume"))
        self.btn_stop.clicked.connect(lambda: self._ctrl("stop"))
        self.btn_step.clicked.connect(lambda: self._ctrl("step"))
        self.btn_dry.toggled.connect(self._dry_toggled)
        self.btn_sim.toggled.connect(self._sim_toggled)
        self.btn_settings.clicked.connect(self._open_settings)
        self.btn_load.clicked.connect(self._load_profile)
        self.btn_save.clicked.connect(self._save_profile)

    def _dry_toggled(self, checked: bool):
        self.profile.debug.dry_run = checked
        self.btn_dry.setText("Dry-run ✓" if checked else "Dry-run")

    def _sim_toggled(self, checked: bool):
        self.btn_sim.setText("Simulate ✓" if checked else "Simulate")

    def _open_settings(self):
        from .settings_page import SettingsDialog

        dialog = SettingsDialog(self.profile, self)
        if dialog.exec() == dialog.Accepted:
            self.profile = dialog.apply_to()
            self._log("Settings applied.")

    def _start(self):
        if self.thread is not None and self.thread.isRunning():
            self._log("Loop already running.", "warn")
            return
        self._running = True
        self.thread = QThread()
        self.worker = _Worker(self.profile, simulate=self.btn_sim.isChecked())
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.log_sig.connect(self._log)
        self.worker.phase_sig.connect(self._phase)
        self.worker.stats_sig.connect(self._stats)
        self.worker.reply_sig.connect(self._reply)
        self.worker.done_sig.connect(self._finished)
        self.thread.start()
        self._set_status("running")
        self._log("Starting loop…")

    def _ctrl(self, what: str):
        if self.worker is None or self.worker.orch is None:
            self._log("Loop not running.", "warn")
            return
        orch = self.worker.orch
        if what == "pause":
            orch.controller.pause()
            self._set_pill("paused")
        elif what == "resume":
            orch.controller.resume()
            self._set_pill("running")
        elif what == "stop":
            orch.controller.request_stop()
        elif what == "step":
            orch.controller.step()

    def _load_profile(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load profile", "", "JSON (*.json)")
        if path:
            self.profile = Profile.load(path)
            self.profile_path = path
            self._log(f"Loaded profile from {path}")

    def _save_profile(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save profile", self.profile_path, "JSON (*.json)")
        if path:
            self.profile.save(path)
            self.profile_path = path
            self._log(f"Saved profile to {path}")

    # ------------------------------------------------------------- signals
    def _log(self, msg: str, level: str = "info"):
        colors = {"info": "#e6e8ef", "warn": "#fbbf24", "error": "#f87171", "debug": "#7c8aa5"}
        color = colors.get(level, colors["info"])
        prefix = {"info": "[i]", "warn": "[!]", "error": "[x]", "debug": "[d]"}.get(level, "[i]")
        self.log_view.appendHtml(
            f"<span style='color:{color}'>{prefix}</span> "
            f"<span style='color:#aab2c5'>{html.escape(msg)}</span>"
        )

    def _phase(self, phase: str, status: str):
        card = self.phase_cards.get(phase)
        if card:
            card.set_state("running" if status == "running" else "done")
        self.lbl_phase.setText(phase)

    def _reply(self, kind: str, text: str):
        if kind == "gpt":
            self.lbl_gpt_reply.setText(text)
            self._truncate(self.lbl_gpt_reply, 160)
        elif kind == "oc":
            self.lbl_oc_reply.setText(text)
            self._truncate(self.lbl_oc_reply, 160)

    def _stats(self, stats: RunStats):
        self._run_stats = stats
        self.lbl_loops.setText(str(stats.loops_completed))
        self.lbl_errors.setText(str(stats.errors))
        self.lbl_retries.setText(str(stats.retries))

    def _finished(self, stats: RunStats):
        self._running = False
        self._stats(stats)
        self.lbl_elapsed.setText(f"{max(0, int(time.time() - stats.started_at))}s")
        self._set_status("finished" if not stats.aborted else "aborted")
        self._log(f"Loop finished — {stats.loops_completed} iterations, "
                  f"aborted={stats.aborted}")
        if self.thread is not None:
            self.thread.quit()

    def _set_status(self, state: str):
        self._set_pill(state)
        self._refresh_buttons()

    def _set_pill(self, state: str):
        colors = {
            "idle": ("#232838", "#9aa3b8"),
            "running": ("#1e3a8a", "#93c5fd"),
            "paused": ("#7c5a00", "#fbbf24"),
            "finished": ("#0f5132", "#86efac"),
            "aborted": ("#7f1d1d", "#fca5a5"),
        }
        bg, fg = colors.get(state, colors["idle"])
        label = {"idle": "idle", "running": "● running", "paused": "⏸ paused",
                 "finished": "✓ finished", "aborted": "✕ aborted"}[state]
        self.status_pill.setText(label)
        self.status_pill.setStyleSheet(
            f"padding: 4px 14px; border-radius: 999px; background: {bg}; "
            f"color: {fg}; font-weight: 700;"
        )

    def _refresh_buttons(self):
        running = self._running
        paused = self.worker is not None and self.worker.orch is not None and \
            self.worker.orch.controller.is_paused
        self.btn_start.setEnabled(not running)
        self.btn_pause.setEnabled(running and not paused)
        self.btn_resume.setEnabled(running and paused)
        self.btn_step.setEnabled(running and paused)
        self.btn_stop.setEnabled(running)
        self.btn_dry.setEnabled(not running)
        self.btn_sim.setEnabled(not running)
        self.btn_settings.setEnabled(not running)
        self.btn_load.setEnabled(not running)
        self.btn_save.setEnabled(not running)
        if paused:
            self._set_pill("paused")

    # ------------------------------------------------------------- elapsed timer
    def _start_elapsed_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(500)

    def _tick(self):
        if self._running:
            elapsed = time.time() - self._run_stats.started_at
            self.lbl_elapsed.setText(f"{int(elapsed)}s")
            self.lbl_mode.setText("simulate" if self.btn_sim.isChecked() else "real")
        # keep pill + button states in sync with the controller
        self._refresh_buttons()

    def closeEvent(self, event):
        if self.thread is not None and self.thread.isRunning():
            answer = QMessageBox.question(
                self, "LoopBridge",
                "The loop is still running. Stop it and quit?",
                QMessageBox.Yes | QMessageBox.No)
            if answer != QMessageBox.Yes:
                event.ignore()
                return
            if self.worker is not None and self.worker.orch is not None:
                self.worker.orch.controller.request_stop()
            self.thread.quit()
            self.thread.wait(5000)
        event.accept()


def run_gui(profile_path: str) -> None:
    app = QApplication(sys.argv)
    apply_theme(app)
    win = MainWindow(profile_path)
    win.show()
    app.exec()
