# for-U Clipper Rebuild

Date: 2026-07-06
Status: approved

## Background

The original `clipper.py` (2022, Selenium 3) automated the full flow: password login,
scroll the Just4U page, click every "Clip Coupon" button. It died in April 2023 when
Albertsons put a captcha on login ("captcha'd EOL"). It is also broken independently of
that: the Selenium 3 API (`find_element_by_*`, `executable_path`) was removed in
Selenium 4, the bundled chromedriver/geckodriver binaries are years stale, and the DOM
selectors it clicked are gone.

The rebuild inverts the architecture: a human logs in once in a real browser, the tool
persists that session, and a scheduled job reuses the session to clip offers through the
for-U JSON API. No automated login, no DOM scraping, no browser on the schedule host.

Prior art confirming the API approach: smkent/safeway-coupons (clips via
`POST /abs/pub/web/j4u/api/offers/clip` with a session token) and JonLuca's
"Reversing private APIs" writeup.

## Decisions (settled with Sam)

- **Approach:** manual session capture + pure HTTP replay. No browser automation of login.
- **Store/banner:** Vons on Turnpike Rd, Santa Barbara. Existing Safeway account works on
  vons.com with password login. Banner is config, not code: `banner = "vons"` maps to
  `https://www.vons.com`. Preferred store is an account setting, set once in the browser,
  not a code concern.
- **Runtime:** Raspberry Pi, nightly cron at 2am, wrapped in `flock`.
- **Language:** Python. Package with `pyproject.toml`. Pi installs only `requests`;
  Playwright is an optional extra (`pip install '.[capture]'`) used only on the Mac.
- **Session refresh flow:** `clipper login` on the Mac opens a headed Playwright browser,
  Sam logs in manually (solving any captcha), the tool saves the session file and pushes
  it to the Pi over ssh (rsync/scp, host and path from config).
- **Notifications:** Pushover. High-priority push on failure/session-expiry, low-priority
  summary push after every successful run (offers found / clipped).
- **Repo:** rewrite in place. Old `clipper.py`, `scriptRunner.sh`, and `webdrivers/` are
  deleted; git history preserves them.

## Components

```
src/clipper/
  cli.py        # entry point: clipper login | clip | status, plus --dry-run on clip
  session.py    # session file: load/save cookies + timestamps, atomic write (tmp+rename)
  api.py        # for-U API client: list offers, clip offer, banner-agnostic base URL
  capture.py    # Mac-only: headed Playwright login -> session file -> push to Pi
  notify.py     # Pushover client
  config.py     # config.toml loader with env-var overrides
deploy/         # cron line + Pi setup notes
tests/          # unit tests with recorded response fixtures
```

Each module stands alone: `session.py` knows nothing about HTTP, `api.py` takes a session
and returns data, `notify.py` takes a message. `cli.py` is the only place they meet.

## Commands

- `clipper login` (Mac): open headed Playwright at the banner sign-in page, wait until
  auth cookies appear (Sam does the typing), save session file, rsync to the Pi. Prints
  confirmation with session destination.
- `clipper clip` (Pi): load session, fetch offers, filter to unclipped, POST a clip per
  offer with a jittered 0.3 to 1.0s delay, write refreshed cookies back to the session
  file, append run stats, send Pushover summary. `--dry-run` does everything except the
  clip POSTs and reports what it would have clipped.
- `clipper status`: session age, last run time and result, from local files only.

## Session lifecycle

Session file is JSON: cookies, captured-at, last-used. Written atomically. Every clip run
persists whatever refreshed tokens the responses set; this cookie write-back is what
stretches a session from days to weeks. When the API answers 401/403 or redirects to
login, the run stops and pushes "session expired, run `clipper login` on the Mac".

## Error handling

- Session invalid: stop, high-priority Pushover, exit nonzero.
- Network errors: retry with backoff (3 attempts), then notify and exit nonzero.
- Individual clip failures: log, continue, include failure count in summary.
- No credentials stored anywhere. Login happens only in a human-driven browser.
- Pushover token/user from env vars or config file with 600 perms.

## Logging

Dated log file under `logs/` (as before) plus one line per run in `runs.jsonl`:
timestamp, offers found, clipped, failed, duration. Carries over the old script's
run-stats habit in a machine-readable form.

## Open item resolved at implementation time

Exact vons.com endpoint paths, required headers, and payload shapes are confirmed by
capturing real network traffic from Sam's browser (Chrome DevTools MCP) while clipping
one coupon by hand, cross-checked against smkent/safeway-coupons. The API client is
built from observed traffic, not guesses. This is the first implementation task.

## Testing

- Unit: session store round-trip and atomicity; API client against recorded fixtures
  (offer list, clip success, 401) using a local HTTP mock.
- End-to-end: `clipper clip --dry-run` validates a real session without side effects.
- Acceptance: capture a real session on the Mac, dry-run on the Pi, then one live run
  that clips real coupons, then confirm the cron entry fires.

## Out of scope

- Automating login or captcha solving, ever.
- Multi-account support.
- Coupon filtering/selection logic (clip everything, same as v1).
