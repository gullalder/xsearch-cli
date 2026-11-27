# xsearch-cli

A small, dependency-free Python command-line tool for searching recent public X posts through TwitterAPI.io's official Advanced Search endpoint. It uses the provider's `Latest` search mode and can follow the API's cursor pagination.

This is an independent example project, not an official TwitterAPI.io client. It has not been tested against the live service in this workspace; the included tests use mocked HTTP responses and do not need an API key.

## Reward disclosure

This repository is being prepared for TwitterAPI.io's Community Rewards program. The offer details associated with this submission state that an approved GitHub submission may earn **$30 in API credits**. The reward is conditional on approval; no approval, stars, live usage, or credits are claimed here. TwitterAPI.io's published rules list GitHub as Tier C and require a public repository that uses the API and has at least 20 stars. Approved GitHub submissions have a seven-day review hold, and unlocked credits expire after 30 days. Please star the project only if you independently find it useful; no purchased or manipulated stars are sought.

Share code for this submission: **`wt7q0ror`**

See the [official Community Rewards rules](https://twitterapi.io/community-rewards) for current terms. The offer amount above is the amount presented to the author and may be subject to the program's review and current rules.

## What it does

- Searches public X posts with a query in TwitterAPI.io's advanced-search syntax.
- Sends the API key only in the `X-API-Key` request header, read from `TWITTERAPI_IO_API_KEY`.
- Defaults to one page. Use `--pages` to request more pages; the tool follows `next_cursor` and stops when the API reports there are no more results.
- Prints readable results by default, or JSON with `--json`.
- Uses only the Python standard library at runtime.

The API can return up to 20 posts per page, and may return fewer. Each requested page is a separate API request. Review your provider account's terms and usage before making requests.

## Requirements

- Python 3.10 or newer
- A TwitterAPI.io API key for live searches

## Install from a local checkout

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

Set the API key in your shell. Do not paste it into source files or commit it:

```bash
export TWITTERAPI_IO_API_KEY="your-api-key"
```

PowerShell:

```powershell
$env:TWITTERAPI_IO_API_KEY = "your-api-key"
```

## Usage

Search for posts mentioning Python:

```bash
xsearch "Python"
```

Use advanced-search operators, for example, search posts from NASA while excluding replies:

```bash
xsearch "from:NASA -filter:replies" --pages 2
```

Return JSON for scripting:

```bash
xsearch "open source" --json
```

`--pages` accepts a value from 1 to 20 and defaults to 1. The service may return fewer than 20 posts on a page. When the chosen page limit is reached but more results are available, the readable output says so; JSON output includes `has_next_page` and `next_cursor`.

Queries are limited to 512 characters by the API. The CLI checks that limit before sending a request. For other supported query operators and endpoint details, see the [official Advanced Search documentation](https://docs.twitterapi.io/api-reference/endpoint/tweet_advanced_search).

## Run the offline tests

From the project root:

```bash
python -m unittest discover -s tests -v
```

The tests do not make network requests and do not require a real API key.

## Security and data handling

The key is read from the environment at runtime and sent to `https://api.twitterapi.io` in the `X-API-Key` header. This tool does not save the key, write it to a configuration file, or print it. Search results are returned by the API and printed locally; treat terminal output according to your own privacy needs.
