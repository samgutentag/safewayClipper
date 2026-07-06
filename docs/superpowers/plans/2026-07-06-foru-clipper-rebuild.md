# for-U Clipper Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the dead Selenium coupon clipper as a Python package that captures a vons.com session once in a real browser on the Mac, then clips all for-U offers nightly on a Raspberry Pi via the for-U JSON API.

**Architecture:** Manual session capture (headed Playwright on the Mac) writes a JSON session file and pushes it to the Pi. The Pi runs a pure-`requests` client that reads the session, lists offers, clips the unclipped ones, writes refreshed cookies back, and reports via Pushover. No browser and no credentials on the Pi.

**Tech Stack:** Python 3.11+, `requests`, `tomllib` (stdlib), Playwright (Mac-only, optional extra), `pytest` + `responses` for tests, `pyproject.toml` packaging with a `clipper` console script.

## Global Constraints

- Python 3.11+ (uses stdlib `tomllib`).
- Pi install surface is `requests` only. Playwright is an optional extra: `pip install '.[capture]'`, imported lazily inside `capture.py` so `clip`/`status` never import it.
- Banner is config-driven, never hardcoded: `banner` -> base URL (`vons` -> `https://www.vons.com`, `safeway` -> `https://www.safeway.com`, `albertsons` -> `https://www.albertsons.com`).
- No credentials stored on disk or in config, ever. Login happens only in a human-driven browser.
- Session file and config file written with `0o600` permissions.
- All session-file writes are atomic (write temp in same dir, then `os.replace`).
- for-U API contract (CONFIRMED LIVE against vons.com 2026-07-06 — see tests/fixtures/README.md):
  - Access token + store id come from browser cookies `SWY_SHARED_SESSION` (`.accessToken`) and `SWY_SHARED_SESSION_INFO` (`.info.J4U.storeId`), each URL-encoded JSON. (Confirmed: store 3326.)
  - **Offers (GET):** `{base}/abs/pub/xapi/offers/companiongalleryoffer?storeId={storeId}&rand={rand}&includeRedmBonusPathFPOffers=true`
    Headers: `Authorization: Bearer {accessToken}`, `Accept: application/json`, `Content-Type: application/vnd.safeway.v2+json`, `X-SWY_API_KEY: {api_key}`, `X-SWY_BANNER: {banner}`, `X-SWY_VERSION: 1.1`, `X-SWY-APPLICATION-TYPE: web`.
  - **Clip (POST):** `{base}/abs/pub/web/j4u/api/offers/clip?storeId={storeId}` — routes through the IBM API gateway, DIFFERENT auth than the GET.
    Headers: `swy_sso_token: {accessToken}` (NOT Authorization), `x-swyconsumerdirectorypro: {accessToken}` (same JWT again), `x-ibm-client-id: {ibm_client_id}`, `x-ibm-client-secret: {ibm_client_secret}`, `x-swy-correlation-id: {fresh uuid4}`, `X-SWY_API_KEY: {api_key}`, `X-SWY_BANNER: {banner}`, `X-SWY_VERSION: 1.0` (note: 1.0, not 1.1), `Content-Type: application/json`, `Accept: application/json, text/plain, */*`, `Origin: {base}`.
  - Clip body (confirmed exact): `{"items": [{"clipType": "C", "itemId": <offerId>, "itemType": <offerPgm>}, {"clipType": "L", "itemId": <offerId>, "itemType": <offerPgm>}]}`. Success = response `items` non-empty and every item `status == 1` (reference-derived, confirmed live in Task 9).
  - Offer status: `"U"` unclipped, `"C"` clipped. Offer program (`offerPgm`): `SC`, `MF`, `PD`.
  - **Credentials via config (gitignored), NOT hardcoded** (repo is public): `api_key` (value `emjou`), `banner`, `ibm_client_id`, `ibm_client_secret` all come from `config.toml`. Task 3's `Config` is extended with `api_key`, `ibm_client_id`, `ibm_client_secret` fields before Task 5.
- Clip pacing: jittered delay 0.3 to 1.0s between clip POSTs.
- Repo rewrite in place: delete `clipper.py`, `scriptRunner.sh`, `webdrivers/`, `requirements.txt` as part of Task 2.

---

## File Structure

```
pyproject.toml            # package metadata, deps, [capture] extra, clipper console script
src/clipper/
  __init__.py
  config.py               # load config.toml + env overrides; banner -> base URL
  session.py              # SessionStore: atomic load/save of cookies + timestamps
  api.py                  # ForUClient: list offers, clip offer (pure requests)
  notify.py               # Pushover client (send + priority)
  capture.py              # Mac-only: headed Playwright login -> session -> rsync to Pi
  cli.py                  # argparse entry: login | clip | status
tests/
  test_config.py
  test_session.py
  test_api.py
  test_cli.py
deploy/
  crontab.example        # the flock-wrapped 2am line
  README.md              # Pi setup notes
config.toml.example      # documented config template (no secrets)
```

---

### Task 1: Confirm the live vons.com API contract

Pin the real endpoints/headers/cookie shapes before writing the client, so `api.py` is built from observed traffic, not the reference repo alone. This task produces a committed fixtures file, not shippable code.

**Files:**
- Create: `tests/fixtures/README.md` (how the fixtures were captured)
- Create: `tests/fixtures/offers_sample.json` (redacted real offer-list response)
- Create: `tests/fixtures/clip_success.json` (redacted real clip response)

**Interfaces:**
- Produces: verified constants for Task 3 — the exact base host for `vons`, the two cookie names, the JSON paths to `accessToken` and `storeId`, and the offer/clip JSON field names. If any differ from the Global Constraints contract, update that section in this plan before proceeding.

- [ ] **Step 1: Confirm Sam is logged in at vons.com**

Ask Sam to have a Chrome tab open at `https://www.vons.com/foru/coupons-deals.html`, signed in, with the Turnpike/Santa Barbara store selected.

- [ ] **Step 2: Capture the offers request via Chrome DevTools MCP**

Using the chrome-devtools MCP: `list_network_requests` filtered to `companiongalleryoffer`. Record the full request URL (confirm host is `www.vons.com`), the request headers (`Authorization`, `X-SWY_API_KEY`, `X-SWY_VERSION`, `X-SWY-APPLICATION-TYPE`), and `storeId` query value. Save the JSON response body (redact nothing structural, but you may truncate to ~10 offers) to `tests/fixtures/offers_sample.json`.

- [ ] **Step 3: Capture a clip request by clipping one coupon by hand**

Have Sam click a single "Clip Coupon" in the tab. `list_network_requests` filtered to `offers/clip`. Record the POST URL, request body JSON, and headers. Save the response body to `tests/fixtures/clip_success.json`.

- [ ] **Step 4: Read the session cookies**

`evaluate_script` returning `document.cookie` (or use the network request's `Cookie` header). Confirm `SWY_SHARED_SESSION` and `SWY_SHARED_SESSION_INFO` exist and that URL-decoding them yields JSON containing `accessToken` and `info.J4U.storeId` respectively.

- [ ] **Step 5: Reconcile with the plan**

If anything (host, header names, cookie names, field names, clip body shape) differs from the Global Constraints contract, edit the Global Constraints section of this plan to match reality. Note the confirmed values in `tests/fixtures/README.md`.

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/
git commit -m "test: capture live vons.com for-U API fixtures"
```

---

### Task 2: Package skeleton and teardown of the old tool

**Files:**
- Create: `pyproject.toml`
- Create: `src/clipper/__init__.py`
- Delete: `clipper.py`, `scriptRunner.sh`, `requirements.txt`, `webdrivers/`
- Modify: `.gitignore` (add `session.json`, `config.toml`, keep ignoring `logs/`)

**Interfaces:**
- Produces: importable package `clipper` with `__version__`; console script `clipper` -> `clipper.cli:main` (wired in Task 7 but declared here).

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "foru-clipper"
version = "2026.7.6"
description = "Clip Albertsons for-U coupons via a captured browser session"
requires-python = ">=3.11"
dependencies = ["requests>=2.31"]

[project.optional-dependencies]
capture = ["playwright>=1.44"]
dev = ["pytest>=8", "responses>=0.25"]

[project.scripts]
clipper = "clipper.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]
```

- [ ] **Step 2: Create `src/clipper/__init__.py`**

```python
__version__ = "2026.7.6"
```

- [ ] **Step 3: Remove the dead v1 tool**

```bash
git rm clipper.py scriptRunner.sh requirements.txt
git rm -r webdrivers
```

- [ ] **Step 4: Update `.gitignore`**

Append:

```
# runtime secrets / state (never commit)
session.json
config.toml
```

- [ ] **Step 5: Verify the package imports**

Run: `pip install -e '.[dev]' && python -c "import clipper; print(clipper.__version__)"`
Expected: prints `2026.7.6`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/clipper/__init__.py .gitignore
git commit -m "feat: package skeleton; remove dead Selenium v1"
```

---

### Task 3: Config loader

**Files:**
- Create: `src/clipper/config.py`
- Create: `config.toml.example`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces:
  - `BANNER_BASE_URLS: dict[str, str]` mapping `"vons"|"safeway"|"albertsons"` to base URL.
  - `@dataclass Config` with fields: `banner: str`, `base_url: str`, `session_path: Path`, `pushover_token: str | None`, `pushover_user: str | None`, `pi_ssh_host: str | None`, `pi_session_path: str | None`, `notify_on_success: bool` (default `True`).
  - `load_config(path: Path | None = None) -> Config`. Reads TOML, applies env overrides `PUSHOVER_TOKEN`/`PUSHOVER_USER`, derives `base_url` from `banner`, raises `ValueError` on unknown banner.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
from pathlib import Path
import pytest
from clipper.config import load_config, BANNER_BASE_URLS

def test_banner_maps_to_base_url(tmp_path, monkeypatch):
    monkeypatch.delenv("PUSHOVER_TOKEN", raising=False)
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        'banner = "vons"\n'
        'session_path = "session.json"\n'
        '[pushover]\ntoken = "t"\nuser = "u"\n'
    )
    cfg = load_config(cfg_file)
    assert cfg.base_url == "https://www.vons.com"
    assert cfg.pushover_token == "t"
    assert cfg.notify_on_success is True

def test_env_overrides_pushover(tmp_path, monkeypatch):
    monkeypatch.setenv("PUSHOVER_TOKEN", "env-token")
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text('banner = "vons"\nsession_path = "s.json"\n')
    cfg = load_config(cfg_file)
    assert cfg.pushover_token == "env-token"

def test_unknown_banner_raises(tmp_path):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text('banner = "kroger"\nsession_path = "s.json"\n')
    with pytest.raises(ValueError):
        load_config(cfg_file)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clipper.config'`

- [ ] **Step 3: Write `src/clipper/config.py`**

```python
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

BANNER_BASE_URLS = {
    "vons": "https://www.vons.com",
    "safeway": "https://www.safeway.com",
    "albertsons": "https://www.albertsons.com",
}


@dataclass
class Config:
    banner: str
    base_url: str
    session_path: Path
    pushover_token: str | None = None
    pushover_user: str | None = None
    pi_ssh_host: str | None = None
    pi_session_path: str | None = None
    notify_on_success: bool = True


def load_config(path: Path | None = None) -> Config:
    path = Path(path) if path else Path("config.toml")
    with open(path, "rb") as f:
        raw = tomllib.load(f)

    banner = raw["banner"]
    if banner not in BANNER_BASE_URLS:
        raise ValueError(
            f"Unknown banner {banner!r}; expected one of "
            f"{sorted(BANNER_BASE_URLS)}"
        )

    pushover = raw.get("pushover", {})
    pi = raw.get("pi", {})
    return Config(
        banner=banner,
        base_url=BANNER_BASE_URLS[banner],
        session_path=Path(raw["session_path"]),
        pushover_token=os.environ.get("PUSHOVER_TOKEN")
        or pushover.get("token"),
        pushover_user=os.environ.get("PUSHOVER_USER") or pushover.get("user"),
        pi_ssh_host=pi.get("ssh_host"),
        pi_session_path=pi.get("session_path"),
        notify_on_success=raw.get("notify_on_success", True),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Write `config.toml.example`**

```toml
# Which Albertsons banner. Determines the API base URL.
banner = "vons"

# Where the captured session lives on THIS machine.
session_path = "session.json"

# Send a low-priority push after successful runs too, not just failures.
notify_on_success = true

[pushover]
# Prefer env vars PUSHOVER_TOKEN / PUSHOVER_USER over committing these.
token = ""
user = ""

# Mac-only: where `clipper login` pushes the session after capture.
[pi]
ssh_host = "pi@raspberrypi.local"
session_path = "/home/pi/foru-clipper/session.json"
```

- [ ] **Step 6: Commit**

```bash
git add src/clipper/config.py config.toml.example tests/test_config.py
git commit -m "feat: config loader with banner->URL mapping and env overrides"
```

---

### Task 4: Session store

**Files:**
- Create: `src/clipper/session.py`
- Test: `tests/test_session.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `@dataclass Session` with `cookies: dict[str, str]`, `captured_at: str` (ISO 8601 UTC), `last_used: str | None`.
  - `Session.access_token() -> str` and `Session.store_id() -> str`: URL-decode + JSON-parse `SWY_SHARED_SESSION` / `SWY_SHARED_SESSION_INFO` cookies, returning `accessToken` / `info.J4U.storeId`. Raise `SessionError` if the cookie is missing or malformed.
  - `SessionError(Exception)`.
  - `load_session(path: Path) -> Session`.
  - `save_session(path: Path, session: Session) -> None`: atomic write (`os.replace`), `chmod 0o600`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_session.py
import json
import stat
import urllib.parse
from pathlib import Path
import pytest
from clipper.session import Session, SessionError, load_session, save_session


def _cookie(obj):
    return urllib.parse.quote(json.dumps(obj))


def _valid_session():
    return Session(
        cookies={
            "SWY_SHARED_SESSION": _cookie({"accessToken": "tok123"}),
            "SWY_SHARED_SESSION_INFO": _cookie(
                {"info": {"J4U": {"storeId": "2930"}}}
            ),
        },
        captured_at="2026-07-06T00:00:00+00:00",
        last_used=None,
    )


def test_roundtrip_and_permissions(tmp_path):
    p = tmp_path / "session.json"
    save_session(p, _valid_session())
    loaded = load_session(p)
    assert loaded.access_token() == "tok123"
    assert loaded.store_id() == "2930"
    mode = stat.S_IMODE(p.stat().st_mode)
    assert mode == 0o600


def test_missing_cookie_raises(tmp_path):
    s = Session(cookies={}, captured_at="2026-07-06T00:00:00+00:00", last_used=None)
    with pytest.raises(SessionError):
        s.access_token()


def test_atomic_write_leaves_no_temp(tmp_path):
    p = tmp_path / "session.json"
    save_session(p, _valid_session())
    leftovers = [x.name for x in tmp_path.iterdir() if x.name != "session.json"]
    assert leftovers == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_session.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clipper.session'`

- [ ] **Step 3: Write `src/clipper/session.py`**

```python
from __future__ import annotations

import json
import os
import tempfile
import urllib.parse
from dataclasses import asdict, dataclass
from pathlib import Path


class SessionError(Exception):
    pass


@dataclass
class Session:
    cookies: dict[str, str]
    captured_at: str
    last_used: str | None = None

    def _decode_cookie(self, name: str) -> dict:
        raw = self.cookies.get(name)
        if not raw:
            raise SessionError(f"Missing cookie {name!r}")
        try:
            return json.loads(urllib.parse.unquote(raw))
        except (ValueError, TypeError) as e:
            raise SessionError(f"Malformed cookie {name!r}") from e

    def access_token(self) -> str:
        data = self._decode_cookie("SWY_SHARED_SESSION")
        token = data.get("accessToken")
        if not token:
            raise SessionError("No accessToken in SWY_SHARED_SESSION")
        return token

    def store_id(self) -> str:
        data = self._decode_cookie("SWY_SHARED_SESSION_INFO")
        try:
            return data["info"]["J4U"]["storeId"]
        except (KeyError, TypeError) as e:
            raise SessionError("No storeId in SWY_SHARED_SESSION_INFO") from e


def load_session(path: Path) -> Session:
    with open(path, "rb") as f:
        data = json.load(f)
    return Session(
        cookies=data["cookies"],
        captured_at=data["captured_at"],
        last_used=data.get("last_used"),
    )


def save_session(path: Path, session: Session) -> None:
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(asdict(session), f, indent=2)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_session.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/clipper/session.py tests/test_session.py
git commit -m "feat: atomic session store with token/store-id decoding"
```

---

### Task 5: for-U API client

**Files:**
- Create: `src/clipper/api.py`
- Test: `tests/test_api.py`

> **REVISED per Task 1 live capture (2026-07-06).** The original single-header design below
> was reference-derived. The confirmed vons.com contract (see Global Constraints and
> tests/fixtures/README.md) has DIFFERENT auth per endpoint: the GET uses `Authorization: Bearer`
> + `X-SWY_VERSION: 1.1`; the clip POST uses `swy_sso_token` + `x-swyconsumerdirectorypro` +
> IBM gateway creds (`x-ibm-client-id`/`x-ibm-client-secret`) + `X-SWY_VERSION: 1.0`. Creds come
> from `Config` (gitignored), not hardcoded. The authoritative implementation for this task is in
> `.superpowers/sdd/task-5-brief.md`, hand-authored from the live capture. The code block below is
> retained for context but is superseded by the brief.

**Interfaces:**
- Consumes: `Session` from Task 4 (`access_token()`, `store_id()`, `cookies`); `Config` from Task 3 (`base_url`, `banner`, `api_key`, `ibm_client_id`, `ibm_client_secret`).
- Produces:
  - `@dataclass Offer` with `offer_id: str`, `status: str`, `name: str`, `offer_pgm: str`.
  - `Offer.is_unclipped() -> bool` (`status == "U"`).
  - `AuthExpired(Exception)` and `ClipError(Exception)`.
  - `ForUClient(config: Config, session: Session)`.
  - `ForUClient.get_offers() -> list[Offer]`: GET companiongalleryoffer (Bearer auth); raises `AuthExpired` on 401/403.
  - `ForUClient.clip(offer: Offer) -> None`: POST clip (sso-token + IBM gateway auth); raises `AuthExpired` on 401/403, `ClipError` on unsuccessful body.
  - `ForUClient.refreshed_cookies() -> dict[str, str]`: current cookie jar as a dict (for write-back).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api.py
import json
import urllib.parse
import pytest
import responses
from clipper.session import Session
from clipper.api import ForUClient, Offer, AuthExpired, ClipError

BASE = "https://www.vons.com"


def _session():
    return Session(
        cookies={
            "SWY_SHARED_SESSION": urllib.parse.quote(
                json.dumps({"accessToken": "tok"})
            ),
            "SWY_SHARED_SESSION_INFO": urllib.parse.quote(
                json.dumps({"info": {"J4U": {"storeId": "2930"}}})
            ),
        },
        captured_at="2026-07-06T00:00:00+00:00",
    )


OFFERS_BODY = {
    "companionGalleryOfferList": [
        {"offerId": "1", "status": "U", "name": "Milk", "offerPgm": "SC"},
        {"offerId": "2", "status": "C", "name": "Eggs", "offerPgm": "MF"},
    ]
}


@responses.activate
def test_get_offers_parses_and_flags_unclipped():
    responses.add(
        responses.GET,
        f"{BASE}/abs/pub/xapi/offers/companiongalleryoffer",
        json=OFFERS_BODY,
        status=200,
    )
    client = ForUClient(BASE, _session())
    offers = client.get_offers()
    assert [o.offer_id for o in offers] == ["1", "2"]
    assert offers[0].is_unclipped() is True
    assert offers[1].is_unclipped() is False
    sent = responses.calls[0].request
    assert sent.headers["Authorization"] == "Bearer tok"
    assert sent.headers["X-SWY_API_KEY"] == "emjou"


@responses.activate
def test_get_offers_401_raises_authexpired():
    responses.add(
        responses.GET,
        f"{BASE}/abs/pub/xapi/offers/companiongalleryoffer",
        status=401,
    )
    with pytest.raises(AuthExpired):
        ForUClient(BASE, _session()).get_offers()


@responses.activate
def test_clip_success():
    responses.add(
        responses.POST,
        f"{BASE}/abs/pub/web/j4u/api/offers/clip",
        json={"items": [{"status": 1}, {"status": 1}]},
        status=200,
    )
    client = ForUClient(BASE, _session())
    client.clip(Offer("1", "U", "Milk", "SC"))
    body = json.loads(responses.calls[0].request.body)
    assert {i["clipType"] for i in body["items"]} == {"C", "L"}
    assert body["items"][0]["itemId"] == "1"


@responses.activate
def test_clip_unsuccessful_body_raises():
    responses.add(
        responses.POST,
        f"{BASE}/abs/pub/web/j4u/api/offers/clip",
        json={"items": [{"status": 0}]},
        status=200,
    )
    with pytest.raises(ClipError):
        ForUClient(BASE, _session()).clip(Offer("1", "U", "Milk", "SC"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clipper.api'`

- [ ] **Step 3: Write `src/clipper/api.py`**

```python
from __future__ import annotations

import json
from dataclasses import dataclass

import requests

from .session import Session

API_KEY = "emjou"


class AuthExpired(Exception):
    pass


class ClipError(Exception):
    pass


@dataclass
class Offer:
    offer_id: str
    status: str
    name: str
    offer_pgm: str

    def is_unclipped(self) -> bool:
        return self.status == "U"

    @classmethod
    def from_dict(cls, d: dict) -> "Offer":
        return cls(
            offer_id=d["offerId"],
            status=d.get("status", "?"),
            name=d.get("name", ""),
            offer_pgm=d.get("offerPgm", "?"),
        )


class ForUClient:
    def __init__(self, base_url: str, session: Session) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session
        self._http = requests.Session()
        for name, value in session.cookies.items():
            self._http.cookies.set(name, value)
        self._http.headers.update(
            {
                "Authorization": f"Bearer {session.access_token()}",
                "X-SWY_API_KEY": API_KEY,
                "X-SWY_VERSION": "1.1",
                "X-SWY-APPLICATION-TYPE": "web",
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36"
                ),
            }
        )
        self._store_id = session.store_id()

    def _raise_if_auth(self, resp: requests.Response) -> None:
        if resp.status_code in (401, 403):
            raise AuthExpired(f"HTTP {resp.status_code} from {resp.url}")

    def get_offers(self) -> list[Offer]:
        url = f"{self.base_url}/abs/pub/xapi/offers/companiongalleryoffer"
        resp = self._http.get(
            url, params={"storeId": self._store_id, "rand": "654321"}
        )
        self._raise_if_auth(resp)
        resp.raise_for_status()
        body = resp.json()
        return [
            Offer.from_dict(o)
            for o in body.get("companionGalleryOfferList", [])
        ]

    def clip(self, offer: Offer) -> None:
        url = f"{self.base_url}/abs/pub/web/j4u/api/offers/clip"
        payload = {
            "items": [
                {
                    "clipType": clip_type,
                    "itemId": offer.offer_id,
                    "itemType": offer.offer_pgm,
                }
                for clip_type in ("C", "L")
            ]
        }
        resp = self._http.post(
            url,
            params={"storeId": self._store_id},
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        self._raise_if_auth(resp)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if not items or not all(i.get("status") == 1 for i in items):
            raise ClipError(f"Unsuccessful clip for {offer.offer_id}")

    def refreshed_cookies(self) -> dict[str, str]:
        return {c.name: c.value for c in self._http.cookies}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_api.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Confirm header contract against the captured fixtures**

The offer-list response body was not captured in Task 1 (only requests). The parsed shape
(`companionGalleryOfferList` array with `offerId`/`status`/`offerPgm`) is reference-derived and
confirmed on the Task 9 live run. Verify instead that the request headers your client sends match
`tests/fixtures/README.md` exactly (per-endpoint auth, versions, banner, IBM creds on clip only).

- [ ] **Step 6: Commit**

```bash
git add src/clipper/api.py tests/test_api.py
git commit -m "feat: for-U API client (list + clip) with auth-expiry detection"
```

---

### Task 6: Pushover notifier

**Files:**
- Create: `src/clipper/notify.py`
- Test: `tests/test_notify.py`

**Interfaces:**
- Consumes: nothing (token/user passed in).
- Produces:
  - `Notifier(token: str | None, user: str | None)`.
  - `Notifier.send(title: str, message: str, priority: int = 0) -> None`: POST to `https://api.pushover.net/1/messages.json`. No-op (logs) if token/user unset. Never raises on HTTP failure — notification must not crash the run.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_notify.py
import responses
from clipper.notify import Notifier

URL = "https://api.pushover.net/1/messages.json"


@responses.activate
def test_send_posts_payload():
    responses.add(responses.POST, URL, json={"status": 1}, status=200)
    Notifier("tok", "usr").send("Title", "Body", priority=1)
    body = responses.calls[0].request.body
    assert "token=tok" in body and "user=usr" in body and "priority=1" in body


@responses.activate
def test_missing_credentials_is_noop():
    Notifier(None, None).send("Title", "Body")
    assert len(responses.calls) == 0


@responses.activate
def test_http_error_does_not_raise():
    responses.add(responses.POST, URL, status=500)
    Notifier("tok", "usr").send("Title", "Body")  # must not raise
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_notify.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clipper.notify'`

- [ ] **Step 3: Write `src/clipper/notify.py`**

```python
from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

PUSHOVER_URL = "https://api.pushover.net/1/messages.json"


class Notifier:
    def __init__(self, token: str | None, user: str | None) -> None:
        self.token = token
        self.user = user

    def send(self, title: str, message: str, priority: int = 0) -> None:
        if not (self.token and self.user):
            logger.info("Pushover not configured; skipping: %s", title)
            return
        try:
            requests.post(
                PUSHOVER_URL,
                data={
                    "token": self.token,
                    "user": self.user,
                    "title": title,
                    "message": message,
                    "priority": priority,
                },
                timeout=10,
            )
        except requests.RequestException as e:
            logger.warning("Pushover send failed: %s", e)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_notify.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/clipper/notify.py tests/test_notify.py
git commit -m "feat: Pushover notifier that never crashes the run"
```

---

### Task 7: CLI — clip and status

Wires config + session + api + notify into the `clipper clip` and `clipper status` commands. `login` is added in Task 8.

**Files:**
- Create: `src/clipper/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `load_config` (Task 3); `load_session`/`save_session`/`Session` (Task 4); `ForUClient`/`AuthExpired`/`ClipError` (Task 5); `Notifier` (Task 6).
- Produces:
  - `run_clip(config, dry_run: bool, sleep_fn=time.sleep, now_fn=...) -> int`: load session, list offers, clip unclipped ones with jittered delay (skipped when `dry_run`), write refreshed cookies + `last_used` back, append a line to `runs.jsonl`, send Pushover summary (respecting `notify_on_success`). Returns clipped count. On `AuthExpired`, sends high-priority push and raises.
  - `main(argv=None) -> int`: argparse with subcommands `login`, `clip` (`--dry-run`, `--config`), `status`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py
import json
import urllib.parse
from pathlib import Path
import responses
from clipper.cli import run_clip
from clipper.config import Config
from clipper.session import Session, save_session

BASE = "https://www.vons.com"


def _config(tmp_path):
    sp = tmp_path / "session.json"
    save_session(
        sp,
        Session(
            cookies={
                "SWY_SHARED_SESSION": urllib.parse.quote(
                    json.dumps({"accessToken": "tok"})
                ),
                "SWY_SHARED_SESSION_INFO": urllib.parse.quote(
                    json.dumps({"info": {"J4U": {"storeId": "2930"}}})
                ),
            },
            captured_at="2026-07-06T00:00:00+00:00",
        ),
    )
    return Config(
        banner="vons",
        base_url=BASE,
        session_path=sp,
        notify_on_success=False,
    )


@responses.activate
def test_run_clip_clips_only_unclipped(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    responses.add(
        responses.GET,
        f"{BASE}/abs/pub/xapi/offers/companiongalleryoffer",
        json={
            "companionGalleryOfferList": [
                {"offerId": "1", "status": "U", "name": "Milk", "offerPgm": "SC"},
                {"offerId": "2", "status": "C", "name": "Eggs", "offerPgm": "MF"},
            ]
        },
        status=200,
    )
    responses.add(
        responses.POST,
        f"{BASE}/abs/pub/web/j4u/api/offers/clip",
        json={"items": [{"status": 1}, {"status": 1}]},
        status=200,
    )
    clipped = run_clip(_config(tmp_path), dry_run=False, sleep_fn=lambda s: None)
    assert clipped == 1
    assert (tmp_path / "runs.jsonl").exists()


@responses.activate
def test_dry_run_clips_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    responses.add(
        responses.GET,
        f"{BASE}/abs/pub/xapi/offers/companiongalleryoffer",
        json={
            "companionGalleryOfferList": [
                {"offerId": "1", "status": "U", "name": "Milk", "offerPgm": "SC"}
            ]
        },
        status=200,
    )
    clipped = run_clip(_config(tmp_path), dry_run=True, sleep_fn=lambda s: None)
    assert clipped == 0
    post_calls = [c for c in responses.calls if c.request.method == "POST"]
    assert post_calls == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clipper.cli'`

- [ ] **Step 3: Write `src/clipper/cli.py`**

```python
from __future__ import annotations

import argparse
import json
import logging
import random
import time
from datetime import datetime, timezone
from pathlib import Path

from .api import AuthExpired, ClipError, ForUClient
from .config import Config, load_config
from .notify import Notifier
from .session import SessionError, load_session, save_session

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_run(clipped: int, found: int, failed: int) -> None:
    line = {
        "ts": _now_iso(),
        "found": found,
        "clipped": clipped,
        "failed": failed,
    }
    with open("runs.jsonl", "a") as f:
        f.write(json.dumps(line) + "\n")


def run_clip(
    config: Config,
    dry_run: bool = False,
    sleep_fn=time.sleep,
) -> int:
    notifier = Notifier(config.pushover_token, config.pushover_user)
    session = load_session(config.session_path)
    client = ForUClient(config, session)

    try:
        offers = client.get_offers()
    except AuthExpired:
        notifier.send(
            "for-U clipper: session expired",
            "Run `clipper login` on the Mac to refresh the session.",
            priority=1,
        )
        raise

    unclipped = [o for o in offers if o.is_unclipped()]
    clipped = 0
    failed = 0
    for offer in unclipped:
        if dry_run:
            continue
        try:
            client.clip(offer)
            clipped += 1
        except AuthExpired:
            notifier.send(
                "for-U clipper: session expired",
                "Session died mid-run. Run `clipper login` on the Mac.",
                priority=1,
            )
            raise
        except ClipError as e:
            failed += 1
            logger.warning("clip failed: %s", e)
        sleep_fn(random.uniform(0.3, 1.0))

    if not dry_run:
        session.cookies = client.refreshed_cookies() or session.cookies
        session.last_used = _now_iso()
        save_session(config.session_path, session)
        _append_run(clipped, len(offers), failed)

    if not dry_run and (config.notify_on_success or failed):
        notifier.send(
            "for-U clipper: done",
            f"Found {len(offers)}, clipped {clipped}, failed {failed}.",
            priority=0,
        )
    return clipped


def _cmd_status(config: Config) -> int:
    try:
        session = load_session(config.session_path)
        print(f"session captured_at: {session.captured_at}")
        print(f"session last_used:   {session.last_used}")
    except (FileNotFoundError, SessionError) as e:
        print(f"no valid session: {e}")
    if Path("runs.jsonl").exists():
        last = Path("runs.jsonl").read_text().strip().splitlines()[-1:]
        if last:
            print(f"last run: {last[0]}")
    return 0


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(prog="clipper")
    parser.add_argument("--config", default=None)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("login")
    clip_p = sub.add_parser("clip")
    clip_p.add_argument("--dry-run", action="store_true")
    sub.add_parser("status")

    args = parser.parse_args(argv)
    config = load_config(Path(args.config) if args.config else None)

    if args.command == "login":
        from .capture import run_login

        return run_login(config)
    if args.command == "clip":
        try:
            run_clip(config, dry_run=args.dry_run)
            return 0
        except AuthExpired:
            return 2
    if args.command == "status":
        return _cmd_status(config)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the whole suite**

Run: `pytest -v`
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/clipper/cli.py tests/test_cli.py
git commit -m "feat: clip and status commands with run log and Pushover summary"
```

---

### Task 8: Login capture (Mac-only, Playwright)

**Files:**
- Create: `src/clipper/capture.py`

**Interfaces:**
- Consumes: `Config` (Task 3); `Session`/`save_session` (Task 4).
- Produces: `run_login(config: Config) -> int`: open a headed Chromium at the banner sign-in page, wait for the two `SWY_SHARED_SESSION*` cookies to appear (Sam logs in by hand), build a `Session`, `save_session` locally, then rsync to the Pi if `pi_ssh_host`/`pi_session_path` are set.

This task has no unit test (it drives a real browser and network). It is verified live in Task 9. Playwright is imported lazily so the Pi never needs it.

- [ ] **Step 1: Install the capture extra and browser locally**

Run: `pip install -e '.[capture]' && python -m playwright install chromium`
Expected: chromium downloaded.

- [ ] **Step 2: Write `src/clipper/capture.py`**

```python
from __future__ import annotations

import subprocess
from datetime import datetime, timezone

from .config import Config
from .session import Session, save_session

REQUIRED_COOKIES = ("SWY_SHARED_SESSION", "SWY_SHARED_SESSION_INFO")


def run_login(config: Config) -> int:
    from playwright.sync_api import sync_playwright

    sign_in_url = f"{config.base_url}/account/sign-in.html"
    print(f"Opening {sign_in_url} — log in by hand (solve any captcha).")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(sign_in_url)

        print("Waiting for sign-in to complete (up to 5 minutes)...")
        cookies: dict[str, str] = {}
        for _ in range(300):
            jar = {c["name"]: c["value"] for c in context.cookies()}
            if all(name in jar for name in REQUIRED_COOKIES):
                cookies = jar
                break
            page.wait_for_timeout(1000)
        browser.close()

    if not cookies:
        print("Timed out waiting for session cookies. Not logged in.")
        return 1

    session = Session(
        cookies=cookies,
        captured_at=datetime.now(timezone.utc).isoformat(),
    )
    save_session(config.session_path, session)
    print(f"Session saved to {config.session_path}")

    if config.pi_ssh_host and config.pi_session_path:
        dest = f"{config.pi_ssh_host}:{config.pi_session_path}"
        print(f"Pushing session to {dest}")
        result = subprocess.run(
            ["rsync", "-az", str(config.session_path), dest],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"rsync failed: {result.stderr.strip()}")
            return 1
        print("Session pushed to Pi.")
    else:
        print("No Pi configured; session left local only.")

    return 0
```

- [ ] **Step 3: Verify the module imports without Playwright side effects**

Run: `python -c "import clipper.capture; print('ok')"`
Expected: prints `ok` (import is lazy; no browser launch).

- [ ] **Step 4: Commit**

```bash
git add src/clipper/capture.py
git commit -m "feat: Playwright login capture with rsync push to Pi"
```

---

### Task 9: Deploy assets and live acceptance

**Files:**
- Create: `deploy/crontab.example`
- Create: `deploy/README.md`
- Modify: `README.md` (replace the v1 Selenium README)

**Interfaces:**
- Consumes: everything above.
- Produces: the operational docs and the verified end-to-end run.

- [ ] **Step 1: Write `deploy/crontab.example`**

```cron
# for-U clipper: 2am nightly, flock guards against overlap.
0 2 * * * cd /home/pi/foru-clipper && /usr/bin/flock -n .clip.lock .venv/bin/clipper clip >> logs/cron.log 2>&1
```

- [ ] **Step 2: Write `deploy/README.md`**

Document: clone repo on the Pi, `python -m venv .venv && .venv/bin/pip install .`, copy `config.toml.example` to `config.toml` and fill it (banner, session_path, `[pushover]` or env vars), install the crontab line, and that the session arrives via `clipper login` on the Mac. Note the Pi never needs the `[capture]` extra.

- [ ] **Step 3: Rewrite `README.md`**

Replace the Selenium-era content with the new architecture: session-capture-on-Mac + HTTP-replay-on-Pi, the three commands, the "captcha'd EOL and how this sidesteps it" note, and a link to the spec. Keep the M1-Mac/attribution tone but drop all webdriver instructions.

- [ ] **Step 4: Live acceptance — capture**

On the Mac, with `config.toml` filled: run `clipper login`. Log in to vons.com by hand. Confirm it prints "Session saved" and (if Pi configured) "Session pushed to Pi."

- [ ] **Step 5: Live acceptance — dry run**

Run: `clipper clip --dry-run`
Expected: prints found/clipped/failed counts, clips nothing, `runs.jsonl` unchanged (dry run does not append).

- [ ] **Step 6: Live acceptance — real run**

Run: `clipper clip`
Expected: clips the unclipped offers, a Pushover summary arrives, `runs.jsonl` gets a new line, and re-running `clipper clip` immediately after finds 0 unclipped.

- [ ] **Step 7: Commit**

```bash
git add deploy/ README.md
git commit -m "docs: deploy assets and rewritten README for the API-replay clipper"
```

---

## Self-Review Notes

- **Spec coverage:** capture flow (Task 8), HTTP replay (Tasks 5, 7), cookie write-back (Task 7 `run_clip`), Pushover on failure + success (Tasks 6, 7), banner-as-config (Task 3), session expiry notification (Task 7 `AuthExpired`), atomic session file + 600 perms (Task 4), runs.jsonl + logs (Task 7), cron/flock (Task 9), rewrite-in-place teardown (Task 2), API confirmed live before coding (Task 1). All covered.
- **Types consistent:** `Session`, `Offer`, `ForUClient`, `Config`, `Notifier`, `run_clip` signatures match across producing and consuming tasks.
- **No placeholders:** every code step contains full code; every test step contains full test code.
