"""System tray integration (optional; used by the GUI launcher on Windows)."""

from __future__ import annotations

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


class LoopTray(QSystemTrayIcon):
    """Tray icon with Start / Pause / Resume / Step / Stop actions.

    The tooltip reflects the current loop state, set via :meth:`set_state`.
    """

    def __init__(self, parent=None):
        icon = QIcon.fromTheme("application-x-executable")
        super().__init__(icon if not icon.isNull() else QIcon(), parent)
        self.setToolTip("LoopBridge — idle")
        self._state = "idle"
        self._on_action = None

        menu = QMenu()
        self._actions = {}
        for label, key in (
            ("Start", "start"),
            ("Pause", "pause"),
            ("Resume", "resume"),
            ("Step once", "step"),
            ("Stop", "stop"),
        ):
            action = QAction(label, menu)
            action.triggered.connect(lambda _checked=False, k=key: self._emit(k))
            self._actions[key] = action
            menu.addAction(action)
        menu.addSeparator()
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self.hide)
        menu.addAction(quit_action)
        self.setContextMenu(menu)
        self._sync_menu()

    def _emit(self, key: str):
        if self._on_action is not None:
            self._on_action(key)

    def set_state(self, state: str) -> None:
        self._state = state
        labels = {
            "idle": "LoopBridge — idle",
            "running": "LoopBridge — running",
            "paused": "LoopBridge — paused",
            "finished": "LoopBridge — finished",
            "aborted": "LoopBridge — aborted",
        }
        self.setToolTip(labels.get(state, labels["idle"]))
        self._sync_menu()

    def _sync_menu(self) -> None:
        self._actions["pause"].setEnabled(self._state == "running")
        self._actions["resume"].setEnabled(self._state == "paused")
        self._actions["step"].setEnabled(self._state == "paused")
        self._actions["start"].setEnabled(self._state != "running")
        self._actions["stop"].setEnabled(self._state in ("running", "paused"))
