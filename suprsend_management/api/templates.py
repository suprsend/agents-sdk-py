from __future__ import annotations

import requests
from urllib.parse import quote

from suprsend_management.api.base import BaseApi, _DEFAULT_TIMEOUT
from suprsend_management.exception import SuprsendManagementException


class TemplatesApi(BaseApi):
    """
    Management API callers for v2/{ws}/template/ endpoints.
    """

    def _url(self, workspace: str, template_slug: str | None = None) -> str:
        base = f"{self.config.base_url}/v2/{quote(workspace, safe='')}/template/"
        if template_slug:
            return f"{base}{quote(template_slug, safe='')}/"
        return base

    def list(
        self,
        workspace: str,
        search: str | None = None,
        slugs: list[str] | None = None,
        mode: str = "draft",
        order_by: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        extra_headers: dict | None = None,
    ) -> dict:
        """GET /v2/{ws}/template/"""
        params: dict = {"mode": mode}
        if search:
            params["search"] = search
        if slugs:
            params["slugs"] = ",".join(slugs)
        if order_by:
            params["order_by"] = order_by
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
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
        template_slug: str,
        mode: str = "draft",
        extra_headers: dict | None = None,
    ) -> dict:
        """GET /v2/{ws}/template/{slug}/"""
        resp = requests.get(
            self._url(workspace, template_slug),
            headers=self._headers(extra_headers),
            params={"mode": mode},
            timeout=_DEFAULT_TIMEOUT,
        )
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()

    def list_variants(
        self,
        workspace: str,
        template_slug: str,
        mode: str = "draft",
        channel: str | None = None,
        include_content: bool = False,
        extra_headers: dict | None = None,
    ) -> dict:
        """GET /v2/{ws}/template/{slug}/variant/"""
        params: dict = {"mode": mode}
        if channel:
            params["channel[]"] = channel
        if include_content:
            params["include_content"] = "true"
        resp = requests.get(
            self._url(workspace, template_slug) + "variant/",
            headers=self._headers(extra_headers),
            params=params,
            timeout=_DEFAULT_TIMEOUT,
        )
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()

    def get_variant_content(
        self,
        workspace: str,
        template_slug: str,
        channel: str,
        variant_id: str = "default",
        mode: str = "draft",
        extra_headers: dict | None = None,
    ) -> dict:
        """GET /v2/{ws}/template/{slug}/channel/{channel}/variant/{variant_id}/content/"""
        url = (
            self._url(workspace, template_slug)
            + f"channel/{quote(channel, safe='')}/variant/{quote(variant_id, safe='')}/content/"
        )
        resp = requests.get(
            url,
            headers=self._headers(extra_headers),
            params={"mode": mode},
            timeout=_DEFAULT_TIMEOUT,
        )
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()

    def list_versions(
        self,
        workspace: str,
        template_slug: str,
        extra_headers: dict | None = None,
    ) -> list:
        """GET /v2/{ws}/template/{slug}/version/"""
        resp = requests.get(
            self._url(workspace, template_slug) + "version/",
            headers=self._headers(extra_headers),
            timeout=_DEFAULT_TIMEOUT,
        )
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()

    def get_mock_data(
        self,
        workspace: str,
        template_slug: str,
        mode: str = "draft",
        extra_headers: dict | None = None,
    ) -> dict:
        """GET /v2/{ws}/template/{slug}/mock_data/"""
        resp = requests.get(
            self._url(workspace, template_slug) + "mock_data/",
            headers=self._headers(extra_headers),
            params={"mode": mode},
            timeout=_DEFAULT_TIMEOUT,
        )
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()

    def update_mock_data(
        self,
        workspace: str,
        template_slug: str,
        data: dict,
        extra_headers: dict | None = None,
    ) -> dict:
        """PATCH /v2/{ws}/template/{slug}/mock_data/"""
        resp = requests.patch(
            self._url(workspace, template_slug) + "mock_data/",
            headers=self._headers(extra_headers),
            json={"data": data},
            timeout=_DEFAULT_TIMEOUT,
        )
        if resp.status_code >= 400:
            raise SuprsendManagementException(resp)
        return resp.json()

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

    def upsert_variant(
        self,
        workspace: str,
        template_slug: str,
        channel: str,
        variant_id: str,
        payload: dict,
        extra_headers: dict | None = None,
    ) -> dict:
        """
        POST /v2/{ws}/template/{slug}/channel/{channel}/variant/{variant_id}/
        Create or update a variant. Creates the variant record if variant_id does not exist;
        updates it if found. Required: locale. Optional: tenant_id, conditions,
        needs_vendor_approval, content.
        Returns 201 for create, 202 for update.
        """
        url = (
            self._url(workspace, template_slug)
            + f"channel/{quote(channel, safe='')}/variant/{quote(variant_id, safe='')}/"
        )
        resp = requests.post(
            url,
            headers=self._headers(extra_headers),
            json=payload,
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
