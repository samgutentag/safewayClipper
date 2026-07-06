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
    print("If prompted, check your email for a one-time verification code and enter it. Waiting up to 5 minutes for a completed sign-in...")

    cookies: dict[str, str] = {}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            try:
                context = browser.new_context()
                page = context.new_page()
                page.goto(sign_in_url)

                print("Waiting for sign-in to complete (up to 5 minutes)...")
                for _ in range(300):
                    jar = {c["name"]: c["value"] for c in context.cookies()}
                    if all(name in jar for name in REQUIRED_COOKIES):
                        cookies = jar
                        break
                    page.wait_for_timeout(1000)
            finally:
                browser.close()
    except Exception as e:
        print(f"Login capture failed: {e}")
        return 1

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
        try:
            result = subprocess.run(
                [
                    "rsync",
                    "-az",
                    "-e",
                    "ssh -o BatchMode=yes -o ConnectTimeout=10",
                    str(config.session_path),
                    dest,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            print("rsync timed out after 60s; Pi may be unreachable.")
            return 1
        if result.returncode != 0:
            print(f"rsync failed: {result.stderr.strip()}")
            return 1
        print("Session pushed to Pi.")
    else:
        print("No Pi configured; session left local only.")

    return 0
