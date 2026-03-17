from __future__ import annotations

import requests

from suprsend_management.api.base import BaseApi
from suprsend_management.exception import SuprsendManagementException


class EventsApi(BaseApi):
    """Management API callers for GET v1/{ws}/event/{event_name}/"""

    def _url(self, workspace: str, event_name: str) -> str:
        return f"{self.config.base_url}/v1/{workspace}/event/{event_name}/"

    def get(self, workspace: str, event_name: str, extra_headers: dict | None = None) -> dict:
        """
        Fetch details of a single event by name.

        Args:
            workspace:     Workspace slug.
            event_name:    The event name (slug) to fetch.
            extra_headers: Additional headers merged into the request.

        Returns:
            Parsed JSON response — event detail object.

        Raises:
            SuprsendManagementException: on 4xx / 5xx responses.
        """
        resp = requests.get(self._url(workspace, event_name), headers=self._headers(extra_headers))
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()
