import json
import urllib.parse
from pathlib import Path

import pytest
import responses

from clipper.config import Config
from clipper.session import Session
from clipper.api import ForUClient, Offer, AuthExpired, ClipError

BASE = "https://www.vons.com"


def _config():
    return Config(
        banner="vons",
        base_url=BASE,
        session_path=Path("unused.json"),
        api_key="emjou",
        ibm_client_id="cid",
        ibm_client_secret="csecret",
    )


def _session():
    return Session(
        cookies={
            "SWY_SHARED_SESSION": urllib.parse.quote(
                json.dumps({"accessToken": "tok"})
            ),
            "SWY_SHARED_SESSION_INFO": urllib.parse.quote(
                json.dumps({"info": {"J4U": {"storeId": "3326"}}})
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
def test_get_offers_parses_and_sends_bearer_auth():
    responses.add(
        responses.GET,
        f"{BASE}/abs/pub/xapi/offers/companiongalleryoffer",
        json=OFFERS_BODY,
        status=200,
    )
    client = ForUClient(_config(), _session())
    offers = client.get_offers()
    assert [o.offer_id for o in offers] == ["1", "2"]
    assert offers[0].is_unclipped() is True
    assert offers[1].is_unclipped() is False
    req = responses.calls[0].request
    assert req.headers["Authorization"] == "Bearer tok"
    assert req.headers["X-SWY_VERSION"] == "1.1"
    assert req.headers["X-SWY_API_KEY"] == "emjou"
    assert req.headers["X-SWY_BANNER"] == "vons"
    assert "includeRedmBonusPathFPOffers=true" in req.url
    assert "storeId=3326" in req.url


@responses.activate
def test_get_offers_401_raises_authexpired():
    responses.add(
        responses.GET,
        f"{BASE}/abs/pub/xapi/offers/companiongalleryoffer",
        status=401,
    )
    with pytest.raises(AuthExpired):
        ForUClient(_config(), _session()).get_offers()


@responses.activate
def test_clip_sends_sso_token_and_ibm_creds_not_bearer():
    responses.add(
        responses.POST,
        f"{BASE}/abs/pub/web/j4u/api/offers/clip",
        json={"items": [{"status": 1}, {"status": 1}]},
        status=200,
    )
    client = ForUClient(_config(), _session())
    client.clip(Offer("79317412", "U", "Milk", "MF"))
    req = responses.calls[0].request
    # clip auth is sso-token + IBM gateway, NOT Authorization bearer
    assert req.headers["swy_sso_token"] == "tok"
    assert req.headers["x-swyconsumerdirectorypro"] == "tok"
    assert req.headers["x-ibm-client-id"] == "cid"
    assert req.headers["x-ibm-client-secret"] == "csecret"
    assert req.headers["X-SWY_VERSION"] == "1.0"
    assert "Authorization" not in req.headers
    assert "x-swy-correlation-id" in req.headers
    body = json.loads(req.body)
    assert {i["clipType"] for i in body["items"]} == {"C", "L"}
    assert all(i["itemId"] == "79317412" and i["itemType"] == "MF" for i in body["items"])


@responses.activate
def test_clip_unsuccessful_body_raises():
    responses.add(
        responses.POST,
        f"{BASE}/abs/pub/web/j4u/api/offers/clip",
        json={"items": [{"status": 0}]},
        status=200,
    )
    with pytest.raises(ClipError):
        ForUClient(_config(), _session()).clip(Offer("1", "U", "Milk", "SC"))


@responses.activate
def test_clip_401_raises_authexpired():
    responses.add(
        responses.POST,
        f"{BASE}/abs/pub/web/j4u/api/offers/clip",
        status=403,
    )
    with pytest.raises(AuthExpired):
        ForUClient(_config(), _session()).clip(Offer("1", "U", "Milk", "SC"))
