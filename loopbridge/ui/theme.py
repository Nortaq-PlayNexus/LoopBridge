"""Shared dark theme for the LoopBridge desktop UI."""

from __future__ import annotations

DARK_QSS = """
QWidget {
    background: #171922;
    color: #e6e8ef;
    font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
    font-size: 13px;
}

QMainWindow, QDialog { background: #171922; }

QGroupBox {
    border: 1px solid #2b2f3d;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 10px;
    font-weight: 600;
    color: #9aa3b8;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #7dd3fc;
}

QPushButton {
    background: #232838;
    border: 1px solid #333a4d;
    border-radius: 6px;
    padding: 8px 14px;
    color: #e6e8ef;
}
QPushButton:hover { background: #2c3348; border-color: #4a5570; }
QPushButton:pressed { background: #383f57; }
QPushButton:disabled { color: #5a6072; background: #1d2029; border-color: #232734; }
QPushButton#primary {
    background: #2563eb; border: none; font-weight: 600;
}
QPushButton#primary:hover { background: #3b82f6; }
QPushButton#danger { background: #7f1d1d; border: none; font-weight: 600; }
QPushButton#danger:hover { background: #b91c1c; }
QPushButton#toggle {
    background: #1d2029; border: 1px dashed #4a5570;
}
QPushButton#toggle:checked {
    background: #0f5132; border: 1px solid #16a34a; color: #bbf7d0;
}

QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background: #1d2029;
    border: 1px solid #2b2f3d;
    border-radius: 6px;
    padding: 6px 8px;
    selection-background-color: #2563eb;
}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #2563eb;
}
QComboBox QAbstractItemView {
    background: #1d2029; border: 1px solid #333a4d; selection-background-color: #2563eb;
}
QCheckBox { spacing: 8px; }
QCheckBox::indicator {
    width: 16px; height: 16px; border-radius: 4px;
    border: 1px solid #4a5570; background: #1d2029;
}
QCheckBox::indicator:checked { background: #2563eb; border-color: #3b82f6; }

QPlainTextEdit { font-family: "Cascadia Code", "Consolas", monospace; font-size: 12px; }

QTabWidget::pane { border: 1px solid #2b2f3d; border-radius: 8px; top: -1px; }
QTabBar::tab {
    background: #1d2029; border: 1px solid #2b2f3d; border-bottom: none;
    border-top-left-radius: 6px; border-top-right-radius: 6px;
    padding: 8px 16px; margin-right: 2px; color: #9aa3b8;
}
QTabBar::tab:selected { background: #232838; color: #e6e8ef; font-weight: 600; }
QTabBar::tab:hover { color: #e6e8ef; }

QScrollBar:vertical { background: #171922; width: 10px; }
QScrollBar::handle:vertical { background: #333a4d; border-radius: 5px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #4a5570; }
QScrollBar:horizontal { background: #171922; height: 10px; }
QScrollBar::handle:horizontal { background: #333a4d; border-radius: 5px; min-width: 30px; }

QStatusBar { background: #1d2029; color: #9aa3b8; }
QToolTip {
    background: #232838; color: #e6e8ef; border: 1px solid #4a5570;
    padding: 4px 8px; border-radius: 4px;
}
QLabel#heading { font-size: 18px; font-weight: 700; }
QLabel#subheading { color: #9aa3b8; }
QLabel#statValue { font-size: 16px; font-weight: 700; }
"""

# Phase card colours: idle / running / done / error
PHASE_COLORS = {
    "idle":   ("#232838", "#5a6072", "#333a4d"),
    "running": ("#dbeafe", "#2563eb", "#2563eb"),
    "done":    ("#d9f7e6", "#16a34a", "#16a34a"),
    "error":   ("#fee2e2", "#dc2626", "#dc2626"),
}


def apply_theme(app) -> None:
    app.setStyleSheet(DARK_QSS)
