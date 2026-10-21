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
        download_all_readmes: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.client = client
        self.projects = projects
        self.output_dir = output_dir
        self.download_all_readmes = download_all_readmes

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

                files_to_download: list[str] = list(project.readme_files)

                # If downloading all READMEs, ensure full tree discovery if files_to_download has <= 1 entry
                if self.download_all_readmes and len(files_to_download) <= 1:
                    discovered = self.client.discover_project_readmes(
                        project=project,
                        cancel_check=self.isInterruptionRequested,
                    )
                    if discovered:
                        files_to_download = discovered

                if self.download_all_readmes and files_to_download:
                    saved_files: list[str] = []
                    for file_path in files_to_download:
                        if self.isInterruptionRequested():
                            break
                        content = self.client.fetch_file_content(
                            project=project,
                            file_path=file_path,
                            cancel_check=self.isInterruptionRequested,
                        )
                        if content is not None:
                            target_file = self.output_dir / project.get_relative_target_path(
                                file_path
                            )
                            target_file.parent.mkdir(parents=True, exist_ok=True)
                            target_file.write_bytes(content)
                            saved_files.append(file_path)

                    if self.isInterruptionRequested():
                        break

                    if saved_files:
                        successful += 1
                        display_text = (
                            f"{len(saved_files)} README{'s' if len(saved_files) > 1 else ''}"
                        )
                        self.item_completed.emit(
                            project,
                            display_text,
                            True,
                            f"Erfolgreich gespeichert ({display_text})",
                        )
                    else:
                        failed += 1
                        self.item_completed.emit(
                            project,
                            "",
                            False,
                            "Keine README-Datei gefunden",
                        )
                else:
                    # Single primary README download (with automatic fallback to subfolder)
                    target_candidate: str | None = (
                        files_to_download[0] if files_to_download else None
                    )
                    readme_result = None

                    if target_candidate:
                        content = self.client.fetch_file_content(
                            project=project,
                            file_path=target_candidate,
                            cancel_check=self.isInterruptionRequested,
                        )
                        if content is not None:
                            readme_result = (target_candidate, content)

                    if readme_result is None:
                        readme_result = self.client.fetch_readme(
                            project=project,
                            cancel_check=self.isInterruptionRequested,
                        )

                    if readme_result is None:
                        # Full discovery fallback if root search failed
                        discovered = self.client.discover_project_readmes(
                            project=project,
                            cancel_check=self.isInterruptionRequested,
                        )
                        if discovered:
                            sub_content = self.client.fetch_file_content(
                                project=project,
                                file_path=discovered[0],
                                cancel_check=self.isInterruptionRequested,
                            )
                            if sub_content is not None:
                                readme_result = (discovered[0], sub_content)

                    if self.isInterruptionRequested():
                        break

                    if readme_result is not None:
                        filename, content = readme_result
                        target_file = self.output_dir / project.get_relative_target_path(filename)
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        target_file.write_bytes(content)
                        successful += 1
                        self.item_completed.emit(
                            project,
                            filename,
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
