import os
from pathlib import Path
import shutil
import sys
import unittest
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from oil_tracker.github_stats import (
    _github_headers,
    GitHubCommitStats,
    GitHubRepoCommitStat,
    fetch_github_commit_stats,
    load_cached_github_commit_stats,
    save_cached_github_commit_stats,
)
from oil_tracker.settings import AppSettings, load_settings, save_settings


class GitHubCommitStatsTests(unittest.TestCase):
    def test_fetch_github_commit_stats_sums_and_sorts_top_repositories(self) -> None:
        repo_payload_page_1 = [
            {"name": "repo-a", "html_url": "https://github.com/goldshoot0720/repo-a"},
            {"name": "repo-b", "html_url": "https://github.com/goldshoot0720/repo-b"},
        ]
        repo_payload_page_2 = [
            {"name": "repo-c", "html_url": "https://github.com/goldshoot0720/repo-c"},
        ]
        contributor_payloads = {
            "repo-a": [{"contributions": 8}, {"contributions": 4}],
            "repo-b": [{"contributions": 20}],
            "repo-c": [{"contributions": 3}, {"contributions": 2}, {"contributions": 1}],
        }

        def fake_fetch_json(url: str, _timeout: int) -> list[dict]:
            parsed = urlparse(url)
            query = parse_qs(parsed.query)

            if parsed.path == "/users/goldshoot0720/repos" and query.get("page") == ["1"]:
                return repo_payload_page_1
            if parsed.path == "/users/goldshoot0720/repos" and query.get("page") == ["2"]:
                return repo_payload_page_2
            if "contributors" in url:
                repo_name = url.split("/repos/goldshoot0720/", 1)[1].split("/contributors", 1)[0]
                return contributor_payloads[repo_name]
            return []

        stats = fetch_github_commit_stats("goldshoot0720", fetch_json=fake_fetch_json)

        self.assertEqual(stats.total_repositories, 3)
        self.assertEqual(stats.total_commits, 38)
        self.assertEqual(stats.top_commit_total, 38)
        self.assertEqual(
            [repo.name for repo in stats.top_repositories],
            ["repo-b", "repo-a", "repo-c"],
        )
        self.assertEqual(
            [repo.commit_count for repo in stats.top_repositories],
            [20, 12, 6],
        )

    def test_fetch_github_commit_stats_can_limit_repository_count(self) -> None:
        repositories = [
            {"name": "repo-a", "html_url": "https://github.com/goldshoot0720/repo-a"},
            {"name": "repo-b", "html_url": "https://github.com/goldshoot0720/repo-b"},
        ]
        contributor_payloads = {
            "repo-a": [{"contributions": 8}],
        }

        def fake_fetch_json(url: str, _timeout: int) -> list[dict]:
            parsed = urlparse(url)
            query = parse_qs(parsed.query)

            if parsed.path == "/users/goldshoot0720/repos" and query.get("page") == ["1"]:
                return repositories
            if parsed.path == "/users/goldshoot0720/repos" and query.get("page") == ["2"]:
                return []
            if "contributors" in url:
                repo_name = url.split("/repos/goldshoot0720/", 1)[1].split("/contributors", 1)[0]
                return contributor_payloads[repo_name]
            return []

        stats = fetch_github_commit_stats("goldshoot0720", max_repositories=1, fetch_json=fake_fetch_json)

        self.assertEqual(stats.total_repositories, 1)
        self.assertEqual(stats.total_commits, 8)
        self.assertEqual([repo.name for repo in stats.top_repositories], ["repo-a"])

    def test_fetch_github_commit_stats_reports_progress(self) -> None:
        repositories = [
            {"name": "repo-a", "html_url": "https://github.com/goldshoot0720/repo-a"},
            {"name": "repo-b", "html_url": "https://github.com/goldshoot0720/repo-b"},
        ]
        contributor_payloads = {
            "repo-a": [{"contributions": 8}],
            "repo-b": [{"contributions": 5}],
        }
        progress_events: list[tuple[str, int, int, str | None, int | None]] = []

        def fake_fetch_json(url: str, _timeout: int) -> list[dict]:
            parsed = urlparse(url)
            query = parse_qs(parsed.query)

            if parsed.path == "/users/goldshoot0720/repos" and query.get("page") == ["1"]:
                return repositories
            if parsed.path == "/users/goldshoot0720/repos" and query.get("page") == ["2"]:
                return []
            if "contributors" in url:
                repo_name = url.split("/repos/goldshoot0720/", 1)[1].split("/contributors", 1)[0]
                return contributor_payloads[repo_name]
            return []

        fetch_github_commit_stats(
            "goldshoot0720",
            fetch_json=fake_fetch_json,
            progress_callback=lambda stage, current, total, repo_name, commit_count: progress_events.append(
                (stage, current, total, repo_name, commit_count)
            ),
        )

        self.assertEqual(
            progress_events,
            [
                ("repositories_loaded", 0, 2, None, None),
                ("repo_commits_loading", 1, 2, "repo-a", None),
                ("repo_commits_loaded", 1, 2, "repo-a", 8),
                ("repo_commits_loading", 2, 2, "repo-b", None),
                ("repo_commits_loaded", 2, 2, "repo-b", 5),
            ],
        )

    def test_github_headers_include_authorization_when_token_is_present(self) -> None:
        original_token = os.environ.get("GITHUB_TOKEN")
        try:
            os.environ["GITHUB_TOKEN"] = "test-token"
            headers = _github_headers()
        finally:
            if original_token is None:
                os.environ.pop("GITHUB_TOKEN", None)
            else:
                os.environ["GITHUB_TOKEN"] = original_token

        self.assertEqual(headers["Authorization"], "Bearer test-token")
        self.assertEqual(headers["Accept"], "application/vnd.github+json")

    def test_settings_can_store_and_load_github_token(self) -> None:
        test_dir = Path("tests_tmp") / self._testMethodName
        if test_dir.exists():
            shutil.rmtree(test_dir)
        settings_path = test_dir / "settings.json"

        save_settings(AppSettings(github_token="saved-token"), settings_path)
        settings = load_settings(settings_path)

        self.assertEqual(settings.github_token, "saved-token")

    def test_github_headers_fall_back_to_saved_settings(self) -> None:
        test_dir = Path("tests_tmp") / self._testMethodName
        if test_dir.exists():
            shutil.rmtree(test_dir)
        settings_path = test_dir / "settings.json"
        save_settings(AppSettings(github_token="saved-token"), settings_path)

        original_token = os.environ.get("GITHUB_TOKEN")
        original_loader = _github_headers.__globals__["load_settings"]
        try:
            os.environ.pop("GITHUB_TOKEN", None)
            _github_headers.__globals__["load_settings"] = lambda: load_settings(settings_path)
            headers = _github_headers()
        finally:
            _github_headers.__globals__["load_settings"] = original_loader
            if original_token is None:
                os.environ.pop("GITHUB_TOKEN", None)
            else:
                os.environ["GITHUB_TOKEN"] = original_token

        self.assertEqual(headers["Authorization"], "Bearer saved-token")

    def test_commit_stats_cache_can_save_and_load(self) -> None:
        test_dir = Path("tests_tmp") / self._testMethodName
        if test_dir.exists():
            shutil.rmtree(test_dir)
        cache_path = test_dir / "commit_stats_cache.json"

        stats = GitHubCommitStats(
            username="goldshoot0720",
            profile_url="https://github.com/goldshoot0720?tab=repositories",
            total_commits=2093,
            total_repositories=162,
            top_repositories=[
                GitHubRepoCommitStat(
                    name="repo-a",
                    html_url="https://github.com/goldshoot0720/repo-a",
                    commit_count=100,
                )
            ],
        )

        saved = save_cached_github_commit_stats(stats, cache_path)
        loaded = load_cached_github_commit_stats(cache_path)

        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded.stats.total_commits, 2093)
        self.assertEqual(loaded.stats.total_repositories, 162)
        self.assertEqual(loaded.stats.top_repositories[0].name, "repo-a")
        self.assertEqual(loaded.fetched_at, saved.fetched_at)


if __name__ == "__main__":
    unittest.main()
