from __future__ import annotations

import requests
from urllib.parse import quote

from suprsend_management.api.base import BaseApi, _DEFAULT_TIMEOUT
from suprsend_management.exception import SuprsendManagementException


class PreferenceCategoriesApi(BaseApi):
    """Management API callers for GET/POST v1/{ws}/preference_category/"""

    def _url(self, workspace: str) -> str:
        return f"{self.config.base_url}/v1/{quote(workspace, safe='')}/preference_category/"

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
        resp = requests.get(self._url(workspace), headers=self._headers(extra_headers), timeout=_DEFAULT_TIMEOUT)
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()

    def update(self, workspace: str, root_categories: list,
               commit: bool = False, commit_message: str = "",
               extra_headers: dict | None = None) -> dict:
        """POST /v1/{workspace}/preference_category/ — full-override update of the preference category tree.

        This is a full override — all three root categories (system, transactional, promotional)
        must be present. Fetch the current state first with list(), modify the target category,
        then pass the complete tree here.

        Args:
            workspace:        Workspace slug.
            root_categories:  Full root_categories list (fetched + modified).
            commit:           If True, changes go live immediately.
            commit_message:   Required when commit=True.
            extra_headers:    Additional headers merged into the request.
        """
        params: dict = {}
        if commit:
            params["commit"] = "true"
            if commit_message:
                params["commit_message"] = commit_message
        resp = requests.post(
            self._url(workspace),
            json={"root_categories": root_categories},
            params=params or None,
            headers=self._headers(extra_headers),
            timeout=_DEFAULT_TIMEOUT,
        )
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()