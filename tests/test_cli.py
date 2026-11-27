"""Offline tests for xsearch-cli; all HTTP responses are mocked."""

from __future__ import annotations

import io
import json
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from xsearch_cli import client
from xsearch_cli.cli import _render_tweets, main


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.body = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


class SearchTests(unittest.TestCase):
    def test_query_validation(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            client.validate_query("   ")
        with self.assertRaisesRegex(ValueError, "512 characters"):
            client.validate_query("x" * 513)
        client.validate_query("x" * 512)

    @patch("xsearch_cli.client.urlopen")
    def test_pagination_uses_cursor_and_deduplicates_ids(self, mocked_urlopen: object) -> None:
        mocked_urlopen.side_effect = [  # type: ignore[attr-defined]
            FakeResponse(
                {
                    "tweets": [{"id": "1", "text": "first"}],
                    "has_next_page": True,
                    "next_cursor": "cursor-1",
                }
            ),
            FakeResponse(
                {
                    "tweets": [{"id": "1", "text": "duplicate"}, {"id": "2", "text": "second"}],
                    "has_next_page": False,
                    "next_cursor": "",
                }
            ),
        ]

        result = client.search("open source", "test-key", max_pages=2)

        self.assertEqual([tweet["id"] for tweet in result.tweets], ["1", "2"])
        self.assertEqual(result.pages_fetched, 2)
        self.assertFalse(result.has_next_page)
        first_request = mocked_urlopen.call_args_list[0].args[0]  # type: ignore[attr-defined]
        second_request = mocked_urlopen.call_args_list[1].args[0]  # type: ignore[attr-defined]
        self.assertEqual(first_request.get_header("X-api-key"), "test-key")
        self.assertEqual(parse_qs(urlparse(first_request.full_url).query)["query"], ["open source"])
        self.assertEqual(parse_qs(urlparse(first_request.full_url).query)["queryType"], ["Latest"])
        self.assertEqual(parse_qs(urlparse(second_request.full_url).query)["cursor"], ["cursor-1"])

    @patch("xsearch_cli.client.urlopen")
    def test_repeated_cursor_stops_with_error(self, mocked_urlopen: object) -> None:
        mocked_urlopen.side_effect = [  # type: ignore[attr-defined]
            FakeResponse({"tweets": [], "has_next_page": True, "next_cursor": "same"}),
            FakeResponse({"tweets": [], "has_next_page": True, "next_cursor": "same"}),
        ]
        with self.assertRaisesRegex(client.APIError, "repeated a pagination cursor"):
            client.search("test", "test-key", max_pages=3)

    def test_rendering_sanitizes_control_characters(self) -> None:
        rendered = _render_tweets(
            [
                {
                    "id": "1",
                    "text": "hello\n\x1b[31mworld",
                    "author": {"userName": "example"},
                }
            ]
        )
        self.assertIn("hello  [31mworld", rendered)
        self.assertNotIn("\x1b", rendered)
        self.assertIn("@example", rendered)

    def test_cli_requires_environment_key_without_network(self) -> None:
        stderr = io.StringIO()
        with patch.dict(os.environ, {"TWITTERAPI_IO_API_KEY": ""}):
            with redirect_stderr(stderr):
                status = main(["test query"])
        self.assertEqual(status, 2)
        self.assertIn("TWITTERAPI_IO_API_KEY", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
