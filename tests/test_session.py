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


def test_malformed_session_raises_sessionerror(tmp_path):
    p = tmp_path / "session.json"
    p.write_text("{not json")
    with pytest.raises(SessionError):
        load_session(p)


def test_missing_key_raises_sessionerror(tmp_path):
    p = tmp_path / "session.json"
    p.write_text("{}")
    with pytest.raises(SessionError):
        load_session(p)
