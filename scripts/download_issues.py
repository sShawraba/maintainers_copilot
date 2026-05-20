#!/usr/bin/env python3
"""
GitHub Issue Downloader for pandas-dev/pandas

Downloads all closed issues from the pandas repository using the GitHub API.
Saves issue data to JSONL format for streaming processing.

Requirements:
    - requests library
    - GITHUB_TOKEN environment variable set

Usage:
    python download_issues.py
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import parse_qs, urlparse

import requests


class GitHubIssueDownloader:
    """Downloads closed issues from a GitHub repository."""

    def __init__(self, token: str, owner: str = "pandas-dev", repo: str = "pandas"):
        """
        Initialize the downloader.

        Args:
            token: GitHub Personal Access Token
            owner: GitHub repository owner
            repo: GitHub repository name
        """
        self.token = token
        self.owner = owner
        self.repo = repo
        self.base_url = f"https://api.github.com/repos/{owner}/{repo}"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "pandas-issue-downloader",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # Rate limit tracking
        self.rate_limit_remaining = None
        self.rate_limit_reset = None
        self.issues_count = 0

    def _update_rate_limit(self, response: requests.Response) -> None:
        """Update rate limit info from response headers."""
        self.rate_limit_remaining = int(
            response.headers.get("X-RateLimit-Remaining", -1)
        )
        self.rate_limit_reset = int(response.headers.get("X-RateLimit-Reset", 0))

    def _handle_rate_limit(self) -> None:
        """Sleep if rate limit is low."""
        if self.rate_limit_remaining is not None and self.rate_limit_remaining < 10:
            if self.rate_limit_reset:
                sleep_time = self.rate_limit_reset - int(time.time())
                if sleep_time > 0:
                    print(
                        f"[RATE LIMIT] Remaining: {self.rate_limit_remaining}. "
                        f"Sleeping {sleep_time}s until reset..."
                    )
                    time.sleep(sleep_time + 1)  # +1s buffer
            else:
                print("[RATE LIMIT] Remaining: 0. Sleeping 60s...")
                time.sleep(60)

    def _make_request(self, url: str, retry_count: int = 0, max_retries: int = 3) -> Optional[requests.Response]:
        """
        Make HTTP request with exponential backoff retry logic.

        Args:
            url: URL to request
            retry_count: Current retry attempt
            max_retries: Maximum number of retries

        Returns:
            Response object or None if all retries failed
        """
        try:
            response = self.session.get(url, timeout=10)
            self._update_rate_limit(response)

            if response.status_code == 200:
                return response
            elif response.status_code == 403:
                # Could be rate limited
                self._handle_rate_limit()
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count  # Exponential backoff: 1, 2, 4s
                    print(
                        f"[RETRY] Status 403 (retry {retry_count + 1}/{max_retries}). "
                        f"Waiting {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    return self._make_request(url, retry_count + 1, max_retries)
                else:
                    print(f"[ERROR] Failed after {max_retries} retries on {url}")
                    return None
            else:
                print(f"[ERROR] HTTP {response.status_code}: {response.reason}")
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    print(f"[RETRY] Retry {retry_count + 1}/{max_retries}. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    return self._make_request(url, retry_count + 1, max_retries)
                return None

        except requests.RequestException as e:
            print(f"[ERROR] Request failed: {e}")
            if retry_count < max_retries:
                wait_time = 2 ** retry_count
                print(f"[RETRY] Retry {retry_count + 1}/{max_retries}. Waiting {wait_time}s...")
                time.sleep(wait_time)
                return self._make_request(url, retry_count + 1, max_retries)
            return None

    def _parse_link_header(self, link_header: Optional[str]) -> Dict[str, str]:
        """
        Parse GitHub's Link header for pagination.

        Example:
            <https://api.github.com/...?page=2>; rel="next",
            <https://api.github.com/...?page=34>; rel="last"

        Args:
            link_header: Link header value from response

        Returns:
            Dict mapping rel types to URLs
        """
        links = {}
        if not link_header:
            return links

        for link in link_header.split(","):
            parts = link.split(";")
            if len(parts) == 2:
                url = parts[0].strip()[1:-1]  # Remove < >
                rel = parts[1].strip().split("=")[1].strip('"')
                links[rel] = url

        return links

    def _extract_fields(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant fields from GitHub issue API response.

        Args:
            issue: Raw issue data from GitHub API

        Returns:
            Filtered dict with relevant fields
        """
        labels = issue.get("labels", [])
        return {
            "number": issue["number"],
            "title": issue["title"],
            "body": issue.get("body"),
            "state": issue["state"],
            "created_at": issue["created_at"],
            "closed_at": issue["closed_at"],
            "labels": [{"name": label["name"]} for label in labels],
            "user": {"login": issue["user"]["login"]},
            "comments_url": issue["comments_url"],
            "html_url": issue["html_url"],
        }

    def download(self, output_path: str = "data/pandas_closed_issues.jsonl") -> bool:
        """
        Download all closed issues and save to JSONL file.

        Args:
            output_path: Path to output JSONL file

        Returns:
            True if successful, False otherwise
        """
        # Create data directory if needed
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        print(f"[START] Downloading closed issues from {self.owner}/{self.repo}")
        print(f"[OUTPUT] Writing to {output_path}")

        url = f"{self.base_url}/issues?state=closed&sort=created&direction=asc&per_page=100"
        closed_dates = []

        try:
            with open(output_path, "w") as f:
                while url:
                    print(f"[FETCH] {url}")
                    response = self._make_request(url)

                    if response is None:
                        print("[ERROR] Failed to fetch issues. Aborting.")
                        return False

                    try:
                        issues = response.json()
                    except json.JSONDecodeError:
                        print("[ERROR] Invalid JSON response. Aborting.")
                        return False

                    # Filter out pull requests and process issues
                    for issue in issues:
                        if "pull_request" in issue:
                            # Skip pull requests
                            continue

                        extracted = self._extract_fields(issue)
                        f.write(json.dumps(extracted) + "\n")
                        self.issues_count += 1

                        # Collect closed dates for verification
                        if extracted["closed_at"]:
                            closed_dates.append(extracted["closed_at"])

                        # Progress logging
                        if self.issues_count % 500 == 0:
                            print(
                                f"[PROGRESS] Downloaded {self.issues_count} issues | "
                                f"Rate limit remaining: {self.rate_limit_remaining}"
                            )

                        if self.issues_count % 1000 == 0:
                            print(
                                f"[RATE LIMIT] Current: {self.rate_limit_remaining} | "
                                f"Reset at: {datetime.fromtimestamp(self.rate_limit_reset)}"
                            )

                    # Rate limit check before next request
                    self._handle_rate_limit()

                    # Check for next page
                    links = self._parse_link_header(response.headers.get("Link"))
                    url = links.get("next")

                    if url:
                        time.sleep(0.1)  # Respect rate limits - 0.1s between requests

        except IOError as e:
            print(f"[ERROR] Failed to write to file: {e}")
            return False

        # Verify and print completion stats
        if closed_dates:
            closed_dates.sort()
            earliest = closed_dates[0]
            latest = closed_dates[-1]
            print(
                f"[COMPLETE] Downloaded {self.issues_count} closed issues\n"
                f"  Earliest closed: {earliest}\n"
                f"  Latest closed: {latest}"
            )
        else:
            print(f"[COMPLETE] Downloaded {self.issues_count} issues (no closed dates found)")

        return True


def main() -> int:
    """Main entry point."""
    # Check for GitHub token
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print(
            "[ERROR] GITHUB_TOKEN environment variable not set.\n"
            "Please set it with: export GITHUB_TOKEN='your_token_here'\n"
            "Get a token at: https://github.com/settings/tokens",
            file=sys.stderr,
        )
        return 1

    # Download issues
    downloader = GitHubIssueDownloader(token)
    success = downloader.download()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
