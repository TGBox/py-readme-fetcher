"""GitLab API client and project data structures."""

import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import requests
import urllib3


def compute_safe_project_dir(path_with_namespace: str) -> str:
    """Compute a safe directory name from a GitLab project path."""
    clean_path = path_with_namespace.strip().strip("/")
    return clean_path.replace("/", "_")


def compute_safe_filename(path_with_namespace: str, readme_filename: str = "README.md") -> str:
    """Compute a flat, collision-free filename from a GitLab project path."""
    prefix = compute_safe_project_dir(path_with_namespace)
    clean_filename = readme_filename.replace("/", "_").replace("\\", "_")
    return f"{prefix}_{clean_filename}"


def compute_relative_target_path(path_with_namespace: str, repo_file_path: str) -> Path:
    """Compute nested target path mirroring repo subfolders: {project_dir}/{repo_file_path}."""
    project_dir = compute_safe_project_dir(path_with_namespace)
    clean_repo_path = repo_file_path.strip().strip("/").replace("\\", "/")
    return Path(project_dir) / Path(clean_repo_path)


IGNORED_DIR_NAMES = frozenset(
    {
        "node_modules",
        "vendor",
        ".git",
        "venv",
        ".venv",
        "dist",
        "build",
        "target",
        "__pycache__",
        ".tox",
        ".eggs",
    }
)


def is_readme_file(path: str) -> bool:
    """Check if a repository file path is a valid README file and not in an ignored dir."""
    clean = path.replace("\\", "/").strip().strip("/")
    parts = clean.split("/")
    for dir_name in parts[:-1]:
        dir_lower = dir_name.lower()
        if dir_lower in IGNORED_DIR_NAMES or dir_lower.endswith(".egg-info"):
            return False
    filename = parts[-1].lower()
    return filename == "readme" or filename.startswith("readme.")


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
    readme_files: tuple[str, ...] = ()

    @property
    def has_default_branch(self) -> bool:
        """Return True if project has a default branch."""
        return bool(self.default_branch and self.default_branch.strip())

    def get_safe_filename(self, readme_filename: str = "README.md") -> str:
        """Return a filesystem-safe flat filename."""
        return compute_safe_filename(self.path_with_namespace, readme_filename)

    def get_relative_target_path(self, repo_file_path: str = "README.md") -> Path:
        """Return a filesystem path mirroring repository hierarchy."""
        return compute_relative_target_path(self.path_with_namespace, repo_file_path)


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

    def get_repository_tree(
        self,
        project_id: int | str,
        ref: str,
        path: str = "",
        recursive: bool = True,
        cancel_check: Callable[[], bool] | None = None,
    ) -> list[dict]:
        """Fetch repository tree items via GitLab API v4 supporting Link header and keyset pagination."""
        encoded_id = urllib.parse.quote(str(project_id).strip(), safe="")
        next_url: str | None = f"{self.base_url}/api/v4/projects/{encoded_id}/repository/tree"
        headers = self._get_headers()
        params: dict[str, str | int] = {
            "ref": ref,
            "recursive": "true" if recursive else "false",
            "per_page": 100,
        }
        if path:
            params["path"] = path

        all_items: list[dict] = []
        page = 1
        max_pages = 100

        while next_url and page <= max_pages:
            if cancel_check and cancel_check():
                break

            try:
                # Use params on the initial request; subsequent requests follow next_url from Link header
                req_params = params if page == 1 else None
                response = self.session.get(
                    next_url,
                    headers=headers,
                    params=req_params,
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                )
                if response.status_code == 404:
                    break
                self._raise_for_status_with_detail(response)
            except requests.RequestException:
                break

            items = response.json()
            if not items or not isinstance(items, list):
                break

            all_items.extend(items)
            page += 1

            # Check next page via RFC 5988 Link header (works for keyset and offset pagination)
            link_next = response.links.get("next", {}).get("url")
            if link_next:
                next_url = link_next
            else:
                next_page_hdr = response.headers.get("X-Next-Page")
                if next_page_hdr and next_page_hdr.strip():
                    next_url = f"{self.base_url}/api/v4/projects/{encoded_id}/repository/tree"
                    params["page"] = int(next_page_hdr)
                else:
                    break

        return all_items

    def discover_project_readmes(
        self,
        project: GitLabProject,
        cancel_check: Callable[[], bool] | None = None,
    ) -> list[str]:
        """Find all README files in project repository, prioritizing root README and checking subdirectories."""
        if not project.has_default_branch or project.empty_repo:
            return []

        branch = project.default_branch or "main"
        items = self.get_repository_tree(
            project_id=project.id,
            ref=branch,
            recursive=True,
            cancel_check=cancel_check,
        )

        found: list[str] = []
        subdirectories: list[str] = []

        for item in items:
            item_type = item.get("type")
            file_path = item.get("path", "")
            if not file_path:
                continue

            if item_type == "blob":
                if is_readme_file(file_path) and file_path not in found:
                    found.append(file_path)
            elif item_type == "tree":
                parts = file_path.replace("\\", "/").strip("/").split("/")
                if not any(
                    p.lower() in IGNORED_DIR_NAMES or p.lower().endswith(".egg-info") for p in parts
                ):
                    subdirectories.append(file_path)

        # Fallback inspection:
        # If any discovered subdirectory does not yet have a found README,
        # inspect it directly in case recursive=true was truncated by GitLab
        for dir_path in subdirectories:
            if cancel_check and cancel_check():
                break
            clean_dir = dir_path.replace("\\", "/").strip("/")
            has_readme_in_dir = any(f.startswith(f"{clean_dir}/") for f in found)
            if not has_readme_in_dir:
                # Query sub-tree for this specific path
                sub_items = self.get_repository_tree(
                    project_id=project.id,
                    ref=branch,
                    path=clean_dir,
                    recursive=True,
                    cancel_check=cancel_check,
                )
                found_in_subtree = False
                for sub_item in sub_items:
                    if sub_item.get("type") == "blob":
                        sub_file = sub_item.get("path", "")
                        if sub_file and is_readme_file(sub_file) and sub_file not in found:
                            found.append(sub_file)
                            found_in_subtree = True

                if not found_in_subtree:
                    # Direct probe for standard README candidates in directory
                    for cand in self.DEFAULT_README_CANDIDATES:
                        probe_path = f"{clean_dir}/{cand}"
                        content = self.fetch_file_content(
                            project, probe_path, cancel_check=cancel_check
                        )
                        if content is not None:
                            if probe_path not in found:
                                found.append(probe_path)
                            break

        # Also probe standard root README if none was found at the root
        if not any("/" not in f and "\\" not in f for f in found):
            root_readme = self.fetch_readme(project, cancel_check=cancel_check)
            if root_readme is not None:
                root_name = root_readme[0]
                if root_name not in found:
                    found.insert(0, root_name)

        def sort_key(p: str) -> tuple[int, int, str]:
            parts = p.replace("\\", "/").strip("/").split("/")
            depth = len(parts) - 1
            filename = parts[-1].lower()
            name_prio = 0 if filename == "readme.md" else 1
            return (depth, name_prio, p.lower())

        found.sort(key=sort_key)
        return found

    def fetch_file_content(
        self,
        project: GitLabProject,
        file_path: str,
        cancel_check: Callable[[], bool] | None = None,
    ) -> bytes | None:
        """Fetch raw content of a specific file in the project."""
        if not project.has_default_branch or project.empty_repo or not file_path:
            return None

        if cancel_check and cancel_check():
            return None

        branch = project.default_branch
        headers = self._get_headers()
        encoded_file = urllib.parse.quote(file_path.strip().strip("/"), safe="")
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
                return response.content
            if response.status_code == 404:
                return None
            self._raise_for_status_with_detail(response)
        except requests.RequestException:
            return None

        return None

    def _determine_readme_candidates(self, project: GitLabProject) -> list[str]:
        candidates: list[str] = []

        if project.readme_files:
            for rf in project.readme_files:
                if rf and rf not in candidates:
                    candidates.append(rf)

        if project.readme_url:
            parsed = urllib.parse.urlparse(project.readme_url)
            filename = parsed.path.rstrip("/").split("/")[-1]
            if filename and filename not in candidates:
                candidates.append(filename)

            blob_marker = "/-/blob/"
            if blob_marker in parsed.path:
                after_blob = parsed.path.split(blob_marker, 1)[1]
                parts = after_blob.split("/", 1)
                if len(parts) == 2 and parts[1]:
                    subpath = parts[1]
                    if subpath not in candidates:
                        candidates.append(subpath)

        for candidate in self.DEFAULT_README_CANDIDATES:
            if candidate not in candidates:
                candidates.append(candidate)

        return candidates

    def fetch_readme(
        self,
        project: GitLabProject,
        file_path: str | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> tuple[str, bytes] | None:
        """Attempt to fetch README content using smart fallback candidates or explicit path."""
        if not project.has_default_branch or project.empty_repo:
            return None

        if file_path:
            content = self.fetch_file_content(project, file_path, cancel_check=cancel_check)
            if content is not None:
                return (file_path, content)
            return None

        candidates = self._determine_readme_candidates(project)
        for candidate in candidates:
            if cancel_check and cancel_check():
                return None

            content = self.fetch_file_content(project, candidate, cancel_check=cancel_check)
            if content is not None:
                return (candidate, content)

        return None
