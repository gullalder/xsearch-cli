"""Command-line interface for xsearch-cli."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from .client import APIError, MAX_PAGES, search


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xsearch",
        description="Search recent public X posts through TwitterAPI.io.",
        epilog=(
            "The API key is read from TWITTERAPI_IO_API_KEY. "
            "Queries may be up to 512 characters."
        ),
    )
    parser.add_argument("query", help="search text or Twitter advanced-search expression")
    parser.add_argument(
        "--pages",
        type=int,
        default=1,
        metavar="N",
        help=f"maximum pages to fetch (1-{MAX_PAGES}; default: 1)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the result as JSON instead of a readable summary",
    )
    return parser


def _display_text(value: Any) -> str:
    """Keep API text from injecting terminal control sequences or extra lines."""
    text = str(value or "").replace("\r", " ").replace("\n", " ").replace("\t", " ")
    return "".join(char if ord(char) >= 32 and ord(char) != 127 else " " for char in text)


def _render_tweets(tweets: list[dict[str, Any]]) -> str:
    if not tweets:
        return "No posts found."

    blocks: list[str] = []
    for index, tweet in enumerate(tweets, start=1):
        author = tweet.get("author") or {}
        if not isinstance(author, dict):
            author = {}
        username = author.get("userName") or author.get("name") or "unknown"
        created_at = tweet.get("createdAt") or "date unknown"
        text = _display_text(tweet.get("text"))
        metrics = (
            f"likes {tweet.get('likeCount', 0)} | "
            f"reposts {tweet.get('retweetCount', 0)} | "
            f"replies {tweet.get('replyCount', 0)}"
        )
        url = tweet.get("url")
        lines = [f"{index}. @{_display_text(username)} · {_display_text(created_at)}", f"   {text}", f"   {metrics}"]
        if url:
            lines.append(f"   {_display_text(url)}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    if not 1 <= args.pages <= MAX_PAGES:
        parser.error(f"--pages must be between 1 and {MAX_PAGES}")

    api_key = os.environ.get("TWITTERAPI_IO_API_KEY", "").strip()
    if not api_key:
        print(
            "Error: set the TWITTERAPI_IO_API_KEY environment variable before searching.",
            file=sys.stderr,
        )
        return 2

    try:
        result = search(args.query, api_key, max_pages=args.pages)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except APIError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        document = {
            "tweets": result.tweets,
            "has_next_page": result.has_next_page,
            "next_cursor": result.next_cursor,
            "pages_fetched": result.pages_fetched,
        }
        json.dump(document, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print(_render_tweets(result.tweets))
        if result.has_next_page:
            print(
                f"\nMore results are available. Fetched {result.pages_fetched} page(s); "
                "increase --pages to fetch more."
            )
    return 0
