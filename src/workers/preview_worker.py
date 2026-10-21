"""Worker thread for fetching a single README for preview."""

from PySide6.QtCore import QThread, Signal

from src.gitlab.client import GitLabClient, GitLabProject


class PreviewWorker(QThread):
    """Fetches a single project's README for the integrated preview."""

    loaded = Signal(object, str, str)  # project, filename, markdown_content
    failed = Signal(object, str)  # project, error_message

    def __init__(
        self,
        client: GitLabClient,
        project: GitLabProject,
        file_path: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.client = client
        self.project = project
        self.file_path = file_path

    def run(self) -> None:
        """Fetch README and emit content as decoded string."""
        try:
            if not self.project.has_default_branch:
                self.failed.emit(self.project, "Projekt hat keinen Standard-Branch.")
                return

            result = self.client.fetch_readme(
                self.project,
                file_path=self.file_path,
                cancel_check=self.isInterruptionRequested,
            )

            if self.isInterruptionRequested():
                return

            if result is None:
                self.failed.emit(self.project, "Keine README-Datei in diesem Projekt gefunden.")
                return

            filename, raw_bytes = result
            # Try decoding utf-8 with fallback replacement
            content = raw_bytes.decode("utf-8", errors="replace")
            self.loaded.emit(self.project, filename, content)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(self.project, f"Fehler beim Laden: {exc}")
