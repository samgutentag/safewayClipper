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
        try:
            data = json.load(f)
            return Session(
                cookies=data["cookies"],
                captured_at=data["captured_at"],
                last_used=data.get("last_used"),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise SessionError(f"Malformed session file {path}: {e}") from e


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
