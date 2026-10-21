"""Application entry point for py-readme-fetcher."""

import sys

from PySide6.QtWidgets import QApplication

from src.ui.main_window import MainWindow


def main() -> None:
    """Initialize and run the PySide6 application."""
    app = QApplication(sys.argv)
    app.setApplicationName("py-readme-fetcher")
    app.setOrganizationName("py-readme-fetcher")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
