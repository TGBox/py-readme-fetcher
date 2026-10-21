"""Stylesheets and theme management for dark and light modes."""

DARK_THEME_QSS = """
/* Global Dark Theme */
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
}

/* GroupBox / Panels */
QGroupBox {
    border: 1px solid #313244;
    border-radius: 8px;
    margin-top: 12px;
    padding: 12px;
    background-color: #181825;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #89b4fa;
}

/* Labels */
QLabel {
    background: transparent;
    color: #cdd6f4;
}

/* Inputs */
QLineEdit {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: #89b4fa;
    selection-color: #11111b;
}
QLineEdit:focus {
    border: 1px solid #89b4fa;
    background-color: #363a4f;
}

/* Buttons */
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #45475a;
    border-color: #585b70;
}
QPushButton:pressed {
    background-color: #585b70;
}
QPushButton:disabled {
    background-color: #181825;
    color: #6c7086;
    border-color: #313244;
}

/* Primary Accent Button */
QPushButton#primaryButton {
    background-color: #89b4fa;
    color: #11111b;
    border: 1px solid #89b4fa;
    font-weight: bold;
}
QPushButton#primaryButton:hover {
    background-color: #b4befe;
    border-color: #b4befe;
}
QPushButton#primaryButton:pressed {
    background-color: #74c7ec;
}
QPushButton#primaryButton:disabled {
    background-color: #313244;
    color: #6c7086;
    border-color: #313244;
}

/* Success Button */
QPushButton#successButton {
    background-color: #a6e3a1;
    color: #11111b;
    border: 1px solid #a6e3a1;
    font-weight: bold;
}
QPushButton#successButton:hover {
    background-color: #94e2d5;
}
QPushButton#successButton:disabled {
    background-color: #313244;
    color: #6c7086;
    border-color: #313244;
}

/* Danger Button */
QPushButton#dangerButton {
    background-color: #f38ba8;
    color: #11111b;
    border: 1px solid #f38ba8;
}
QPushButton#dangerButton:hover {
    background-color: #eba0ac;
}
QPushButton#dangerButton:disabled {
    background-color: #313244;
    color: #6c7086;
    border-color: #313244;
}

/* Checkboxes */
QCheckBox {
    spacing: 8px;
    background: transparent;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #45475a;
    background-color: #313244;
}
QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}

/* Tables */
QTableWidget {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 8px;
    gridline-color: #313244;
    selection-background-color: #45475a;
    selection-color: #cdd6f4;
}
QHeaderView::section {
    background-color: #11111b;
    color: #a6adc8;
    padding: 8px 6px;
    border: none;
    border-right: 1px solid #313244;
    border-bottom: 1px solid #313244;
    font-weight: bold;
}
QTableWidget::item {
    padding: 4px 6px;
}
QTableWidget::item:selected {
    background-color: #313244;
}

/* Splitter */
QSplitter::handle {
    background-color: #313244;
    width: 4px;
    height: 4px;
}
QSplitter::handle:hover {
    background-color: #89b4fa;
}

/* TextBrowser (Markdown Viewer) */
QTextBrowser {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 8px;
    padding: 12px;
    color: #cdd6f4;
    line-height: 1.5;
}

/* Progress Bar */
QProgressBar {
    border: 1px solid #313244;
    border-radius: 6px;
    text-align: center;
    background-color: #181825;
    color: #cdd6f4;
    height: 18px;
}
QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 5px;
}

/* Status Bar */
QStatusBar {
    background-color: #11111b;
    color: #a6adc8;
    border-top: 1px solid #313244;
}
"""

LIGHT_THEME_QSS = """
/* Global Light Theme */
QWidget {
    background-color: #f8fafc;
    color: #1e293b;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
}

/* GroupBox / Panels */
QGroupBox {
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    margin-top: 12px;
    padding: 12px;
    background-color: #ffffff;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #2563eb;
}

/* Labels */
QLabel {
    background: transparent;
    color: #1e293b;
}

/* Inputs */
QLineEdit {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: #3b82f6;
    selection-color: #ffffff;
}
QLineEdit:focus {
    border: 1px solid #3b82f6;
    background-color: #ffffff;
}

/* Buttons */
QPushButton {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #f1f5f9;
    border-color: #94a3b8;
}
QPushButton:pressed {
    background-color: #e2e8f0;
}
QPushButton:disabled {
    background-color: #f8fafc;
    color: #94a3b8;
    border-color: #e2e8f0;
}

/* Primary Accent Button */
QPushButton#primaryButton {
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #2563eb;
    font-weight: bold;
}
QPushButton#primaryButton:hover {
    background-color: #1d4ed8;
    border-color: #1d4ed8;
}
QPushButton#primaryButton:pressed {
    background-color: #1e40af;
}
QPushButton#primaryButton:disabled {
    background-color: #e2e8f0;
    color: #94a3b8;
    border-color: #e2e8f0;
}

/* Success Button */
QPushButton#successButton {
    background-color: #16a34a;
    color: #ffffff;
    border: 1px solid #16a34a;
    font-weight: bold;
}
QPushButton#successButton:hover {
    background-color: #15803d;
}
QPushButton#successButton:disabled {
    background-color: #e2e8f0;
    color: #94a3b8;
    border-color: #e2e8f0;
}

/* Danger Button */
QPushButton#dangerButton {
    background-color: #dc2626;
    color: #ffffff;
    border: 1px solid #dc2626;
}
QPushButton#dangerButton:hover {
    background-color: #b91c1c;
}
QPushButton#dangerButton:disabled {
    background-color: #e2e8f0;
    color: #94a3b8;
    border-color: #e2e8f0;
}

/* Checkboxes */
QCheckBox {
    spacing: 8px;
    background: transparent;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #cbd5e1;
    background-color: #ffffff;
}
QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #2563eb;
}

/* Tables */
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    gridline-color: #f1f5f9;
    selection-background-color: #e0f2fe;
    selection-color: #0369a1;
}
QHeaderView::section {
    background-color: #f1f5f9;
    color: #475569;
    padding: 8px 6px;
    border: none;
    border-right: 1px solid #e2e8f0;
    border-bottom: 1px solid #e2e8f0;
    font-weight: bold;
}
QTableWidget::item {
    padding: 4px 6px;
}
QTableWidget::item:selected {
    background-color: #e0f2fe;
}

/* Splitter */
QSplitter::handle {
    background-color: #e2e8f0;
    width: 4px;
    height: 4px;
}
QSplitter::handle:hover {
    background-color: #3b82f6;
}

/* TextBrowser (Markdown Viewer) */
QTextBrowser {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 12px;
    color: #1e293b;
    line-height: 1.5;
}

/* Progress Bar */
QProgressBar {
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    text-align: center;
    background-color: #ffffff;
    color: #1e293b;
    height: 18px;
}
QProgressBar::chunk {
    background-color: #2563eb;
    border-radius: 5px;
}

/* Status Bar */
QStatusBar {
    background-color: #f1f5f9;
    color: #64748b;
    border-top: 1px solid #e2e8f0;
}
"""


def apply_theme(widget, dark_mode: bool = True) -> None:
    """Apply the chosen theme stylesheet to the widget or application."""
    widget.setStyleSheet(DARK_THEME_QSS if dark_mode else LIGHT_THEME_QSS)
