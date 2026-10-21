"""Worker thread for discovering projects within a GitLab group."""

from PySide6.QtCore import QThread, Signal

from src.gitlab.client import GitLabClient


class ScanWorker(QThread):
    """Asynchronously scans a GitLab group for projects."""

    progress = Signal(int, int, str)  # current, total, message
    finished = Signal(list)  # list of GitLabProject
    error = Signal(str)  # error description

    def __init__(
        self,
        client: GitLabClient,
        group_id: str,
        include_subgroups: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.client = client
        self.group_id = group_id
        self.include_subgroups = include_subgroups

    def run(self) -> None:
        """Execute project scanning loop."""
        try:
            self.progress.emit(0, 0, f"Scanne Gruppe '{self.group_id}'...")

            def on_page(page: int, total_pages: int) -> None:
                if total_pages > 0:
                    msg = f"Lade Seite {page} von {total_pages}..."
                else:
                    msg = f"Lade Seite {page}..."
                self.progress.emit(page, total_pages, msg)

            projects = self.client.get_group_projects(
                group_id=self.group_id,
                include_subgroups=self.include_subgroups,
                cancel_check=self.isInterruptionRequested,
                page_callback=on_page,
            )

            if self.isInterruptionRequested():
                self.progress.emit(0, 0, "Scan abgebrochen.")
                self.finished.emit([])
                return

            self.progress.emit(len(projects), len(projects), f"{len(projects)} Projekte gefunden.")
            self.finished.emit(projects)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))
