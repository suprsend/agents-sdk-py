from __future__ import annotations

import requests
from urllib.parse import quote

from suprsend_management.api.base import BaseApi, _DEFAULT_TIMEOUT
from suprsend_management.exception import SuprsendManagementException


class TemplatesApi(BaseApi):
    """
    Management API callers for v2/{ws}/template/ endpoints.
    """

    def _url(self, workspace: str, template_slug: str) -> str:
        return (
            f"{self.config.base_url}/v2/{quote(workspace, safe='')}/"
            f"template/{quote(template_slug, safe='')}/"
        )

    def validate(
        self,
        workspace: str,
        template_slug: str,
        payload: dict,
        extra_headers: dict | None = None,
    ) -> dict:
        """
        POST /v2/{ws}/template/{slug}/validate/
        Full end-to-end template validation — checks metadata and all variant content
        in a single call. No DB writes.
        Response includes `action` ("create"|"update"), `is_valid`, `template_group`, `variants`.
        """
        resp = requests.post(
            self._url(workspace, template_slug) + "validate/",
            headers=self._headers(extra_headers),
            json=payload,
            timeout=_DEFAULT_TIMEOUT,
        )
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()

    def upsert(
        self,
        workspace: str,
        template_slug: str,
        payload: dict,
        extra_headers: dict | None = None,
    ) -> dict:
        """
        POST /v2/{ws}/template/{slug}/
        Create or update template group metadata (name, description, enabled channels, tags).
        Returns 201 for create, 202 for update.
        """
        resp = requests.post(
            self._url(workspace, template_slug),
            headers=self._headers(extra_headers),
            json=payload,
            timeout=_DEFAULT_TIMEOUT,
        )
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()

    def upsert_variant_content(
        self,
        workspace: str,
        template_slug: str,
        channel: str,
        variant_id: str,
        content: dict,
        extra_headers: dict | None = None,
    ) -> dict:
        """
        PATCH /v2/{ws}/template/{slug}/channel/{channel}/variant/{variant_id}/content/
        Set or update channel-specific content for a variant.
        """
        url = (
            self._url(workspace, template_slug)
            + f"channel/{quote(channel, safe='')}/variant/{quote(variant_id, safe='')}/content/"
        )
        resp = requests.patch(
            url,
            headers=self._headers(extra_headers),
            json={"content": content},
            timeout=_DEFAULT_TIMEOUT,
        )
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()

    def validate_variant(
        self,
        workspace: str,
        template_slug: str,
        payload: dict,
        extra_headers: dict | None = None,
    ) -> dict:
        """
        POST /v2/{ws}/template/{slug}/validate_variant/
        Stateless per-channel content validation. No DB writes.
        """
        resp = requests.post(
            self._url(workspace, template_slug) + "validate_variant/",
            headers=self._headers(extra_headers),
            json=payload,
            timeout=_DEFAULT_TIMEOUT,
        )
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()

    def pre_commit_validate(
        self,
        workspace: str,
        template_slug: str,
        extra_headers: dict | None = None,
    ) -> dict:
        """
        POST /v2/{ws}/template/{slug}/pre_commit_validate/
        Full cross-channel draft validation with diff vs live version.
        Writes intermediate state to DB (draft only, not published).
        """
        resp = requests.post(
            self._url(workspace, template_slug) + "pre_commit_validate/",
            headers=self._headers(extra_headers),
            json={},
            timeout=_DEFAULT_TIMEOUT,
        )
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()

    def commit(
        self,
        workspace: str,
        template_slug: str,
        variants: list[dict],
        commit_message: str = "",
        extra_headers: dict | None = None,
    ) -> dict:
        """
        PATCH /v2/{ws}/template/{slug}/commit/
        Publish the current draft as the new live version.
        variants: list of {"channel": "...", "id": "..."} dicts.
        """
        params = {}
        if commit_message:
            params["commit_message"] = commit_message
        resp = requests.patch(
            self._url(workspace, template_slug) + "commit/",
            headers=self._headers(extra_headers),
            params=params or None,
            json={"variants": variants},
            timeout=_DEFAULT_TIMEOUT,
        )
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()
