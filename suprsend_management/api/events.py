from __future__ import annotations

import requests
from urllib.parse import quote

from suprsend_management.api.base import BaseApi, _DEFAULT_TIMEOUT
from suprsend_management.exception import SuprsendManagementException


class EventsApi(BaseApi):
    """Management API callers for GET v1/{ws}/event/{event_name}/"""

    def _url(self, workspace: str, event_name: str) -> str:
        return f"{self.config.base_url}/v1/{quote(workspace, safe='')}/event/{quote(event_name, safe='')}/"

    def link_schema(
        self,
        workspace: str,
        event_ref: str,
        schema_slug: str,
        version_no: int | None = None,
        extra_headers: dict | None = None,
    ) -> dict:
        """
        PATCH /v1/{ws}/event/{event_ref}/ — link a trigger schema to an event.

        Sets the event's payload_schema to the given schema slug. The link is
        created immediately (no commit step required for events).

        Args:
            workspace:     Workspace slug.
            event_ref:     Event name (slug).
            schema_slug:   Trigger schema slug to link.
            version_no:    Specific schema version to link (None = always use live version).
            extra_headers: Additional headers merged into the request.

        Returns:
            Updated event detail object.

        Raises:
            SuprsendManagementException: on 4xx / 5xx responses.
        """
        body = {"payload_schema": {"schema": schema_slug, "version_no": version_no}}
        resp = requests.patch(
            self._url(workspace, event_ref),
            headers=self._headers(extra_headers),
            json=body,
            timeout=_DEFAULT_TIMEOUT,
        )
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()

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
        resp = requests.get(self._url(workspace, event_name), headers=self._headers(extra_headers), timeout=_DEFAULT_TIMEOUT)
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()
