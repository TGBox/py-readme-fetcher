"""UI tests for MainWindow using pytest-qt."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit

from src.gitlab.client import GitLabProject
from src.ui.main_window import MainWindow


def test_main_window_initialization(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    assert "py-readme-fetcher" in window.windowTitle()
    assert window.scan_btn.isEnabled()
    assert not window.download_btn.isEnabled()
    assert not window.cancel_btn.isEnabled()
    assert window.token_input.echoMode() == QLineEdit.EchoMode.Password


def test_main_window_toggle_theme(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    initial_mode = window.dark_mode
    window._toggle_theme()
    assert window.dark_mode != initial_mode
    assert (
        ("Dunkel" in window.theme_btn.text())
        if window.dark_mode
        else ("Hell" in window.theme_btn.text())
    )


def test_main_window_toggle_token_visibility(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.token_input.echoMode() == QLineEdit.EchoMode.Password
    window._toggle_token_visibility()
    assert window.token_input.echoMode() == QLineEdit.EchoMode.Normal
    window._toggle_token_visibility()
    assert window.token_input.echoMode() == QLineEdit.EchoMode.Password


def test_main_window_populate_table_and_filtering(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    projects = [
        GitLabProject(
            id=1, name="Frontend", path_with_namespace="org/team/frontend", default_branch="main"
        ),
        GitLabProject(
            id=2, name="Backend", path_with_namespace="org/team/backend", default_branch="develop"
        ),
        GitLabProject(
            id=3, name="Empty", path_with_namespace="org/team/empty", default_branch=None
        ),
    ]

    window._on_scan_finished(projects)
    assert window.table.rowCount() == 3
    assert window.download_btn.isEnabled()

    # Empty repo should not be checked by default
    assert window.table.item(0, 0).checkState() == Qt.CheckState.Checked
    assert window.table.item(1, 0).checkState() == Qt.CheckState.Checked
    assert window.table.item(2, 0).checkState() == Qt.CheckState.Unchecked

    # Selection counter
    assert "2 von 3" in window.table_count_label.text()

    # Filter functionality
    window.filter_input.setText("backend")
    assert window.table.isRowHidden(0)
    assert not window.table.isRowHidden(1)
    assert window.table.isRowHidden(2)

    # Clear filter
    window.filter_input.setText("")
    assert not window.table.isRowHidden(0)
    assert not window.table.isRowHidden(1)
    assert not window.table.isRowHidden(2)


def test_main_window_select_all_none(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    projects = [
        GitLabProject(id=1, name="A", path_with_namespace="g/a", default_branch="main"),
        GitLabProject(id=2, name="B", path_with_namespace="g/b", default_branch="main"),
    ]
    window._on_scan_finished(projects)

    window._set_all_selected(False)
    assert window.table.item(0, 0).checkState() == Qt.CheckState.Unchecked
    assert window.table.item(1, 0).checkState() == Qt.CheckState.Unchecked
    assert "0 von 2" in window.table_count_label.text()

    window._set_all_selected(True)
    assert window.table.item(0, 0).checkState() == Qt.CheckState.Checked
    assert window.table.item(1, 0).checkState() == Qt.CheckState.Checked
    assert "2 von 2" in window.table_count_label.text()


def test_main_window_fullscreen_toggle(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    assert not window.isFullScreen()
    window._toggle_fullscreen()
    assert window.isFullScreen()
    window._toggle_fullscreen()
    assert not window.isFullScreen()


def test_main_window_settings_persistence(qtbot, tmp_path):
    window = MainWindow()
    qtbot.addWidget(window)

    window.url_input.setText("https://gitlab.custom.internal")
    window.group_input.setText("custom-group/sub")
    window.output_dir_input.setText(str(tmp_path / "custom_readmes"))
    window.save_token_cb.setChecked(True)
    window.token_input.setText("glpat-secret-123")

    window._save_settings()

    # Re-read via another window instance
    window2 = MainWindow()
    qtbot.addWidget(window2)

    assert window2.url_input.text() == "https://gitlab.custom.internal"
    assert window2.group_input.text() == "custom-group/sub"
    assert window2.output_dir_input.text() == str(tmp_path / "custom_readmes")
    assert window2.save_token_cb.isChecked()
    assert window2.token_input.text() == "glpat-secret-123"
