from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

import requests

from .config import Config
from .session import Session

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15"
)


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
    def __init__(self, config: Config, session: Session) -> None:
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.session = session
        self._token = session.access_token()
        self._store_id = session.store_id()
        self._http = requests.Session()
        for name, value in session.cookies.items():
            self._http.cookies.set(name, value)
        self._http.headers.update({"User-Agent": USER_AGENT, "DNT": "1"})

    def _raise_if_auth(self, resp: requests.Response) -> None:
        if resp.status_code in (401, 403):
            raise AuthExpired(f"HTTP {resp.status_code} from {resp.url}")

    def get_offers(self) -> list[Offer]:
        url = f"{self.base_url}/abs/pub/xapi/offers/companiongalleryoffer"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
            "Content-Type": "application/vnd.safeway.v2+json",
            "X-SWY_API_KEY": self.config.api_key,
            "X-SWY_BANNER": self.config.banner,
            "X-SWY_VERSION": "1.1",
            "X-SWY-APPLICATION-TYPE": "web",
        }
        resp = self._http.get(
            url,
            params={
                "storeId": self._store_id,
                "rand": "654321",
                "includeRedmBonusPathFPOffers": "true",
            },
            headers=headers,
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
        headers = {
            "swy_sso_token": self._token,
            "x-swyconsumerdirectorypro": self._token,
            "x-ibm-client-id": self.config.ibm_client_id or "",
            "x-ibm-client-secret": self.config.ibm_client_secret or "",
            "x-swy-correlation-id": str(uuid.uuid4()),
            "X-SWY_API_KEY": self.config.api_key,
            "X-SWY_BANNER": self.config.banner,
            "X-SWY_VERSION": "1.0",
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": self.base_url,
        }
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
            headers=headers,
        )
        self._raise_if_auth(resp)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if not items or not all(i.get("status") == 1 for i in items):
            raise ClipError(f"Unsuccessful clip for {offer.offer_id}")

    def refreshed_cookies(self) -> dict[str, str]:
        return {c.name: c.value for c in self._http.cookies}
