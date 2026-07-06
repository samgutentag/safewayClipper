from __future__ import annotations

import argparse
import json
import logging
import random
import sys
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
    try:
        session = load_session(config.session_path)
    except (FileNotFoundError, SessionError) as e:
        notifier.send(
            "for-U clipper: no valid session",
            f"Session file missing or invalid at {config.session_path}. "
            "Run `clipper login` on the Mac.",
            priority=1,
        )
        raise AuthExpired(str(e)) from e
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
    try:
        config = load_config(Path(args.config) if args.config else None)
    except (FileNotFoundError, ValueError) as e:
        print(f"Config error: {e}", file=sys.stderr)
        return 1

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
