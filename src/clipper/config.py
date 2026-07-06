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
    api_key: str = "emjou"
    ibm_client_id: str | None = None
    ibm_client_secret: str | None = None


def load_config(path: Path | None = None) -> Config:
    path = Path(path) if path else Path("config.toml")
    with open(path, "rb") as f:
        raw = tomllib.load(f)

    if "banner" not in raw:
        raise ValueError(f"Missing required config key 'banner' in {path}")
    banner = raw["banner"]
    if banner not in BANNER_BASE_URLS:
        raise ValueError(
            f"Unknown banner {banner!r}; expected one of "
            f"{sorted(BANNER_BASE_URLS)}"
        )

    if "session_path" not in raw:
        raise ValueError(f"Missing required config key 'session_path' in {path}")

    pushover = raw.get("pushover", {})
    pi = raw.get("pi", {})
    api = raw.get("api", {})
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
        api_key=api.get("key", "emjou"),
        ibm_client_id=api.get("ibm_client_id"),
        ibm_client_secret=api.get("ibm_client_secret"),
    )
