import json
import urllib.parse
from pathlib import Path
import pytest
import responses
from clipper.api import AuthExpired
from clipper.cli import main, run_clip
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
        ibm_client_id="cid",
        ibm_client_secret="csecret",
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


@responses.activate
def test_run_clip_missing_session_notifies_and_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    responses.add(
        responses.POST,
        "https://api.pushover.net/1/messages.json",
        json={"status": 1},
        status=200,
    )
    config = Config(
        banner="vons",
        base_url=BASE,
        session_path=tmp_path / "missing-session.json",
        notify_on_success=False,
        ibm_client_id="cid",
        ibm_client_secret="csecret",
        pushover_token="tok",
        pushover_user="user",
    )
    with pytest.raises(AuthExpired):
        run_clip(config, dry_run=False, sleep_fn=lambda s: None)

    pushover_calls = [
        c for c in responses.calls if "api.pushover.net" in c.request.url
    ]
    assert len(pushover_calls) == 1
    body = pushover_calls[0].request.body
    if isinstance(body, bytes):
        body = body.decode()
    assert "priority=1" in body


def test_main_bad_config_returns_1(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = main(["--config", str(tmp_path / "nonexistent.toml"), "clip"])
    assert rc == 1
