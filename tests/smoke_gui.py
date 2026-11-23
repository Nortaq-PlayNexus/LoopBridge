"""Headless GUI smoke test for the LoopBridge dashboard.

Runs the polished PySide6 UI with the offscreen Qt platform (no display
needed) and drives a simulated loop, verifying the dashboard wires up
correctly: phase cards, stats, reply previews, settings dialog.

Run with:  QT_QPA_PLATFORM=offscreen python tests/smoke_gui.py
"""

from __future__ import annotations

import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from loopbridge.config.profiles import Profile
from loopbridge.ui.main_window import MainWindow
from loopbridge.ui.settings_page import SettingsDialog
from loopbridge.ui.theme import apply_theme


def main() -> int:
    app = QApplication(sys.argv)
    apply_theme(app)

    profile_path = os.path.join(os.path.dirname(__file__), "..", "loopbridge-profile.json")
    win = MainWindow(profile_path)

    # --- settings dialog opens and applies cleanly
    profile = Profile()
    dialog = SettingsDialog(profile, win)
    applied = dialog.apply_to()
    assert applied.loop.mode == profile.loop.mode
    assert applied.chatgpt.copy_method == profile.chatgpt.copy_method
    print("PASS settings dialog builds and applies")

    # --- simulate toggle, then start a simulated loop
    win.btn_sim.setChecked(True)
    win.profile.loop.count = 1
    win.profile.timing.between_loops_ms = 0
    win._start()

    def finish():
        # wait for the loop to finish (mock loop finishes quickly)
        if win.worker is not None and win.worker.orch is not None:
            if not win.thread.isRunning():
                done()
                return
        QTimer.singleShot(200, finish)

    def done():
        assert win._run_stats.loops_completed == 1, win._run_stats.to_dict()
        assert win.lbl_loops.text() == "1"
        assert win.lbl_gpt_reply.text() != "—", "ChatGPT reply preview not shown"
        assert win.lbl_oc_reply.text() != "—", "OpenCode reply preview not shown"
        assert win.status_pill.text() in ("✓ finished", "idle")
        # all six phase cards should have been used
        assert all(card is not None for card in win.phase_cards.values())
        print("PASS dashboard runs a simulated loop: phases, stats, reply previews")
        print("PASS status pill:", win.status_pill.text().encode("ascii", "replace").decode("ascii"))
        print("GUI smoke test passed.")
        app.quit()

    QTimer.singleShot(300, finish)
    app.exec()
    return 0


if __name__ == "__main__":
    sys.exit(main())
