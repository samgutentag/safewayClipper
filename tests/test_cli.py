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
