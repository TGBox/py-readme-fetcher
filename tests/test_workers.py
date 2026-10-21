"""Tests for background workers."""

from unittest.mock import MagicMock

from src.gitlab.client import GitLabClient, GitLabProject
from src.workers.download_worker import DownloadWorker
from src.workers.preview_worker import PreviewWorker
from src.workers.scan_worker import ScanWorker


def test_scan_worker_execution(qtbot):
    mock_client = MagicMock(spec=GitLabClient)
    sample_projects = [
        GitLabProject(id=1, name="P1", path_with_namespace="g/p1", default_branch="main"),
        GitLabProject(id=2, name="P2", path_with_namespace="g/p2", default_branch="main"),
    ]
    mock_client.get_group_projects.return_value = sample_projects

    worker = ScanWorker(client=mock_client, group_id="my-group", include_subgroups=True)

    with qtbot.waitSignal(worker.finished, timeout=2000) as blocker:
        worker.start()

    assert blocker.args == [sample_projects]
    mock_client.get_group_projects.assert_called_once()


def test_download_worker_execution(qtbot, tmp_path):
    mock_client = MagicMock(spec=GitLabClient)
    project = GitLabProject(
        id=10, name="Repo", path_with_namespace="grp/repo", default_branch="main"
    )
    mock_client.fetch_readme.return_value = ("README.md", b"# Repo Content")

    worker = DownloadWorker(
        client=mock_client,
        projects=[project],
        output_dir=tmp_path,
    )

    with qtbot.waitSignal(worker.finished, timeout=2000) as blocker:
        worker.start()

    success_count, failed_count = blocker.args
    assert success_count == 1
    assert failed_count == 0

    downloaded_file = tmp_path / "grp_repo_README.md"
    assert downloaded_file.exists()
    assert downloaded_file.read_text(encoding="utf-8") == "# Repo Content"


def test_preview_worker_execution(qtbot):
    mock_client = MagicMock(spec=GitLabClient)
    project = GitLabProject(
        id=20, name="Viewer", path_with_namespace="grp/viewer", default_branch="main"
    )
    mock_client.fetch_readme.return_value = ("README.md", b"# Markdown Header\nSome details.")

    worker = PreviewWorker(client=mock_client, project=project)

    with qtbot.waitSignal(worker.loaded, timeout=2000) as blocker:
        worker.start()

    emitted_proj, filename, content = blocker.args
    assert emitted_proj.id == 20
    assert filename == "README.md"
    assert "Markdown Header" in content
