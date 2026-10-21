"""GitLab API client and project data structures."""

import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass

import requests
import urllib3


def compute_safe_filename(path_with_namespace: str, readme_filename: str = "README.md") -> str:
    """Compute a flat, collision-free filename from a GitLab project path."""
    clean_path = path_with_namespace.strip().strip("/")
    prefix = clean_path.replace("/", "_")
    return f"{prefix}_{readme_filename}"


@dataclass(frozen=True)
class GitLabProject:
    """Represents a GitLab project with metadata needed for README retrieval."""

    id: int
    name: str
    path_with_namespace: str
    default_branch: str | None
    readme_url: str | None = None
    web_url: str | None = None
    description: str | None = None
    archived: bool = False
    empty_repo: bool = False

    @property
    def has_default_branch(self) -> bool:
        """Return True if project has a default branch."""
        return bool(self.default_branch and self.default_branch.strip())

    def get_safe_filename(self, readme_filename: str = "README.md") -> str:
        """Return a filesystem-safe flat filename."""
        return compute_safe_filename(self.path_with_namespace, readme_filename)


class GitLabClient:
    """Client for interacting with the GitLab REST API v4."""

    DEFAULT_README_CANDIDATES = (
        "README.md",
        "readme.md",
        "README.markdown",
        "README.rst",
        "README.txt",
        "README",
    )

    def __init__(
        self,
        base_url: str = "https://gitlab.com",
        private_token: str = "",
        timeout: float = 20.0,
        verify_ssl: bool = True,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.private_token = private_token.strip()
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.session = session or requests.Session()

        if not self.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _get_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "application/json",
            "User-Agent": "py-readme-fetcher/0.1.0",
        }
        if self.private_token:
            if self.private_token.lower().startswith("bearer "):
                headers["Authorization"] = self.private_token
            else:
                headers["PRIVATE-TOKEN"] = self.private_token
        return headers

    @staticmethod
    def _raise_for_status_with_detail(response: requests.Response) -> None:
        """Raise HTTPError enriched with GitLab JSON or text response body."""
        if response.ok:
            return

        detail = ""
        try:
            body = response.json()
            if isinstance(body, dict):
                detail = body.get("message") or body.get("error") or ""
                if isinstance(detail, dict):
                    detail = ", ".join(f"{k}: {v}" for k, v in detail.items())
            elif isinstance(body, list):
                detail = ", ".join(str(x) for x in body)
        except (ValueError, TypeError, KeyError):
            detail = response.text[:300] if response.text else ""

        error_msg = f"{response.status_code} {response.reason}"
        if detail:
            error_msg += f" — {detail}"
        raise requests.HTTPError(error_msg, response=response)

    def get_group_projects(
        self,
        group_id: str | int,
        include_subgroups: bool = True,
        cancel_check: Callable[[], bool] | None = None,
        page_callback: Callable[[int, int], None] | None = None,
    ) -> list[GitLabProject]:
        """Fetch all non-archived projects belonging to a GitLab group and its subgroups."""
        encoded_group_id = urllib.parse.quote(str(group_id).strip(), safe="")
        projects_url = f"{self.base_url}/api/v4/groups/{encoded_group_id}/projects"

        headers = self._get_headers()
        params: dict[str, str | int] = {
            "include_subgroups": "true" if include_subgroups else "false",
            "archived": "false",
            "per_page": 100,
        }

        all_projects: list[GitLabProject] = []
        page = 1

        while True:
            if cancel_check and cancel_check():
                break

            response = self.session.get(
                projects_url,
                headers=headers,
                params={**params, "page": page},
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
            self._raise_for_status_with_detail(response)

            total_pages_header = response.headers.get("X-Total-Pages")
            total_pages = (
                int(total_pages_header)
                if total_pages_header and total_pages_header.isdigit()
                else 0
            )

            if page_callback:
                page_callback(page, total_pages)

            items = response.json()
            if not items:
                break

            for item in items:
                branch = item.get("default_branch")
                is_empty = item.get("empty_repo", False) or not bool(branch)

                project = GitLabProject(
                    id=item["id"],
                    name=item.get("name", ""),
                    path_with_namespace=item.get("path_with_namespace", str(item["id"])),
                    default_branch=branch,
                    readme_url=item.get("readme_url"),
                    web_url=item.get("web_url"),
                    description=item.get("description"),
                    archived=item.get("archived", False),
                    empty_repo=is_empty,
                )
                all_projects.append(project)

            # Check next page from header or increment
            next_page = response.headers.get("X-Next-Page")
            if next_page and next_page.strip():
                page = int(next_page)
            else:
                # If no X-Next-Page header or empty, check if items returned < per_page
                if len(items) < 100:
                    break
                page += 1

        return all_projects

    def _determine_readme_candidates(self, project: GitLabProject) -> list[str]:
        candidates: list[str] = []

        if project.readme_url:
            parsed = urllib.parse.urlparse(project.readme_url)
            filename = parsed.path.rstrip("/").split("/")[-1]
            if filename:
                candidates.append(filename)

        for candidate in self.DEFAULT_README_CANDIDATES:
            if candidate not in candidates:
                candidates.append(candidate)

        return candidates

    def fetch_readme(
        self,
        project: GitLabProject,
        cancel_check: Callable[[], bool] | None = None,
    ) -> tuple[str, bytes] | None:
        """Attempt to fetch README content using smart fallback candidates."""
        if not project.has_default_branch or project.empty_repo:
            return None

        branch = project.default_branch
        headers = self._get_headers()
        candidates = self._determine_readme_candidates(project)

        for filename in candidates:
            if cancel_check and cancel_check():
                return None

            encoded_file = urllib.parse.quote(filename, safe="")
            raw_url = (
                f"{self.base_url}/api/v4/projects/{project.id}/repository/files/{encoded_file}/raw"
            )

            try:
                response = self.session.get(
                    raw_url,
                    headers=headers,
                    params={"ref": branch},
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                )
                if response.status_code == 200:
                    return (filename, response.content)
                if response.status_code == 404:
                    continue
                self._raise_for_status_with_detail(response)
            except requests.RequestException:
                # In case of 404 or connection error for a candidate, continue or abort
                continue

        return None
