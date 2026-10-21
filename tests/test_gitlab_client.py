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
