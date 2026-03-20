from pathlib import Path
import sys
import unittest
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from oil_tracker.github_stats import fetch_github_commit_stats


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


if __name__ == "__main__":
    unittest.main()
