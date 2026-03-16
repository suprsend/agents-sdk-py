from __future__ import annotations

import requests

from suprsend_management.api.base import BaseApi
from suprsend_management.exception import SuprsendManagementException


class WorkflowsApi(BaseApi):
    """
    Management API callers for v1/{ws}/workflow/ endpoints.
    """

    def _url(self, workspace: str, workflow_slug: str | None = None) -> str:
        base = f"{self.config.base_url}/v1/{workspace}/workflow/"
        if workflow_slug:
            return f"{base}{workflow_slug}/"
        return base

    def list(
        self,
        workspace: str,
        search: str | None = None,
        slugs: list[str] | None = None,
        include_archived: bool = False,
        order_by: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
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
            limit:            Maximum number of results to return (max 50).
            offset:           Number of results to skip for pagination.
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
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

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

    def push(
        self,
        workspace: str,
        workflow_slug: str,
        workflow: dict,
        commit: bool = True,
        commit_message: str = "",
        extra_headers: dict | None = None,
    ) -> dict:
        """
        Create or update a workflow definition.

        POST {base_url}/v1/{workspace}/workflow/{slug}/?commit={commit}&commit_message={msg}
        Body: full workflow definition dict.
        Returns: {"validation_result": {"is_valid": bool, "errors": [...]}}
        """
        params = {"commit": "true" if commit else "false"}
        if commit_message:
            params["commit_message"] = commit_message
        resp = requests.post(
            self._url(workspace, workflow_slug),
            headers=self._headers(extra_headers),
            params=params,
            json=workflow,
        )
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()
