from __future__ import annotations

from typing import TYPE_CHECKING

import requests

from suprsend_management.exception import SuprsendManagementException

if TYPE_CHECKING:
    from suprsend_management.client import SuprsendManagement


class PreferenceCategoriesApi:
    """
    Management API callers for GET v1/{ws}/notification_category/
    """

    def __init__(self, config: "SuprsendManagement") -> None:
        self.config = config

    def _url(self, workspace: str) -> str:
        return f"{self.config.base_url}/v1/{workspace}/preference_category/"

    def _headers(self, extra: dict | None = None) -> dict:
        h: dict = {"Content-Type": "application/json"}
        if self.config.auth:
            h.update(self.config.auth.get_headers())
        if extra:
            h.update(extra)
        return h

    def list(self, workspace: str, extra_headers: dict | None = None) -> dict:
        """
        List all notification/preference categories for a workspace.

        Args:
            workspace:     Workspace slug.
            extra_headers: Additional headers merged into the request.

        Returns:
            Parsed JSON response — {"meta": {...}, "results": [...]}.

        Raises:
            SuprsendManagementException: on 4xx / 5xx responses.
        """
        resp = requests.get(self._url(workspace), headers=self._headers(extra_headers))
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()
