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
