"""Tests for background workers."""

from unittest.mock import MagicMock

from src.gitlab.client import GitLabClient, GitLabProject
from src.workers.download_worker import DownloadWorker
from src.workers.preview_worker import PreviewWorker
from src.workers.scan_worker import ScanWorker


def test_scan_worker_execution_fast_scan(qtbot):
    mock_client = MagicMock(spec=GitLabClient)
    sample_projects = [
        GitLabProject(id=1, name="P1", path_with_namespace="g/p1", default_branch="main"),
        GitLabProject(id=2, name="P2", path_with_namespace="g/p2", default_branch="main"),
    ]
    mock_client.get_group_projects.return_value = sample_projects

    worker = ScanWorker(
        client=mock_client,
        group_id="my-group",
        include_subgroups=True,
        search_subfolders=False,
    )

    with qtbot.waitSignal(worker.finished, timeout=2000) as blocker:
        worker.start()

    assert blocker.args == [sample_projects]
    mock_client.get_group_projects.assert_called_once()
    mock_client.discover_project_readmes.assert_not_called()


def test_scan_worker_with_subfolder_discovery(qtbot):
    mock_client = MagicMock(spec=GitLabClient)
    sample_projects = [
        GitLabProject(id=1, name="P1", path_with_namespace="g/p1", default_branch="main"),
        GitLabProject(id=2, name="P2", path_with_namespace="g/p2", default_branch=None),  # empty
    ]
    mock_client.get_group_projects.return_value = sample_projects
    mock_client.discover_project_readmes.return_value = ["docs/README.md", "README.md"]

    worker = ScanWorker(
        client=mock_client,
        group_id="my-group",
        include_subgroups=True,
        search_subfolders=True,
    )

    with qtbot.waitSignal(worker.finished, timeout=2000) as blocker:
        worker.start()

    finished_projects = blocker.args[0]
    assert len(finished_projects) == 2
    assert finished_projects[0].readme_files == ("docs/README.md", "README.md")
    assert finished_projects[1].readme_files == ()  # empty repo not queried
    mock_client.discover_project_readmes.assert_called_once_with(
        project=sample_projects[0],
        cancel_check=worker.isInterruptionRequested,
    )


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

    downloaded_file = tmp_path / "grp_repo" / "README.md"
    assert downloaded_file.exists()
    assert downloaded_file.read_text(encoding="utf-8") == "# Repo Content"


def test_download_worker_subfolder_readme(qtbot, tmp_path):
    mock_client = MagicMock(spec=GitLabClient)
    project = GitLabProject(
        id=15,
        name="DataChat",
        path_with_namespace="grp/data-chat",
        default_branch="main",
        readme_files=("client/README.md",),
    )
    mock_client.fetch_readme.return_value = ("client/README.md", b"# Client Documentation")

    worker = DownloadWorker(
        client=mock_client,
        projects=[project],
        output_dir=tmp_path,
        download_all_readmes=False,
    )

    with qtbot.waitSignal(worker.finished, timeout=2000) as blocker:
        worker.start()

    success_count, failed_count = blocker.args
    assert success_count == 1
    assert failed_count == 0

    downloaded_file = tmp_path / "grp_data-chat" / "client" / "README.md"
    assert downloaded_file.exists()
    assert downloaded_file.read_text(encoding="utf-8") == "# Client Documentation"


def test_download_worker_download_all_readmes(qtbot, tmp_path):
    mock_client = MagicMock(spec=GitLabClient)
    project = GitLabProject(
        id=16,
        name="MultiDoc",
        path_with_namespace="grp/multidoc",
        default_branch="main",
        readme_files=("README.md", "docs/README.md"),
    )
    mock_client.fetch_file_content.side_effect = lambda project, file_path, cancel_check=None: (
        b"# Root Content" if file_path == "README.md" else b"# Docs Content"
    )

    worker = DownloadWorker(
        client=mock_client,
        projects=[project],
        output_dir=tmp_path,
        download_all_readmes=True,
    )

    with qtbot.waitSignal(worker.finished, timeout=2000) as blocker:
        worker.start()

    success_count, failed_count = blocker.args
    assert success_count == 1
    assert failed_count == 0

    root_file = tmp_path / "grp_multidoc" / "README.md"
    docs_file = tmp_path / "grp_multidoc" / "docs" / "README.md"
    assert root_file.exists()
    assert docs_file.exists()
    assert root_file.read_text(encoding="utf-8") == "# Root Content"
    assert docs_file.read_text(encoding="utf-8") == "# Docs Content"


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


def test_preview_worker_with_specific_file_path(qtbot):
    mock_client = MagicMock(spec=GitLabClient)
    project = GitLabProject(
        id=21, name="SpecificViewer", path_with_namespace="grp/specific", default_branch="main"
    )
    mock_client.fetch_readme.return_value = ("sub/README.md", b"# Sub Header")

    worker = PreviewWorker(client=mock_client, project=project, file_path="sub/README.md")

    with qtbot.waitSignal(worker.loaded, timeout=2000) as blocker:
        worker.start()

    emitted_proj, filename, content = blocker.args
    assert emitted_proj.id == 21
    assert filename == "sub/README.md"
    assert "Sub Header" in content
    mock_client.fetch_readme.assert_called_with(
        project, file_path="sub/README.md", cancel_check=worker.isInterruptionRequested
    )
