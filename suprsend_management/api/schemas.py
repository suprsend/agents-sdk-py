from __future__ import annotations

import requests
from urllib.parse import quote

from suprsend_management.api.base import BaseApi, _DEFAULT_TIMEOUT
from suprsend_management.exception import SuprsendManagementException


class SchemasApi(BaseApi):
    """
    Management API callers for v1/{ws}/schema/ endpoints.
    """

    def _url(self, workspace: str, slug: str | None = None, suffix: str = "") -> str:
        base = f"{self.config.base_url}/v1/{quote(workspace, safe='')}/schema/"
        if slug:
            base += f"{quote(slug, safe='')}/"
        if suffix:
            base += f"{suffix}/"
        return base

    def list(
        self,
        workspace: str,
        mode: str = "draft",
        limit: int = 20,
        offset: int = 0,
        extra_headers: dict | None = None,
    ) -> dict:
        """
        GET /v1/{ws}/schema/ — list all trigger schemas.

        Args:
            workspace:     Workspace slug.
            mode:          "draft" or "live" (default "draft").
            limit:         Max results to return.
            offset:        Pagination offset.
            extra_headers: Additional headers merged into the request.

        Returns:
            Paginated JSON response — {"count": N, "results": [...]}.

        Raises:
            SuprsendManagementException: on 4xx / 5xx responses.
        """
        params: dict = {"mode": mode, "limit": limit, "offset": offset}
        resp = requests.get(
            self._url(workspace),
            headers=self._headers(extra_headers),
            params=params,
            timeout=_DEFAULT_TIMEOUT,
        )
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()

    def get(
        self,
        workspace: str,
        slug: str,
        mode: str = "draft",
        extra_headers: dict | None = None,
    ) -> dict:
        """
        GET /v1/{ws}/schema/{slug}/ — fetch a single trigger schema.

        Args:
            workspace:     Workspace slug.
            slug:          Schema slug.
            mode:          "draft" or "live" (default "draft").
            extra_headers: Additional headers merged into the request.

        Returns:
            Schema detail object including json_schema, status, version info.

        Raises:
            SuprsendManagementException: on 4xx / 5xx responses.
        """
        resp = requests.get(
            self._url(workspace, slug),
            headers=self._headers(extra_headers),
            params={"mode": mode},
            timeout=_DEFAULT_TIMEOUT,
        )
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()

    def push(
        self,
        workspace: str,
        slug: str,
        json_schema: dict,
        name: str = "",
        description: str = "",
        extra_headers: dict | None = None,
    ) -> dict:
        """
        POST /v1/{ws}/schema/{slug}/ — create or update a trigger schema draft.

        Always saves as draft. Use commit() to promote to live.

        Args:
            workspace:     Workspace slug.
            slug:          Schema slug (created if it does not exist).
            json_schema:   JSON Schema dict (must include "$schema", "type": "object", "properties").
            name:          Human-readable name (optional).
            description:   Description (optional).
            extra_headers: Additional headers merged into the request.

        Returns:
            Schema detail object with status, hash, and version info.

        Raises:
            SuprsendManagementException: on 4xx / 5xx responses.
        """
        body: dict = {"json_schema": json_schema}
        if name:
            body["name"] = name
        if description:
            body["description"] = description
        resp = requests.post(
            self._url(workspace, slug),
            headers=self._headers(extra_headers),
            json=body,
            timeout=_DEFAULT_TIMEOUT,
        )
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()

    def commit(
        self,
        workspace: str,
        slug: str,
        commit_message: str = "",
        extra_headers: dict | None = None,
    ) -> dict:
        """
        PATCH /v1/{ws}/schema/{slug}/commit/ — promote draft to live.

        Args:
            workspace:      Workspace slug.
            slug:           Schema slug.
            commit_message: Optional description of what changed.
            extra_headers:  Additional headers merged into the request.

        Returns:
            Committed schema detail object.

        Raises:
            SuprsendManagementException: on 4xx / 5xx responses.
        """
        body: dict = {}
        if commit_message:
            body["commit_message"] = commit_message
        resp = requests.patch(
            self._url(workspace, slug, suffix="commit"),
            headers=self._headers(extra_headers),
            json=body,
            timeout=_DEFAULT_TIMEOUT,
        )
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()
