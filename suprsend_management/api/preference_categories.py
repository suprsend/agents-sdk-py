from __future__ import annotations

import requests

from suprsend_management.api.base import BaseApi
from suprsend_management.exception import SuprsendManagementException


class PreferenceCategoriesApi(BaseApi):
    """
    Management API callers for GET v1/{ws}/notification_category/
    """

    def _url(self, workspace: str) -> str:
        return f"{self.config.base_url}/v1/{workspace}/preference_category/"

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
