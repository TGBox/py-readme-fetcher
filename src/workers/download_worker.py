"""Worker thread for downloading README files from selected projects."""

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from src.gitlab.client import GitLabClient, GitLabProject


class DownloadWorker(QThread):
    """Asynchronously downloads README files for a collection of projects."""

    progress = Signal(int, int, str)  # current, total, project path
    item_completed = Signal(object, str, bool, str)  # project, filename, success, message
    finished = Signal(int, int)  # success_count, failed_count
    error = Signal(str)

    def __init__(
        self,
        client: GitLabClient,
        projects: list[GitLabProject],
        output_dir: Path,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.client = client
        self.projects = projects
        self.output_dir = output_dir

    def run(self) -> None:
        """Execute download loop over selected projects."""
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            total = len(self.projects)
            successful = 0
            failed = 0

            for index, project in enumerate(self.projects, start=1):
                if self.isInterruptionRequested():
                    self.progress.emit(index - 1, total, "Download abgebrochen.")
                    break

                self.progress.emit(index, total, project.path_with_namespace)

                if not project.has_default_branch:
                    failed += 1
                    self.item_completed.emit(
                        project,
                        "",
                        False,
                        "Kein Standard-Branch (leeres Repository)",
                    )
                    continue

                readme_result = self.client.fetch_readme(
                    project=project,
                    cancel_check=self.isInterruptionRequested,
                )

                if self.isInterruptionRequested():
                    break

                if readme_result is not None:
                    filename, content = readme_result
                    safe_name = project.get_safe_filename(filename)
                    target_file = self.output_dir / safe_name
                    target_file.write_bytes(content)
                    successful += 1
                    self.item_completed.emit(
                        project,
                        safe_name,
                        True,
                        f"Erfolgreich gespeichert ({len(content)} Bytes)",
                    )
                else:
                    failed += 1
                    self.item_completed.emit(
                        project,
                        "",
                        False,
                        "Keine README-Datei gefunden",
                    )

            self.finished.emit(successful, failed)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))
