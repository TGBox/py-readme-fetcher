"""Worker thread for discovering projects within a GitLab group."""

from dataclasses import replace

from PySide6.QtCore import QThread, Signal

from src.gitlab.client import GitLabClient, GitLabProject


class ScanWorker(QThread):
    """Asynchronously scans a GitLab group for projects and discovers their README files."""

    progress = Signal(int, int, str)  # current, total, message
    finished = Signal(list)  # list of GitLabProject
    error = Signal(str)  # error description

    def __init__(
        self,
        client: GitLabClient,
        group_id: str,
        include_subgroups: bool = True,
        search_subfolders: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.client = client
        self.group_id = group_id
        self.include_subgroups = include_subgroups
        self.search_subfolders = search_subfolders

    def run(self) -> None:
        """Execute project scanning loop."""
        try:
            self.progress.emit(0, 0, f"Scanne Gruppe '{self.group_id}'...")

            def on_page(page: int, total_pages: int) -> None:
                if total_pages > 0:
                    msg = f"Lade Projekte-Seite {page} von {total_pages}..."
                else:
                    msg = f"Lade Projekte-Seite {page}..."
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

            total_projects = len(projects)
            if not self.search_subfolders:
                self.progress.emit(
                    total_projects,
                    total_projects,
                    f"{total_projects} Projekte gefunden.",
                )
                self.finished.emit(projects)
                return

            # Discover README files in repositories (including subfolders)
            updated_projects: list[GitLabProject] = []
            for index, project in enumerate(projects, start=1):
                if self.isInterruptionRequested():
                    self.progress.emit(0, 0, "Scan abgebrochen.")
                    self.finished.emit([])
                    return

                if not project.has_default_branch or project.empty_repo:
                    updated_projects.append(project)
                    continue

                self.progress.emit(
                    index,
                    total_projects,
                    f"Suche READMEs ({index}/{total_projects}): {project.path_with_namespace}",
                )

                discovered = self.client.discover_project_readmes(
                    project=project,
                    cancel_check=self.isInterruptionRequested,
                )

                updated_project = replace(project, readme_files=tuple(discovered))
                updated_projects.append(updated_project)

            if self.isInterruptionRequested():
                self.progress.emit(0, 0, "Scan abgebrochen.")
                self.finished.emit([])
                return

            self.progress.emit(
                total_projects,
                total_projects,
                f"{total_projects} Projekte gescannt.",
            )
            self.finished.emit(updated_projects)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))
