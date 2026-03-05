from __future__ import annotations
from abc import ABC, abstractmethod


class SuprSendAuth(ABC):
    """
    Base class for all auth strategies.
    Subclasses produce the Authorization headers needed for each request.
    The async HTTP client in client.py calls get_headers() before every
    outgoing request.
    """

    @abstractmethod
    def get_headers(self) -> dict[str, str]: ...


class ServiceTokenAuth(SuprSendAuth):
    """
    Standard auth for SDK users and service accounts.

    Uses a service token issued from the SuprSend dashboard.
    Header format: Authorization: ServiceToken {token}

    Safe to instantiate once and reuse across all tool calls.

        auth = ServiceTokenAuth(token="sst_...")
        toolkit = SuprSendToolkit(service_token="sst_...", workspace="my-workspace")
        # ServiceTokenAuth constructed internally
    """

    def __init__(self, token: str) -> None:
        self.token = token

    def get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"ServiceToken {self.token}",
            "Content-Type": "application/json",
        }


class JWTAuth(SuprSendAuth):
    """
    For per-user flows (e.g. the SuprSend Copilot).

    Takes a raw JWT string. Does not know or care where the token came
    from — use the factory class methods to extract it from request
    headers or cookies without manual parsing.

    Inside LangGraph:
        Token is forwarded via config.configurable.jwt_token and resolved
        automatically at tool call time. No manual construction needed.

    Outside LangGraph (route handlers, standalone agents):
        auth = JWTAuth(token="eyJ...")
        auth = JWTAuth.from_header("Bearer eyJ...")
        auth = JWTAuth.from_cookie(cookie_header, cookie_name="my-auth")
        auth = JWTAuth.from_request(
            authorization_header=..., cookie_header=..., cookie_name=...
        )
    """

    def __init__(self, token: str) -> None:
        self.token = token

    def get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    @classmethod
    def from_header(cls, authorization_header: str) -> "JWTAuth":
        """Extract from 'Bearer <token>' Authorization header."""
        parts = authorization_header.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return cls(token=parts[1])
        raise ValueError("Invalid Authorization header format. Expected: 'Bearer <token>'.")

    @classmethod
    def from_cookie(cls, cookie_header: str, cookie_name: str) -> "JWTAuth":
        """
        Extract from Cookie header by name. cookie_name is required — no default.

        If cookie_header has no '=' (i.e. it is a raw JWT string, not a
        key=value cookie), cookie_name is ignored and the whole value is used.
        """
        from urllib.parse import unquote
        cookie_header = cookie_header.strip()
        if "=" not in cookie_header:
            return cls(token=unquote(cookie_header))
        cookies = {
            k.strip(): v.strip()
            for part in cookie_header.split(";")
            if "=" in part
            for k, _, v in [part.partition("=")]
        }
        token = cookies.get(cookie_name)
        if not token:
            raise ValueError(f"Cookie '{cookie_name}' not found.")
        return cls(token=unquote(token))

    @classmethod
    def from_request(
        cls,
        authorization_header: str | None = None,
        cookie_header: str | None = None,
        cookie_name: str | None = None,
    ) -> "JWTAuth":
        """
        Try cookie first, fall back to Authorization header.
        cookie_name required for structured cookies; omit if cookie is a raw JWT.
        """
        if cookie_header:
            cookie_header = cookie_header.strip()
            if "=" not in cookie_header:
                from urllib.parse import unquote
                return cls(token=unquote(cookie_header))
            if cookie_name:
                try:
                    return cls.from_cookie(cookie_header, cookie_name=cookie_name)
                except ValueError:
                    pass
        if authorization_header:
            try:
                return cls.from_header(authorization_header)
            except ValueError:
                pass
        raise ValueError(
            "No JWT found. Checked "
            + (f"cookie '{cookie_name}' and " if cookie_name else "")
            + "Authorization header."
        )
