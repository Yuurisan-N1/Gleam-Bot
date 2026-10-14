<div align="center">

<img width="100%" alt="header" src="https://capsule-render.vercel.app/api?type=waving&height=210&text=Gleam%20Bot&fontAlign=50&fontAlignY=36&fontSize=56&desc=MCP%20Server%20%7C%20Gleam.io%20Giveaway%20Automation%20%7C%20X%20Actions%20%7C%20Multi-Account&descAlign=50&descAlignY=58"/>

<img alt="typing" src="https://readme-typing-svg.demolab.com?font=Inter&size=18&duration=3000&pause=650&center=true&vCenter=true&width=900&lines=Auto+Join+Gleam.io+Giveaway+%7C+Pure+HTTP+No+Browser;Auto+X+Actions+%7C+Follow+%2F+Like+%2F+Retweet+%2F+Reply+%2F+Post;Resolver+%7C+Maps+Entry+Methods+to+.env+Keys;18+MCP+Tools+%7C+Call+from+Any+AI+Agent;Cloudflare+Resistant+%7C+JA3+Impersonation+%2B+Proxy"/>

<p>
  <img alt="python" src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white"/>
  <img alt="mcp" src="https://img.shields.io/badge/MCP-Server-111111"/>
  <img alt="platform" src="https://img.shields.io/badge/Platform-Gleam.io-111111"/>
  <img alt="author" src="https://img.shields.io/badge/by-Yuurisandesu-111111"/>
</p>

<p>
  <b>Gleam Bot</b> is an MCP server for automating gleam.io giveaway entries.<br/>
  It fetches and parses live campaigns, maps every entry method to the correct value from your <code>.env</code>, submits entries via pure HTTP with locally computed request signatures, handles mandatory entry chains, and executes all required X actions (follow, like, retweet, reply, post) automatically. It exposes 18 MCP tools callable from any AI agent or script without interactive input.<br/>
  Built and distributed by <b>Yuurisandesu</b>.
</p>

</div>

---

## Table of Contents

- [Requirements](#requirements)
- [Install Python](#install-python)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Server](#running-the-server)
- [Register with Hermes](#register-with-hermes)
- [Usage](#usage)
- [MCP Tools](#mcp-tools)
- [Features](#features)
- [File Structure](#file-structure)
- [Disclaimer](#disclaimer)

---

## Requirements

- Python `3.10+`
- Git
- `uv` (recommended) or `pip`
- `xvfb` (only needed for `gleam_login` on headless servers)

---

## Install Python

### Linux

```bash
sudo apt update && sudo apt install -y python3 python3-pip git
```

### macOS

```bash
brew install python
```

### Windows

Download the latest installer from https://www.python.org/downloads/windows. Check **Add Python to PATH** during installation.

### Termux (Android)

```bash
pkg update && pkg install python git
```

---

## Installation

**Clone the repository:**

```bash
git clone https://github.com/Yuurisan-N1/Gleam-Bot.git
cd Gleam-Bot
```

**Install with uv (recommended):**

```bash
# Linux / macOS
uv venv .venv
uv pip install --python .venv/bin/python -e .
cp .env.example .env

# Windows
uv venv .venv
uv pip install --python .venv\Scripts\python.exe -e .
copy .env.example .env
```

**Install without uv:**

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
cp .env.example .env
```

**For `gleam_login` on a headless server (required for X OAuth):**

```bash
sudo apt-get install -y xvfb
uv pip install --python .venv/bin/python camoufox playwright
.venv/bin/python -m camoufox fetch
```

---

## Configuration

All credentials and values used by campaigns are stored in a single `.env` file. The bot selects the correct key per entry method automatically. Available key categories:

| Category | Keys |
|---|---|
| Identity | `EMAIL`, `PHONE` |
| Wallets | `WALLET_EVM`, `WALLET_SOL`, `WALLET_BTC`, `WALLET_TON`, `WALLET_TRON`, `WALLET_SUI`, and 10 others |
| Exchange UIDs | `KUCOIN_UID`, `BINANCE_UID`, `OKX_UID`, `BYBIT_UID`, `GATE_UID`, and 5 others |
| Social | `X_USERNAME`, `TELEGRAM_USERNAME`, `DISCORD_USERNAME`, `TIKTOK_USERNAME`, and 15 others |
| Content | `REFERRAL_LINK`, `SUBMIT_URL`, `SECRET_CODE`, `QUIZ_ANSWER`, `CUSTOM_TEXT`, and 10 others |
| X Auto Action | `X_AUTO_ACTION`, `X_TWEET_TEXT`, `X_COMMENT_TEXT`, `X_REPLY_TARGET` |
| X Session backup | `X_AUTH_TOKEN`, `X_CT0`, `X_BEARER` |
| Proxy | `PROXY_FILE`, `PROXY_URL` |
| Browser | `BROWSER_ENGINE`, `BROWSER_HEADLESS`, `BROWSER_TIMEOUT` |

See `.env.example` for the full list with comments on every key.

**Value resolution priority per entry method:**

1. Per-campaign override: `CAMPAIGN_<SLUG>_<KEY>`
2. Indexed account: `<KEY>_<N>`
3. Main field: `<KEY>`
4. Fallback: `<KEY>_DEFAULT`
5. Alternate: `<KEY>_ALT_<N>`

If a required key is not filled in, that entry is skipped and reported rather than failing the whole run.

### Session Files

Place cookie files in the `session/` folder. The bot auto-detects the format (name/value array, Playwright export, flat map, or raw Cookie header string):

```
session/
├── x.json               # X (Twitter) session cookie
├── gleam_cookie.json    # Created automatically by gleam_login
├── threads.json         # Optional Threads session
└── custom.json          # Any other service
```

Copy the example and fill in your cookie:

```bash
cp session/x.json.example session/x.json
chmod 600 session/x.json
```

---

## Running the Server

The server communicates over stdio and logs to stderr:

```bash
export GLEAM_ENV_FILE=$PWD/.env
export GLEAM_PROXY_FILE=$HOME/proxy.txt
.venv/bin/python -m gleam_mcp
```

**Test scripts:**

```bash
.venv/bin/python scripts/mcp_smoke.py          # smoke test
.venv/bin/python scripts/mcp_gleam_test.py     # test gleam_state and gleam_enter
.venv/bin/python scripts/gleam_run.py          # state and dry-run
DRY=0 .venv/bin/python scripts/gleam_run.py    # submit for real
.venv/bin/python scripts/cookie_check.py       # check cookie files

# gleam_login on a headless server
xvfb-run -a .venv/bin/python scripts/gleam_login_cli.py "https://gleam.io/<key>/<slug>"
```

---

## Register with Hermes

```bash
hermes mcp add gleam \
  --command /absolute/path/to/.venv/bin/python \
  --env GLEAM_ENV_FILE=/absolute/path/to/.env GLEAM_PROXY_FILE=/absolute/path/to/proxy.txt \
  --args -m gleam_mcp
```

`--args` must come last. Verify:

```bash
hermes mcp test gleam
```

All paths must be absolute when using Hermes since it runs in its own environment.

---

## Usage

No interactive input is required. The campaign link is passed as a tool parameter. A full run looks like:

**1. Check campaign status and which `.env` keys will be used:**

```
gleam_state(campaign="https://gleam.io/oNewO/kucoin-x-tina-x-space")
```

**2. Connect X once per account (opens a browser for OAuth):**

```
gleam_login(campaign="https://gleam.io/oNewO/kucoin-x-tina-x-space")
```

**3. Preview the plan without submitting anything:**

```
gleam_enter(campaign="https://gleam.io/oNewO/kucoin-x-tina-x-space", dry_run=true)
```

**4. Submit entries for real:**

```
gleam_enter(campaign="https://gleam.io/oNewO/kucoin-x-tina-x-space", dry_run=false)
```

For a different campaign, change the `campaign` parameter. The X cookie and `.env` values stay the same across campaigns.

---

## MCP Tools

| Tool | Description |
|---|---|
| `gleam_login` | Connect X to a campaign via OAuth (opens browser once). Auto-skips if the session is already linked. Use `force=true` to force a new session |
| `gleam_state` | Campaign status and contestant state with the `.env` key mapped to each entry method |
| `gleam_enter` | Submit entries via pure HTTP. `dry_run=true` reports the plan without sending |
| `gleam_get_campaign` | Fetch and parse a campaign, return a summary and entry type aggregates |
| `gleam_entry_plan` | Map each entry method to its `.env` key, value, and resolver status |
| `gleam_parse_local` | Parse a campaign from a saved HTML file offline |
| `gleam_env_audit` | Inventory the `.env` file and validate the format of each value |
| `gleam_supported_types` | Catalog of all 48 supported entry types, wallet chains, and intent rules |
| `x_status` | Check whether the X session cookie is still valid |
| `x_user_lookup` | Look up a public X profile using the session cookie |
| `cookie_status` | Status of all session cookie files: present, format, count, session cookie |
| `cookie_connect` | Open a temporary browser with a cookie file and verify the session is alive |
| `x_follow` | Follow an X account using the session cookie |
| `x_auto_plan` | Map each entry method to the X action required (follow, like, retweet, reply, post) |
| `x_auto_run` | Execute the X actions only without touching gleam entries |
| `x_action` | Single X action: `follow`, `unfollow`, `like`, `unlike`, `retweet`, `unretweet`, `post`, `reply`, `verify` |
| `x_ops_refresh` | Re-read X GraphQL operation IDs from the live web bundle |
| `x_ops_report` | Show stored operation IDs and check for drift from the built-in map |
| `browser_info` | Active browser engine, headless mode, and proxy |

---

## Features

### Pure HTTP Entry Submission
Entries are submitted without a browser in the critical path. The bot computes the request signature locally from campaign data, submits the entry to the queue endpoint, then polls the task URL until the server confirms completion. The signature algorithm is verified against live campaign data.

### Mandatory Chain Handling
Many campaigns lock entry N until the previous entry is complete. The bot processes entries in order and stops if any mandatory step fails, preventing invalid submissions.

### Automatic X Actions
For entry methods that require X activity, the bot executes all needed actions automatically: follows the required account, likes or retweets the target tweet, posts a new tweet, or replies with a comment. Tweet text is generated from the entry label and can be overridden with `X_TWEET_TEXT` and `X_COMMENT_TEXT`. Links to created tweets and replies are fetched and submitted to gleam automatically.

### X Operation ID Auto-refresh
X changes GraphQL operation IDs when it releases a new bundle. The bot reads the live bundle and updates the stored IDs automatically so operations continue to work after X updates.

### Idempotent Actions
Follow, like, and retweet status are checked before acting. If the action has already been done, it is skipped without repeating.

### Entry Resolver
Every entry method is classified into one of five resolver statuses before submission: `ready` (data available), `missing` (key not in `.env`), `visit-only` (no data needed), `auth-only` (gleam verifies via linked X account), or `no-data` (unmapped entry type). Missing entries are skipped and reported, not failed.

### Multi-Account Support
The `.env` supports indexed keys (`EMAIL_1`, `WALLET_EVM_2`) and per-campaign overrides (`CAMPAIGN_<SLUG>_<KEY>`) for running multiple accounts and campaign-specific values from a single config file.

### Cloudflare Resistance
The HTTP client impersonates Chrome using `curl_cffi` JA3 fingerprinting. Requests that return 403, 429, or 5xx are retried automatically with proxy rotation from the configured proxy pool.

### Temporary Browser Sessions
When a browser is needed (only for `gleam_login` OAuth and cookie verification), the bot opens a temporary browser instance, injects the session cookie, performs the action, and closes the browser immediately. No browser state is written back to disk and no persistent user data directory is used.

### Cookie Format Auto-Detection
Session cookie files are accepted in any format: name/value array, Playwright export, flat map, or raw Cookie header string. The format is detected automatically on load.

---

## File Structure

```text
Gleam-Bot/
├── src/gleam_mcp/
│   ├── __init__.py
│   ├── __main__.py
│   ├── server.py                  # MCP tool registry and entry point
│   ├── entry.py                   # Pure HTTP entry engine: signature, queue, poll
│   ├── browser.py                 # Temporary browser sessions and X OAuth
│   ├── cookies.py                 # Cookie registry and multi-format loader
│   ├── resolver.py                # Entry method to .env key mapper
│   ├── keyspec.py                 # Key specification: 48 entry types, wallet chains, intent rules
│   ├── parse.py                   # Campaign HTML parser (AngularJS legacy)
│   ├── envstore.py                # .env reader with indexed and per-campaign override support
│   ├── transport.py               # HTTP client: curl_cffi impersonation, proxy pool, retry
│   └── sources/
│       ├── gleam.py               # Gleam.io HTTP operations
│       ├── x.py                   # X HTTP operations: follow, like, retweet, reply, post
│       └── xact.py                # X GraphQL operation ID store and auto-refresh
├── scripts/
│   ├── gleam_run.py               # CLI: state and entry run
│   ├── gleam_login_cli.py         # CLI: connect X via OAuth
│   ├── mcp_smoke.py               # MCP smoke test
│   ├── mcp_gleam_test.py          # Test gleam_state and gleam_enter
│   ├── mcp_live.py                # Test against a live campaign via MCP
│   ├── browser_e2e.py             # Browser end-to-end test
│   ├── cookie_check.py            # Cookie file status check
│   └── demo_resolve.py            # Resolver demo
├── session/
│   ├── x.json.example             # X cookie template
│   ├── threads.json.example       # Threads cookie template
│   └── custom.json.example        # Custom service cookie template
├── utils/
│   └── banner.py                  # Banner using yuurisan module
├── pyproject.toml                 # Project manifest and dependencies
├── requirements.txt               # Pinned dependencies
├── .env.example                   # Full .env template with all 50 keys documented
└── LICENSE                        # License file
```

---

## Disclaimer

This tool is built for educational and technical exploration purposes. Use it wisely and at your own responsibility.

---

<div align="center">
<img width="100%" alt="footer" src="https://capsule-render.vercel.app/api?type=waving&height=120&section=footer"/>
</div>