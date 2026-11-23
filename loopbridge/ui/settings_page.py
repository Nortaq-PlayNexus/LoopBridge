"""Settings dialog: tabbed editor for every profile option.

Tabs: Loop · Windows · ChatGPT · OpenCode · Text · Watchdog · Debug ·
Advanced JSON. Every field has a tooltip explaining what it does, and the
Advanced tab holds the raw JSON for options not exposed in the form.
"""

from __future__ import annotations

import json

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QLabel, QLineEdit, QPlainTextEdit, QTabWidget, QSpinBox,
    QVBoxLayout, QWidget,
)

from ..config.profiles import Profile


def _line(default: str, tooltip: str = "") -> QLineEdit:
    w = QLineEdit(default)
    if tooltip:
        w.setToolTip(tooltip)
    return w


def _spin(default: int, lo: int, hi: int, tooltip: str = "") -> QSpinBox:
    w = QSpinBox()
    w.setRange(lo, hi)
    w.setValue(default)
    if tooltip:
        w.setToolTip(tooltip)
    return w


def _dspin(default: float, lo: float, hi: float, decimals: int = 1, tooltip: str = "") -> QDoubleSpinBox:
    w = QDoubleSpinBox()
    w.setRange(lo, hi)
    w.setDecimals(decimals)
    w.setValue(default)
    if tooltip:
        w.setToolTip(tooltip)
    return w


def _check(default: bool, tooltip: str = "") -> QCheckBox:
    w = QCheckBox()
    w.setChecked(default)
    if tooltip:
        w.setToolTip(tooltip)
    return w


def _combo(options, default: str, tooltip: str = "") -> QComboBox:
    w = QComboBox()
    w.addItems(options)
    w.setCurrentText(default)
    if tooltip:
        w.setToolTip(tooltip)
    return w


class SettingsDialog(QDialog):
    def __init__(self, profile: Profile, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.setWindowTitle("LoopBridge — Settings")
        self.resize(820, 680)

        tabs = QTabWidget()
        tabs.addTab(self._tab_loop(), "Loop")
        tabs.addTab(self._tab_windows(), "Windows")
        tabs.addTab(self._tab_chatgpt(), "ChatGPT")
        tabs.addTab(self._tab_opencode(), "OpenCode")
        tabs.addTab(self._tab_text(), "Text")
        tabs.addTab(self._tab_watchdog(), "Watchdog")
        tabs.addTab(self._tab_debug(), "Debug")
        tabs.addTab(self._tab_json(), "Advanced JSON")

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------ tabs
    def _tab_loop(self) -> QWidget:
        p = self.profile
        w = QWidget()
        f = QFormLayout(w)
        self.mode_combo = _combo(["infinite", "count"], p.loop.mode,
                                 "infinite = run forever; count = stop after N iterations")
        self.count_spin = _spin(p.loop.count, 0, 1_000_000, "0 means unlimited")
        self.mult_dspin = _dspin(p.timing.global_multiplier, 0.1, 10.0, 2,
                                 "Scales every delay — raise it if the loop is too fast")
        self.between_spin = _spin(p.timing.between_loops_ms, 0, 600000,
                                 "Delay between completed iterations")
        f.addRow("Loop mode", self.mode_combo)
        f.addRow("Loop count", self.count_spin)
        f.addRow("Timing multiplier", self.mult_dspin)
        f.addRow("Delay between loops (ms)", self.between_spin)
        return w

    def _tab_windows(self) -> QWidget:
        p = self.profile
        w = QWidget()
        f = QFormLayout(w)
        self.brave_regex = _line(p.windows.brave.title_regex,
                                 "Regex matched against the window title to find the Brave/ChatGPT window")
        self.brave_procs = _line(", ".join(p.windows.brave.processes),
                                 "Process names (comma-separated) used to disambiguate the window")
        self.ps_regex = _line(p.windows.powershell.title_regex,
                              "Regex matched against the window title to find the PowerShell/OpenCode window")
        self.ps_procs = _line(", ".join(p.windows.powershell.processes),
                              "Process names (comma-separated) used to disambiguate the window")
        self.restore_check = _check(p.windows.auto_restore, "Restore the window if it is minimized before acting")
        self.topmost_check = _check(p.windows.set_topmost, "Keep the target window on top while driving it")
        self.find_spin = _spin(p.windows.find_interval_ms, 100, 5000,
                               "How often to re-scan for the target windows")
        f.addRow("Brave title regex", self.brave_regex)
        f.addRow("Brave processes", self.brave_procs)
        f.addRow("PowerShell title regex", self.ps_regex)
        f.addRow("PowerShell processes", self.ps_procs)
        f.addRow("Auto-restore minimized", self.restore_check)
        f.addRow("Set topmost", self.topmost_check)
        f.addRow("Find interval (ms)", self.find_spin)
        return w

    def _tab_chatgpt(self) -> QWidget:
        p = self.profile
        w = QWidget()
        f = QFormLayout(w)
        self.copy_combo = _combo(["autocopy_button", "select_all", "cdp"], p.chatgpt.copy_method,
                                 "autocopy_button = click ChatGPT's copy button; select_all = Ctrl+A/Ctrl+C; "
                                 "cdp = read the page via DevTools (most robust, needs Brave with debug port)")
        self.done_combo = _combo(["uia_poll", "stop_button_gone", "cdp"], p.chatgpt.done_detection,
                                 "How the tool knows ChatGPT finished generating")
        self.send_combo = _combo(["enter", "ctrl_enter", "custom"], p.chatgpt.send_key,
                                 "Key that submits the composer message")
        self.custom_keys = _line(p.chatgpt.custom_send_keys, "Send keys used when send key = custom")
        self.paste_combo = _combo(["clipboard", "typing"], p.chatgpt.paste_method,
                                  "clipboard = Ctrl+V (fast); typing = typed character-by-character fallback")
        self.poll_spin = _spin(p.chatgpt.poll_interval_ms, 100, 10000,
                               "How often to poll ChatGPT for reply completion")
        self.cgpt_timeout = _dspin(p.chatgpt.timeout_s, 10, 86400, 0, "Timeout for the reply-wait phase")
        f.addRow("Copy method", self.copy_combo)
        f.addRow("Done detection", self.done_combo)
        f.addRow("Send key", self.send_combo)
        f.addRow("Custom send keys", self.custom_keys)
        f.addRow("Paste method", self.paste_combo)
        f.addRow("Poll interval (ms)", self.poll_spin)
        f.addRow("Reply timeout (s)", self.cgpt_timeout)
        return w

    def _tab_opencode(self) -> QWidget:
        p = self.profile
        w = QWidget()
        f = QFormLayout(w)
        self.oc_mode_combo = _combo(["screen_marker", "clipboard_noop", "api"], p.opencode.completion_mode,
                                    "screen_marker = poll terminal text for a prompt marker; clipboard_noop = "
                                    "detect a stable selection; api = run 'opencode run --format json' for exact signals")
        self.marker_line = _line(p.opencode.marker_regex,
                                 "Regex matched against the terminal text to detect that OpenCode finished")
        self.submit_combo = _combo(["paste_enter", "paste_select_enter"], p.opencode.submit,
                                   "paste_select_enter = paste, select all, then Enter (your flow)")
        self.capture_combo = _combo(["select_all_copy", "anchor_last_block"], p.opencode.capture,
                                    "How the OpenCode reply is selected and copied")
        self.oc_timeout = _dspin(p.opencode.timeout_s, 10, 86400, 0, "Timeout for the OpenCode-wait phase")
        self.oc_command = _line(p.opencode.command, "Command used in api mode")
        self.oc_cwd = _line(p.opencode.working_dir, "Working directory for the api-mode command (empty = current)")
        self.oc_visible = _check(p.opencode.visible_console, "Show the api-mode console window while opencode runs")
        self.oc_events = _line(", ".join(p.opencode.done_event_types),
                               "JSON event types treated as completion in api mode")
        f.addRow("Completion mode", self.oc_mode_combo)
        f.addRow("Marker regex", self.marker_line)
        f.addRow("Submit method", self.submit_combo)
        f.addRow("Reply capture", self.capture_combo)
        f.addRow("OpenCode timeout (s)", self.oc_timeout)
        f.addRow("API command", self.oc_command)
        f.addRow("API working dir", self.oc_cwd)
        f.addRow("Show API console", self.oc_visible)
        f.addRow("Done event types", self.oc_events)
        return w

    def _tab_text(self) -> QWidget:
        p = self.profile
        w = QWidget()
        f = QFormLayout(w)
        self.ansi_check = _check(p.text.sanitize_ansi,
                                 "Strip ANSI escape codes and control characters from copied text (recommended)")
        self.md_check = _check(p.text.strip_markdown, "Remove markdown code fences from copied text")
        self.prefix_line = _line(p.text.prefix, "Text prepended to every copied reply")
        self.suffix_line = _line(p.text.suffix, "Text appended to every copied reply")
        self.maxlen_spin = _spin(p.text.max_len, 0, 100000, "0 = no length limit; truncates replies longer than this")
        f.addRow("Sanitize ANSI", self.ansi_check)
        f.addRow("Strip markdown fences", self.md_check)
        f.addRow("Prefix", self.prefix_line)
        f.addRow("Suffix", self.suffix_line)
        f.addRow("Max length (chars)", self.maxlen_spin)
        return w

    def _tab_watchdog(self) -> QWidget:
        p = self.profile
        w = QWidget()
        f = QFormLayout(w)
        self.wd_timeout = _dspin(p.watchdog.default_timeout_s, 1, 86400, 0,
                                 "Default deadline for any phase that waits")
        self.retries_spin = _spin(p.watchdog.retries, 0, 50, "How many times a failed phase is retried")
        self.backoff_spin = _spin(p.watchdog.backoff_ms, 0, 60000,
                                  "Base backoff between retries (increases per attempt)")
        self.cont_check = _check(p.watchdog.continue_on_error,
                                 "Keep looping even if a phase fails its retries; otherwise the loop aborts")
        self.maxtime_dspin = _dspin(p.watchdog.max_run_time_s, 0, 86400, 0,
                                    "0 = no cap; otherwise the loop stops after this many seconds")
        f.addRow("Default phase timeout (s)", self.wd_timeout)
        f.addRow("Retries per phase", self.retries_spin)
        f.addRow("Backoff (ms)", self.backoff_spin)
        f.addRow("Continue on error", self.cont_check)
        f.addRow("Max run time (s)", self.maxtime_dspin)
        return w

    def _tab_debug(self) -> QWidget:
        p = self.profile
        w = QWidget()
        f = QFormLayout(w)
        self.dbg_check = _check(p.debug.enabled, "General debug logging")
        self.dry_check = _check(p.debug.dry_run,
                                "Act through the loop but do not actually send to OpenCode / ChatGPT")
        self.shot_check = _check(p.debug.screenshots, "Capture a screenshot on every phase (debugging)")
        self.tree_check = _check(p.debug.capture_tree, "Log the UIA control tree on failures (debugging)")
        f.addRow("Debug enabled", self.dbg_check)
        f.addRow("Dry-run", self.dry_check)
        f.addRow("Phase screenshots", self.shot_check)
        f.addRow("Capture UI tree", self.tree_check)
        return w

    def _tab_json(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        hint = QLabel("Raw profile JSON — edit anything, including options not in the form tabs. "
                      "Invalid JSON is ignored on apply.")
        hint.setStyleSheet("color: #9aa3b8;")
        self.json_view = QPlainTextEdit()
        self.json_view.setPlainText(json.dumps(self.profile.to_dict(), indent=2))
        self.json_view.setFont(QFont("Cascadia Code", 11))
        v.addWidget(hint)
        v.addWidget(self.json_view, stretch=1)
        return w

    # ------------------------------------------------------------------ apply
    def apply_to(self) -> Profile:
        """Write the form fields (and the valid parts of the JSON view) into the profile."""
        p = self.profile
        p.loop.mode = self.mode_combo.currentText().strip()
        p.loop.count = self.count_spin.value()
        p.timing.global_multiplier = self.mult_dspin.value()
        p.timing.between_loops_ms = self.between_spin.value()

        p.windows.brave.title_regex = self.brave_regex.text()
        p.windows.brave.processes = [s.strip() for s in self.brave_procs.text().split(",") if s.strip()]
        p.windows.powershell.title_regex = self.ps_regex.text()
        p.windows.powershell.processes = [s.strip() for s in self.ps_procs.text().split(",") if s.strip()]
        p.windows.auto_restore = self.restore_check.isChecked()
        p.windows.set_topmost = self.topmost_check.isChecked()
        p.windows.find_interval_ms = self.find_spin.value()

        p.chatgpt.copy_method = self.copy_combo.currentText().strip()
        p.chatgpt.done_detection = self.done_combo.currentText().strip()
        p.chatgpt.send_key = self.send_combo.currentText().strip()
        p.chatgpt.custom_send_keys = self.custom_keys.text()
        p.chatgpt.paste_method = self.paste_combo.currentText().strip()
        p.chatgpt.poll_interval_ms = self.poll_spin.value()
        p.chatgpt.timeout_s = self.cgpt_timeout.value()

        p.opencode.completion_mode = self.oc_mode_combo.currentText().strip()
        p.opencode.marker_regex = self.marker_line.text()
        p.opencode.submit = self.submit_combo.currentText().strip()
        p.opencode.capture = self.capture_combo.currentText().strip()
        p.opencode.timeout_s = self.oc_timeout.value()
        p.opencode.command = self.oc_command.text()
        p.opencode.working_dir = self.oc_cwd.text()
        p.opencode.visible_console = self.oc_visible.isChecked()
        p.opencode.done_event_types = [s.strip() for s in self.oc_events.text().split(",") if s.strip()]

        p.text.sanitize_ansi = self.ansi_check.isChecked()
        p.text.strip_markdown = self.md_check.isChecked()
        p.text.prefix = self.prefix_line.text()
        p.text.suffix = self.suffix_line.text()
        p.text.max_len = self.maxlen_spin.value()

        p.watchdog.default_timeout_s = self.wd_timeout.value()
        p.watchdog.retries = self.retries_spin.value()
        p.watchdog.backoff_ms = self.backoff_spin.value()
        p.watchdog.continue_on_error = self.cont_check.isChecked()
        p.watchdog.max_run_time_s = self.maxtime_dspin.value()

        p.debug.enabled = self.dbg_check.isChecked()
        p.debug.dry_run = self.dry_check.isChecked()
        p.debug.screenshots = self.shot_check.isChecked()
        p.debug.capture_tree = self.tree_check.isChecked()

        # Merge the raw JSON on top (validated; invalid JSON is ignored)
        try:
            data = json.loads(self.json_view.toPlainText())
            return Profile.from_dict({**p.to_dict(), **data})
        except (json.JSONDecodeError, TypeError):
            return p
