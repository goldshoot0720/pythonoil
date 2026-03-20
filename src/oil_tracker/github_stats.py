from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from .paths import default_commit_stats_cache_path
    from .settings import load_settings
except ImportError:
    from paths import default_commit_stats_cache_path
    from settings import load_settings

GITHUB_API_BASE = "https://api.github.com"
GITHUB_PROFILE_BASE = "https://github.com"
USER_AGENT = "Mozilla/5.0 (compatible; oil-tracker/0.1; +https://github.com/)"
JsonFetcher = Callable[[str, int], list[dict]]
ProgressCallback = Callable[[str, int, int, str | None, int | None], None]


@dataclass(slots=True)
class GitHubRepoCommitStat:
    name: str
    html_url: str
    commit_count: int


@dataclass(slots=True)
class GitHubCommitStats:
    username: str
    profile_url: str
    total_commits: int
    total_repositories: int
    top_repositories: list[GitHubRepoCommitStat]

    @property
    def top_commit_total(self) -> int:
        return sum(repo.commit_count for repo in self.top_repositories)


@dataclass(slots=True)
class CachedGitHubCommitStats:
    stats: GitHubCommitStats
    fetched_at: str


def fetch_github_commit_stats(
    username: str,
    timeout: int = 20,
    max_repositories: int | None = None,
    fetch_json: JsonFetcher | None = None,
    progress_callback: ProgressCallback | None = None,
) -> GitHubCommitStats:
    json_fetcher = fetch_json or _fetch_json
    repositories = _list_user_repositories(username, timeout, json_fetcher)
    if max_repositories is not None:
        repositories = repositories[:max_repositories]
    if progress_callback is not None:
        progress_callback("repositories_loaded", 0, len(repositories), None, None)

    repo_stats: list[GitHubRepoCommitStat] = []
    for index, repo in enumerate(repositories, start=1):
        if progress_callback is not None:
            progress_callback("repo_commits_loading", index, len(repositories), str(repo["name"]), None)
        commit_count = _fetch_repo_commit_count(username, repo["name"], timeout, json_fetcher)
        repo_stats.append(
            GitHubRepoCommitStat(
                name=repo["name"],
                html_url=repo["html_url"],
                commit_count=commit_count,
            )
        )
        if progress_callback is not None:
            progress_callback("repo_commits_loaded", index, len(repositories), str(repo["name"]), commit_count)

    sorted_repositories = sorted(repo_stats, key=lambda repo: (-repo.commit_count, repo.name.lower()))
    return GitHubCommitStats(
        username=username,
        profile_url=f"{GITHUB_PROFILE_BASE}/{username}?tab=repositories",
        total_commits=sum(repo.commit_count for repo in repo_stats),
        total_repositories=len(repo_stats),
        top_repositories=sorted_repositories[:10],
    )


def _list_user_repositories(
    username: str,
    timeout: int,
    fetch_json: JsonFetcher,
) -> list[dict]:
    repositories: list[dict] = []
    page = 1
    while True:
        url = (
            f"{GITHUB_API_BASE}/users/{username}/repos"
            f"?type=owner&sort=updated&per_page=100&page={page}"
        )
        page_items = fetch_json(url, timeout)
        if not page_items:
            break
        repositories.extend(page_items)
        page += 1
    return repositories


def _fetch_repo_commit_count(
    owner: str,
    repo_name: str,
    timeout: int,
    fetch_json: JsonFetcher,
) -> int:
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo_name}/contributors?per_page=100&anon=1"
    contributors = fetch_json(url, timeout)
    return sum(int(contributor.get("contributions", 0)) for contributor in contributors)


def _fetch_json(url: str, timeout: int) -> list[dict]:
    request = Request(
        url,
        headers=_github_headers(),
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"GitHub API request failed ({exc.code}): {detail or exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(f"GitHub API is unavailable: {exc.reason}") from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError("GitHub API returned invalid JSON.") from exc

    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected GitHub API response: {data}")
    return data


def _github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("PYTHONOIL_GITHUB_TOKEN")
    if not token:
        token = load_settings().github_token
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def load_cached_github_commit_stats(path: Path | None = None) -> CachedGitHubCommitStats | None:
    cache_path = path or default_commit_stats_cache_path()
    if not cache_path.exists():
        return None

    data = json.loads(cache_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None
    stats_data = data.get("stats")
    if not isinstance(stats_data, dict):
        return None
    top_repositories_data = stats_data.get("top_repositories", [])
    if not isinstance(top_repositories_data, list):
        top_repositories_data = []

    stats = GitHubCommitStats(
        username=str(stats_data.get("username", "")),
        profile_url=str(stats_data.get("profile_url", "")),
        total_commits=int(stats_data.get("total_commits", 0)),
        total_repositories=int(stats_data.get("total_repositories", 0)),
        top_repositories=[
            GitHubRepoCommitStat(
                name=str(repo.get("name", "")),
                html_url=str(repo.get("html_url", "")),
                commit_count=int(repo.get("commit_count", 0)),
            )
            for repo in top_repositories_data
            if isinstance(repo, dict)
        ],
    )
    return CachedGitHubCommitStats(stats=stats, fetched_at=str(data.get("fetched_at", "")))


def save_cached_github_commit_stats(stats: GitHubCommitStats, path: Path | None = None) -> CachedGitHubCommitStats:
    cache_path = path or default_commit_stats_cache_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cached = CachedGitHubCommitStats(
        stats=stats,
        fetched_at=datetime.now(UTC).astimezone().strftime("%Y-%m-%d %H:%M:%S"),
    )
    cache_path.write_text(
        json.dumps(
            {
                "fetched_at": cached.fetched_at,
                "stats": {
                    "username": stats.username,
                    "profile_url": stats.profile_url,
                    "total_commits": stats.total_commits,
                    "total_repositories": stats.total_repositories,
                    "top_repositories": [
                        {
                            "name": repo.name,
                            "html_url": repo.html_url,
                            "commit_count": repo.commit_count,
                        }
                        for repo in stats.top_repositories
                    ],
                },
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    return cached
