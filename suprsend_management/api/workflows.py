from __future__ import annotations

from typing import TYPE_CHECKING

import requests

from suprsend_management.exception import SuprsendManagementException

if TYPE_CHECKING:
    from suprsend_management.client import SuprsendManagement


class WorkflowsApi:
    """
    Management API callers for v1/{ws}/workflow/ endpoints.
    """

    def __init__(self, config: "SuprsendManagement") -> None:
        self.config = config

    def _url(self, workspace: str, workflow_slug: str | None = None) -> str:
        base = f"{self.config.base_url}/v1/{workspace}/workflow/"
        if workflow_slug:
            return f"{base}{workflow_slug}/"
        return base

    def _headers(self, extra: dict | None = None) -> dict:
        h: dict = {"Content-Type": "application/json"}
        if self.config.auth:
            h.update(self.config.auth.get_headers())
        if extra:
            h.update(extra)
        return h

    def list(
        self,
        workspace: str,
        search: str | None = None,
        slugs: list[str] | None = None,
        include_archived: bool = False,
        order_by: str | None = None,
        extra_headers: dict | None = None,
    ) -> dict:
        """
        List workflows for a workspace.

        Args:
            workspace:        Workspace slug.
            search:           Text search on workflow name, slug, or description.
            slugs:            Filter to specific workflow slugs (OR logic).
            include_archived: When True, include archived workflows (default False).
            order_by:         Sort order — one of "last_executed_at", "-last_executed_at",
                              "updated_at", "-updated_at".
            extra_headers:    Additional headers merged into the request.

        Returns:
            Paginated JSON response — {"count": N, "results": [...]}.

        Raises:
            SuprsendManagementException: on 4xx / 5xx responses.
        """
        params: dict = {}
        if search:
            params["search"] = search
        if slugs:
            params["slugs"] = ",".join(slugs)
        if include_archived:
            params["include_archived"] = "true"
        if order_by:
            params["order_by"] = order_by

        resp = requests.get(
            self._url(workspace),
            headers=self._headers(extra_headers),
            params=params or None,
        )
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()

    def get(
        self,
        workspace: str,
        workflow_slug: str,
        extra_headers: dict | None = None,
    ) -> dict:
        """
        Fetch a single workflow by slug.

        Args:
            workspace:      Workspace slug.
            workflow_slug:  The workflow identifier.
            extra_headers:  Additional headers merged into the request.

        Returns:
            Parsed JSON response — workflow detail object.

        Raises:
            SuprsendManagementException: on 4xx / 5xx responses.
        """
        resp = requests.get(
            self._url(workspace, workflow_slug),
            headers=self._headers(extra_headers),
        )
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()
