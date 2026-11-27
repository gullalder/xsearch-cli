"""Minimal client for TwitterAPI.io's Advanced Search endpoint."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_ENDPOINT = "https://api.twitterapi.io/twitter/tweet/advanced_search"
MAX_QUERY_LENGTH = 512
MAX_PAGES = 20


class APIError(RuntimeError):
    """Raised when a request or API response cannot be used."""


@dataclass(frozen=True)
class SearchResult:
    tweets: list[dict[str, Any]]
    has_next_page: bool
    next_cursor: str | None
    pages_fetched: int


def validate_query(query: str) -> None:
    """Reject empty or overlong queries before making a network request."""
    if not query.strip():
        raise ValueError("The search query must not be empty.")
    if len(query) > MAX_QUERY_LENGTH:
        raise ValueError(
            f"The API query limit is {MAX_QUERY_LENGTH} characters; "
            f"this query has {len(query)}."
        )


def search(query: str, api_key: str, max_pages: int = 1, timeout: int = 30) -> SearchResult:
    """Search recent public posts and optionally follow cursor pagination."""
    validate_query(query)
    if not api_key.strip():
        raise ValueError("An API key is required.")
    if not 1 <= max_pages <= MAX_PAGES:
        raise ValueError(f"Page count must be between 1 and {MAX_PAGES}.")
    if timeout <= 0:
        raise ValueError("Timeout must be greater than zero.")

    tweets: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_cursors: set[str] = set()
    cursor: str | None = None
    has_next_page = False
    next_cursor: str | None = None
    pages_fetched = 0

    for _ in range(max_pages):
        params = {"query": query, "queryType": "Latest"}
        if cursor:
            params["cursor"] = cursor
        request = Request(
            f"{API_ENDPOINT}?{urlencode(params)}",
            headers={"X-API-Key": api_key.strip()},
            method="GET",
        )

        try:
            with urlopen(request, timeout=timeout) as response:
                raw_body = response.read()
        except HTTPError as exc:
            raise APIError(f"The API returned HTTP {exc.code}.") from None
        except URLError as exc:
            raise APIError(f"Could not reach the API: {exc.reason}") from None
        except TimeoutError:
            raise APIError(f"The API request timed out after {timeout} seconds.") from None

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise APIError("The API response was not valid UTF-8 JSON.") from None

        if not isinstance(payload, dict):
            raise APIError("The API response was not a JSON object.")
        if "tweets" not in payload and ("error" in payload or "message" in payload):
            detail = payload.get("message") or payload.get("error")
            raise APIError(f"The API reported an error: {detail}")

        page_tweets = payload.get("tweets", [])
        if not isinstance(page_tweets, list):
            raise APIError("The API response's 'tweets' field was not a list.")
        for tweet in page_tweets:
            if not isinstance(tweet, dict):
                continue
            tweet_id = tweet.get("id")
            if tweet_id is None:
                tweets.append(tweet)
                continue
            normalized_id = str(tweet_id)
            if normalized_id not in seen_ids:
                seen_ids.add(normalized_id)
                tweets.append(tweet)

        pages_fetched += 1
        has_next_page = bool(payload.get("has_next_page"))
        raw_cursor = payload.get("next_cursor")
        next_cursor = str(raw_cursor) if raw_cursor else None

        if not has_next_page or not next_cursor:
            break
        if next_cursor in seen_cursors:
            raise APIError("The API repeated a pagination cursor; stopping to avoid a loop.")
        seen_cursors.add(next_cursor)
        cursor = next_cursor

    return SearchResult(
        tweets=tweets,
        has_next_page=has_next_page,
        next_cursor=next_cursor,
        pages_fetched=pages_fetched,
    )
