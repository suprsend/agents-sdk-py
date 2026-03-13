from __future__ import annotations

import requests

from suprsend_management.api.base import BaseApi
from suprsend_management.exception import SuprsendManagementException


class TranslationsApi(BaseApi):
    """Management API callers for GET v1/{ws}/translation/content/{filename}/"""

    def _url(self, workspace: str, filename: str) -> str:
        return f"{self.config.base_url}/v1/{workspace}/translation/content/{filename}/"

    def get(self, workspace: str, filename: str, extra_headers: dict | None = None) -> dict:
        """
        Fetch the content of a translation file by filename.

        Args:
            workspace:     Workspace slug.
            filename:      The translation filename (e.g. 'en_common.json').
            extra_headers: Additional headers merged into the request.

        Returns:
            Parsed JSON response — translation content object.

        Raises:
            SuprsendManagementException: on 4xx / 5xx responses.
        """
        resp = requests.get(self._url(workspace, filename), headers=self._headers(extra_headers))
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()
