"""Tests for GitLabClient and related functions."""

from unittest.mock import MagicMock

import requests

from src.gitlab.client import GitLabClient, GitLabProject, compute_safe_filename


def test_compute_safe_filename():
    assert (
        compute_safe_filename("my-group/subgroup/project", "README.md")
        == "my-group_subgroup_project_README.md"
    )
    assert (
        compute_safe_filename("/leading/and/trailing/", "readme.rst")
        == "leading_and_trailing_readme.rst"
    )


def test_gitlab_project_properties():
    proj = GitLabProject(
        id=123,
        name="Test Proj",
        path_with_namespace="org/team/test-proj",
        default_branch="main",
        readme_url="https://gitlab.com/org/team/test-proj/-/blob/main/README.md",
    )
    assert proj.has_default_branch is True
    assert proj.get_safe_filename("README.md") == "org_team_test-proj_README.md"

    empty_proj = GitLabProject(
        id=124,
        name="Empty Proj",
        path_with_namespace="org/team/empty-proj",
        default_branch=None,
    )
    assert empty_proj.has_default_branch is False


def test_determine_readme_candidates():
    client = GitLabClient()
    proj = GitLabProject(
        id=1,
        name="Proj",
        path_with_namespace="g/p",
        default_branch="main",
        readme_url="https://gitlab.example.com/g/p/-/blob/main/docs/README.md",
    )
    candidates = client._determine_readme_candidates(proj)
    assert candidates[0] == "README.md"
    assert "readme.md" in candidates
    assert "README.rst" in candidates

    proj_rst = GitLabProject(
        id=2,
        name="ProjRst",
        path_with_namespace="g/p2",
        default_branch="main",
        readme_url="https://gitlab.example.com/g/p2/-/blob/main/README.rst",
    )
    candidates_rst = client._determine_readme_candidates(proj_rst)
    assert candidates_rst[0] == "README.rst"
    assert candidates_rst.count("README.rst") == 1


def test_get_group_projects_pagination():
    mock_session = MagicMock(spec=requests.Session)

    res_page1 = MagicMock()
    res_page1.status_code = 200
    res_page1.headers = {"X-Total-Pages": "2", "X-Next-Page": "2"}
    res_page1.json.return_value = [
        {
            "id": 1,
            "name": "Project 1",
            "path_with_namespace": "group/sub/p1",
            "default_branch": "main",
            "readme_url": "https://gitlab.com/group/sub/p1/-/blob/main/README.md",
        }
    ]

    res_page2 = MagicMock()
    res_page2.status_code = 200
    res_page2.headers = {"X-Total-Pages": "2", "X-Next-Page": ""}
    res_page2.json.return_value = [
        {
            "id": 2,
            "name": "Project 2",
            "path_with_namespace": "group/sub/p2",
            "default_branch": "master",
            "readme_url": None,
        }
    ]

    mock_session.get.side_effect = [res_page1, res_page2]

    client = GitLabClient(
        base_url="https://gitlab.example.com/",
        private_token="test-token",
        session=mock_session,
    )

    pages_visited: list[tuple[int, int]] = []

    def on_page(page: int, total: int):
        pages_visited.append((page, total))

    projects = client.get_group_projects(
        "group/sub",
        include_subgroups=True,
        page_callback=on_page,
    )

    assert len(projects) == 2
    assert projects[0].id == 1
    assert projects[1].id == 2
    assert pages_visited == [(1, 2), (2, 2)]

    # Check request call
    assert mock_session.get.call_count == 2
    first_call_args, first_call_kwargs = mock_session.get.call_args_list[0]
    assert first_call_kwargs["headers"]["PRIVATE-TOKEN"] == "test-token"
    assert "group%2Fsub" in first_call_args[0]


def test_fetch_readme_success_on_fallback():
    mock_session = MagicMock(spec=requests.Session)

    # 404 for README.md, then 200 for readme.md
    res_404 = MagicMock()
    res_404.status_code = 404

    res_200 = MagicMock()
    res_200.status_code = 200
    res_200.content = b"# Readme Content"

    mock_session.get.side_effect = [res_404, res_200]

    client = GitLabClient(session=mock_session)
    proj = GitLabProject(
        id=10,
        name="Fallback Proj",
        path_with_namespace="my/proj",
        default_branch="main",
    )

    result = client.fetch_readme(proj)
    assert result is not None
    filename, content = result
    assert filename == "readme.md"
    assert content == b"# Readme Content"


def test_fetch_readme_empty_repo():
    client = GitLabClient()
    empty_proj = GitLabProject(
        id=99,
        name="Empty",
        path_with_namespace="g/empty",
        default_branch=None,
    )
    assert client.fetch_readme(empty_proj) is None


def test_verify_ssl_setting():
    mock_session = MagicMock(spec=requests.Session)
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = []
    mock_session.get.return_value = mock_res

    client = GitLabClient(verify_ssl=False, session=mock_session)
    assert client.verify_ssl is False

    client.get_group_projects("my-group")
    assert mock_session.get.call_args[1]["verify"] is False


def test_is_readme_file():
    from src.gitlab.client import is_readme_file

    assert is_readme_file("README.md") is True
    assert is_readme_file("README") is True
    assert is_readme_file("readme.rst") is True
    assert is_readme_file("docs/README.md") is True
    assert is_readme_file("deep/nested/sub/README.txt") is True

    # Ignored directories
    assert is_readme_file("node_modules/pkg/README.md") is False
    assert is_readme_file("vendor/bundle/README.md") is False
    assert is_readme_file(".git/README.md") is False
    assert is_readme_file("venv/lib/README.md") is False
    assert is_readme_file(".venv/lib/README.md") is False
    assert is_readme_file("dist/README.md") is False
    assert is_readme_file("pkg.egg-info/README.txt") is False

    # Non-readme files
    assert is_readme_file("main.py") is False
    assert is_readme_file("readme_helper.py") is False


def test_compute_relative_target_path():
    from pathlib import Path

    from src.gitlab.client import compute_relative_target_path

    path = compute_relative_target_path("org/team/data-chat", "client/README.md")
    assert path == Path("org_team_data-chat") / "client" / "README.md"


def test_discover_project_readmes():
    mock_session = MagicMock(spec=requests.Session)
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.headers = {}
    mock_res.json.return_value = [
        {"type": "blob", "path": "packages/client/README.md"},
        {"type": "blob", "path": "node_modules/pkg/README.md"},
        {"type": "blob", "path": "README.md"},
        {"type": "blob", "path": "docs/README.rst"},
        {"type": "blob", "path": "src/main.py"},
    ]
    mock_session.get.return_value = mock_res

    client = GitLabClient(session=mock_session)
    project = GitLabProject(
        id=42,
        name="DataChat",
        path_with_namespace="org/data-chat",
        default_branch="main",
    )

    readmes = client.discover_project_readmes(project)
    # Root README first, then depth 1 (docs/), then depth 2 (packages/client/)
    assert readmes == ["README.md", "docs/README.rst", "packages/client/README.md"]


def test_fetch_file_content_url_encoded():
    mock_session = MagicMock(spec=requests.Session)
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.content = b"# Subfolder Content"
    mock_session.get.return_value = mock_res

    client = GitLabClient(base_url="https://gitlab.example.com", session=mock_session)
    project = GitLabProject(
        id=42,
        name="DataChat",
        path_with_namespace="org/data-chat",
        default_branch="main",
    )

    content = client.fetch_file_content(project, "client/sub/README.md")
    assert content == b"# Subfolder Content"

    call_url = mock_session.get.call_args[0][0]
    assert "client%2Fsub%2FREADME.md" in call_url


def test_get_repository_tree_link_header_pagination():
    mock_session = MagicMock(spec=requests.Session)
    res_page1 = MagicMock()
    res_page1.status_code = 200
    res_page1.links = {
        "next": {
            "url": "https://gitlab.example.com/api/v4/projects/42/repository/tree?pagination=keyset&page_token=abc"
        }
    }
    res_page1.headers = {}
    res_page1.json.return_value = [
        {"type": "blob", "path": "file1.txt"},
    ]

    res_page2 = MagicMock()
    res_page2.status_code = 200
    res_page2.links = {}
    res_page2.headers = {}
    res_page2.json.return_value = [
        {"type": "blob", "path": "file2.txt"},
    ]

    mock_session.get.side_effect = [res_page1, res_page2]

    client = GitLabClient(base_url="https://gitlab.example.com", session=mock_session)
    items = client.get_repository_tree(project_id=42, ref="main", recursive=True)

    assert len(items) == 2
    assert items[0]["path"] == "file1.txt"
    assert items[1]["path"] == "file2.txt"
    assert mock_session.get.call_count == 2
    # Second call should follow the exact link URL
    assert mock_session.get.call_args_list[1][0][0] == (
        "https://gitlab.example.com/api/v4/projects/42/repository/tree?pagination=keyset&page_token=abc"
    )


def test_discover_project_readmes_deep_subfolder_probe():
    """Verify that when root tree only lists directory trees (e.g. web, svc), subfolders are inspected."""
    mock_session = MagicMock(spec=requests.Session)

    # Root tree call: returns root README.md and directory trees for 'web' and 'svc'
    res_root = MagicMock()
    res_root.status_code = 200
    res_root.links = {}
    res_root.headers = {}
    res_root.json.return_value = [
        {"type": "blob", "path": "README.md"},
        {"type": "tree", "path": "web"},
        {"type": "tree", "path": "svc"},
    ]

    # web tree call: returns web/README.md
    res_web = MagicMock()
    res_web.status_code = 200
    res_web.links = {}
    res_web.headers = {}
    res_web.json.return_value = [
        {"type": "blob", "path": "web/README.md"},
    ]

    # svc tree call: returns svc/README.md
    res_svc = MagicMock()
    res_svc.status_code = 200
    res_svc.links = {}
    res_svc.headers = {}
    res_svc.json.return_value = [
        {"type": "blob", "path": "svc/README.md"},
    ]

    mock_session.get.side_effect = [res_root, res_web, res_svc]

    client = GitLabClient(base_url="https://gitlab.example.com", session=mock_session)
    project = GitLabProject(
        id=99,
        name="data-chat",
        path_with_namespace="org/data-chat",
        default_branch="main",
    )

    readmes = client.discover_project_readmes(project)
    assert "README.md" in readmes
    assert "web/README.md" in readmes
    assert "svc/README.md" in readmes
    assert readmes[0] == "README.md"
