from __future__ import annotations


class SuprsendManagement:
    """
    Management API client for https://management-api.suprsend.com.

    Can be used standalone (auth provided at init) or with injected headers
    per-call (used by agents-sdk-py tools).

    Standalone with service token:
        from suprsend_management import SuprsendManagement
        from suprsend_agents_toolkit.auth import ServiceTokenAuth

        mgmt = SuprsendManagement(auth=ServiceTokenAuth("sst_..."))
        mgmt.preference_categories.list("my-workspace")
        mgmt.workflows.list("my-workspace", status=["active"])

    Injected auth (used internally by agents-sdk-py ManagementTool):
        mgmt = SuprsendManagement()    # no auth at init
        mgmt.workflows.list("my-workspace", extra_headers={...})
    """

    def __init__(
        self,
        base_url: str = "https://management-api.suprsend.com",
        auth=None,
    ) -> None:
        """
        Args:
            base_url:  Management API base URL. Override for staging/self-hosted.
            auth:      Optional auth object with a .get_headers() -> dict method.
                       Supported: ServiceTokenAuth, JWTAuth from suprsend_agents_toolkit.auth.
                       When None, no auth headers are added — pass extra_headers per call.
        """
        self.base_url = base_url.rstrip("/")
        self.auth = auth

        from suprsend_management.api.preference_categories import PreferenceCategoriesApi
        from suprsend_management.api.workflows import WorkflowsApi
        from suprsend_management.api.events import EventsApi
        from suprsend_management.api.translations import TranslationsApi

        self.preference_categories = PreferenceCategoriesApi(self)
        self.workflows = WorkflowsApi(self)
        self.events = EventsApi(self)
        self.translations = TranslationsApi(self)
