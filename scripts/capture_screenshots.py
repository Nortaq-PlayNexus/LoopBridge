"""Capture real screenshots of the LoopBridge desktop UI (offscreen Qt).

Usage:
    python scripts/capture_screenshots.py

Writes PNGs to docs/screenshots/. Requires PySide6. No display is needed:
the Qt offscreen platform renders the real widgets to images.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "windows")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtGui import QFont, QFontDatabase  # noqa: E402
from PySide6.QtWidgets import QApplication, QTabWidget  # noqa: E402

from loopbridge.ui.main_window import MainWindow  # noqa: E402
from loopbridge.ui.settings_page import SettingsDialog  # noqa: E402
from loopbridge.ui.theme import apply_theme  # noqa: E402

WINDOWS_FONTS = Path("C:/Windows/Fonts")


def register_fonts() -> None:
    """The offscreen platform has no system font database; load the fonts we use."""
    for name in ("segoeui.ttf", "segoeuib.ttf", "consola.ttf", "consolab.ttf",
                 "seguisb.ttf", "CascadiaCode.ttf", "CascadiaMono.ttf"):
        path = WINDOWS_FONTS / name
        if path.exists():
            QFontDatabase.addApplicationFont(str(path))

OUT = ROOT / "docs" / "screenshots"


def pump(app: QApplication, ms: int) -> None:
    end = time.time() + (ms / 1000.0)
    while time.time() < end:
        app.processEvents()
        time.sleep(0.01)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)
    register_fonts()
    app.setFont(QFont("Segoe UI", 9))
    apply_theme(app)

    win = MainWindow(str(ROOT / "loopbridge-profile.json"))
    win.resize(1100, 780)
    win.show()
    pump(app, 500)
    win.grab().save(str(OUT / "01-dashboard.png"))

    # Run a real simulated loop through the real orchestrator (mock drivers).
    win.btn_sim.setChecked(True)
    win.profile.loop.mode = "count"
    win.profile.loop.count = 2
    win.profile.timing.between_loops_ms = 0
    win._start()

    deadline = time.time() + 20
    while time.time() < deadline:
        app.processEvents()
        if win._run_stats.loops_completed >= 2 and not win._running:
            break
        time.sleep(0.02)
    pump(app, 400)
    win.grab().save(str(OUT / "02-dashboard-finished.png"))

    # Settings dialog, default tab.
    dialog = SettingsDialog(win.profile, win)
    dialog.resize(820, 680)
    dialog.show()
    pump(app, 350)
    dialog.grab().save(str(OUT / "03-settings.png"))

    # Settings dialog, OpenCode tab.
    tabs = dialog.findChild(QTabWidget)
    if tabs is not None:
        tabs.setCurrentIndex(3)
        pump(app, 250)
        dialog.grab().save(str(OUT / "04-settings-opencode.png"))

    if win.thread is not None:
        win.thread.quit()
        win.thread.wait(3000)

    print("wrote screenshots to", OUT)
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    # Qt can crash in interpreter teardown after a worker thread has run; the
    # files are already written, so exit without running global destructors.
    os._exit(code)
