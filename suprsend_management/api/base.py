from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from suprsend_management.client import SuprsendManagement

# Default timeout (seconds) for all management API requests.
# Keeps the asyncio.to_thread worker from blocking indefinitely.
_DEFAULT_TIMEOUT = 60


class BaseApi:
    def __init__(self, config: "SuprsendManagement") -> None:
        self.config = config

    def _headers(self, extra: dict | None = None) -> dict:
        h: dict = {"Content-Type": "application/json"}
        if self.config.auth:
            h.update(self.config.auth.get_headers())
        if extra:
            h.update(extra)
        return h
